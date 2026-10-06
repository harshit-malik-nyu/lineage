"""
Concentration is a property of where you cut the ranking, not of the ecosystem.

The finding this module exists for
----------------------------------
The first collection walked 400 chains and reported the top three
organisations as 57.2% of derivatives. The second walked 1,200 and reported
45.8%. The obvious reading is that the small sample was wrong.

It is not what happened. Subsampling the 1,200 shows the share statistics are
stable in n — 46.8% at a hundred chains, 45.8% at twelve hundred. Sampling
variance does not explain an eleven-point move.

What explains it is which models were in the pool. The first run took the 250
most-downloaded models per construction type; the second took 500. Taking the
top 400 by downloads *out of the larger pool* reproduces the original figure
almost exactly:

    top 400 by downloads      58.2% from three orgs,  61 distinct orgs
    the remaining 800         40.2% from three orgs, 159 distinct orgs

**The popular end of the ecosystem is concentrated. The tail is not.** Both
sentences are true, and which one a study reports is decided by how deep it
collected, not by anything about open weights.

Why this matters beyond this repository
---------------------------------------
Open-weight policy arguments cite concentration in both directions. "A handful
of labs control the ecosystem" and "hundreds of organisations publish base
models" are both supportable from the same data, by choosing a cut.

Any such claim is therefore incomplete without its sampling depth, and almost
none state one. That is a methodological finding rather than a fact about
model weights, and it is the more useful of the two.

What this does not show
-----------------------
That the tail is unimportant. A model with few downloads can still be deployed
somewhere that matters, and download counts are a poor proxy for deployment —
they count CI runs, mirrors and people trying something once. The curve below
describes how an estimate moves with the cut, not which cut is correct. There
may not be a correct one.
"""

from __future__ import annotations

from dataclasses import dataclass

from .analyse import analyse


@dataclass
class Slice:
    label: str
    n: int
    rank_from: int
    rank_to: int
    top3_share_of_derivatives: float
    top3_share_of_downloads: float
    distinct_root_orgs: int
    median_downloads: float

    def as_dict(self) -> dict:
        return {
            "label": self.label, "n": self.n,
            "rank_from": self.rank_from, "rank_to": self.rank_to,
            "top3_share_of_derivatives": self.top3_share_of_derivatives,
            "top3_share_of_downloads": self.top3_share_of_downloads,
            "distinct_root_orgs": self.distinct_root_orgs,
            "median_downloads": self.median_downloads,
        }


def by_rank(chains: list[dict], cuts: list[int] | None = None) -> list[Slice]:
    """
    Concentration within successive bands of the download ranking.

    Bands rather than cumulative prefixes, because a cumulative series hides
    the effect: each prefix is dominated by the head it contains, so the
    curve flattens and looks like convergence. Disjoint bands show what each
    part of the ranking actually looks like.
    """
    ordered = sorted(chains, key=lambda w: -w.get("downloads", 0))
    n = len(ordered)
    cuts = cuts or [0, 100, 200, 400, 800, n]
    cuts = [c for c in cuts if c <= n]
    if cuts[-1] != n:
        cuts.append(n)

    out = []
    for lo, hi in zip(cuts, cuts[1:]):
        band = ordered[lo:hi]
        if len(band) < 20:
            continue
        a = analyse(band)
        c = a.concentration(3)
        dls = sorted(w.get("downloads", 0) for w in band)
        out.append(Slice(
            label=f"rank {lo + 1}-{hi}", n=len(band),
            rank_from=lo + 1, rank_to=hi,
            top3_share_of_derivatives=c["share_of_derivatives"],
            top3_share_of_downloads=c["share_of_downloads"],
            distinct_root_orgs=a.as_dict()["distinct_root_orgs"],
            median_downloads=dls[len(dls) // 2],
        ))
    return out


def cumulative(chains: list[dict], cuts: list[int] | None = None) -> list[Slice]:
    """
    The same statistic over cumulative prefixes — how a study that collected
    only the top N would report it.

    This is the view that matters for reading other people's work: a paper
    that collected the top 500 models is reporting the prefix figure, whether
    or not it says so.
    """
    ordered = sorted(chains, key=lambda w: -w.get("downloads", 0))
    n = len(ordered)
    cuts = [c for c in (cuts or [100, 200, 400, 800, n]) if c <= n]
    out = []
    for hi in cuts:
        band = ordered[:hi]
        a = analyse(band)
        c = a.concentration(3)
        dls = sorted(w.get("downloads", 0) for w in band)
        out.append(Slice(
            label=f"top {hi}", n=hi, rank_from=1, rank_to=hi,
            top3_share_of_derivatives=c["share_of_derivatives"],
            top3_share_of_downloads=c["share_of_downloads"],
            distinct_root_orgs=a.as_dict()["distinct_root_orgs"],
            median_downloads=dls[len(dls) // 2],
        ))
    return out


def spread(chains: list[dict]) -> dict:
    """
    The range a study could report by choosing its depth.

    This is the number worth quoting: how far apart two honest studies of the
    same ecosystem can land by cutting the ranking differently.
    """
    cum = cumulative(chains)
    if not cum:
        return {}
    shares = [s.top3_share_of_derivatives for s in cum]
    orgs = [s.distinct_root_orgs for s in cum]
    return {
        "depths": [s.n for s in cum],
        "top3_share_range": [min(shares), max(shares)],
        "top3_share_spread_points": (max(shares) - min(shares)) * 100,
        "distinct_orgs_range": [min(orgs), max(orgs)],
        "note": ("Both ends are honest readings of the same data. A claim "
                 "about ecosystem concentration is incomplete without the "
                 "sampling depth that produced it."),
    }
