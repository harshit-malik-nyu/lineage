"""
Is concentration changing, or just differently measured?

What the two-sample comparison left open
----------------------------------------
Recently uploaded models are fifteen points more concentrated than the popular
stock, confirmed at 4.8 standard deviations against sample-size noise. The
natural reading is that the ecosystem is concentrating over time.

That reading does not follow. A recency sample and a popularity sample differ
in two ways at once — *when* the models were uploaded and *how much* they are
used — so a gap between them cannot be attributed to either on its own.

Bucketing a single sample by upload date separates them. Within one sample,
selected the same way throughout, concentration by period is a trend or it is
not.

What a rising trend would and would not mean
---------------------------------------------
**Would:** newer models cluster on fewer bases than older ones did. That is a
statement about what is being built now.

**Would not:** that the ecosystem is becoming less resilient. Old derivatives
do not disappear when new ones arrive, so the installed base stays as diverse
as it was. A rising trend describes the flow and says nothing about the stock
except that the stock's composition will drift toward it.

The confound that cannot be removed
-----------------------------------
Base models have lifecycles. A base released eighteen months ago has had
eighteen months to accumulate derivatives; one released last month has had a
month. So the most recent period will always look concentrated around whatever
launched most recently, regardless of any underlying trend.

That is not a bias to correct away — it is a real property of how the ecosystem
works — but it means a single rising series is weak evidence. What would be
stronger is the trend persisting across periods that each had time to mature,
which needs a longer window than this sample covers.

Stated plainly: this measures a trend and cannot establish that it is secular
rather than a lifecycle artefact.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from .analyse import analyse


@dataclass
class Period:
    label: str
    n: int
    top3_share: float
    top3_downloads: float
    distinct_orgs: int
    top_root: str
    top_root_share: float

    def as_dict(self) -> dict:
        return {
            "label": self.label, "n": self.n,
            "top3_share": self.top3_share,
            "top3_downloads": self.top3_downloads,
            "distinct_orgs": self.distinct_orgs,
            "top_root": self.top_root,
            "top_root_share": self.top_root_share,
        }


def month_of(chain: dict) -> str | None:
    ts = chain.get("created_at")
    if not isinstance(ts, str) or len(ts) < 7:
        return None
    return ts[:7]


def by_period(chains: list[dict], min_n: int = 25) -> list[Period]:
    """
    Concentration within each upload month.

    Months with fewer than `min_n` chains are dropped rather than plotted,
    because a concentration figure over a dozen models is noise and a reader
    looking at a line chart will not know which points to distrust.
    """
    buckets: dict[str, list[dict]] = {}
    for c in chains:
        m = month_of(c)
        if m:
            buckets.setdefault(m, []).append(c)

    out = []
    for month in sorted(buckets):
        rows = buckets[month]
        if len(rows) < min_n:
            continue
        a = analyse(rows)
        conc = a.concentration(3)
        roots = Counter((w.get("root") or "").split("/")[0] for w in rows)
        top, cnt = roots.most_common(1)[0] if roots else ("", 0)
        out.append(Period(
            label=month, n=len(rows),
            top3_share=conc["share_of_derivatives"],
            top3_downloads=conc["share_of_downloads"],
            distinct_orgs=a.as_dict()["distinct_root_orgs"],
            top_root=top, top_root_share=cnt / len(rows),
        ))
    return out


def trend(periods: list[Period]) -> dict:
    """
    Direction and size of the change across periods.

    Reported as the first-to-last difference and a simple slope rather than a
    fitted model with a p-value: with a handful of monthly points, a
    regression would give a number far more precise than the data deserves.
    """
    if len(periods) == 2:
        # Two periods is a comparison, not a trend, and is reported as one.
        # The distinction matters because the download gap between adjacent
        # months is dominated by maturation: the newer month's downloads are
        # still accumulating and concentrate on whatever got attention first.
        a, b = periods
        return {
            "periods": 2,
            "is_trend": False,
            "first": {"label": a.label, "top3_share": a.top3_share,
                      "top3_downloads": a.top3_downloads},
            "last": {"label": b.label, "top3_share": b.top3_share,
                     "top3_downloads": b.top3_downloads},
            "model_share_change_points": (b.top3_share - a.top3_share) * 100,
            "download_share_change_points":
                (b.top3_downloads - a.top3_downloads) * 100,
            "verdict": _two_period_verdict(a, b),
            "caveat": ("Two adjacent months cannot separate a trend from "
                       "maturation. The newer month's models have had less "
                       "time to accumulate downloads, so their download "
                       "concentration reflects how fast early attention "
                       "concentrates, not how the ecosystem is changing."),
        }
    if len(periods) < 2:
        return {"periods": len(periods),
                "note": "too few periods with enough models to say anything"}

    shares = [p.top3_share for p in periods]
    orgs = [p.distinct_orgs for p in periods]
    n = len(shares)
    slope = (shares[-1] - shares[0]) / (n - 1)

    rising = sum(1 for a, b in zip(shares, shares[1:]) if b > a)
    monotone = rising == n - 1 or rising == 0

    return {
        "periods": n,
        "first": {"label": periods[0].label, "top3_share": shares[0]},
        "last": {"label": periods[-1].label, "top3_share": shares[-1]},
        "change_points": (shares[-1] - shares[0]) * 100,
        "slope_per_period": slope,
        "steps_rising": rising,
        "monotone": monotone,
        "distinct_orgs_first_last": [orgs[0], orgs[-1]],
        "verdict": _verdict(shares, rising, n),
        "caveat": ("Base models have lifecycles: a base released months ago "
                   "has had longer to accumulate derivatives, so the most "
                   "recent period looks concentrated around whatever launched "
                   "last regardless of any trend. This measures a trend and "
                   "cannot establish it is secular."),
    }


def _two_period_verdict(a: "Period", b: "Period") -> str:
    """
    What two adjacent months support, which is less than it looks.

    If model-count concentration is flat while download concentration jumps,
    the honest reading is maturation rather than structural change: downloads
    on month-old models are still concentrating, and a month later they will
    have spread.
    """
    m = (b.top3_share - a.top3_share) * 100
    d = (b.top3_downloads - a.top3_downloads) * 100
    if abs(m) < 5 and d > 10:
        return (f"Model-count concentration is flat between {a.label} and "
                f"{b.label} ({m:+.1f} points) while download concentration "
                f"rises {d:+.1f}. The newer month's downloads are still "
                "accumulating, so this is consistent with early attention "
                "concentrating and then spreading — maturation, not a "
                "structural change. Two adjacent months cannot tell them "
                "apart.")
    if abs(m) < 5:
        return (f"Both measures are flat between {a.label} and {b.label}. "
                "Nothing here suggests the ecosystem's structure is moving.")
    return (f"Model-count concentration moves {m:+.1f} points between "
            f"{a.label} and {b.label}. With two periods this is a comparison "
            "rather than a trend, and maturation is not ruled out.")


def _verdict(shares: list[float], rising: int, n: int) -> str:
    change = (shares[-1] - shares[0]) * 100
    if abs(change) < 5:
        return ("Concentration is flat across periods. The gap between the "
                "recency and popularity samples is about use, not about time.")
    if change > 0:
        return (f"Concentration rises {change:.1f} points across the window, "
                f"with {rising} of {n - 1} steps increasing. Consistent with "
                "newer models clustering on fewer bases — and also with the "
                "lifecycle artefact, which this cannot rule out.")
    return (f"Concentration falls {abs(change):.1f} points across the window. "
            "Newer uploads are spread across more bases than older ones.")
