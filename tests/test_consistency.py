"""
Every headline figure in the README must regenerate from the committed data.

This matters more here than in most of these projects, because the data is
collected rather than computed: a larger collection changes every number at
once, and a README written against a 400-chain sample silently becomes a
README about a sample that no longer exists.

These recompute from `evidence/derivatives.json` and assert the document
matches. If a collection run changes the figures, these fail — which is the
intent. The failure is the notification.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from lineage.analyse import analyse
from lineage.blast import broad_only, compute, union_exposure

ROOT = Path(__file__).resolve().parents[1]


def readme() -> str:
    return (ROOT / "README.md").read_text()


@pytest.fixture(scope="module")
def chains():
    p = ROOT / "evidence" / "derivatives.json"
    if not p.exists():
        pytest.skip("no collected data")
    return json.loads(p.read_text())


def cites_pct(text: str, value: float, tol: float = 0.011) -> bool:
    """
    Does the document quote this figure as a percentage or as points?

    A gap written as "25.7 points" is the same claim as "25.7%" and is the
    right way to write a difference between two percentages. Matching only
    the % sign made a correct document fail.
    """
    for m in re.finditer(r"([0-9]+\.?[0-9]*)\s*(?:%|points?)", text):
        if abs(float(m.group(1)) / 100 - value) <= tol:
            return True
    return False


def cites_int(text: str, value: int) -> bool:
    for m in re.finditer(r"([0-9][0-9,]*)", text):
        try:
            if int(m.group(1).replace(",", "")) == value:
                return True
        except ValueError:
            continue
    return False


class TestConcentrationFigures:

    def test_sample_size_is_current(self, chains):
        assert cites_int(readme(), len(chains)), \
            f"README does not state the current chain count ({len(chains)})"

    def test_top3_shares_are_current(self, chains):
        c = analyse(chains).concentration(3)
        t = readme()
        assert cites_pct(t, c["share_of_derivatives"])
        assert cites_pct(t, c["share_of_downloads"])

    def test_distinct_root_orgs_is_current(self, chains):
        assert cites_int(readme(), analyse(chains).as_dict()["distinct_root_orgs"])

    def test_use_weighting_exceeds_count_weighting(self, chains):
        """
        The direction the whole concentration argument rests on. If a larger
        sample ever reverses it, the README's framing is wrong and this is
        where that surfaces.
        """
        c = analyse(chains).concentration(3)
        assert c["share_of_downloads"] > c["share_of_derivatives"]


class TestDepthFigures:

    def test_intermediary_share_is_current(self, chains):
        assert cites_pct(readme(), analyse(chains).through_intermediary)

    def test_max_depth_is_current(self, chains):
        assert cites_int(readme(), analyse(chains).as_dict()["max_depth"])


class TestLicenceFigures:

    def test_the_categories_are_current(self, chains):
        d = analyse(chains).as_dict()
        t = readme()
        total = d["chains"]
        for name in ("consistent", "narrows", "widens"):
            n = d["licence_categories"].get(name, 0)
            assert cites_int(t, n) or cites_pct(t, n / total), \
                f"licence category {name} ({n}) not reflected in README"

    def test_the_naive_rate_is_still_far_higher(self, chains):
        """
        REGRESSION on the overclaim. Counting string inequality gives one
        number; reading what the licences permit gives another an order of
        magnitude smaller. If a change collapses that gap, the correction has
        been undone.
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
        widens = analyse(chains).as_dict()["widening_count"]
        assert raw > 10 * max(widens, 1)

        # Both denominators must appear, because the two differ and quoting
        # one without saying which is how 20.9% and 18.8% become the same
        # claim in a reader's memory.
        both_known = sum(
            1 for w in chains
            if w.get("license") and any(
                n.get("resolved") and n.get("license")
                for n in (w.get("chain") or [])))
        t = readme()
        assert cites_pct(t, raw / len(chains), tol=0.005), "share of ALL chains missing"
        assert cites_pct(t, raw / both_known, tol=0.005), "share of BOTH-DECLARED missing"
        assert str(both_known) in t, "the both-declared denominator is not stated"


class TestBlastFigures:

    def test_the_broadest_node_is_current(self, chains):
        b = broad_only(compute(chains))
        assert b, "no broad nodes"
        t = readme()
        assert b[0].node.split("/")[-1] in t or b[0].node in t
        assert cites_int(t, b[0].descendants)
        assert cites_pct(t, b[0].share_of_downloads)

    def test_the_union_figure_is_current(self, chains):
        b = broad_only(compute(chains))
        u = union_exposure(chains, [x.node for x in b[:5]])
        assert cites_pct(readme(), u["share_of_downloads"])


class TestDocumentIntegrity:

    def test_internal_links_resolve(self):
        for name in ("README.md", "docs/against.md"):
            p = ROOT / name
            for m in re.finditer(r"\[([^\]]+)\]\(([^)]+)\)", p.read_text()):
                target = m.group(2).split("#")[0]
                if target.startswith(("http", "mailto:")) or not target:
                    continue
                assert (p.parent / target).resolve().exists()

    def test_against_leads_with_the_sampling_problem(self):
        """
        A sample selected on downloads used to make a claim about downloads.
        That has to be first, not buried under six smaller objections.

        The assertion changed when the objection stopped being hypothetical.
        It originally required the phrase "most serious objection"; the
        argument is now quantified, so what must be present is the
        measurement and the statement of what it costs.
        """
        t = (ROOT / "docs" / "against.md").read_text()
        head = t[:t.index("## 2.")]
        # Normalised, because prose wraps and a check that fires on a line
        # break teaches people to ignore it.
        flat = " ".join(head.split())
        assert "popularity is exactly what the concentration finding measures" in flat, \
            "argument 1 must state the circularity"
        assert "quantified" in flat, "argument 1 should carry its measurement"
        assert "68.0%" in flat and "34.2%" in flat, "the range should be stated"
        assert "What it costs" in flat

    def test_blast_figures_are_marked_as_an_upper_bound(self):
        t = readme() + (ROOT / "docs" / "against.md").read_text()
        assert "upper bound" in t

    def test_the_licence_result_is_not_called_a_violation_rate(self):
        """
        0.2% is a count of leaves claiming more than an ancestor grants. It is
        not a legal finding and the documents must not read as one.
        """
        t = readme()
        assert "not a legal finding" in (ROOT / "docs" / "against.md").read_text()
        assert "violation rate" not in t.lower() or "wrong" in t.lower()


class TestTwoSampleFigures:
    """
    The comparison figures moved twice — once when the recency sample grew from
    245 to 1,500, and once when the verdict stopped judging on model count
    alone. Both times the README carried stale numbers until a test said so.
    """

    @pytest.fixture(scope="class")
    def both(self):
        a = ROOT / "evidence" / "derivatives.json"
        b = ROOT / "evidence" / "unbiased.json"
        if not (a.exists() and b.exists()):
            pytest.skip("both samples required")
        return json.loads(a.read_text()), json.loads(b.read_text())

    def test_both_sample_sizes_are_stated(self, both):
        pop, rec = both
        t = readme()
        assert cites_int(t, len(pop)) and cites_int(t, len(rec))

    def test_the_model_count_shares_are_current(self, both):
        from lineage.compare import compare
        pop, rec = both
        c = compare(pop, rec)
        t = readme()
        assert cites_pct(t, c["popularity"]["top3_share_of_derivatives"])
        assert cites_pct(t, c["recency"]["top3_share_of_derivatives"])

    def test_the_download_shares_are_current(self, both):
        from lineage.compare import compare
        pop, rec = both
        c = compare(pop, rec)
        t = readme()
        assert cites_pct(t, c["popularity"]["top3_share_of_downloads"])
        assert cites_pct(t, c["recency"]["top3_share_of_downloads"])

    def test_the_download_gap_is_reported_as_the_large_one(self, both):
        """
        Judging these samples on model count alone would call them agreed.
        The README has to carry the download gap, which is five times larger.
        """
        from lineage.compare import compare
        pop, rec = both
        c = compare(pop, rec)
        assert abs(c["gap_top3_downloads"]) > abs(c["gap_top3_share"]) * 3
        assert cites_pct(readme(), abs(c["gap_top3_downloads"]), tol=0.02)

    def test_the_significance_check_figure_is_current(self, both):
        from lineage.compare import is_the_gap_sample_size
        pop, rec = both
        r = is_the_gap_sample_size(pop, rec, trials=60)
        assert not r["inside_range"]
        assert cites_int(readme(), round(abs(r["sd_from_mean"]))) or \
            f"{abs(r['sd_from_mean']):.1f}" in readme()

    def test_the_window_correction_is_recorded(self):
        """
        The README once reported a fifteen-point gap from a two-day window.
        The correction has to stay visible, not be quietly replaced.
        """
        t = readme()
        assert "was wrong" in t
        assert "60.8%" in t and "window width" in t

    def test_no_trend_is_claimed(self):
        """
        Two adjacent months is a comparison, not a trend. A line fitted to two
        points — one of which has not finished accumulating downloads — is the
        easiest wrong claim available here.

        The assertion changed when the historical sample arrived: the document
        no longer says "single month" because it now has two, and what it must
        say instead is that two cannot separate a trend from maturation.
        """
        flat = " ".join(readme().split())
        assert "comparison rather than a trend" in flat
        assert "cohorts old enough to have matured equally" in flat

    def test_the_withdrawn_claim_stays_withdrawn(self):
        """
        The 25.7-point download gap was the project's most quotable number and
        it does not survive removing three models from each side. The
        withdrawal has to sit beside the figure, not in a later section a
        quoting reader never reaches.
        """
        flat = " ".join(readme().split())
        i = flat.index("25.7 points")
        nearby = flat[i:i + 900]
        assert "does not survive inspection" in nearby
        assert "49.5%" in nearby
        assert "does not hold" in nearby
