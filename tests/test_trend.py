"""
Tests for the period analysis.

The central ones pin a correction to this project's own headline. The
two-sample comparison reported that "the flow clusters use far more than it
clusters models". Two adjacent months of history show the same pattern between
September and October, which maturation explains as well as any structural
change — and the module must not claim otherwise.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from lineage.trend import Period, by_period, month_of, trend

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def history():
    p = ROOT / "evidence" / "history.json"
    if not p.exists():
        pytest.skip("no historical sample")
    return json.loads(p.read_text())


class TestBucketing:

    def test_undated_chains_are_dropped(self):
        assert month_of({}) is None
        assert month_of({"created_at": "x"}) is None
        assert month_of({"created_at": "2026-09-14T10:00:00Z"}) == "2026-09"

    def test_thin_months_are_dropped_not_plotted(self):
        """
        A concentration figure over a dozen models is noise, and a reader
        looking at a series will not know which points to distrust.
        """
        rows = [{"created_at": "2026-01-02", "root": "a/b", "downloads": 1,
                 "chain": []} for _ in range(5)]
        assert by_period(rows, min_n=25) == []

    def test_real_months_are_found(self, history):
        ps = by_period(history, min_n=25)
        assert len(ps) >= 2
        assert all(p.n >= 25 for p in ps)


class TestTwoPeriodsIsNotATrend:

    def test_two_periods_are_reported_as_a_comparison(self, history):
        t = trend(by_period(history, min_n=25))
        assert t["periods"] == 2
        assert t["is_trend"] is False

    def test_the_maturation_confound_is_named(self, history):
        """
        THE CORRECTION. Model-count concentration is flat between the two
        months while download concentration rises 24 points. The newer
        month's downloads are still accumulating, so maturation explains it
        as well as any structural change.
        """
        t = trend(by_period(history, min_n=25))
        assert abs(t["model_share_change_points"]) < 5
        assert t["download_share_change_points"] > 10
        assert "maturation" in t["verdict"]
        assert "cannot tell them apart" in t["verdict"]

    def test_the_caveat_travels_with_the_result(self, history):
        t = trend(by_period(history, min_n=25))
        assert "cannot separate a trend from maturation" in t["caveat"]

    def test_one_period_declines_entirely(self):
        rows = [{"created_at": "2026-09-01", "root": "a/b", "downloads": 1,
                 "chain": []} for _ in range(40)]
        t = trend(by_period(rows, min_n=25))
        assert "too few periods" in t.get("note", "")


class TestThreePeriodsWouldBeATrend:

    def _periods(self, shares):
        return [Period(label=f"2026-0{i+1}", n=100, top3_share=s,
                       top3_downloads=s, distinct_orgs=50,
                       top_root="Qwen", top_root_share=0.4)
                for i, s in enumerate(shares)]

    def test_a_rising_series_is_reported_as_rising(self):
        t = trend(self._periods([0.40, 0.50, 0.60]))
        assert t["change_points"] > 15
        assert "rises" in t["verdict"]

    def test_a_flat_series_is_reported_as_flat(self):
        t = trend(self._periods([0.50, 0.51, 0.50]))
        assert "flat" in t["verdict"]

    def test_the_lifecycle_caveat_is_attached_to_trends_too(self):
        t = trend(self._periods([0.40, 0.50, 0.60]))
        assert "lifecycles" in t["caveat"]
        assert "cannot establish it is secular" in t["caveat"]
