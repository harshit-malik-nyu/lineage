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
        The direction held when the sample grew; the magnitude did not.

        At n=245 the gap read as fifteen points. Scaling the recency
        collection to 1,500 — a wider time window, not just more rows — put it
        at under five. The narrow window was the more concentrated thing, not
        the recency.
        """
        pop, rec = samples
        c = compare(pop, rec)
        assert c["gap_top3_share"] < 0, "recency should still be the higher one"
        assert c["gap_top3_downloads"] < -0.15, "the download gap is the large one"

    def test_the_download_gap_is_the_large_one(self, samples):
        """
        Model-count concentration differs by under five points; download
        concentration differs by twenty-five. What the flow does is cluster
        USE, more than it clusters models.
        """
        pop, rec = samples
        c = compare(pop, rec)
        gap = (c["recency"]["top3_share_of_downloads"]
               - c["popularity"]["top3_share_of_downloads"])
        assert gap > 0.15

    def test_root_diversity_is_comparable_once_the_windows_match(self, samples):
        """
        At n=245 the recency sample showed 62 distinct roots against 188 — a
        third. That was a two-day window. Across a week it shows 200, slightly
        MORE than the popularity sample, so the original reading was about
        window width rather than about the flow.
        """
        pop, rec = samples
        p, r = summarise(pop, "p"), summarise(rec, "r")
        assert r.distinct_root_orgs > p.distinct_root_orgs * 0.8

    def test_download_concentration_is_higher_in_the_flow_too(self, samples):
        pop, rec = samples
        c = compare(pop, rec)
        assert (c["recency"]["top3_share_of_downloads"]
                > c["popularity"]["top3_share_of_downloads"])

    def test_the_verdict_names_what_it_means(self, samples):
        pop, rec = samples
        v = compare(pop, rec)["verdict"]
        assert "clusters use far more than it clusters models" in v
        assert "understates where the stock is heading" in v


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

    def test_the_download_gulf_between_the_samples_is_enormous(self, samples):
        """
        Median downloads: 11,570 against 19. At the narrower window it was
        zero, which crashed the ratio and had to be handled — a model uploaded
        today has not been downloaded yet. Across a week it is 19, which is
        the same fact with a little time applied.
        """
        pop, rec = samples
        c = compare(pop, rec)
        assert c["median_download_ratio"] > 100

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

    def test_the_check_runs_whichever_sample_is_larger(self, samples):
        """
        The recency collection was scaled from 245 to 1,500 and overtook the
        popularity set, which made the original one-directional check stop
        applying. It now subsamples whichever is bigger.
        """
        from lineage.compare import is_the_gap_sample_size
        pop, rec = samples
        r = is_the_gap_sample_size(pop, rec, trials=60)
        assert r["applicable"]
        assert r["subsample_size"] == min(len(pop), len(rec))
        assert r["subsampled"] in ("popularity", "recency")

    def test_the_gap_survives_the_size_difference(self, samples):
        """
        Subsampling the larger set to the smaller one's size, a hundred times,
        never reaches the other's figure. The gap shrank when the window
        widened but it did not come from the sample size.
        """
        from lineage.compare import is_the_gap_sample_size
        pop, rec = samples
        r = is_the_gap_sample_size(pop, rec, trials=100)
        assert not r["inside_range"]
        assert abs(r["sd_from_mean"]) > 3

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
