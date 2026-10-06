"""
What the lineage tree shows, measured on 400 walked chains.

Three questions, and the third needs more care than it first appears.

Concentration
-------------
Counting derivatives understates it. Of 400 chains walked, 39.8% trace to a
Qwen model and **55.5% of the downloads do**. Weighting by use rather than by
model count moves the figure by sixteen points, in the direction that matters:
the ecosystem is more concentrated in what people actually run than in what
exists.

Depth
-----
43.2% of chains pass through at least one intermediary. The deepest observed
runs eight links. That matters because an intermediary is usually a third
party's re-upload or quantisation — so a consumer of the leaf inherits from
someone whose name never appears on the model they chose.

Licence
-------
20.9% of chains where both ends declare a licence declare **different** ones.
That figure is easy to report and wrong to call a violation, which is why this
module does not.

A derivative may lawfully carry a different licence from its ancestor. MIT and
Apache-2.0 both permit relicensing under more restrictive terms, so
`MIT -> Apache-2.0` is ordinary and correct. What is worth flagging is the
opposite direction: a leaf claiming terms more permissive than an ancestor
grants. That is a potential problem, and still only potential — the ancestor's
terms may permit it, the model card may be wrong rather than the licence, and
"other" covers everything from a bespoke research licence to an unfilled form.

So this reports three categories and refuses to collapse them into a
violation count.
"""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

# Ordered by permissiveness. Only relationships WITHIN this set can be judged;
# anything outside it is unknown, and "other" is deliberately outside because
# it covers bespoke terms that cannot be ranked.
PERMISSIVENESS = {
    "mit": 4,
    "apache-2.0": 4,
    "bsd-3-clause": 4,
    "cc-by-4.0": 3,
    "openrail": 2,
    "openrail++": 2,
    "creativeml-openrail-m": 2,
    "cc-by-nc-4.0": 1,
    "cc-by-nc-sa-4.0": 1,
}

# Licences whose text does not let a downstream user widen the grant.
NAMED_RESTRICTIVE = {"gemma", "llama2", "llama3", "llama3.1", "llama3.2",
                     "llama3.3", "gpl-3.0", "agpl-3.0", "cc-by-nc-4.0",
                     "cc-by-nc-sa-4.0"}


@dataclass
class LicenceFinding:
    leaf_id: str
    leaf_licence: str
    root_licence: str
    downloads: int
    category: str
    note: str

    def as_dict(self) -> dict:
        return {"leaf": self.leaf_id, "leaf_licence": self.leaf_licence,
                "root_licence": self.root_licence, "downloads": self.downloads,
                "category": self.category, "note": self.note}


def classify_licence_pair(leaf: str, root: str) -> tuple[str, str]:
    """
    How does the leaf's declared licence relate to its ancestor's?

    Returns (category, note). The categories are deliberately coarse, because
    the data does not support fine ones: a model card is a claim, not a legal
    instrument, and "other" is a text box.
    """
    if leaf == root:
        return "consistent", "same licence declared at both ends"

    if root in NAMED_RESTRICTIVE and leaf in PERMISSIVENESS:
        return ("widens", f"leaf claims {leaf} while the ancestor is {root}, "
                          "which does not grant that")

    lp, rp = PERMISSIVENESS.get(leaf), PERMISSIVENESS.get(root)
    if lp is not None and rp is not None:
        if lp > rp:
            return ("widens", f"leaf claims {leaf}, more permissive than the "
                              f"ancestor's {root}")
        return ("narrows", f"leaf claims {leaf}, no wider than the ancestor's "
                           f"{root} — permitted")

    # One or both sit outside the rankable set. "other" is the common case and
    # it is a text box, not a licence, so nothing can be concluded.
    return ("unrankable", f"{leaf} against {root}: at least one is not a "
                          "licence that can be ranked")


@dataclass
class Analysis:
    chains: int = 0
    total_downloads: int = 0

    by_org_count: Counter = field(default_factory=Counter)
    by_org_downloads: Counter = field(default_factory=Counter)
    depths: Counter = field(default_factory=Counter)

    licence_categories: Counter = field(default_factory=Counter)
    licence_findings: list[LicenceFinding] = field(default_factory=list)

    unresolved: int = 0
    cycles: int = 0

    def concentration(self, k: int = 3) -> dict:
        top = self.by_org_count.most_common(k)
        c = sum(n for _, n in top)
        d = sum(self.by_org_downloads[o] for o, _ in top)
        return {
            "k": k,
            "orgs": [o for o, _ in top],
            "share_of_derivatives": c / self.chains if self.chains else 0,
            "share_of_downloads": d / self.total_downloads if self.total_downloads else 0,
        }

    @property
    def through_intermediary(self) -> float:
        deep = sum(v for k, v in self.depths.items() if k >= 2)
        return deep / self.chains if self.chains else 0

    def as_dict(self) -> dict:
        return {
            "chains": self.chains,
            "distinct_root_orgs": len(self.by_org_count),
            "concentration_top3": self.concentration(3),
            "concentration_top5": self.concentration(5),
            "through_intermediary": self.through_intermediary,
            "max_depth": max(self.depths) if self.depths else 0,
            "depth_distribution": dict(sorted(self.depths.items())),
            "licence_categories": dict(self.licence_categories),
            "widening_count": self.licence_categories.get("widens", 0),
            "unresolved_parents": self.unresolved,
            "cycles": self.cycles,
        }


def analyse(chains: list[dict]) -> Analysis:
    a = Analysis(chains=len(chains))

    for w in chains:
        org = (w.get("root") or "").split("/")[0]
        dl = w.get("downloads", 0)
        a.by_org_count[org] += 1
        a.by_org_downloads[org] += dl
        a.total_downloads += dl
        a.depths[w.get("depth", 0)] += 1
        if w.get("missing_parent"):
            a.unresolved += 1
        if w.get("cycle"):
            a.cycles += 1

        leaf = w.get("license")
        root_lic = None
        for node in reversed(w.get("chain") or []):
            if node.get("resolved") and node.get("license"):
                root_lic = node["license"]
                break
        if not leaf or not root_lic:
            a.licence_categories["undeclared"] += 1
            continue

        cat, note = classify_licence_pair(leaf, root_lic)
        a.licence_categories[cat] += 1
        if cat == "widens":
            a.licence_findings.append(LicenceFinding(
                leaf_id=w["id"], leaf_licence=leaf, root_licence=root_lic,
                downloads=dl, category=cat, note=note))

    a.licence_findings.sort(key=lambda f: -f.downloads)
    return a


def load(path: str | Path | None = None) -> list[dict]:
    p = Path(path) if path else ROOT / "evidence" / "derivatives.json"
    return json.loads(p.read_text())
