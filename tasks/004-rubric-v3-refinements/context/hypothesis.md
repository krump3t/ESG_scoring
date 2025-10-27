# Hypothesis: Rubric v3.0 Precision Refinements

**Task ID:** 004-rubric-v3-refinements
**Date:** 2025-10-22
**Protocol:** SCA v13.8

---

## Primary Hypothesis

Implementing 4 targeted pattern-matching refinements in `rubric_v3_scorer.py` will increase exact match rate against official rubric specification from **73.9% → ≥85%** while maintaining 100% determinism and eliminating all violations (>1 stage off).

---

## Primary Metrics

### Target Metric: Exact Match Rate
- **Baseline (Task 003):** 73.9% (17/23 tests pass exactly)
- **Target:** ≥85% (≥20/23 tests pass exactly)
- **Measurement:** `validate_rubric_compliance.py` test suite

### Secondary Metrics
- **Violations:** 2 → 0 (>1 stage deviation from rubric specification)
- **Warnings:** 4 → ≤2 (±1 stage deviation, acceptable)
- **Acceptable Rate:** 91.3% (maintain ≥90%)

### Determinism (Must Maintain)
- **Baseline:** 100% (0 violations across 2,447 differential tests)
- **Target:** 100% (0 violations after refinements)
- **Measurement:** Re-run `test_rubric_v3_differential.py` (1,200+ fuzz cases)

---

## Input/Output Thresholds

### Inputs
1. **Validation Test Cases:** 23 tests (15 rubric stage tests + 8 Microsoft findings)
2. **Differential Test Cases:** 2,447 total (1,200 unique fuzz cases)
3. **Scorer Implementation:** `agents/scoring/rubric_v3_scorer.py` (4 methods modified)

### Outputs
1. **Refined Scorer:** Modified `score_rd()`, `score_ghg()`, `score_rmm()` methods
2. **TDD Tests:** 4 new failure-path tests in `tests/test_rubric_v3_refinements.py`
3. **Validation Reports:** Post-refinement rubric compliance + differential results

### Thresholds
- **Minimum Improvement:** +5 percentage points exact match (73.9% → 78.9%)
- **Target Improvement:** +11 percentage points exact match (73.9% → 85%)
- **Determinism Tolerance:** 0 violations (hard requirement)
- **Coverage Requirement:** ≥95% line & branch on CP code
- **Type Safety:** 0 mypy --strict errors

---

## Critical Path (CP)

**Definition:** Code paths that directly impact rubric scoring fidelity

### CP Files
- `agents/scoring/rubric_v3_scorer.py` (entire file = CP)

### CP Methods (Modified)
1. `score_rd()` - Lines 442-476 (Reporting & Disclosure scoring)
2. `score_ghg()` - Lines 422-440 (GHG Accounting scoring)
3. `score_rmm()` - Lines 498-516 (Risk Management scoring)

### CP Test Requirements (SCA v13.8)
- ≥1 test per CP method marked `@pytest.mark.cp`
- ≥1 Hypothesis `@given(...)` property test
- ≥1 failure-path test per refinement (4 total)

---

## Exclusions

### Out of Scope
- Changes to non-CP dimensions (TSP, OSP, DM, EI) - already 100% compliant or no issues
- Performance optimization - not a priority (scoring is <10ms per finding)
- Additional test cases beyond existing 23 - scope limited to fixing known issues
- Re-training/ML approaches - pattern-matching refinements only

### Explicitly NOT Changed
- Overall maturity calculation (lines 518-546)
- Pattern extraction logic (lines 548-566)
- DimensionScore dataclass (lines 13-19)
- Existing test suites (except adding new TDD tests)

---

## Power Analysis & Confidence Intervals

### Statistical Power
- **Sample Size:** 23 validation tests (fixed)
- **Effect Size:** 4 refinements targeting 4 specific failures
- **Expected Success:** 4/6 current failures fixed (4 targeted + 2 collateral improvements)

### Confidence Intervals (95%)
- **Best Case:** 87% exact match (20/23 tests)
- **Expected Case:** 85% exact match (19-20/23 tests)
- **Worst Case:** 78% exact match (18/23 tests) - still acceptable

### Success Criteria
- **Minimum Acceptable:** ≥78% exact match (≥18/23 tests) AND 0 violations
- **Target:** ≥85% exact match (≥20/23 tests) AND 0 violations AND 100% determinism

---

## Risk Counters

### Risk 1: Breaking Existing Correct Scores
- **Probability:** Medium
- **Impact:** High (regression in already-passing tests)
- **Mitigation:**
  - TDD approach - write failure tests first, confirm current failures
  - Re-run full differential suite (2,447 cases) to detect unintended changes
  - Generate delta report comparing Task 003 baseline vs Task 004 results

### Risk 2: Determinism Violation
- **Probability:** Low
- **Impact:** Critical (violates SCA v13.8 authenticity invariant)
- **Mitigation:**
  - All changes are additive pattern matching (no randomness introduced)
  - Re-run differential suite with 10 iterations per case
  - Hash-based determinism verification

### Risk 3: Pattern Matching Over-Generalization
- **Probability:** Medium
- **Impact:** Medium (new false positives)
- **Mitigation:**
  - Conservative pattern design (specific, not broad)
  - Validation on Microsoft real-world findings (8 cases)
  - Delta report documents all scoring changes

### Risk 4: Coverage/Type Safety Regression
- **Probability:** Low
- **Impact:** High (blocks SCA gate passage)
- **Mitigation:**
  - Run mypy --strict after each refinement
  - Add type hints to new code paths
  - Confirm ≥95% coverage maintained

---

## Validation Plan

### Phase 1: TDD Baseline
1. Write 4 failure tests (one per refinement)
2. Run tests → confirm 4 failures (baseline)

### Phase 2: Implementation
1. Implement Refinement 1 (RD Stage 0)
2. Implement Refinement 2 (GHG assurance)
3. Implement Refinement 3 (RMM implicit)
4. Implement Refinement 4 (RD framework)

### Phase 3: Validation Gates
1. TDD: Run 4 tests → confirm 4 passes
2. Coverage: ≥95% line & branch on CP
3. Type Safety: mypy --strict = 0 errors
4. Complexity: CCN ≤10, Cognitive ≤15
5. Docs: ≥95% interrogate on CP
6. Differential: 100% determinism maintained
7. Rubric Compliance: ≥85% exact match, 0 violations
8. Delta Report: Document all score changes

---

## Success Criteria (All Must Pass)

- [ ] Exact match rate ≥85% (≥20/23 tests)
- [ ] Violations = 0 (no >1 stage deviations)
- [ ] Warnings ≤2 (±1 stage deviations acceptable)
- [ ] Determinism = 100% (0 violations across 2,447 differential tests)
- [ ] Coverage ≥95% line & branch on `rubric_v3_scorer.py`
- [ ] Type safety = 0 mypy --strict errors
- [ ] Complexity: CCN ≤10, Cognitive ≤15
- [ ] Documentation ≥95% interrogate on CP
- [ ] TDD: 4 failure tests written first, then pass
- [ ] Traceability: run_log, manifest, events captured

---

## Timeline

- **Phase 1 (TDD Baseline):** 1 hour
- **Phase 2 (Implementation):** 2 hours
- **Phase 3 (Validation):** 3-4 hours
- **Total:** 6-7 hours

---

**Hypothesis Approved:** Ready for implementation under SCA Protocol v13.8
