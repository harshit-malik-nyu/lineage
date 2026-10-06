# The case against this analysis

The strongest argument that it should not change anyone's view of the
open-weight ecosystem.

---

## 1. The sample is drawn from one slice — and this is now measured

Chains are walked from the most-downloaded models carrying five derivative
tags. That is not a random sample of HuggingFace, and popularity is exactly
what the concentration finding measures.

**This objection is no longer hypothetical. It is quantified, and it is large.**
`src/lineage/depth.py` shows the top-three share falling from 68.0% in the
first hundred models to 34.2% in ranks 801–1200, with distinct organisations
rising from 24 to 115. A study collecting the top 100 and a study collecting
the top 1,200 report 68.0% and 45.8% from the same ecosystem.

The README now leads with this rather than defending against it, because the
sensitivity turned out more interesting than the concentration figure it
undermines.

**What it costs:** every absolute concentration number in this repository is a
statement about a sampling depth. Only the *direction* — that downloads
concentrate more than models, at every cut — is a claim about the ecosystem.

**What remains unfixed:** a random sample of the full model index would give a
population figure rather than a depth-conditional one. The API supports it and
this collection did not do it.

## 2. Declared lineage is not actual lineage

Everything rests on `base_model:` tags, which are self-reported. A model card
is a claim. Three failure modes it cannot distinguish:

- A derivative that declares the wrong parent, or an intermediate rather than
  the true one.
- A model trained from scratch that declares a base to inherit its audience.
- A derivative that declares nothing, which drops out of the tree entirely and
  therefore out of every count.

The coverage figures (82–94% among plain derivatives) say the tag is *usually
present*. They say nothing about whether it is *right*.

## 3. Concentration may be a fact about naming, not about weights

Qwen appears as 39.8% of roots. Part of that is real adoption. Part is that
Qwen publishes many variants under one organisation name, while a lab shipping
one model under several org accounts would look more diverse without being so.

Counting by organisation is a choice, and it flatters organisations with tidy
naming.

## 4. "Inherits" is doing more work than it can carry

The blast-radius figures assume a property of a base reaches its descendants.
For some properties that is nearly true — a licence, a tokenizer quirk. For
others it is weak: a fine-tune on clean data dilutes a bias, a quantisation can
break a backdoor by accident, and a merge averages away a lot.

**The numbers are an upper bound on exposure, not a prediction of propagation**,
and a reader who takes 21.4% as "21.4% of downloads would be affected by a flaw
in Qwen3.8-27B" is reading more than the method supports.

## 5. Downloads are a poor proxy for deployment

A download is a `from_pretrained` call. It counts CI runs, mirrors, scrapers
and people trying a model once. A model with ten million downloads is not
necessarily running anywhere.

Weighting by downloads is better than weighting by model count — which was the
point of doing it — but it is still a proxy, and nothing here validates it
against deployment.

## 6. The licence analysis rests on a ranking I wrote

`PERMISSIVENESS` is my ordering of nine licences. The 0.2% widening figure
depends on it, and on `other` being treated as unrankable. A lawyer would
likely disagree with some of the ordering, and `other` covers 13.8% of the
sample — a share large enough that the real widening rate could be several
times higher or zero.

The correction from 20.9% to 0.2% is a genuine improvement over counting string
inequality. It is not a legal finding.

## 7. The snapshot is one moment

HuggingFace changes daily. Models are deleted, renamed, re-licensed and
re-uploaded. Four parents were already unresolvable at collection time and
three chains contained cycles. A run next month gives different numbers, and
nothing here establishes which parts are stable.

---

## What survives

- **Declaration coverage is high among derivatives.** 82–94% is measured, not
  inferred, and it establishes that a tree can be walked at all.
- **Weighting by use changes the picture.** Whatever the sampling problems,
  within this sample the top three organisations are 57.2% of models and 67.8%
  of downloads, and that direction is not an artefact of the ranking.
- **Chains have depth.** 43.2% pass through an intermediary. That is a
  structural fact about how these models are built, and it does not depend on
  the concentration argument.
- **The licence correction.** Counting string inequality gives 20.9%; reading
  what the licences permit gives 0.2%. The gap is real regardless of whether my
  ranking is perfect.

## The objection I cannot answer

Argument 1. The sample is selected on the variable the headline finding
measures. Fixing it needs a random sample of the full model index, which the
API supports and which would take a much larger collection — and until that
runs, the concentration figure describes the popular end of the ecosystem
rather than the ecosystem.
