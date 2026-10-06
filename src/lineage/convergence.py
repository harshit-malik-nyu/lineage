"""
Has the estimate settled, or is it still moving?

Why this exists
---------------
Tripling the sample from 400 to 1,200 chains moved the top-three concentration
figure by eleven points and tripled the count of distinct root organisations.
That is a useful warning and a useless stopping rule: it says the small sample
was wrong without saying whether the large one is right.

The question is answerable from the data already collected. Subsample the 1,200
chains at a range of sizes, recompute the statistic many times at each, and
look at the spread. An estimate that has converged shows a spread narrowing
toward zero; one that has not shows a spread that is still wide at the full
sample size, or a centre that is still drifting with n.

What this cannot do
-------------------
Subsampling tells you about sampling variance **within the population you
collected**. It cannot tell you that the population is right. If the collection
itself is biased — and `docs/against.md` argues it is, because chains are drawn
from the most-downloaded models — then every subsample inherits that bias and
converges neatly to the wrong number.

So a narrow spread here means "more of the same data would not move this", not
"this is the truth about HuggingFace". Those are different claims and the
second is not available from this design.

Which statistics are worth testing
----------------------------------
Not all of them behave alike:

    share statistics      concentration, intermediary share. Bounded, and
                          expected to converge quickly.
    count statistics      distinct root organisations. Unbounded, and expected
                          NOT to converge — every new chain can introduce an
                          organisation never seen before, so the count rises
                          with n indefinitely.
    rare-event rates      licence widening at 1.67%. Twenty events in 1,200,
                          so the estimate is noisy by construction and the
                          spread should be wide.

Reporting all three together is the point. A reader who sees only the share
statistics converge would conclude the sample is adequate, when the count
statistic is telling them the population has a tail they have not reached.
"""

from __future__ import annotations

import random
import statistics
from dataclasses import dataclass, field

from .analyse import analyse


@dataclass
class Curve:
    """How one statistic behaves as the sample grows."""

    name: str
    sizes: list[int] = field(default_factory=list)
    means: list[float] = field(default_factory=list)
    spreads: list[float] = field(default_factory=list)
    lo: list[float] = field(default_factory=list)
    hi: list[float] = field(default_factory=list)

    @property
    def converged(self) -> bool:
        """
        Has the spread stopped shrinking meaningfully?

        Compares the spread at the largest size against the midpoint one. A
        statistic still halving its spread between those has not settled.

        This is a heuristic and is labelled as one — there is no test for
        convergence that does not smuggle in an assumption about the
        underlying distribution.
        """
        if len(self.spreads) < 3:
            return False
        mid = self.spreads[len(self.spreads) // 2]
        last = self.spreads[-1]
        if mid <= 0:
            return True
        return last / mid > 0.6

    @property
    def drifting(self) -> bool:
        """Is the CENTRE still moving, not just the spread narrowing?"""
        if len(self.means) < 3:
            return False
        early, late = self.means[len(self.means) // 3], self.means[-1]
        if early == 0:
            return late != 0
        return abs(late - early) / abs(early) > 0.15

    def as_dict(self) -> dict:
        return {
            "name": self.name, "sizes": self.sizes,
            "means": self.means, "spreads": self.spreads,
            "lo": self.lo, "hi": self.hi,
            "converged": self.converged, "drifting": self.drifting,
        }


STATISTICS = {
    "top3_share_of_derivatives":
        lambda ch: analyse(ch).concentration(3)["share_of_derivatives"],
    "top3_share_of_downloads":
        lambda ch: analyse(ch).concentration(3)["share_of_downloads"],
    "through_intermediary":
        lambda ch: analyse(ch).through_intermediary,
    "distinct_root_orgs":
        lambda ch: float(analyse(ch).as_dict()["distinct_root_orgs"]),
    "licence_widening_rate":
        lambda ch: analyse(ch).as_dict()["widening_count"] / max(1, len(ch)),
}


def curve(chains: list[dict], stat: str, sizes: list[int] | None = None,
          trials: int = 40, seed: int = 0) -> Curve:
    """
    Resample at each size and record the spread.

    Sampling is WITHOUT replacement, so at the full size every trial returns
    the same answer and the spread is exactly zero. That is correct and worth
    seeing: it marks the point past which this data cannot inform the
    question.
    """
    fn = STATISTICS[stat]
    n = len(chains)
    sizes = sizes or [s for s in (50, 100, 200, 400, 800, n) if s <= n]
    rng = random.Random(seed)
    c = Curve(name=stat)

    for size in sizes:
        vals = []
        for _ in range(trials if size < n else 1):
            vals.append(fn(rng.sample(chains, size)))
        c.sizes.append(size)
        c.means.append(statistics.fmean(vals))
        c.spreads.append(statistics.pstdev(vals) if len(vals) > 1 else 0.0)
        c.lo.append(min(vals))
        c.hi.append(max(vals))
    return c


def report(chains: list[dict], trials: int = 40, seed: int = 0) -> dict:
    """Every statistic, with a verdict on each."""
    out = {}
    for name in STATISTICS:
        out[name] = curve(chains, name, trials=trials, seed=seed).as_dict()
    return out
