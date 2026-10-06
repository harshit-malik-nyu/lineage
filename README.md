# What is actually inside the model you deployed?

Every open model on HuggingFace looks like an independent artifact. Almost none
of them are.

A few base models are fine-tuned into tens of thousands of derivatives. Those
get merged, quantised, re-fine-tuned and deployed into production systems whose
operators have no idea what is underneath.

**400 chains walked. Here is what is underneath.**

---

## The ecosystem is more concentrated in use than in appearance

| | Share of derivatives | Share of downloads |
|---|---:|---:|
| Top 3 orgs (Qwen, Google, MiniMaxAI) | 57.2% | **67.8%** |
| Top 5 orgs | 64.8% | 69.4% |
| Qwen alone | 39.8% | **55.5%** |

There are **65 distinct root organisations** in the sample. Three of them carry
two thirds of the downloads.

**Counting models understates it by ten points.** A survey that reports "65
organisations publish base models" describes a diverse ecosystem; weighting by
what people actually run describes a concentrated one.

## Most consumers inherit from someone they have never heard of

**43.2%** of chains pass through at least one intermediary, and the deepest
observed runs **eight links**. A representative chain:

```
Qwopus3.6-35B-Coder  ->  Qwopus3.6-v1  ->  unsloth/Qwen3.6-35B  ->  Qwen/Qwen3.6-35B
     the leaf              a fine-tune       a third party's          the base
                                             re-upload
```

Someone deploying the leaf has a dependency on `unsloth`, whose name appears
nowhere in their decision.

## The licence finding is the one that nearly went wrong

The raw figure is alarming: **20.9%** of chains declare a different licence at
the leaf than at the root. Reported as a violation rate, that is a headline.

It is also wrong. A derivative may lawfully carry a different licence from its
ancestor — MIT and Apache-2.0 both permit relicensing under more restrictive
terms, so `MIT -> Apache-2.0` is ordinary and correct. What matters is the
opposite direction: a leaf claiming terms its ancestor does not grant.

Classified properly:

| Relationship | Count | Share |
|---|---:|---:|
| Consistent | 284 | 71.0% |
| Unrankable (mostly `other`) | 55 | 13.8% |
| Undeclared at one end | 41 | 10.2% |
| Narrows — permitted | 19 | 4.8% |
| **Widens — claims more than granted** | **1** | **0.2%** |

**One chain in four hundred.** `kenpath/svara-tts-v1` declares `apache-2.0`
with a `llama3.2` ancestor, at 52,406 downloads.

The gap between 20.9% and 0.2% is entirely the difference between counting
string inequality and reasoning about what the licences permit. A test pins it,
so a future simplification that reintroduces the naive count fails rather than
quietly inflating the result.

`other` is doing a lot of work in that table — it is a text box covering
everything from a bespoke research licence to an unfilled form, and nothing can
be concluded from the 13.8% it accounts for.

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
unauthenticated. 400 chains cost **301 requests**.

## Reproducing

```bash
pip install -e ".[dev]"
pytest -q
python -c "from lineage.analyse import analyse, load; print(analyse(load()).as_dict())"
```

Collection re-runs on a push to `.collect-trigger`.

## License

MIT. Model metadata is published by HuggingFace under its own terms.
