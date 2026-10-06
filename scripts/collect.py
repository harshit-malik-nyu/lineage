#!/usr/bin/env python3
"""
Walk the open-weight lineage tree and record what was found.

What the probe established
--------------------------
Lineage is declared in tags as `base_model:NAME`, not in `cardData`, which the
list endpoint does not return. Coverage is 30-36% across the top models overall
and **83-95% among models that are derivatives by construction** — LoRAs, PEFT
adapters, merges and GGUF quantisations, each of which has a parent by
definition. The low overall figure is base models correctly declaring none.

Chains resolve and have depth. One observed:

    Qwopus3.6-35B-Coder -> Qwopus3.6-v1 -> unsloth/Qwen3.6-35B -> Qwen/Qwen3.6-35B

a derivative of a derivative of a re-upload of a base. Intermediaries matter:
the middle link is a third party's copy, so a consumer of the leaf inherits
from someone they have never heard of.

What this collects
------------------
Derivatives across several construction types, then each one's chain walked to
a root. Downloads travel with the node, because concentration weighted by use
is a different number from concentration by model count, and the second is
easy and misleading.

Cost is recorded
----------------
The API is unauthenticated and rate-limited in practice rather than by a
published number. Every run records requests spent, models seen, chains walked
and resolution failures, so a later claim about coverage can be checked against
what was actually bought.
"""

from __future__ import annotations

import argparse
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from pathlib import Path

API = "https://huggingface.co/api"
ROOT = Path(__file__).resolve().parents[1]

# Tags that make a model a derivative by construction. Each has a parent by
# definition, so absence of a declaration is a reporting gap rather than
# evidence the model is original.
DERIVATIVE_TAGS = ("lora", "peft", "merge", "gguf", "adapter")


class Client:
    def __init__(self, pause: float = 0.25):
        self.pause = pause
        self.requests = 0
        self.errors: list[dict] = []
        self.cache: dict[str, dict] = {}

    def get(self, path: str, params: dict | None = None, retries: int = 3):
        url = f"{API}/{path}"
        if params:
            url += "?" + urllib.parse.urlencode(params, doseq=True)
        for attempt in range(retries):
            self.requests += 1
            try:
                req = urllib.request.Request(
                    url, headers={"User-Agent": "lineage-collector"})
                with urllib.request.urlopen(req, timeout=45) as r:
                    time.sleep(self.pause)
                    return json.loads(r.read())
            except urllib.error.HTTPError as e:
                if e.code == 429 and attempt < retries - 1:
                    time.sleep(8 * (attempt + 1))
                    continue
                self.errors.append({"path": path, "status": e.code})
                return None
            except Exception as exc:                    # noqa: BLE001
                self.errors.append({"path": path, "error": type(exc).__name__})
                return None
        return None

    def model(self, name: str) -> dict | None:
        """Cached single-model fetch; chains revisit the same parents often."""
        if name in self.cache:
            return self.cache[name]
        m = self.get(f"models/{name}")
        if isinstance(m, dict) and "id" in m:
            self.cache[name] = m
            return m
        self.cache[name] = {}
        return None


def parents(m: dict) -> list[str]:
    """Declared parents, from tags of the form base_model[:role]:OWNER/NAME."""
    out = []
    for t in m.get("tags") or []:
        if isinstance(t, str) and t.startswith("base_model:"):
            name = t.split(":")[-1]
            if "/" in name:
                out.append(name)
    return out


def licence(m: dict) -> str | None:
    for t in m.get("tags") or []:
        if isinstance(t, str) and t.startswith("license:"):
            return t.split(":", 1)[1]
    return None


def walk(client: Client, m: dict, max_depth: int = 8) -> dict:
    """
    Follow one model's chain to a root.

    Cycles are possible — two models can declare each other, usually through a
    re-upload — and are recorded rather than followed, because a cycle is a
    data-quality finding and not an error to swallow.
    """
    chain, seen = [], {m.get("id")}
    node, truncated, cycle, missing = m, False, False, None

    for _ in range(max_depth):
        ps = parents(node)
        if not ps:
            break
        parent_name = ps[0]
        if parent_name in seen:
            cycle = True
            break
        seen.add(parent_name)
        parent = client.model(parent_name)
        if parent is None:
            missing = parent_name
            chain.append({"id": parent_name, "resolved": False})
            break
        chain.append({
            "id": parent_name, "resolved": True,
            "downloads": parent.get("downloads", 0),
            "license": licence(parent),
            "n_parents": len(parents(parent)),
        })
        node = parent
    else:
        truncated = True

    return {
        "id": m.get("id"),
        "downloads": m.get("downloads", 0),
        "likes": m.get("likes", 0),
        "license": licence(m),
        "tags_derivative": [t for t in DERIVATIVE_TAGS
                            if t in (m.get("tags") or [])],
        "chain": chain,
        "depth": len(chain),
        "root": chain[-1]["id"] if chain else m.get("id"),
        "root_resolved": chain[-1]["resolved"] if chain else True,
        "truncated": truncated,
        "cycle": cycle,
        "missing_parent": missing,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--per-tag", type=int, default=500)
    ap.add_argument("--walk", type=int, default=1200,
                    help="how many derivatives to walk to a root")
    ap.add_argument("--max-requests", type=int, default=6000)
    ap.add_argument("--out", default=str(ROOT / "evidence"))
    args = ap.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    client = Client()
    started = time.time()

    seen: dict[str, dict] = {}
    coverage: dict[str, dict] = {}

    print("collecting derivatives by construction type", flush=True)
    for tag in DERIVATIVE_TAGS:
        data = client.get("models", {"filter": tag, "sort": "downloads",
                                     "direction": -1, "limit": args.per_tag,
                                     "full": "true"})
        rows = data if isinstance(data, list) else []
        declared = sum(1 for m in rows if parents(m))
        coverage[tag] = {"n": len(rows), "declared": declared,
                         "share": declared / len(rows) if rows else 0}
        print(f"  {tag:8s} {declared:>4}/{len(rows):<4} declare a parent "
              f"({coverage[tag]['share']:.1%})", flush=True)
        for m in rows:
            if m.get("id") and m["id"] not in seen:
                seen[m["id"]] = m

    print(f"\n{len(seen):,} distinct derivatives collected", flush=True)

    walkable = [m for m in seen.values() if parents(m)]
    walkable.sort(key=lambda m: m.get("downloads", 0), reverse=True)
    walkable = walkable[:args.walk]

    print(f"walking {len(walkable):,} chains to a root", flush=True)
    walked = []
    for i, m in enumerate(walkable, 1):
        if client.requests > args.max_requests:
            print(f"  request budget reached at {i}", flush=True)
            break
        walked.append(walk(client, m))
        if i % 50 == 0:
            print(f"  {i}/{len(walkable)} ({client.requests} requests)", flush=True)

    (out / "derivatives.json").write_text(json.dumps(walked, indent=2))

    roots = Counter()
    root_dl = Counter()
    for w in walked:
        roots[w["root"]] += 1
        root_dl[w["root"]] += w["downloads"]

    manifest = {
        "collected_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "coverage_by_tag": coverage,
        "distinct_derivatives": len(seen),
        "chains_walked": len(walked),
        "requests": client.requests,
        "elapsed_s": round(time.time() - started, 1),
        "errors": client.errors[:20],
        "unresolved_parents": sum(1 for w in walked if w["missing_parent"]),
        "cycles": sum(1 for w in walked if w["cycle"]),
        "truncated": sum(1 for w in walked if w["truncated"]),
        "top_roots_by_count": roots.most_common(20),
        "top_roots_by_downloads": root_dl.most_common(20),
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2))

    print()
    print(f"  requests spent      {client.requests:,}")
    print(f"  chains walked       {len(walked):,}")
    print(f"  unresolved parents  {manifest['unresolved_parents']}")
    print(f"  cycles              {manifest['cycles']}")
    print(f"  truncated at depth  {manifest['truncated']}")
    print("\n  top roots by derivative count:")
    for name, c in roots.most_common(8):
        print(f"    {name[:48]:50s} {c:>5}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
