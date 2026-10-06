"""
Tests for the depth-sensitivity finding.

This is the project's headline, so these pin it hard: the direction, the
monotonicity, and the fact that two honest studies can disagree by twenty
points without either being wrong.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from lineage.convergence import curve
from lineage.depth import by_rank, cumulative, spread

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def chains():
    p = ROOT / "evidence" / "derivatives.json"
    if not p.exists():
        pytest.skip("no collected data")
    return json.loads(p.read_text())


class TestDepthSensitivity:

    def test_concentration_falls_monotonically_with_depth(self, chains):
        """
        THE FINDING. The popular end is concentrated and the tail is not, so
        a study's reported concentration is set by how deep it collected.
        """
        shares = [s.top3_share_of_derivatives for s in by_rank(chains)]
        assert shares == sorted(shares, reverse=True), \
            f"expected a monotone fall, got {shares}"
        assert shares[0] - shares[-1] > 0.2, "the effect should be large"

    def test_organisational_diversity_rises_with_depth(self, chains):
        orgs = [s.distinct_root_orgs for s in by_rank(chains)]
        assert orgs == sorted(orgs)
        assert orgs[-1] > 4 * orgs[0]

    def test_two_honest_studies_can_disagree_by_twenty_points(self, chains):
        sp = spread(chains)
        assert sp["top3_share_spread_points"] > 15
        lo, hi = sp["distinct_orgs_range"]
        assert hi > 5 * lo

    def test_bands_are_disjoint_not_cumulative(self, chains):
        """
        A cumulative series hides the effect: every prefix is dominated by the
        head it contains, so the curve flattens and reads as convergence.
        """
        bands = by_rank(chains)
        for a, b in zip(bands, bands[1:]):
            assert a.rank_to == b.rank_from - 1 or a.rank_to < b.rank_from

    def test_the_cumulative_view_reproduces_a_shallow_study(self, chains):
        """
        The first collection walked the top 400 and reported 57.2%. Taking the
        top 400 out of the larger pool reproduces it, which is what showed the
        move was depth and not sample size.
        """
        top400 = [s for s in cumulative(chains) if s.n == 400]
        assert top400
        assert 0.54 < top400[0].top3_share_of_derivatives < 0.62


class TestItIsNotSamplingVariance:

    def test_share_statistics_are_stable_in_n(self, chains):
        """
        REGRESSION on my own first explanation. I attributed an eleven-point
        move to sample size. Subsampling shows the share statistics barely
        move with n — 46.8% at a hundred chains against 45.8% at twelve
        hundred — so sampling variance cannot explain it.
        """
        c = curve(chains, "top3_share_of_derivatives", trials=20, seed=3)
        assert abs(c.means[0] - c.means[-1]) < 0.05

    def test_count_statistics_do_not_converge(self, chains):
        """
        Distinct organisations is unbounded: every new chain can introduce one
        never seen before. Reporting the share statistics as converged without
        this would tell a reader the sample is adequate when the count is
        saying the tail has not been reached.
        """
        c = curve(chains, "distinct_root_orgs", trials=20, seed=3)
        assert c.drifting
        assert c.means[-1] > 3 * c.means[0]

    def test_rare_event_rates_are_noisy_by_construction(self, chains):
        """Twenty widenings in twelve hundred: the estimate cannot be precise."""
        c = curve(chains, "licence_widening_rate", trials=20, seed=3)
        assert c.spreads[0] > 0


class TestHonesty:

    def test_subsampling_is_marked_as_not_validating_the_population(self):
        """
        A narrow spread means more of the same data would not move this. It
        does not mean the collection is unbiased, and the two are easy to
        confuse.
        """
        import lineage.convergence as cv
        doc = " ".join(cv.__doc__.split())
        assert "cannot tell you that the population is right" in doc
        assert "converges neatly to the wrong number" in doc

    def test_the_depth_module_refuses_to_name_a_correct_cut(self):
        import lineage.depth as dp
        doc = " ".join(dp.__doc__.split())
        assert "There may not be a correct one" in doc

    def test_convergence_is_labelled_a_heuristic(self):
        import inspect

        from lineage.convergence import Curve
        doc = " ".join(inspect.getdoc(Curve.converged.fget).split())
        assert "heuristic" in doc
