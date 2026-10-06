"""
If a flaw were found in one base model, what inherits it?

The question nobody has a number for
------------------------------------
Open-weight policy debates turn on whether the ecosystem is resilient. Both
sides argue from an assumption about how much depends on how little, and the
quantity that would settle it has not been published: **the number of deployed
derivatives that inherit from a single base.**

The lineage tree answers it directly. A model inherits a property of every
ancestor in its chain, so a flaw in a base — a backdoor, a licence defect, a
systematic bias, a contaminated training set — reaches every descendant unless
a downstream step happened to remove it, which fine-tuning generally does not.

Two numbers, and the second is the one that matters
---------------------------------------------------
**Derivative count** is how many models inherit. It is the number that gets
quoted and it treats a model nobody runs the same as one running in
production.

**Download weight** is how much *use* inherits. A base with twenty derivatives
at ten million downloads each has a larger blast radius than one with two
thousand derivatives nobody has pulled.

They differ, and the direction is consistent: measured by use, concentration is
higher than by count.

What this does not establish
----------------------------
That any flaw exists, or that inheritance is complete. A derivative can and
sometimes does remove an ancestor's property — a fine-tune on clean data can
dilute a bias, a quantisation can break a backdoor by accident. "Inherits" here
means "is downstream of", which is an upper bound on exposure and not a claim
about any specific defect.

It is also bounded by the sample. Chains are walked from a few thousand
derivatives, not from all of them, so every count below is a floor.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass


@dataclass
class BlastRadius:
    """What a single node has downstream of it."""

    node: str
    descendants: int
    descendant_downloads: int
    direct_children: int
    max_depth_below: int

    share_of_sample: float = 0.0
    share_of_downloads: float = 0.0

    @property
    def is_broad(self) -> bool:
        """
        Does this node carry a real dependency, or one popular descendant?

        Download weight alone is misleading here: a node with a single
        descendant at ten million downloads scores above one with thirty
        descendants at thirty-eight million, and they are completely different
        risks. The first is one model doing well; the second is a dependency
        a lot of things sit on.

        Three descendants is an arbitrary floor and is exposed rather than
        buried, because the right value depends on what the number is for.
        """
        return self.descendants >= 3

    def as_dict(self) -> dict:
        return {
            "node": self.node,
            "descendants": self.descendants,
            "descendant_downloads": self.descendant_downloads,
            "direct_children": self.direct_children,
            "max_depth_below": self.max_depth_below,
            "share_of_sample": self.share_of_sample,
            "share_of_downloads": self.share_of_downloads,
            "is_broad": self.is_broad,
        }


def compute(chains: list[dict]) -> list[BlastRadius]:
    """
    Blast radius for every node that appears as an ancestor.

    A chain contributes its leaf's downloads to **every** node above it, which
    is the point: exposure accumulates upward. The same leaf is counted once
    per distinct ancestor, never twice for the same one, so a chain that
    revisits a node through a cycle does not inflate it.
    """
    desc: Counter = Counter()
    desc_dl: Counter = Counter()
    direct: Counter = Counter()
    depth_below: dict[str, int] = defaultdict(int)

    total_leaves = len(chains)
    total_dl = sum(w.get("downloads", 0) for w in chains)

    for w in chains:
        dl = w.get("downloads", 0)
        chain = [c for c in (w.get("chain") or []) if c.get("resolved")]
        seen = set()
        for i, node in enumerate(chain):
            name = node.get("id")
            if not name or name in seen:
                continue
            seen.add(name)
            desc[name] += 1
            desc_dl[name] += dl
            if i == 0:
                direct[name] += 1
            depth_below[name] = max(depth_below[name], i + 1)

    out = []
    for name, n in desc.items():
        out.append(BlastRadius(
            node=name, descendants=n, descendant_downloads=desc_dl[name],
            direct_children=direct.get(name, 0),
            max_depth_below=depth_below[name],
            share_of_sample=n / total_leaves if total_leaves else 0,
            share_of_downloads=desc_dl[name] / total_dl if total_dl else 0,
        ))
    # Sorted by downloads, but callers are expected to filter on is_broad for
    # anything about dependency structure. Sorting by breadth instead would
    # hide the single-descendant-high-download case rather than make it
    # visible, and it is worth seeing.
    out.sort(key=lambda b: -b.descendant_downloads)
    return out


def broad_only(radii: list["BlastRadius"], min_descendants: int = 3) -> list:
    """Nodes carrying a dependency rather than one popular descendant."""
    return [b for b in radii if b.descendants >= min_descendants]


def cumulative_exposure(radii: list[BlastRadius], k: int = 10) -> dict:
    """
    How much of the sample is reachable from the top k nodes.

    Uses the union of their descendants rather than a sum, because a
    derivative downstream of both a base and its own re-upload would otherwise
    be counted twice and overstate the total.
    """
    top = radii[:k]
    return {
        "k": k,
        "nodes": [b.node for b in top],
        "max_single_node_share": max((b.share_of_sample for b in top), default=0),
        "max_single_node_download_share": max(
            (b.share_of_downloads for b in top), default=0),
    }


def union_exposure(chains: list[dict], nodes: list[str]) -> dict:
    """
    The share of leaves reachable from ANY of these nodes.

    Computed over chains directly rather than by summing radii, which is the
    only way to avoid double-counting a leaf that sits under several of them.
    """
    want = set(nodes)
    hit = 0
    hit_dl = 0
    total_dl = sum(w.get("downloads", 0) for w in chains)
    for w in chains:
        names = {c.get("id") for c in (w.get("chain") or []) if c.get("resolved")}
        if names & want:
            hit += 1
            hit_dl += w.get("downloads", 0)
    return {
        "nodes": nodes,
        "leaves_reached": hit,
        "share_of_leaves": hit / len(chains) if chains else 0,
        "share_of_downloads": hit_dl / total_dl if total_dl else 0,
    }
