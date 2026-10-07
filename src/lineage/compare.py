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


def is_the_gap_sample_size(popularity: list[dict], recency: list[dict],
                           trials: int = 200, seed: int = 11) -> dict:
    """
    Could the gap be explained by the two samples having different sizes?

    This project already mistook a selection effect for a sample-size effect
    once, so the question gets asked rather than assumed. Subsample the larger
    set down to the smaller one's size, many times, and see where the smaller
    set's actual figure falls in that distribution.

    A figure inside the subsample range means the gap is consistent with
    noise. Outside it means the two samples are drawing from different
    populations, which is the claim being made.
    """
    import random
    import statistics

    # Either sample may be the larger one: the recency collection was scaled
    # from 245 to 1,500 chains and overtook the popularity set. Subsampling
    # always runs on whichever is bigger, so the check does not silently stop
    # applying when the sizes cross over.
    if len(popularity) == len(recency):
        return {"applicable": False, "note": "the samples are the same size"}

    big, small = ((popularity, recency) if len(popularity) > len(recency)
                  else (recency, popularity))
    big_label = "popularity" if big is popularity else "recency"

    rng = random.Random(seed)
    vals = []
    for _ in range(trials):
        sub = rng.sample(big, len(small))
        vals.append(analyse(sub).concentration(3)["share_of_derivatives"])

    actual = analyse(small).concentration(3)["share_of_derivatives"]
    mean = statistics.fmean(vals)
    sd = statistics.pstdev(vals)
    lo, hi = min(vals), max(vals)

    return {
        "applicable": True,
        "subsampled": big_label,
        "subsample_size": len(small), "trials": trials,
        "subsample_mean": mean, "subsample_sd": sd,
        "subsample_range": [lo, hi],
        "other_actual": actual,
        # Kept so earlier evidence files and callers still resolve.
        "popularity_mean": mean, "popularity_sd": sd,
        "popularity_range": [lo, hi], "recency_actual": actual,
        "inside_range": lo <= actual <= hi,
        "sd_from_mean": (actual - mean) / sd if sd else float("inf"),
        "verdict": ("consistent with sampling noise" if lo <= actual <= hi
                    else "outside every subsample: the samples draw from "
                         "different populations"),
    }


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
    dl_gap = p.top3_share_of_downloads - r.top3_share_of_downloads

    # Judging on model count alone would call these samples agreed. They
    # differ by under five points there and by twenty-five on download
    # concentration, which is the larger and more meaningful gap: the flow
    # clusters USE far more than it clusters models.
    if abs(gap) < 0.05 and abs(dl_gap) >= 0.10:
        verdict = (f"The two rules agree on model-count concentration, within "
                   f"{abs(gap)*100:.1f} points, and disagree sharply on "
                   f"download concentration, by {abs(dl_gap)*100:.1f} points. "
                   "The flow clusters use far more than it clusters models: "
                   "newly uploaded derivatives spread across a comparable "
                   "number of bases, but the attention goes to fewer of them. "
                   "A count of models understates where the stock is heading.")
    elif abs(gap) < 0.05:
        verdict = ("The two selection rules agree within five points on both "
                   "measures, so the concentration figure does not depend on "
                   "either and can be read as a property of the population.")
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
        "sample_size_check": is_the_gap_sample_size(popularity, recency),
        "gap_top3_share": gap,
        "gap_top3_downloads": dl_gap,
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
