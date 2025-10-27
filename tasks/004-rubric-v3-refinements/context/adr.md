# Architectural Decision Records - Task 004: Rubric v3.0 Refinements

**Task ID:** 004-rubric-v3-refinements
**Date:** 2025-10-22

---

## ADR-001: Pattern-Matching Refinements Over Algorithmic Redesign

**Status:** Accepted

**Context:**
Task 003 validation identified 91.3% acceptable alignment (73.9% exact match) with rubric specification. Two approaches considered:
1. Refine existing pattern-matching logic (additive changes)
2. Redesign scorer with rule engine or ML-based approach

**Decision:** Refine existing pattern-matching logic

**Rationale:**
- Current approach is 91.3% compliant (above 80% threshold)
- Pattern refinements are low-risk, additive changes
- Maintains 100% determinism (no randomness introduced)
- Preserves existing test coverage and validation
- Faster implementation (6-8 hours vs weeks for redesign)

**Consequences:**
- Positive: Low risk, fast delivery, maintains determinism
- Negative: Doesn't address fundamental pattern-matching limitations for complex cases
- Mitigation: Document limitations; consider ML approach for future v4.0 if needed

---

## ADR-002: TDD-First Implementation Approach

**Status:** Accepted

**Context:**
SCA Protocol v13.8 requires tests before implementation for CP code. Two approaches:
1. Write failure tests first, confirm failures, then implement
2. Implement refinements, then write tests

**Decision:** Write 4 failure tests FIRST, confirm failures, then implement

**Rationale:**
- SCA v13.8 hard requirement for CP code
- Confirms baseline behavior before changes
- Prevents false positives (tests passing incorrectly)
- Documents expected behavior explicitly

**Consequences:**
- Positive: Protocol compliance, clear baseline, prevents regression
- Negative: Slightly longer initial setup
- Mitigation: Reuse test structure from validate_rubric_compliance.py

---

## ADR-003: Explicit Stage 0 Detection vs Lowering Framework Boost

**Status:** Accepted

**Context:**
RD dimension over-scores brochure text (Stage 0 → Stage 2). Two fixes considered:
1. Add explicit Stage 0 patterns BEFORE framework boost
2. Remove or lower framework boost from 2 → 1

**Decision:** Add explicit Stage 0 patterns before framework boost

**Rationale:**
- Framework boost is correct for actual TCFD/ISSB disclosures
- Problem is weak text triggering boost, not the boost itself
- Early-return pattern prevents over-scoring without breaking valid cases
- Length constraint (<200 chars) prevents false positives on real reports

**Consequences:**
- Positive: Fixes violation without breaking existing correct scores
- Negative: Adds ~10 lines of code
- Mitigation: Test on Microsoft findings to ensure no regressions

---

## ADR-004: Assurance Level Check Order (Stage 3 Before Stage 4)

**Status:** Accepted

**Context:**
GHG dimension doesn't distinguish "limited" (Stage 3) vs "reasonable" (Stage 4) assurance. Two fixes:
1. Check Stage 3 "limited assurance" BEFORE generic "third-party" (Stage 4)
2. Add negative patterns to Stage 4 (exclude "limited")

**Decision:** Check Stage 3 before Stage 4 + add negative check

**Rationale:**
- Order matters in pattern matching (first match wins)
- Stage 3 is more specific ("limited assurance") than Stage 4 ("third-party assurance")
- Negative check (`not reasonable`) prevents false Stage 3 when both mentioned
- Aligns with rubric specification language

**Consequences:**
- Positive: Correctly distinguishes assurance levels per rubric
- Negative: Slightly more complex logic
- Mitigation: Add explicit test case for "reasonable assurance" to ensure Stage 4 still works

---

## ADR-005: Implicit Detection for RMM Stage 2 (TCFD Narrative)

**Status:** Accepted

**Context:**
RMM dimension misses implicit risk disclosure in TCFD narratives. Two approaches:
1. Add implicit Stage 2 patterns (TCFD pillars = risk identification)
2. Require explicit "scenario testing" keywords for all Stage 2+

**Decision:** Add implicit Stage 2 patterns for TCFD/framework narratives

**Rationale:**
- Rubric Stage 2 = "Defined risk taxonomy; periodic assessments"
- TCFD pillars (governance, strategy, risk, metrics) indicate risk framework exists
- Many companies disclose via TCFD narrative without explicit "scenario testing" keywords
- Lower confidence (0.70) reflects less certain inference

**Consequences:**
- Positive: Fixes violation, aligns with common disclosure practice
- Negative: May over-score narrative-only risk disclosure without actual framework
- Mitigation: Lower confidence score; place after explicit Stage 4/3 checks

---

## ADR-006: Framework Attribution Requires Text Evidence

**Status:** Accepted

**Context:**
RD dimension scores framework boost based on parameter alone, even if text doesn't mention framework. Two fixes:
1. Require framework mention in TEXT + parameter for boost
2. Remove framework parameter entirely, rely only on text patterns

**Decision:** Require BOTH framework parameter AND text mention for boost

**Rationale:**
- Rubric requires explicit framework reference in disclosure
- Parameter may come from metadata/tagging (not actual text content)
- Maintains boost logic for valid cases (framework mentioned in text)
- Prevents over-scoring when framework inferred but not disclosed

**Consequences:**
- Positive: Aligns with rubric requirement for explicit framework disclosure
- Negative: May under-score some cases where framework implicit
- Mitigation: Document this as intentional conservative scoring

---

## ADR-007: Delta Report vs Re-Baseline for Microsoft Findings

**Status:** Accepted

**Context:**
Refinements will change Microsoft aggregation scores. Two approaches:
1. Re-baseline (update expected scores to match new output)
2. Keep old baseline, document deltas

**Decision:** Keep old baseline (Task 003), document deltas in separate report

**Rationale:**
- Preserves historical record of Task 003 results
- Enables before/after comparison
- Validates that refinements improve (not degrade) scoring
- Transparency for future audits

**Consequences:**
- Positive: Clear audit trail, validates improvements
- Negative: Two sets of results to maintain
- Mitigation: Create clear delta report showing before/after comparison

---

**ADRs Complete:** 7 decisions documented
