# Prioritize dependency review by exposure and unresolved provenance

Review highly exposed roots and unresolved paths together. A popularity-only queue misses unknown dependencies and should not be treated as a complete control.

**Observed evidence:** The frozen Hub graph distinguishes descendant-count and download concentration. Downloads are not unique users, selection is not population sampling, and license metadata flags are not legal findings.

**Decision owner:** Model governance lead (proposed role, not a client).

**Base planning case:** Root-prioritized review with unresolved queue. This is conditional on the assumptions, not deployment approval.

| Alternative | Economic cost | Cash outlay | Reviewer hours | Passes risk and capacity |
|---|---:|---:|---:|---|
| Uniform model-by-model review | $54,700 | $0 | 500.0 | True |
| Root-prioritized review with unresolved queue | $48,420 | $16,060 | 280.0 | True |
| Popularity-only review | $42,300 | $4,000 | 100.0 | False |

Economic cost includes valued staff capacity and scenario incident losses. Cash outlay excludes salaried capacity and contingent losses. These are not realized savings.

**Sensitivity across 27 equally enumerated scenarios:** Uniform model-by-model review: 2, NO FEASIBLE OPTION: 21, Root-prioritized review with unresolved queue: 4. Grid counts are not probabilities.

**Synthetic product experiment:** HOLD. Primary effect 8.2%; 95% interval [4.4%, 12.0%]. Guardrail effect 0.6%; interval [-0.1%, 1.4%]. These numbers test the decision logic, not product performance.

**Priority order:**

1. Put unresolved roots and cycles on an explicit exception queue.
2. Compare descendant and download-weighted review coverage without conflating the denominators.
3. Set metadata freshness and ownership requirements before recurring review.

**What would reverse the recommendation:** If roots cannot be resolved reliably, shared-root amortization is not justified; revert to direct review for affected models.

**Remaining uncertainty:** Incident-loss values are illustrative operational scenarios, not estimates of license liability.
