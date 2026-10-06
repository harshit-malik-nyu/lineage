#!/usr/bin/env python3
"""
A sample NOT selected on popularity.

The objection this answers
--------------------------
Every figure so far comes from chains walked out of the most-downloaded
models. `depth.py` showed how much that matters: the top-three share falls from
68.0% in the first hundred models to 34.2% in ranks 801-1200. So the headline
concentration number is a statement about a sampling depth, and the obvious
question — what is it for the population? — has not been answered.

It is answerable. The API sorts by fields uncorrelated with downloads, so
paging through `createdAt` and taking a stride gives a sample selected on when
a model was uploaded rather than on how popular it became.

Why createdAt rather than random
--------------------------------
The API has no random sampler. Sorting by creation date and striding is the
closest available thing, and it has a known bias of its own: the model
population grows over time, so a stride across the sorted index
over-represents whatever period has the most uploads.

That bias is in a different direction from popularity, which is the point. If
the two samples agree, the finding is robust to both. If they disagree, the
difference bounds how much selection is doing.

Nothing here pretends this is a random sample. It is a differently-biased one,
and the comparison is the evidence.
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
    def __init__(self, pause: float = 0.25):
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
        """
        Fetch a full URL and keep the Link header.

        The API ignores a `page` parameter entirely — the first version of
        this sampler requested sixty pages and received the same hundred
        models sixty times, ending with a pool of fifteen. Pagination is
        cursor-based through the Link header, which is why this returns it.
        """
        self.next_url = None
        for attempt in range(retries):
            self.requests += 1
            try:
                req = urllib.request.Request(
                    url, headers={"User-Agent": "lineage-sampler"})
                with urllib.request.urlopen(req, timeout=45) as r:
                    link = r.headers.get("Link") or ""
                    for part in link.split(","):
                        if 'rel="next"' in part:
                            self.next_url = part.split(";")[0].strip(" <>")
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
            "chain": chain, "depth": len(chain),
            "root": chain[-1]["id"] if chain else m.get("id"),
            "root_resolved": chain[-1]["resolved"] if chain else True,
            "truncated": truncated, "cycle": cycle, "missing_parent": missing}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pages", type=int, default=60,
                    help="pages of the createdAt-sorted index to stride across")
    ap.add_argument("--stride", type=int, default=7,
                    help="take every Nth model within a page")
    ap.add_argument("--walk", type=int, default=900)
    ap.add_argument("--max-requests", type=int, default=5000)
    ap.add_argument("--out", default=str(ROOT / "evidence"))
    args = ap.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    client = Client()
    started = time.time()

    pool: dict[str, dict] = {}
    print(f"striding {args.pages} cursor pages of the createdAt index", flush=True)
    data = client.get("models", {"sort": "createdAt", "direction": -1,
                                 "limit": 100, "full": "true"})
    page = 0
    while data is not None and page < args.pages:
        rows = data if isinstance(data, list) else []
        if not rows:
            print(f"  page {page + 1} empty — index ends here", flush=True)
            break
        for m in rows[::args.stride]:
            if m.get("id"):
                pool[m["id"]] = m
        page += 1
        if page % 10 == 0:
            print(f"  page {page}: pool {len(pool)}", flush=True)
        if client.requests > args.max_requests or not client.next_url:
            if not client.next_url:
                print(f"  no next cursor after page {page}", flush=True)
            break
        data = client.get_url(client.next_url)

    declared = [m for m in pool.values() if parents(m)]
    print(f"\n{len(pool):,} sampled, {len(declared):,} declare a parent "
          f"({len(declared)/max(1,len(pool)):.1%})", flush=True)

    walked = []
    for i, m in enumerate(declared[:args.walk], 1):
        if client.requests > args.max_requests:
            print(f"  budget reached at {i}", flush=True)
            break
        walked.append(walk(client, m))
        if i % 100 == 0:
            print(f"  {i} walked ({client.requests} requests)", flush=True)

    (out / "unbiased.json").write_text(json.dumps(walked, indent=2))
    meta = {
        "collected_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "sampling": "stride over createdAt-sorted index, NOT popularity",
        "pool": len(pool), "declaring_a_parent": len(declared),
        "walked": len(walked), "requests": client.requests,
        "elapsed_s": round(time.time() - started, 1),
        "errors": client.errors[:20],
        "caveat": ("createdAt striding has its own bias: the population grows "
                   "over time, so this over-represents whatever period has the "
                   "most uploads. It is differently biased from popularity "
                   "sampling, not unbiased."),
    }
    (out / "unbiased-manifest.json").write_text(json.dumps(meta, indent=2))
    print(f"\n  walked {len(walked)}, {client.requests} requests")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
