#!/usr/bin/env python3
"""
Does the lineage metadata exist before anything is designed around it?

The project assumes derivatives declare their ancestry. If `base_model` tags
are sparse, inconsistent, or absent on the models that matter, there is no
tree to walk and the project dies here — which is the right outcome, found in
minutes rather than after a day of building.

Four questions, in the order that kills the project fastest:

    1. is the API reachable and unauthenticated?
    2. do models carry a base_model tag at all?
    3. what share of popular models carry one?
    4. do the tags resolve to real models, or to names that no longer exist?
"""

from __future__ import annotations

import json
import sys
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
            with urllib.request.urlopen(req, timeout=40) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < retries - 1:
                time.sleep(5 * (attempt + 1))
                continue
            return {"__error__": f"HTTP {e.code}"}
        except Exception as exc:                        # noqa: BLE001
            return {"__error__": type(exc).__name__}
    return {"__error__": "exhausted"}


def main() -> int:
    out: dict = {"probed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}

    print("1. reachable and unauthenticated?", flush=True)
    one = get("models", {"limit": 1})
    ok = isinstance(one, list) and one
    print(f"   {'yes' if ok else 'NO: ' + str(one)[:120]}")
    out["reachable"] = bool(ok)
    if not ok:
        print(json.dumps(out, indent=2))
        return 1

    print("\n2. what does a model record carry?", flush=True)
    sample = get("models", {"limit": 20, "sort": "downloads", "direction": -1,
                            "full": "true"})
    keys = Counter()
    for m in sample if isinstance(sample, list) else []:
        keys.update(m.keys())
    print("   fields present on the 20 most-downloaded:")
    for k, v in keys.most_common():
        print(f"     {k:28s} {v}/20")
    out["record_fields"] = dict(keys)

    print("\n3. do they declare a base model?", flush=True)
    # base_model lives in cardData or in tags as 'base_model:...'
    declared, examples = 0, []
    for m in sample if isinstance(sample, list) else []:
        card = m.get("cardData") or {}
        base = card.get("base_model")
        tagbase = [t for t in (m.get("tags") or [])
                   if isinstance(t, str) and t.startswith("base_model")]
        if base or tagbase:
            declared += 1
            if len(examples) < 5:
                examples.append({"id": m.get("id"), "cardData_base": base,
                                 "tags": tagbase[:3]})
    print(f"   {declared}/20 of the most-downloaded declare a base model")
    for e in examples:
        print(f"     {e['id'][:46]:48s} {str(e['cardData_base'])[:34]}")
    out["declared_on_top20"] = declared
    out["examples"] = examples

    print("\n4. how common is it across a wider slice?", flush=True)
    wide = get("models", {"limit": 200, "sort": "downloads", "direction": -1,
                          "full": "true"})
    n = len(wide) if isinstance(wide, list) else 0
    with_base = sum(
        1 for m in (wide if isinstance(wide, list) else [])
        if (m.get("cardData") or {}).get("base_model")
        or any(isinstance(t, str) and t.startswith("base_model")
               for t in (m.get("tags") or [])))
    print(f"   {with_base}/{n} of the top {n} by downloads declare a base model")
    out["wide_sample"] = {"n": n, "with_base_model": with_base,
                          "share": with_base / n if n else 0}

    print("\n5. can the tree be walked? (does a declared base resolve?)", flush=True)
    resolved = 0
    for e in examples[:3]:
        name = e["cardData_base"]
        if isinstance(name, list):
            name = name[0] if name else None
        if not isinstance(name, str):
            continue
        r = get(f"models/{name}")
        got = isinstance(r, dict) and "id" in r
        resolved += bool(got)
        print(f"   {name[:50]:52s} {'resolves' if got else 'MISSING'}")
    out["resolution_checked"] = resolved

    print()
    print(json.dumps(out["wide_sample"], indent=2))
    with open("evidence/probe.json", "w") as f:
        json.dump(out, f, indent=2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
