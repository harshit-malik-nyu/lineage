"""
Tests for the two-sample comparison.

The central one pins a result I predicted backwards. I expected the
popularity-selected sample to be the more concentrated one; the
recency-selected sample is more concentrated by fifteen points.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from lineage.compare import compare, summarise

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def samples():
    a = ROOT / "evidence" / "derivatives.json"
    b = ROOT / "evidence" / "unbiased.json"
    if not (a.exists() and b.exists()):
        pytest.skip("both samples required")
    return json.loads(a.read_text()), json.loads(b.read_text())


class TestTheInvertedResult:

    def test_the_recency_sample_is_more_concentrated(self, samples):
        """
        THE RESULT, and it went the other way from my prediction. New uploads
        pile onto whichever base is current; the popular stock has accumulated
        across several generations of base model.
        """
        pop, rec = samples
        c = compare(pop, rec)
        assert c["gap_top3_share"] < -0.05
        assert "MORE concentrated" in c["verdict"]

    def test_the_flow_has_fewer_distinct_roots_than_the_stock(self, samples):
        pop, rec = samples
        p, r = summarise(pop, "p"), summarise(rec, "r")
        assert r.distinct_root_orgs < p.distinct_root_orgs / 2

    def test_download_concentration_is_higher_in_the_flow_too(self, samples):
        pop, rec = samples
        c = compare(pop, rec)
        assert (c["recency"]["top3_share_of_downloads"]
                > c["popularity"]["top3_share_of_downloads"])

    def test_the_verdict_names_what_it_means(self, samples):
        """
        A snapshot of what exists understates where the ecosystem is heading.
        That is the interpretation, and it has to be in the output rather than
        left for a reader to derive.
        """
        pop, rec = samples
        assert "where the ecosystem is heading" in compare(pop, rec)["verdict"]


class TestWhatIsRobust:

    def test_chain_depth_agrees_across_selection_rules(self, samples):
        """
        53.0% against 51.0%. Structure survives the selection rule even though
        concentration does not, so it is a claim about how these models are
        built rather than about which ones were sampled.
        """
        pop, rec = samples
        c = compare(pop, rec)
        gap = abs(c["popularity"]["through_intermediary"]
                  - c["recency"]["through_intermediary"])
        assert gap < 0.06

    def test_licence_widening_agrees_across_selection_rules(self, samples):
        pop, rec = samples
        c = compare(pop, rec)
        gap = abs(c["popularity"]["widening_rate"]
                  - c["recency"]["widening_rate"])
        assert gap < 0.01


class TestHonesty:

    def test_a_zero_median_is_handled_as_information(self, samples):
        """
        The recency sample's median download count is zero: a model uploaded
        today has not been downloaded. The first version of this divided by it
        and crashed; it is now reported, because it states the difference
        between the two samples in one number.
        """
        pop, rec = samples
        c = compare(pop, rec)
        assert c["recency_median_is_zero"] is True
        assert c["median_download_ratio"] == float("inf")

    def test_neither_sample_is_claimed_to_be_random(self, samples):
        pop, rec = samples
        c = compare(pop, rec)
        assert "Neither sample is random" in c["caveat"]
        assert "bounds selection effects rather than removing them" in c["caveat"]

    def test_the_recency_bias_is_stated_in_the_sampler(self):
        src = (ROOT / "scripts" / "sample_unbiased.py").read_text()
        flat = " ".join(src.split())
        assert "over-represents whatever period has the most uploads" in flat
        assert "not unbiased" in flat


class TestTheGapIsNotSampleSize:
    """
    This project mistook a selection effect for a sample-size effect once
    already. The question now gets asked in code rather than assumed.
    """

    def test_the_check_runs_and_is_applicable(self, samples):
        from lineage.compare import is_the_gap_sample_size
        pop, rec = samples
        r = is_the_gap_sample_size(pop, rec, trials=60)
        assert r["applicable"]
        assert r["subsample_size"] == len(rec)

    def test_the_recency_figure_is_outside_every_subsample(self, samples):
        """
        Subsampling the 1,200 down to 245, two hundred times, never reaches
        60.8%. The gap is not the sample size.
        """
        from lineage.compare import is_the_gap_sample_size
        pop, rec = samples
        r = is_the_gap_sample_size(pop, rec, trials=100)
        assert not r["inside_range"]
        assert r["sd_from_mean"] > 3

    def test_the_check_is_reported_alongside_the_comparison(self, samples):
        """
        A fifteen-point gap quoted without this check is exactly the claim I
        got wrong earlier in this project.
        """
        from lineage.compare import compare
        pop, rec = samples
        c = compare(pop, rec)
        assert "sample_size_check" in c
        assert c["sample_size_check"]["verdict"].startswith("outside")

    def test_it_declines_when_the_larger_sample_is_not_larger(self, samples):
        from lineage.compare import is_the_gap_sample_size
        _, rec = samples
        assert not is_the_gap_sample_size(rec, rec)["applicable"]
