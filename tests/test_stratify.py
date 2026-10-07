"""
Tests for the download-matched comparison.

The central one pins a negative: the two samples barely overlap in download
level, so the control that was supposed to settle the maturation question
mostly cannot be applied. That is a more useful thing to know than a number
computed over one thin band would have been.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from lineage.stratify import STRATA, stratify, verdict

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def samples():
    a = ROOT / "evidence" / "derivatives.json"
    b = ROOT / "evidence" / "unbiased.json"
    if not (a.exists() and b.exists()):
        pytest.skip("both samples required")
    return json.loads(a.read_text()), json.loads(b.read_text())


def row(dl, root="Qwen/x"):
    return {"id": "m", "downloads": dl, "root": root, "license": None,
            "chain": [{"id": root, "resolved": True, "downloads": dl}]}


class TestStrata:

    def test_bands_are_contiguous_and_cover_the_range(self):
        for (a_lo, a_hi), (b_lo, b_hi) in zip(STRATA, STRATA[1:]):
            assert a_hi == b_lo
        assert STRATA[0][0] == 0
        assert STRATA[-1][1] >= 10**9

    def test_models_land_in_the_right_band(self):
        st = stratify([row(500)] * 40, [row(500)] * 40)
        band = [s for s in st if s.lo == 100][0]
        assert band.n_a == 40 and band.n_b == 40

    def test_a_thin_side_makes_a_band_incomparable(self):
        """
        Thirty on each side is the floor. A concentration share over a handful
        of models is noise, and reporting it beside well-populated bands
        invites a reader to weight them equally.
        """
        st = stratify([row(500)] * 40, [row(500)] * 5)
        band = [s for s in st if s.lo == 100][0]
        assert not band.comparable
        assert band.gap is None


class TestTheControlMostlyCannotBeApplied:

    def test_the_samples_barely_overlap(self, samples):
        """
        THE FINDING. The popularity sample has no models under a thousand
        downloads; the recency sample has over a thousand under a hundred.
        There is almost nothing to match.
        """
        pop, rec = samples
        st = stratify(pop, rec)
        comparable = [s for s in st if s.comparable]
        assert len(comparable) <= 2, \
            "if the samples start overlapping, the maturation story changes"

    def test_the_non_overlap_is_reported_as_the_story(self, samples):
        pop, rec = samples
        v = verdict(stratify(pop, rec))
        assert v["single_band_only"] is True
        assert "IS the maturation story" in v["verdict"]

    def test_a_single_band_is_not_dressed_as_an_average(self, samples):
        """
        Saying 'on average' over one stratum would present a thin comparison
        as a summary of several. The verdict names the band and its thinner
        side instead.
        """
        pop, rec = samples
        v = verdict(stratify(pop, rec))
        assert "on average" not in v["verdict"]
        assert str(v["thinnest_side"]) in v["verdict"]

    def test_the_collider_problem_is_stated(self, samples):
        """
        Downloads are downstream of base popularity, so conditioning on them
        can create an association as easily as remove one.
        """
        pop, rec = samples
        v = verdict(stratify(pop, rec))
        assert "collider" in v["caveat"]
        assert "direction, not a causal answer" in v["caveat"]

    def test_no_bands_at_all_is_handled(self):
        v = verdict(stratify([row(5)] * 40, [row(10**8)] * 40))
        assert v["comparable_strata"] == 0
        assert "barely overlap" in v["note"]
