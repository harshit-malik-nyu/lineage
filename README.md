# What is actually inside the model you deployed?

Every open model on HuggingFace looks like an independent artifact. Almost none
of them are.

A few base models are fine-tuned into tens of thousands of derivatives. Those
get merged, quantised, re-fine-tuned and deployed into production systems whose
operators have no idea what is underneath.

**1,200 chains walked. Here is what is underneath.**

---

## Concentration is a property of where you look, not of the ecosystem

This is the finding, and it arrived by accident.

The first collection walked 400 chains and reported the top three
organisations as **57.2%** of derivatives. The second walked 1,200 and reported
**45.8%**. The obvious reading is that the small sample was wrong.

It is not what happened. Subsampling the 1,200 shows the share statistics are
stable in n — **46.8% at a hundred chains, 45.8% at twelve hundred**. Sampling
variance cannot produce an eleven-point move.

What produced it was collection depth. The first run took the 250
most-downloaded models per construction type; the second took 500. Taking the
top 400 by downloads *out of the larger pool* reproduces the original figure.

### The popular end is concentrated. The tail is not.

| Band of the download ranking | Top 3 orgs | Distinct orgs | Median downloads |
|---|---:|---:|---:|
| rank 1–100 | **68.0%** | 24 | 788,473 |
| rank 101–200 | 65.0% | 27 | 349,468 |
| rank 201–400 | 54.5% | 51 | 158,176 |
| rank 401–800 | 47.0% | 89 | 11,570 |
| rank 801–1200 | **34.2%** | 115 | 3,106 |

### What a study would report, by how deep it collected

| Collected | Top 3 orgs | Distinct orgs |
|---|---:|---:|
| Top 100 | **68.0%** | 24 |
| Top 400 | 58.2% | 61 |
| Top 1,200 | **45.8%** | 188 |

**Two honest studies of the same ecosystem, differing only in sampling depth,
can report 45.8% or 68.0% concentration — a spread of 22 points — and 24 or 188
organisations, a factor of eight.**

Open-weight policy arguments cite concentration in both directions. *"A handful
of labs control the ecosystem"* and *"hundreds of organisations publish base
models"* are both supportable from this data, by choosing a cut. Any such claim
is incomplete without its sampling depth, and almost none state one.

That is a methodological finding rather than a fact about model weights, and it
is the more useful of the two.

### A second sample, selected differently — and the result inverted

Depth sensitivity raises the obvious question: what does the *population* look
like? The API has no random sampler, but it sorts by fields uncorrelated with
downloads. Striding across the index sorted by **upload date** gives a sample
selected on when a model appeared rather than on how popular it became.

That has its own bias — the population grows over time, so it over-represents
whatever period uploaded most. The point is that the bias runs in a different
direction.

I expected the popularity sample to be the more concentrated one. It is not.

| | Popularity-sampled | Recency-sampled |
|---|---:|---:|
| Chains | 1,200 | 245 |
| Top 3 share of models | 45.8% | **60.8%** |
| Top 3 share of downloads | 63.3% | **80.6%** |
| Distinct root organisations | 188 | **62** |
| Median downloads | 11,570 | **0** |
| Chains through an intermediary | 53.0% | 51.0% |
| Licence widening | 1.7% | 1.6% |

**The flow is more concentrated than the stock, by fifteen points.** New uploads
pile onto whichever base is currently fashionable; the popular set has
accumulated across several generations of base model. A median download count
of zero in the recency sample is not a glitch — it is the difference between
the two samples stated in one number.

#### Is the gap just the smaller sample?

This project already mistook a selection effect for a sample-size effect once,
so the question is asked in code rather than assumed. Subsampling the 1,200
popularity chains down to 245 — the recency sample's size — two hundred times:

| | |
|---|---:|
| Subsample mean | 46.6% |
| Subsample range across 200 trials | 38.8% – 53.5% |
| Recency sample actual | **60.8%** |
| Standard deviations from the mean | **+4.8** |

**Outside every one of the two hundred subsamples.** The gap is not the sample
size.

**A snapshot of what exists understates where the ecosystem is heading.**

### What survives both selection rules

Chain depth agrees — 53.0% against 51.0%. Licence widening agrees — 1.7%
against 1.6%. Those are claims about how these models are *built*, and they
survive a change of selection rule that moves concentration by fifteen points.

Concentration does not survive it, in either direction. Every absolute
concentration figure here is conditional on a sampling rule, and the two rules
available bracket it between 45.8% and 60.8%.

### What survives the depth problem

Within every band, **downloads concentrate more than models do**. At the full
sample the top three are 45.8% of derivatives and **63.3%** of downloads. That
direction holds at every cut, so it is a claim about the ecosystem rather than
about the sampling.

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
