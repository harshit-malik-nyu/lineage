#!/usr/bin/env python3
"""
Does the lineage metadata support a tree?

The first probe found the API open and 37% of the top 200 models declaring a
base. That number is not yet interpretable: many of the most-downloaded models
ARE bases, and correctly declare no parent. The question is what share of
DERIVATIVES declare their ancestry, and whether those declarations resolve.

It also found the declaration is not where it was looked for. `cardData` is
absent from the list endpoint; lineage appears in `tags` as `base_model:NAME`.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter

API = "https://huggingface.co/api"


def get(path: str, params: dict | None = None, retries: int = 3):
    url = f"{API}/{path}"
    if params:
        url += "?" + urllib.parse.urlencode(params, doseq=True)
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "lineage-probe"})
            with urllib.request.urlopen(req, timeout=45) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < retries - 1:
                time.sleep(6 * (attempt + 1))
                continue
            return {"__error__": f"HTTP {e.code}"}
        except Exception as exc:                        # noqa: BLE001
            return {"__error__": type(exc).__name__}
    return {"__error__": "exhausted"}


def bases_from_tags(m: dict) -> list[str]:
    """Lineage is declared in tags as base_model:NAME or base_model:ROLE:NAME."""
    out = []
    for t in m.get("tags") or []:
        if isinstance(t, str) and t.startswith("base_model:"):
            parts = t.split(":")
            name = parts[-1]
            if "/" in name:
                out.append(name)
    return out


def main() -> int:
    out: dict = {"probed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}

    print("1. coverage by slice (how many declare a parent?)\n", flush=True)
    slices = {
        "top by downloads": {"sort": "downloads", "direction": -1},
        "top by likes": {"sort": "likes", "direction": -1},
        "recently created": {"sort": "createdAt", "direction": -1},
    }
    cov = {}
    for label, params in slices.items():
        data = get("models", {**params, "limit": 300, "full": "true"})
        rows = data if isinstance(data, list) else []
        declared = sum(1 for m in rows if bases_from_tags(m))
        cov[label] = {"n": len(rows), "declared": declared,
                      "share": declared / len(rows) if rows else 0}
        print(f"   {label:20s} {declared:>4}/{len(rows):<4} {cov[label]['share']:>7.1%}")
    out["coverage"] = cov

    print("\n2. among models that are PLAINLY derivatives\n", flush=True)
    # Adapters and merges are derivative by construction: a LoRA has a base.
    for tag in ("lora", "peft", "merge", "gguf"):
        data = get("models", {"filter": tag, "sort": "downloads",
                              "direction": -1, "limit": 200, "full": "true"})
        rows = data if isinstance(data, list) else []
        declared = sum(1 for m in rows if bases_from_tags(m))
        share = declared / len(rows) if rows else 0
        print(f"   {tag:8s} {declared:>4}/{len(rows):<4} {share:>7.1%}")
        out.setdefault("derivative_coverage", {})[tag] = {
            "n": len(rows), "declared": declared, "share": share}

    print("\n3. do declared parents resolve, and how deep does it go?\n", flush=True)
    data = get("models", {"filter": "lora", "sort": "downloads",
                          "direction": -1, "limit": 40, "full": "true"})
    rows = [m for m in (data if isinstance(data, list) else []) if bases_from_tags(m)]
    resolved = missing = 0
    depths = []
    for m in rows[:12]:
        chain, seen, node = [], set(), m
        while True:
            bases = bases_from_tags(node)
            if not bases:
                break
            parent = bases[0]
            if parent in seen:
                chain.append(f"{parent} (CYCLE)")
                break
            seen.add(parent)
            chain.append(parent)
            r = get(f"models/{parent}")
            if not (isinstance(r, dict) and "id" in r):
                missing += 1
                chain[-1] += " (MISSING)"
                break
            resolved += 1
            node = r
            if len(chain) >= 6:
                break
        depths.append(len(chain))
        print(f"   {m['id'][:34]:36s} -> {' -> '.join(c[:30] for c in chain)}")
    out["resolution"] = {"resolved": resolved, "missing": missing,
                         "depths": depths,
                         "max_depth": max(depths) if depths else 0}

    print("\n4. concentration: which bases do the derivatives point at?\n", flush=True)
    roots = Counter()
    data = get("models", {"filter": "lora", "sort": "downloads",
                          "direction": -1, "limit": 300, "full": "true"})
    for m in (data if isinstance(data, list) else []):
        for b in bases_from_tags(m):
            roots[b.split("/")[0]] += 1
    for org, c in roots.most_common(8):
        print(f"   {org:30s} {c}")
    out["top_parent_orgs"] = dict(roots.most_common(15))

    with open("evidence/probe.json", "w") as f:
        json.dump(out, f, indent=2)
    print("\nwritten to evidence/probe.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
