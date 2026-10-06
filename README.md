# What is actually inside the model you deployed?

Every open model on HuggingFace looks like an independent artifact. Almost none
of them are.

A few base models are fine-tuned into tens of thousands of derivatives. Those
get merged, quantised, re-fine-tuned and deployed into production systems whose
operators have no idea what is underneath.

**1,200 chains walked. Here is what is underneath.**

---

## The ecosystem is more concentrated in use than in appearance

| | Share of derivatives | Share of downloads |
|---|---:|---:|
| Top 3 orgs (Qwen, Google, Black Forest Labs) | 45.8% | **63.3%** |

There are **188 distinct root organisations** in the sample. Three of them
carry nearly two thirds of the downloads.

**Counting models understates it by seventeen points.** A survey reporting "188
organisations publish base models" describes a diverse ecosystem; weighting by
what people actually run describes a concentrated one.

### The sample size mattered, and this is how much

The first run walked 400 chains. Tripling it moved every headline figure:

| | 400 chains | 1,200 chains |
|---|---:|---:|
| Top 3 share of derivatives | 57.2% | **45.8%** |
| Top 3 share of downloads | 67.8% | **63.3%** |
| Distinct root organisations | 65 | **188** |
| Chains through an intermediary | 43.2% | **53.0%** |
| Licence widening | 0.2% | **1.67%** |

**The small sample overstated concentration by eleven points and understated
the organisational tail by a factor of three.** It also found one licence
widening where the larger sample finds twenty.

What survived is the direction: downloads concentrate more than models do, and
the gap *widened* from ten points to seventeen. That is the claim worth making,
and it is the only one the first sample would have supported.

Figures below are from the 1,200-chain run. A consistency test recomputes each
one from the committed data, so the next collection failing them is the
notification rather than a silent drift.

## Most consumers inherit from someone they have never heard of

**53.0%** of chains pass through at least one intermediary, and the deepest
observed runs **eight links**. A representative chain:

```
Qwopus3.6-35B-Coder  ->  Qwopus3.6-v1  ->  unsloth/Qwen3.6-35B  ->  Qwen/Qwen3.6-35B
     the leaf              a fine-tune       a third party's          the base
                                             re-upload
```

Someone deploying the leaf has a dependency on `unsloth`, whose name appears
nowhere in their decision.

## The licence finding is the one that nearly went wrong

The raw figure is alarming: of the 956 chains where **both ends declare a
licence**, **23.4%** declare different ones — 224 chains, or 18.7% of all
1,200. Reported as a violation rate, either number is a headline.

It is also wrong. A derivative may lawfully carry a different licence from its
ancestor — MIT and Apache-2.0 both permit relicensing under more restrictive
terms, so `MIT -> Apache-2.0` is ordinary and correct. What matters is the
opposite direction: a leaf claiming terms its ancestor does not grant.

Classified properly:

| Relationship | Count | Share |
|---|---:|---:|
| Consistent | 732 | 61.0% |
| Undeclared at one end | 244 | 20.3% |
| Unrankable (mostly `other`) | 157 | 13.1% |
| Narrows — permitted | 47 | 3.9% |
| **Widens — claims more than granted** | **20** | **1.67%** |

**Twenty chains in twelve hundred.** The gap between 23.4% and 1.67% is
entirely the difference between counting string inequality and reasoning about
what the licences permit. A test pins it,
so a future simplification that reintroduces the naive count fails rather than
quietly inflating the result.

## Blast radius: what one base carries

If a flaw were found in a base model, what is downstream of it?

`Qwen/Qwen3.8-27B` has **55 descendants** in the sample, carrying **18.8%** of
its downloads. Of 989 nodes that appear as an ancestor, **170 carry three or
more descendants** — the rest are a single derivative each.

**The five broadest nodes together reach 34.5% of download-weighted
exposure.**

### The correction that was needed first

Ranking by download weight alone put `nvidia/LocateAnything-3B` near the top on
6.1% of downloads — from a **single descendant**. That is one popular model,
not a dependency, and treating it as one conflates two different risks.

Nodes now carry a breadth flag at a threshold that is exposed rather than
buried, and narrow ones stay visible in the ranking instead of being filtered
away, because seeing them is the point.

**"Inherits" means "is downstream of."** It is an upper bound on exposure, not
a prediction that a flaw propagates — a fine-tune on clean data dilutes a bias
and a quantisation can break a backdoor by accident. And chains are walked from
a sample, so every count is a floor.

---

`other` and `undeclared` are doing a lot of work in that table — together
**33.4%** of chains. `other` is a text box covering everything from a bespoke
research licence to an unfilled form, and nothing can be concluded from it. The
true widening rate could be several times 1.67% or could be zero.

---

## How the data was collected

Reachability first, as always. The probe asked four questions in the order that
would kill the project fastest, and found two things worth recording:

**Lineage is not where the documentation suggests.** `cardData` is absent from
the list endpoint entirely; declarations live in `tags` as `base_model:NAME`.

**Coverage looks poor and is not.** Only 30–36% of top models declare a parent,
which sounds like the tree cannot be walked. Decomposed by construction type:

| Type | Declare a parent |
|---|---:|
| LoRA | 94.4% |
| PEFT | 90.0% |
| GGUF | 89.2% |
| Merge | 84.4% |
| Adapter | 82.4% |

The low overall figure is **base models correctly declaring no parent**. Among
models that have one by construction, declaration is near-universal.

Collection runs in CI because `huggingface.co` is unreachable from the
development sandbox. No key is needed; public model metadata is
unauthenticated. 1,200 chains cost roughly 1,800 requests, unauthenticated.

## Reproducing

```bash
pip install -e ".[dev]"
pytest -q
python -c "from lineage.analyse import analyse, load; print(analyse(load()).as_dict())"
```

Collection re-runs on a push to `.collect-trigger`.

## License

MIT. Model metadata is published by HuggingFace under its own terms.
