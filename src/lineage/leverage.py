"""
How much of a download-weighted figure rests on a handful of models?

Why this exists
---------------
Download-weighted concentration is the more meaningful measure — a base with
twenty heavily-used derivatives matters more than one with two thousand nobody
pulls. It is also fragile in a way the model-count measure is not, because
downloads are distributed across orders of magnitude and a single popular
derivative can carry a quarter of a cohort.

Measured on two adjacent months of this data:

    September   top 3 models carry 31.7% of the cohort's downloads
    October     top 3 models carry 42.4%

So a 24-point difference in cohort-level download concentration can turn on
which month happened to contain one popular model. That is not a finding about
the ecosystem; it is a finding about the statistic.

What this measures
------------------
For any sample, how much a download-weighted figure moves when the largest
contributors are removed. A figure that survives dropping the top few rests on
the body of the distribution. One that collapses rests on its tail, and should
be quoted with that attached or not quoted.

This is a sensitivity check, not a correction. Removing the biggest models
produces a number that is less fragile and also less true — those downloads are
real. The point is to know which kind of figure you are holding.
"""

from __future__ import annotations

from dataclasses import dataclass

from .analyse import analyse


@dataclass
class Leverage:
    n: int
    full: float
    """Download-weighted top-3 concentration over the whole sample."""

    without_top: dict
    """The same figure with the k largest models removed, keyed by k."""

    top_model_share: float
    """What fraction of the sample's downloads the single largest carries."""

    top3_model_share: float

    @property
    def fragile(self) -> bool:
        """
        Does dropping three models move the figure by more than five points?

        Five is a judgement and is exposed. The useful signal is not the
        threshold but the size of the move relative to the gaps being
        discussed: a statistic that shifts eight points when three rows leave
        cannot support a four-point claim.
        """
        k3 = self.without_top.get(3)
        return k3 is not None and abs(k3 - self.full) > 0.05

    def as_dict(self) -> dict:
        return {"n": self.n, "full": self.full,
                "without_top": self.without_top,
                "top_model_share": self.top_model_share,
                "top3_model_share": self.top3_model_share,
                "fragile": self.fragile}


def leverage(chains: list[dict], ks: tuple[int, ...] = (1, 3, 10)) -> Leverage:
    ordered = sorted(chains, key=lambda w: -w.get("downloads", 0))
    total = sum(w.get("downloads", 0) for w in ordered) or 1

    full = analyse(ordered).concentration(3)["share_of_downloads"]
    without = {}
    for k in ks:
        rest = ordered[k:]
        if len(rest) >= 20:
            without[k] = analyse(rest).concentration(3)["share_of_downloads"]

    return Leverage(
        n=len(ordered), full=full, without_top=without,
        top_model_share=ordered[0].get("downloads", 0) / total if ordered else 0,
        top3_model_share=sum(w.get("downloads", 0) for w in ordered[:3]) / total,
    )


def compare_fragility(a: list[dict], b: list[dict],
                      label_a: str = "a", label_b: str = "b") -> dict:
    """
    Whether a gap between two samples survives removing their biggest models.

    A gap that shrinks toward zero was carried by a few rows. One that holds
    is a property of the samples.
    """
    la, lb = leverage(a), leverage(b)
    raw_gap = la.full - lb.full

    trimmed = {}
    for k in (1, 3, 10):
        if k in la.without_top and k in lb.without_top:
            trimmed[k] = la.without_top[k] - lb.without_top[k]

    k3 = trimmed.get(3)
    if k3 is None:
        verdict = "not enough rows to trim and still compare"
    elif abs(raw_gap) > 0 and abs(k3) < abs(raw_gap) * 0.5:
        verdict = (f"The gap falls from {raw_gap*100:+.1f} points to "
                   f"{k3*100:+.1f} when three models are removed from each "
                   "side. It was carried by a handful of popular derivatives "
                   "rather than by the samples' structure.")
    else:
        verdict = (f"The gap holds at {k3*100:+.1f} points with three models "
                   f"removed from each side, against {raw_gap*100:+.1f} raw. "
                   "It is not an artefact of a few popular derivatives.")

    return {
        label_a: la.as_dict(), label_b: lb.as_dict(),
        "raw_gap": raw_gap, "trimmed_gaps": trimmed,
        "verdict": verdict,
        "caveat": ("Trimming produces a less fragile figure and a less true "
                   "one — those downloads are real. This says which kind of "
                   "figure the headline is, not which number to use."),
    }
