"""
Does the finding survive a different selection rule?

Two samples, two biases
-----------------------
The main collection walks chains out of the most-downloaded models. The second
strides across the index sorted by upload date. Both are biased; the biases
point in different directions.

    popularity sample    over-represents models people use. Its concentration
                         figure is high because the head of the ranking is
                         concentrated.
    recency sample       over-represents whatever period uploaded most. It has
                         no reason to favour any particular base model, so a
                         concentration figure here is closer to a population
                         statement.

Agreement between them would mean the finding does not depend on either
selection rule. Disagreement bounds how much selection contributes, which is
weaker and still worth having — and `depth.py` has already shown disagreement
is the likely outcome.

What a difference would mean
----------------------------
If the recency sample shows lower concentration, the popularity figure is a
statement about use rather than about the ecosystem, and the README's framing
is correct. If it shows the same, concentration is a property of the population
and the depth finding is about sampling noise rather than about selection.

Either way the comparison settles something, which is why it is worth the
requests.
"""

from __future__ import annotations

from dataclasses import dataclass

from .analyse import analyse


@dataclass
class SampleSummary:
    label: str
    n: int
    top3_share_of_derivatives: float
    top3_share_of_downloads: float
    distinct_root_orgs: int
    through_intermediary: float
    median_downloads: float
    widening_rate: float

    def as_dict(self) -> dict:
        return {
            "label": self.label, "n": self.n,
            "top3_share_of_derivatives": self.top3_share_of_derivatives,
            "top3_share_of_downloads": self.top3_share_of_downloads,
            "distinct_root_orgs": self.distinct_root_orgs,
            "through_intermediary": self.through_intermediary,
            "median_downloads": self.median_downloads,
            "widening_rate": self.widening_rate,
        }


def summarise(chains: list[dict], label: str) -> SampleSummary:
    a = analyse(chains)
    d = a.as_dict()
    c = a.concentration(3)
    dls = sorted(w.get("downloads", 0) for w in chains)
    return SampleSummary(
        label=label, n=len(chains),
        top3_share_of_derivatives=c["share_of_derivatives"],
        top3_share_of_downloads=c["share_of_downloads"],
        distinct_root_orgs=d["distinct_root_orgs"],
        through_intermediary=a.through_intermediary,
        median_downloads=dls[len(dls) // 2] if dls else 0,
        widening_rate=d["widening_count"] / max(1, len(chains)),
    )


def compare(popularity: list[dict], recency: list[dict]) -> dict:
    """
    Both samples side by side, with the gap on each statistic.

    The verdict field says what the comparison supports, not what would be
    convenient: a large gap means the popularity figure describes use rather
    than the ecosystem, and the headline has to be read that way.
    """
    p = summarise(popularity, "popularity-sampled")
    r = summarise(recency, "recency-sampled")

    gap = p.top3_share_of_derivatives - r.top3_share_of_derivatives
    if abs(gap) < 0.05:
        verdict = ("The two selection rules agree within five points, so the "
                   "concentration figure does not depend on either and can be "
                   "read as a property of the population.")
    elif gap < 0:
        # The direction that was not predicted. Recently uploaded models are
        # MORE concentrated than the popular stock, because new uploads pile
        # onto whichever base is currently fashionable while the popular set
        # has accumulated across several generations of base model.
        verdict = (f"The recency sample is {abs(gap)*100:.1f} points MORE "
                   "concentrated than the popularity sample. New uploads pile "
                   "onto whichever base is current, while the popular stock "
                   "has accumulated across several generations. The flow is "
                   "more concentrated than the stock, which means a snapshot "
                   "of what exists understates where the ecosystem is heading.")
    else:
        verdict = (f"The two disagree by {abs(gap)*100:.1f} points, with the "
                   "popularity sample more concentrated. That figure describes "
                   "what people use rather than what exists.")

    return {
        "popularity": p.as_dict(),
        "recency": r.as_dict(),
        "gap_top3_share": gap,
        "gap_distinct_orgs": p.distinct_root_orgs - r.distinct_root_orgs,
        # The recency sample's median downloads is zero: a model uploaded
        # today has not been downloaded yet. That is not a glitch, it is the
        # difference between the two samples stated in one number — one
        # measures stock, the other measures flow.
        "median_download_ratio": (p.median_downloads / r.median_downloads
                                  if r.median_downloads else float("inf")),
        "recency_median_is_zero": r.median_downloads == 0,
        "verdict": verdict,
        "caveat": ("Neither sample is random. Recency striding over-represents "
                   "whatever period uploaded most; popularity sampling "
                   "over-represents the head. The comparison bounds selection "
                   "effects rather than removing them."),
    }
