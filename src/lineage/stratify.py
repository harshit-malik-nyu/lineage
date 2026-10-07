"""
Does the concentration gap survive controlling for download level?

The question
-----------
The recency sample's download concentration is 89.0% against the popularity
sample's 63.3% — a twenty-five point gap. Two adjacent months of history show
the same shape, which maturation explains: a fresh cohort's downloads have not
had time to spread.

If maturation is the whole story, the gap should disappear once the two
samples are compared at **matched download levels**. A model with ten thousand
downloads is a model with ten thousand downloads, whenever it was uploaded. If
concentration still differs within those strata, something other than
maturation is producing it.

This is a control, not a proof
------------------------------
Stratifying on downloads conditions on a variable that is downstream of the
thing being measured: a model gets downloads partly *because* its base is
popular. Conditioning on a collider can create an association as easily as
remove one, and nothing here rules that out.

What the comparison does give is a direction. If the gap vanishes under the
control, maturation is sufficient and no structural claim is needed. If it
survives, maturation is not sufficient — which is weaker than saying structure
caused it, and is the most this design supports.

Why strata rather than a regression
-----------------------------------
Download counts span seven orders of magnitude and are heavily skewed. A linear
control would be dominated by a handful of models and a log transform would
impose a functional form the data has no reason to follow. Strata make the
comparison visible: a reader can see which buckets have enough models to carry
a figure and which do not.
"""

from __future__ import annotations

from dataclasses import dataclass

from .analyse import analyse

# Boundaries in downloads. Chosen as decades because the distribution spans
# seven of them; they are exposed rather than buried so a reader can see that
# the result does not hinge on where the lines fall.
STRATA = [(0, 100), (100, 1_000), (1_000, 10_000),
          (10_000, 100_000), (100_000, 10**9)]


@dataclass
class Stratum:
    lo: int
    hi: int
    n_a: int
    n_b: int
    share_a: float | None
    share_b: float | None
    dl_share_a: float | None
    dl_share_b: float | None

    @property
    def comparable(self) -> bool:
        """Both sides need enough models for a share to mean anything."""
        return self.n_a >= 30 and self.n_b >= 30

    @property
    def gap(self) -> float | None:
        if not self.comparable or self.share_a is None or self.share_b is None:
            return None
        return self.share_a - self.share_b

    @property
    def dl_gap(self) -> float | None:
        if not self.comparable or self.dl_share_a is None or self.dl_share_b is None:
            return None
        return self.dl_share_a - self.dl_share_b

    def label(self) -> str:
        hi = "∞" if self.hi >= 10**9 else f"{self.hi:,}"
        return f"{self.lo:,}–{hi}"

    def as_dict(self) -> dict:
        return {"lo": self.lo, "hi": self.hi, "label": self.label(),
                "n_a": self.n_a, "n_b": self.n_b,
                "share_a": self.share_a, "share_b": self.share_b,
                "dl_share_a": self.dl_share_a, "dl_share_b": self.dl_share_b,
                "comparable": self.comparable, "gap": self.gap,
                "dl_gap": self.dl_gap}


def _share(rows: list[dict]) -> tuple[float | None, float | None]:
    if len(rows) < 5:
        return None, None
    c = analyse(rows).concentration(3)
    return c["share_of_derivatives"], c["share_of_downloads"]


def stratify(a: list[dict], b: list[dict]) -> list[Stratum]:
    """Concentration within matched download bands."""
    out = []
    for lo, hi in STRATA:
        ra = [w for w in a if lo <= w.get("downloads", 0) < hi]
        rb = [w for w in b if lo <= w.get("downloads", 0) < hi]
        sa, da = _share(ra)
        sb, db = _share(rb)
        out.append(Stratum(lo=lo, hi=hi, n_a=len(ra), n_b=len(rb),
                           share_a=sa, share_b=sb,
                           dl_share_a=da, dl_share_b=db))
    return out


def verdict(strata: list[Stratum]) -> dict:
    """
    What the stratified comparison supports.

    The headline is whether the download-concentration gap survives inside
    strata. A gap that collapses means maturation is sufficient; one that
    persists means it is not.
    """
    usable = [s for s in strata if s.comparable]
    if not usable:
        return {"comparable_strata": 0,
                "note": ("no download band has enough models on both sides; "
                         "the two samples barely overlap in download level, "
                         "which is itself the maturation story")}

    gaps = [s.dl_gap for s in usable if s.dl_gap is not None]
    mean_gap = sum(gaps) / len(gaps) if gaps else 0.0

    # The non-overlap is the finding, and it is larger than anything inside
    # the one band where the samples meet. Saying "on average" over a single
    # stratum would dress one thin comparison as a summary of several.
    thinnest = min((min(s.n_a, s.n_b) for s in usable), default=0)
    single = len(usable) == 1

    if single:
        s0 = usable[0]
        text = (f"Only one download band — {s0.label()} — has enough models on "
                f"both sides, and the thinner side has {thinnest}. The samples "
                "barely overlap in download level at all, which IS the "
                "maturation story: freshly uploaded models have not had time "
                "to accumulate downloads, so there is almost nothing to match "
                f"them against. Inside that one band the gap is "
                f"{s0.dl_gap*100:+.1f} points, which is suggestive and rests "
                f"on {thinnest} models.")
    elif abs(mean_gap) < 0.08:
        text = (f"Across {len(usable)} matched download bands the gap collapses "
                f"to {mean_gap*100:+.1f} points, from 25.7 unmatched. "
                "Maturation is sufficient to explain it and no structural "
                "claim is needed.")
    else:
        text = (f"Across {len(usable)} matched download bands the gap is still "
                f"{mean_gap*100:+.1f} points. Maturation alone does not account "
                "for it — which is weaker than saying structure does, and is "
                "the most this design supports.")

    return {
        "comparable_strata": len(usable),
        "single_band_only": single,
        "thinnest_side": thinnest,
        "bands": [s.label() for s in usable],
        "mean_download_gap": mean_gap,
        "unmatched_gap": 0.257,
        "verdict": text,
        "caveat": ("Downloads are downstream of base popularity, so this "
                   "conditions on a collider. It gives a direction, not a "
                   "causal answer. And with the samples overlapping in one "
                   "band, the control is weak wherever it is not absent."),
    }
