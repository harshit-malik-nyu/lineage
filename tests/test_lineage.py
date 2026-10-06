"""
Tests for the lineage analysis.

Several pin a correction. The raw licence-mismatch rate is 20.9% and sounds
alarming; the share where a leaf actually claims more than its ancestor grants
is 0.2%. Reporting the first as a violation count would have been a real
overclaim, and these keep the distinction from eroding.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from lineage.analyse import (
    NAMED_RESTRICTIVE, PERMISSIVENESS, analyse, classify_licence_pair,
)

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def chains():
    p = ROOT / "evidence" / "derivatives.json"
    if not p.exists():
        pytest.skip("no collected data")
    return json.loads(p.read_text())


class TestLicenceClassification:

    def test_identical_licences_are_consistent(self):
        cat, _ = classify_licence_pair("apache-2.0", "apache-2.0")
        assert cat == "consistent"

    def test_relicensing_mit_under_apache_is_permitted(self):
        """
        Both permit relicensing under more restrictive terms, so this is
        ordinary and correct. Counting it as a mismatch is what inflates the
        naive figure.
        """
        cat, _ = classify_licence_pair("apache-2.0", "mit")
        assert cat in ("consistent", "narrows")

    def test_claiming_apache_over_a_llama_ancestor_widens(self):
        cat, note = classify_licence_pair("apache-2.0", "llama3.2")
        assert cat == "widens"
        assert "does not grant" in note

    def test_narrowing_is_not_flagged(self):
        cat, _ = classify_licence_pair("cc-by-nc-4.0", "apache-2.0")
        assert cat == "narrows"

    def test_other_is_not_rankable(self):
        """
        "other" is a text box covering everything from a bespoke research
        licence to an unfilled form. Nothing can be concluded from it, and
        pretending otherwise is where the naive count goes wrong.
        """
        assert classify_licence_pair("apache-2.0", "other")[0] == "unrankable"
        assert classify_licence_pair("other", "apache-2.0")[0] == "unrankable"

    def test_named_restrictive_licences_are_not_in_the_rankable_set(self):
        """
        Llama and Gemma terms are judged by name rather than by rank, because
        their restrictions are not a point on a permissiveness scale.
        """
        for lic in ("gemma", "llama3.2"):
            assert lic in NAMED_RESTRICTIVE
            assert lic not in PERMISSIVENESS


class TestMeasuredFindings:

    def test_concentration_is_higher_by_downloads_than_by_count(self, chains):
        """
        THE FINDING. Counting derivatives understates it: the top three orgs
        are 57.2% of models and 67.8% of downloads. Weighting by use moves it
        ten points in the direction that matters.
        """
        a = analyse(chains)
        c = a.concentration(3)
        assert c["share_of_downloads"] > c["share_of_derivatives"]
        assert c["share_of_downloads"] > 0.6

    def test_most_chains_pass_through_an_intermediary_or_are_direct(self, chains):
        a = analyse(chains)
        assert 0.3 < a.through_intermediary < 0.6

    def test_chains_reach_real_depth(self, chains):
        """
        An intermediary is usually a third party's re-upload, so a consumer of
        the leaf inherits from someone whose name is not on the model they
        chose.
        """
        a = analyse(chains)
        assert max(a.depths) >= 4

    def test_actual_licence_widening_is_rare(self, chains):
        """
        REGRESSION on an overclaim. The raw mismatch rate is about 21%; the
        share where a leaf claims terms its ancestor does not grant is under
        1%. The difference is entirely in doing the licence reasoning rather
        than counting string inequality.
        """
        a = analyse(chains)
        d = a.as_dict()
        assert d["widening_count"] / d["chains"] < 0.02

    def test_raw_mismatch_would_have_been_far_higher(self, chains):
        """
        Pins the gap itself, so a future simplification that reintroduces the
        naive count fails here rather than quietly inflating the result.
        """
        raw = 0
        for w in chains:
            leaf = w.get("license")
            root = None
            for node in reversed(w.get("chain") or []):
                if node.get("resolved") and node.get("license"):
                    root = node["license"]
                    break
            if leaf and root and leaf != root:
                raw += 1
        a = analyse(chains)
        assert raw > 10 * a.as_dict()["widening_count"]

    def test_the_ecosystem_has_many_roots_but_few_that_matter(self, chains):
        a = analyse(chains)
        assert a.as_dict()["distinct_root_orgs"] > 40
        assert a.concentration(3)["share_of_derivatives"] > 0.5


class TestDataQuality:

    def test_cycles_are_recorded_not_swallowed(self, chains):
        """
        Two models can declare each other through a re-upload. That is a
        data-quality finding, not an error to ignore.
        """
        a = analyse(chains)
        assert "cycles" in a.as_dict()

    def test_unresolved_parents_are_counted(self, chains):
        a = analyse(chains)
        assert a.as_dict()["unresolved_parents"] >= 0

    def test_undeclared_licences_are_their_own_category(self, chains):
        """
        A model with no licence is not the same as one whose licence matches,
        and folding them together would inflate the consistent share.
        """
        a = analyse(chains)
        assert "undeclared" in a.as_dict()["licence_categories"]
