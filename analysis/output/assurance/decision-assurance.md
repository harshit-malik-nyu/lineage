# Decision assurance: lineage

Review highly exposed roots and unresolved paths together. A popularity-only queue misses unknown dependencies and should not be treated as a complete control.

**Evidence:** The frozen Hub graph distinguishes descendant-count and download concentration. Downloads are not unique users, selection is not population sampling, and license metadata flags are not legal findings.

**Uncertainty:** Incident-loss values are illustrative operational scenarios, not estimates of license liability.

## Robustness of the assumed business case

| Alternative | Feasible grid cases / 27 | Worst regret when feasible | Maximum volume at fixed review capacity |
|---|---:|---:|---:|
| Uniform model-by-model review | 6 | $16,700.00 | 1200 |
| Root-prioritized review with unresolved queue | 6 | $7,465.00 | 2142 |
| Popularity-only review | 0 | No feasible case | 6000 |

**Robust minimax choice:** None. No option is feasible across the entire stress grid.

Finite assumed grid, not a probability distribution or protection outside the grid. Conditional regret never overrides feasibility. Null robust option means no unconditional recommendation. Cost regret is relative to the cheapest feasible option in that same scenario. Failure counts can overlap.

## Missing-outcome sensitivity

| Outcomes masked per arm | Primary effect bounds | Incident effect bounds | Every completion clears margins? |
|---|---:|---:|---|
| 0% | [8.2%, 8.2%] | [0.6%, 0.6%] | False |
| 5% | [2.7%, 12.7%] | [-4.5%, 5.5%] | False |
| 10% | [-2.3%, 17.7%] | [-9.5%, 10.5%] | False |
| 20% | [-12.3%, 27.7%] | [-19.6%, 20.4%] | False |

These are identification bounds on deliberately masked synthetic outcomes, not confidence intervals or measured missingness. Failures and non-starters remain in the assigned denominator. Passing this sensitivity check would still require statistical and domain-quality gates.

## Domain measurement contract

**Decision:** Prioritize model-family metadata review under a fixed governance budget.

**Primary outcome:** Confirmed actionable metadata issues resolved per reviewer hour, with coverage by model family and download exposure.

**Denominator:** All models in the explicitly frozen selected graph; neither the graph nor downloads represent all users or all models.

**Independent unit:** Root family; descendants can share the same inherited issue.

**Quality guardrail:** No legal verdict from metadata alone; track unresolved lineage and missing license fields.

**Minimum required data:** Model/root IDs, snapshot date, ancestry edges, metadata fields, download measure definition, review disposition and time.

**Missingness and failure handling:** Missing license or ancestry stays unknown. Do not convert absent metadata into compliant or noncompliant labels.

**Release rule:** Prioritize transparent exposure scenarios while requiring qualified review for legal conclusions; report both counts and download weighting.

**Reversal trigger:** Ancestry errors, concentrated duplicated issues, or changed exposure weights alter which roots deserve priority.

## Interview defense

**Are downloads users?**

No. Download counts are an activity proxy. I show both count concentration and download concentration without claiming unique-user exposure.

**Why prioritize roots?**

A root-level review may resolve a shared issue across descendants, but that benefit depends on verified inheritance, not graph position alone.

## Implementation handoff

1. Freeze the eligible population, denominator, outcome horizon and proposed decision owner before comparison.
2. Reconcile assignment and outcome records at the independence unit; classify missingness without deleting cases.
3. Estimate the domain outcome and its uncertainty separately from activation. Apply risk and capacity vetoes before comparing costs.
4. Record approve, hold, or reverse with the evidence version and violated gate. An unmeasured required domain gate means HOLD.

The supplied cluster-budget grid is a planning sensitivity check with assumed ICC. It is not an estimate from real clusters and does not guarantee joint power. No stakeholder approval or real experiment is asserted.
