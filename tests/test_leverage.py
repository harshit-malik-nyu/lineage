"""
Tests for the fragility check.

This module exists because it killed a headline. The project reported that
newly uploaded models cluster downloads far more than the popular stock — a
25.7-point gap. One model carries 49.5% of the recency sample's downloads, and
the gap falls to 11.0 points when three rows are removed from each side.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from lineage.leverage import compare_fragility, leverage

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def samples():
    a = ROOT / "evidence" / "derivatives.json"
    b = ROOT / "evidence" / "unbiased.json"
    if not (a.exists() and b.exists()):
        pytest.skip("both samples required")
    return json.loads(a.read_text()), json.loads(b.read_text())


def row(dl, root):
    return {"id": f"m{dl}", "downloads": dl, "root": root, "license": None,
            "chain": [{"id": root, "resolved": True, "downloads": dl}]}


class TestMechanics:

    def test_one_huge_model_makes_a_figure_fragile(self):
        rows = [row(10_000_000, "Qwen/a")] + [row(10, f"org{i}/b")
                                              for i in range(60)]
        assert leverage(rows).fragile

    def test_an_even_distribution_is_robust(self):
        rows = [row(1000, f"org{i % 20}/b") for i in range(100)]
        assert not leverage(rows).fragile

    def test_trimming_needs_rows_left_to_measure(self):
        """A trim that leaves fewer than twenty rows is not reported."""
        assert leverage([row(10, "a/b") for _ in range(15)]).without_top == {}

    def test_the_top_share_is_of_downloads_not_models(self):
        rows = [row(900, "a/b")] + [row(10, f"o{i}/c") for i in range(10)]
        assert leverage(rows).top_model_share > 0.8


class TestTheHeadlineThatBroke:

    def test_the_recency_download_figure_is_fragile(self, samples):
        """
        THE CORRECTION. 89.0% download concentration, and one model is 49.5%
        of the sample's downloads. A statistic that moves twenty points when
        three rows leave cannot support a twenty-five point claim.
        """
        _, rec = samples
        l = leverage(rec)
        assert l.fragile
        assert l.top_model_share > 0.3

    def test_the_popularity_download_figure_is_not(self, samples):
        """
        The contrast matters: the same statistic is stable on the larger,
        more mature sample, so fragility is a property of fresh cohorts
        rather than of the measure everywhere.
        """
        pop, _ = samples
        assert not leverage(pop).fragile

    def test_the_gap_does_not_survive_trimming(self, samples):
        pop, rec = samples
        c = compare_fragility(pop, rec)
        assert abs(c["trimmed_gaps"][3]) < abs(c["raw_gap"]) * 0.6
        assert "carried by a handful" in c["verdict"]

    def test_trimming_ten_closes_it_almost_entirely(self, samples):
        pop, rec = samples
        c = compare_fragility(pop, rec)
        assert abs(c["trimmed_gaps"][10]) < 0.1

    def test_model_count_concentration_is_unaffected(self, samples):
        """
        Only the download-weighted measure is fragile. The model-count
        figures, and the depth and window findings built on them, do not rest
        on a few rows.
        """
        from lineage.analyse import analyse
        pop, rec = samples
        for rows in (pop, rec):
            ordered = sorted(rows, key=lambda w: -w.get("downloads", 0))
            full = analyse(ordered).concentration(3)["share_of_derivatives"]
            trimmed = analyse(ordered[10:]).concentration(3)["share_of_derivatives"]
            assert abs(full - trimmed) < 0.05


class TestHonesty:

    def test_trimming_is_called_a_check_not_a_correction(self, samples):
        """
        The removed downloads are real. Trimming gives a less fragile figure
        and a less true one, and the output has to say which kind of number
        the reader is holding.
        """
        pop, rec = samples
        c = compare_fragility(pop, rec)
        assert "less true" in c["caveat"]
        assert "not which number to use" in c["caveat"]

    def test_the_threshold_is_exposed(self):
        import inspect

        from lineage.leverage import Leverage
        doc = " ".join(inspect.getdoc(Leverage.fragile.fget).split())
        assert "judgement and is exposed" in doc
