"""
Tests for blast radius.

The central one pins a distinction the first version of this module got wrong:
download weight alone ranks a node with one very popular descendant above a
node that thirty models actually depend on, and those are different risks.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from lineage.blast import broad_only, compute, union_exposure

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def chains():
    p = ROOT / "evidence" / "derivatives.json"
    if not p.exists():
        pytest.skip("no collected data")
    return json.loads(p.read_text())


def chain(leaf, dl, ancestors):
    return {"id": leaf, "downloads": dl,
            "chain": [{"id": a, "resolved": True} for a in ancestors]}


class TestComputation:

    def test_exposure_accumulates_upward(self):
        """
        A leaf's downloads count toward every ancestor, because a flaw at any
        level reaches it.
        """
        r = {b.node: b for b in compute([chain("leaf", 100, ["mid", "base"])])}
        assert r["mid"].descendant_downloads == 100
        assert r["base"].descendant_downloads == 100

    def test_a_leaf_is_counted_once_per_ancestor(self):
        """
        A chain that revisits a node must not inflate it. Cycles exist in this
        data — two models can declare each other through a re-upload.
        """
        r = {b.node: b for b in compute([chain("leaf", 10, ["a", "b", "a"])])}
        assert r["a"].descendants == 1

    def test_direct_children_are_distinguished_from_descendants(self):
        rows = [chain("x", 1, ["mid", "base"]), chain("y", 1, ["base"])]
        r = {b.node: b for b in compute(rows)}
        assert r["base"].descendants == 2
        assert r["base"].direct_children == 1

    def test_unresolved_ancestors_are_skipped(self):
        """
        A parent that no longer exists cannot be reasoned about, and counting
        it would attribute exposure to a name rather than a model.
        """
        rows = [{"id": "leaf", "downloads": 5,
                 "chain": [{"id": "gone", "resolved": False}]}]
        assert compute(rows) == []


class TestBreadthVersusPopularity:

    def test_one_popular_descendant_is_not_a_dependency(self):
        """
        THE CORRECTION. A node with a single descendant at ten million
        downloads outranks one with thirty descendants on download weight
        alone, and they are completely different risks: the first is one model
        doing well, the second is something a lot of things sit on.
        """
        rows = [chain("hit", 10_000_000, ["narrow"])]
        rows += [chain(f"d{i}", 100_000, ["broad"]) for i in range(30)]
        r = compute(rows)
        assert r[0].node == "narrow", "download weight should still rank it first"
        assert not r[0].is_broad
        broad = broad_only(r)
        assert [b.node for b in broad] == ["broad"]

    def test_the_threshold_is_exposed_not_buried(self):
        rows = [chain(f"d{i}", 1, ["n"]) for i in range(3)]
        assert broad_only(compute(rows), min_descendants=4) == []
        assert len(broad_only(compute(rows), min_descendants=3)) == 1

    def test_the_rationale_is_documented(self):
        import inspect

        from lineage.blast import BlastRadius
        doc = " ".join(inspect.getdoc(BlastRadius.is_broad.fget).split())
        assert "one popular descendant" in doc
        assert "arbitrary floor" in doc


class TestUnion:

    def test_a_leaf_under_two_nodes_is_counted_once(self):
        """
        Summing radii would double-count a derivative sitting under both a
        base and its own re-upload, overstating the total.
        """
        rows = [chain("leaf", 100, ["mid", "base"])]
        u = union_exposure(rows, ["mid", "base"])
        assert u["leaves_reached"] == 1
        assert u["share_of_leaves"] == 1.0

    def test_union_grows_with_more_nodes(self):
        rows = [chain("a", 1, ["x"]), chain("b", 1, ["y"])]
        assert union_exposure(rows, ["x"])["leaves_reached"] == 1
        assert union_exposure(rows, ["x", "y"])["leaves_reached"] == 2


class TestMeasured:

    def test_a_single_base_carries_a_large_share(self, chains):
        b = broad_only(compute(chains))
        assert b, "no broad dependency nodes found"
        assert b[0].share_of_downloads > 0.1

    def test_a_handful_of_nodes_reach_a_third_of_use(self, chains):
        b = broad_only(compute(chains))
        u = union_exposure(chains, [x.node for x in b[:5]])
        assert u["share_of_downloads"] > 0.2

    def test_counts_are_a_floor_not_a_total(self, chains):
        """
        Chains are walked from a sample, so every count is a lower bound. The
        module docstring has to say so rather than let the figures read as
        totals.
        """
        import lineage.blast as bl
        doc = " ".join(bl.__doc__.split())
        assert "every count below is a floor" in doc
        assert "upper bound on exposure" in doc
