# Architecture Decision Records (ADR)

**Task ID:** 003-rubric-v3-implementation
**Date:** 2025-10-22

---

## ADR-001: Use Rule-Based Scoring Instead of LLM

**Status:** Accepted
**Date:** 2025-10-22

### Context
Need to score ESG maturity with rubric v3.0. Could use:
1. Rule-based regex pattern matching
2. LLM-based scoring (GPT-4, Claude, etc.)
3. Hybrid approach

### Decision
Use rule-based regex pattern matching for v1 implementation.

### Rationale
- **Determinism:** Same input → same output (critical for SCA v13.8)
- **Traceability:** Explicit evidence snippets from pattern matches
- **Cost:** Zero API costs, no rate limits
- **Speed:** < 500ms per finding vs. 2-5s for LLM
- **Compliance:** SCA protocol requires authentic computation, not LLM black boxes

### Consequences
- **Positive:** Deterministic, fast, traceable, cost-free
- **Negative:** May miss nuanced evidence, requires manual pattern tuning
- **Migration:** Can add LLM option later as `use_llm=True` parameter

---

## ADR-002: 7-Dimensional Schema (Breaking Change)

**Status:** Accepted
**Date:** 2025-10-22

### Context
Previous gold schema had single `maturity_level` field (0-5 scale).
Rubric v3.0 requires 7 separate dimensions (TSP, OSP, DM, GHG, RD, EI, RMM).

### Decision
Add 28 new fields to gold schema (4 fields × 7 dimensions).
This is a **breaking change** - old schema incompatible.

### Rationale
- **Rubric Compliance:** Rubric v3.0 specification mandates 7 dimensions
- **Granularity:** Dimension-specific scores enable better analysis
- **Explainability:** Each dimension has evidence and confidence
- **SCA Compliance:** Fixes V-003 (Wrong Algorithm) critical violation

### Consequences
- **Positive:** Authentic rubric implementation, granular insights
- **Negative:** ALL previous test results invalidated, migration complexity
- **Mitigation:** Explicit documentation, fresh pipeline run required

---

## ADR-003: Average of 7 Dimensions for Overall Maturity

**Status:** Accepted
**Date:** 2025-10-22

### Context
How to calculate overall maturity from 7 dimension scores?
Options:
1. Simple average (sum / 7)
2. Weighted average (prioritize certain dimensions)
3. Minimum score (conservative)
4. Maximum score (optimistic)

### Decision
Use simple average: `overall_maturity = sum(7 dimensions) / 7`

### Rationale
- **Rubric Specification:** Rubric v3.0 doesn't specify weights
- **Simplicity:** Easy to understand and explain
- **Fairness:** All dimensions equally important
- **Transparency:** No hidden weighting assumptions

### Consequences
- **Positive:** Simple, transparent, unbiased
- **Negative:** Doesn't prioritize high-impact dimensions (e.g., GHG)
- **Future:** Can add weighted option if requirements change

---

## ADR-004: Evidence Truncation to 200 Characters

**Status:** Accepted
**Date:** 2025-10-22

### Context
Evidence snippets can be long (full paragraphs).
Need to balance detail vs. storage/display.

### Decision
Truncate evidence to max 200 characters with "..." suffix.

### Rationale
- **Storage:** Reduces gold layer size
- **Readability:** Prevents UI overflow
- **Context:** 200 chars provides enough context for validation
- **Full Text:** Original text available in silver layer if needed

### Consequences
- **Positive:** Compact, readable, storage-efficient
- **Negative:** May lose some context in edge cases
- **Mitigation:** Store full finding_id for linkage to silver layer

---

## ADR-005: Stage 4 → 3 → 2 → 1 Matching Order

**Status:** Accepted
**Date:** 2025-10-22

### Context
When scoring a dimension, which stage patterns to check first?
Options:
1. Stage 1 → 2 → 3 → 4 (bottom-up)
2. Stage 4 → 3 → 2 → 1 (top-down)

### Decision
Check stages in descending order (4 → 3 → 2 → 1).
Stop at first match, return that stage score.

### Rationale
- **Best Score:** Finds highest applicable stage
- **Efficiency:** Often fewer patterns to check (stage 4 is rare)
- **Rubric Semantics:** Higher stages subsume lower stages

### Consequences
- **Positive:** Optimal scoring, intuitive behavior
- **Negative:** None identified
- **Implementation:** Explicit in each `score_X()` method

---

## ADR-006: No Backward Compatibility with Old Schema

**Status:** Accepted
**Date:** 2025-10-22

### Context
Breaking change to gold schema means old scores incompatible with new.
Could provide migration script or backward compatibility layer.

### Decision
No backward compatibility. All old scores considered invalid.

### Rationale
- **Correctness:** Old scores used wrong algorithm (trivial substitute)
- **Clean Break:** Rubric v3.0 is fundamentally different
- **Documentation:** Explicitly state all previous results invalid
- **Effort:** Migration would be complex and low value

### Consequences
- **Positive:** Clean implementation, no technical debt
- **Negative:** Cannot compare to old results
- **Mitigation:** Document in RUBRIC_V3_IMPLEMENTATION_COMPLETE.md

---

## ADR-007: Framework Boost for RD Dimension Only

**Status:** Accepted
**Date:** 2025-10-22

### Context
Should framework detection (SBTi, TCFD, etc.) boost scores?
If yes, which dimensions?

### Decision
Framework boosts **only RD (Reporting & Disclosure)** dimension.
- TCFD/ISSB → RD minimum stage 2
- GRI/SASB → RD minimum stage 1

### Rationale
- **Rubric Semantics:** Frameworks are disclosure standards (RD domain)
- **Specificity:** SBTi targets score in TSP based on content, not framework name
- **Avoid Inflation:** Don't artificially boost unrelated dimensions

### Consequences
- **Positive:** Accurate dimension scoring, no false inflation
- **Negative:** Framework mentions don't boost TSP/GHG (intentional)
- **Validation:** Matches expert understanding of framework scope

---

**Total ADRs:** 7
**Last Updated:** 2025-10-22
