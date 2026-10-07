#!/usr/bin/env python3
"""
Reach back far enough to see whether concentration is changing.

The gap this fills
------------------
The recency sample's 1,500 dated models all fall in a single month: at current
upload rates, 24,000 models span under thirty days. Bucketing it by period
yields one bucket, so `trend.py` correctly declines to report.

Measuring a trend needs a window of months, which means paginating much deeper
into the date-sorted index. That is the only cost — the requests are cheap and
unauthenticated, there is just a lot of index between here and six months ago.

Why not sort ascending instead
------------------------------
Sorting by creation date ascending would reach the oldest models in one step.
It would also be useless: `base_model` tagging is a convention that postdates
the earliest models, so an ascending sample would show near-zero declared
lineage and the absence would be a fact about tagging history rather than
about the ecosystem.

This samples densely near the present and sparsely further back, which biases
precision rather than direction.

What it still cannot settle
---------------------------
Base models have lifecycles. One released six months ago has had six months to
accumulate derivatives; one released last month has had a month. So the most
recent bucket will look concentrated around whatever launched last, regardless
of trend. A rising series here is consistent with concentration increasing AND
with nothing changing except which base is new.

Distinguishing those needs each bucket to contain only derivatives of bases
that had equal time to mature, which this sampling cannot arrange.
"""

from __future__ import annotations

import argparse
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

API = "https://huggingface.co/api"
ROOT = Path(__file__).resolve().parents[1]


class Client:
    def __init__(self, pause: float = 0.12):
        self.pause = pause
        self.requests = 0
        self.errors: list[dict] = []
        self.cache: dict[str, dict] = {}
        self.next_url: str | None = None

    def get(self, path: str, params: dict | None = None, retries: int = 3):
        url = f"{API}/{path}"
        if params:
            url += "?" + urllib.parse.urlencode(params, doseq=True)
        return self.get_url(url, retries)

    def get_url(self, url: str, retries: int = 3):
        self.next_url = None
        for attempt in range(retries):
            self.requests += 1
            try:
                req = urllib.request.Request(
                    url, headers={"User-Agent": "lineage-history"})
                with urllib.request.urlopen(req, timeout=45) as r:
                    link = r.headers.get("Link") or ""
                    for part in link.split(","):
                        if 'rel="next"' in part:
                            self.next_url = part.split(";")[0].strip(" <>")
                    time.sleep(self.pause)
                    return json.loads(r.read())
            except urllib.error.HTTPError as e:
                if e.code == 429 and attempt < retries - 1:
                    time.sleep(10 * (attempt + 1))
                    continue
                self.errors.append({"url": url[:120], "status": e.code})
                return None
            except Exception as exc:                    # noqa: BLE001
                self.errors.append({"url": url[:120],
                                    "error": type(exc).__name__})
                return None
        return None

    def model(self, name: str) -> dict | None:
        if name in self.cache:
            return self.cache[name] or None
        m = self.get(f"models/{name}")
        ok = isinstance(m, dict) and "id" in m
        self.cache[name] = m if ok else {}
        return m if ok else None


def parents(m: dict) -> list[str]:
    out = []
    for t in m.get("tags") or []:
        if isinstance(t, str) and t.startswith("base_model:"):
            n = t.split(":")[-1]
            if "/" in n:
                out.append(n)
    return out


def licence(m: dict) -> str | None:
    for t in m.get("tags") or []:
        if isinstance(t, str) and t.startswith("license:"):
            return t.split(":", 1)[1]
    return None


def walk(client: Client, m: dict, max_depth: int = 8) -> dict:
    chain, seen = [], {m.get("id")}
    node, truncated, cycle, missing = m, False, False, None
    for _ in range(max_depth):
        ps = parents(node)
        if not ps:
            break
        pn = ps[0]
        if pn in seen:
            cycle = True
            break
        seen.add(pn)
        parent = client.model(pn)
        if parent is None:
            missing = pn
            chain.append({"id": pn, "resolved": False})
            break
        chain.append({"id": pn, "resolved": True,
                      "downloads": parent.get("downloads", 0),
                      "license": licence(parent),
                      "n_parents": len(parents(parent))})
        node = parent
    else:
        truncated = True
    return {"id": m.get("id"), "downloads": m.get("downloads", 0),
            "likes": m.get("likes", 0), "license": licence(m),
            "created_at": m.get("createdAt"),
            "chain": chain, "depth": len(chain),
            "root": chain[-1]["id"] if chain else m.get("id"),
            "root_resolved": chain[-1]["resolved"] if chain else True,
            "truncated": truncated, "cycle": cycle, "missing_parent": missing}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pages", type=int, default=3000,
                    help="cursor pages to traverse; each is 100 models")
    ap.add_argument("--keep-every", type=int, default=40,
                    help="keep one model per N scanned, to spread the sample")
    ap.add_argument("--walk", type=int, default=1400)
    ap.add_argument("--max-requests", type=int, default=9000)
    ap.add_argument("--out", default=str(ROOT / "evidence"))
    args = ap.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    client = Client()
    started = time.time()

    pool: dict[str, dict] = {}
    months: dict[str, int] = {}
    print(f"traversing up to {args.pages} cursor pages", flush=True)

    data = client.get("models", {"sort": "createdAt", "direction": -1,
                                 "limit": 100, "full": "true"})
    page = 0
    scanned = 0
    while data is not None and page < args.pages:
        rows = data if isinstance(data, list) else []
        if not rows:
            print(f"  index ends at page {page}", flush=True)
            break
        for m in rows:
            scanned += 1
            ca = m.get("createdAt")
            if isinstance(ca, str) and len(ca) >= 7:
                months[ca[:7]] = months.get(ca[:7], 0) + 1
            if scanned % args.keep_every == 0 and m.get("id"):
                pool[m["id"]] = m
        page += 1
        if page % 200 == 0:
            span = f"{min(months)} to {max(months)}" if months else "?"
            print(f"  page {page}: scanned {scanned:,}, pool {len(pool)}, "
                  f"span {span}", flush=True)
        if client.requests > args.max_requests or not client.next_url:
            if not client.next_url:
                print(f"  cursor ends at page {page}", flush=True)
            break
        data = client.get_url(client.next_url)

    span = f"{min(months)} to {max(months)}" if months else "none"
    print(f"\nscanned {scanned:,} models spanning {span}")
    print(f"months seen: {dict(sorted(months.items()))}", flush=True)

    declared = [m for m in pool.values() if parents(m)]
    print(f"pool {len(pool):,}, {len(declared):,} declare a parent", flush=True)

    walked = []
    for i, m in enumerate(declared[:args.walk], 1):
        if client.requests > args.max_requests:
            print(f"  budget reached at {i}", flush=True)
            break
        walked.append(walk(client, m))
        if i % 200 == 0:
            print(f"  {i} walked ({client.requests} requests)", flush=True)

    (out / "history.json").write_text(json.dumps(walked, indent=2))
    (out / "history-manifest.json").write_text(json.dumps({
        "collected_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "pages": page, "scanned": scanned, "months_scanned": months,
        "pool": len(pool), "declaring": len(declared), "walked": len(walked),
        "requests": client.requests,
        "elapsed_s": round(time.time() - started, 1),
        "sampling": f"every {args.keep_every}th model of a date-sorted traversal",
        "caveat": ("Dense near the present, sparse further back. Base models "
                   "have lifecycles, so a recent bucket looks concentrated "
                   "around whatever launched last regardless of trend."),
    }, indent=2))
    print(f"\n  walked {len(walked)}, {client.requests} requests, "
          f"{time.time()-started:.0f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
