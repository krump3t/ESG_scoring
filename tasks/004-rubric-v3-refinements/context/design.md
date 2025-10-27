# Design: Rubric v3.0 Precision Refinements

**Task ID:** 004-rubric-v3-refinements
**Date:** 2025-10-22
**Protocol:** SCA v13.8

---

## Overview

Implement 4 targeted refinements to `rubric_v3_scorer.py` to fix identified violations and warnings from Task 003 rubric compliance validation. All changes are pattern-matching enhancements (no algorithmic changes, no randomness).

---

## Refinement 1: RD Stage 0 Detection

### Problem
**Test Case:** "See our company brochure for sustainability highlights."
- **Expected:** Stage 0 (No formal ESG reporting)
- **Actual:** Stage 2 (TCFD-aligned narrative)
- **Root Cause:** No explicit Stage 0 patterns; defaults to framework boost even for weak text

### Solution Strategy
Add **explicit Stage 0 detection patterns** before framework boost logic in `score_rd()` method.

### Implementation
**File:** `agents/scoring/rubric_v3_scorer.py`
**Method:** `score_rd()`
**Location:** Insert after line 444 (before framework boost)

```python
# Explicit Stage 0 detection (BEFORE framework boost)
stage_0_patterns = [
    r'^\s*.{0,100}(brochure|website|web page)',
    r'sustainability.{0,30}highlights',
    r'see our.{0,30}(site|website)',
    r'^.{0,50}(no|limited).{0,30}(report|disclosure)',
]

# Trigger only for short, promotional text
if self._match_patterns(text_lower, stage_0_patterns) and len(text) < 200:
    return DimensionScore(
        score=0,
        evidence=self._extract_evidence(text, stage_0_patterns),
        confidence=0.85,
        stage_descriptor=self.RD_STAGES[0]
    )
```

### Rationale
- **Length constraint:** Brochure text is typically <200 chars (prevents false positives on real reports that mention brochures)
- **Early return:** Prevents framework boost from over-scoring weak evidence
- **Confidence 0.85:** High confidence when clear promotional language detected

### Expected Impact
- Fixes **1 VIOLATION** (RD test 1: brochure text)
- May fix **1 WARNING** (RD test 2: GRI mapping if text is promotional)

---

## Refinement 2: GHG Assurance Distinction

### Problem
**Test Case:** "We report Scope 1, 2, and 3 emissions... limited assurance by Bureau Veritas."
- **Expected:** Stage 3 (Limited assurance)
- **Actual:** Stage 4 (Reasonable assurance)
- **Root Cause:** Pattern `r'third[- ]?party.{0,50}(assurance|verification)'` matches before checking assurance level

### Solution Strategy
Check **"limited assurance"** (Stage 3) **BEFORE** generic "third-party assurance" (Stage 4).

### Implementation
**File:** `agents/scoring/rubric_v3_scorer.py`
**Method:** `score_ghg()`
**Location:** Replace lines 426-433 (stage loop)

```python
# Check Stage 3 LIMITED assurance FIRST (before generic third-party)
limited_assurance_patterns = [
    r'limited.{0,30}assurance',
    r'assurance.{0,30}limited',
]

if self._match_patterns(text_lower, limited_assurance_patterns):
    # Confirm NOT reasonable assurance (avoid false Stage 3 if reasonable mentioned)
    if not re.search(r'reasonable.{0,30}assurance', text_lower):
        return DimensionScore(
            score=3,
            evidence=self._extract_evidence(text, limited_assurance_patterns),
            confidence=0.80,
            stage_descriptor=self.GHG_STAGES[3]
        )

# Then check remaining stages (4, 2, 1)
for stage in [4, 2, 1]:
    if self._match_patterns(text_lower, self.ghg_patterns.get(stage, [])):
        return DimensionScore(
            score=stage,
            evidence=self._extract_evidence(text, self.ghg_patterns[stage]),
            confidence=0.70 + (stage * 0.05),
            stage_descriptor=self.GHG_STAGES[stage]
        )
```

### Rationale
- **Order matters:** Stage 3 specific check before Stage 4 generic check
- **Negative check:** Ensures "reasonable assurance" doesn't match Stage 3
- **Rubric alignment:** Stage 3 = "limited assurance", Stage 4 = "reasonable assurance" per rubric spec

### Expected Impact
- Fixes **1 WARNING** (GHG test for msft_2023_002: limited assurance)

---

## Refinement 3: RMM Implicit Detection

### Problem
**Test Case:** "We publish climate-related financial disclosures aligned with TCFD covering governance, strategy, risk management, and metrics."
- **Expected:** Stage 2 (Climate risks identified via TCFD pillars)
- **Actual:** Stage 0 (No risk management evidence found)
- **Root Cause:** RMM patterns require explicit keywords ("scenario testing", "risk taxonomy"); misses implicit TCFD narrative

### Solution Strategy
Add **implicit Stage 2 detection** for TCFD/framework-based risk identification.

### Implementation
**File:** `agents/scoring/rubric_v3_scorer.py`
**Method:** `score_rmm()`
**Location:** After Stage 4/3 checks, before explicit Stage 2 patterns

```python
# After checking explicit stages 4, 3...

# Implicit Stage 2: TCFD/framework-based risk identification
implicit_stage_2_patterns = [
    r'TCFD.{0,50}(governance|strategy|risk|metrics)',
    r'climate.{0,30}risk.{0,30}(identified|disclosed|reported)',
    r'risk.{0,30}management.{0,30}(pillar|framework|disclosure)',
    r'(transition|physical).{0,30}risk.{0,30}(exposure|identified)',
]

if self._match_patterns(text_lower, implicit_stage_2_patterns):
    return DimensionScore(
        score=2,
        evidence=self._extract_evidence(text, implicit_stage_2_patterns),
        confidence=0.70,
        stage_descriptor=self.RMM_STAGES[2]
    )

# Continue with explicit Stage 2, 1 checks...
```

### Rationale
- **TCFD pillars:** "governance, strategy, risk, metrics" indicates Stage 2 risk identification per rubric
- **Lower confidence:** 0.70 (implicit detection less certain than explicit "scenario testing")
- **Placement:** After Stage 4/3 checks to avoid under-scoring explicit scenario testing

### Expected Impact
- Fixes **1 VIOLATION** (RMM test for msft_2023_003: TCFD narrative)

---

## Refinement 4: RD Framework Attribution

### Problem
**Test Case:** "We report our emissions annually..." + `framework="TCFD"` parameter
- **Expected:** Stage 1 (Annual reporting, no framework mentioned in text)
- **Actual:** Stage 2 (Framework detected via parameter)
- **Root Cause:** Framework boost applies based on parameter alone, even if text doesn't mention framework

### Solution Strategy
Require **explicit text evidence** of framework before applying boost.

### Implementation
**File:** `agents/scoring/rubric_v3_scorer.py`
**Method:** `score_rd()`
**Location:** Replace lines 447-451 (framework boost logic)

```python
# Framework boost requires BOTH parameter AND text mention
framework_boost = 0
framework_mentioned_in_text = False

if framework:
    # Check if framework is actually mentioned in text
    framework_pattern = re.escape(framework.lower())
    if re.search(framework_pattern, text_lower):
        framework_mentioned_in_text = True
        if framework in ['TCFD', 'ISSB']:
            framework_boost = 2
        elif framework in ['GRI', 'SASB']:
            framework_boost = 1

# Continue with pattern matching...
# Only apply framework_boost if framework_mentioned_in_text == True
```

### Rationale
- **Text evidence required:** Aligns with rubric requirement that disclosure must explicitly reference framework
- **Parameter alone insufficient:** Prevents over-scoring when framework inferred from metadata
- **Maintains boost logic:** Still applies boost when framework IS mentioned in text

### Expected Impact
- Fixes **2 WARNINGS** (RD tests where framework parameter present but text doesn't mention it)

---

## Data Strategy

### No New Data Required
- **Existing Validation Suite:** 23 test cases from `validate_rubric_compliance.py`
- **Existing Differential Suite:** 2,447 test cases from `test_rubric_v3_differential.py`
- **Existing Microsoft Findings:** 8 findings from `aggregate_microsoft_report.py`

### Data Splits
- **Not applicable:** No training/test split needed (pattern-matching, not ML)

### Normalization
- **Text lowercasing:** Already handled via `text_lower = text.lower()`
- **Whitespace handling:** Regex patterns use `.{0,N}` for flexible whitespace

### Leakage Guards
- **Not applicable:** No training phase; validation suite is fixed from Task 003

---

## Verification Plan

### Phase 1: TDD Baseline
**Objective:** Confirm current failures before implementing fixes

1. Write 4 failure-path tests in `tests/test_rubric_v3_refinements.py`:
   - `test_refinement_1_rd_stage0_brochure_text()` - EXPECT FAIL (currently scores 2, should be 0)
   - `test_refinement_2_ghg_limited_assurance()` - EXPECT FAIL (currently scores 4, should be 3)
   - `test_refinement_3_rmm_implicit_tcfd_risk()` - EXPECT FAIL (currently scores 0, should be 2)
   - `test_refinement_4_rd_framework_attribution_requires_text()` - EXPECT FAIL (currently scores 2, should be 1)

2. Run tests:
   ```bash
   pytest tests/test_rubric_v3_refinements.py -v -m cp
   # Expected: 4 failed, 0 passed
   ```

3. Capture baseline:
   ```bash
   pytest tests/test_rubric_v3_refinements.py -v > tasks/004-rubric-v3-refinements/qa/tdd_baseline_failures.txt
   ```

### Phase 2: Implementation
**Objective:** Implement 4 refinements in order

1. Implement Refinement 1 (RD Stage 0)
2. Implement Refinement 2 (GHG assurance)
3. Implement Refinement 3 (RMM implicit)
4. Implement Refinement 4 (RD framework)

### Phase 3: TDD Validation
**Objective:** Confirm all 4 tests now pass

```bash
pytest tests/test_rubric_v3_refinements.py -v -m cp
# Expected: 4 passed, 0 failed
```

### Phase 4: Full SCA Validation
**Objective:** Pass all 8 SCA v13.8 gates

1. **Coverage Gate:**
   ```bash
   pytest --cov=agents/scoring/rubric_v3_scorer --cov-branch --cov-report=xml:tasks/004-rubric-v3-refinements/qa/coverage.xml
   # Requirement: ≥95% line & branch
   ```

2. **Type Safety Gate:**
   ```bash
   mypy --strict agents/scoring/rubric_v3_scorer.py > tasks/004-rubric-v3-refinements/qa/mypy.txt
   # Requirement: 0 errors
   ```

3. **Complexity Gate:**
   ```bash
   python -m lizard agents/scoring/rubric_v3_scorer.py -o tasks/004-rubric-v3-refinements/qa/lizard_report.txt
   # Requirement: CCN ≤10, Cognitive ≤15
   ```

4. **Documentation Gate:**
   ```bash
   python -m interrogate agents/scoring/ > tasks/004-rubric-v3-refinements/qa/interrogate.txt
   # Requirement: ≥95% docstring coverage
   ```

5. **Security Gate:**
   ```bash
   detect-secrets scan agents/ > tasks/004-rubric-v3-refinements/qa/secrets.json
   bandit -r agents/ -f json -o tasks/004-rubric-v3-refinements/qa/bandit.json
   # Requirement: 0 findings
   ```

6. **Differential Re-Test (Determinism):**
   ```bash
   python scripts/test_rubric_v3_differential.py > tasks/004-rubric-v3-refinements/qa/differential_post_refinement.txt
   # Requirement: 2,447 cases, 0 crashes, 100% determinism
   ```

7. **Rubric Compliance Re-Validation:**
   ```bash
   python scripts/validate_rubric_compliance.py | tee tasks/004-rubric-v3-refinements/qa/rubric_compliance_post_refinement.txt
   # Target: ≥85% exact match, 0 violations
   ```

8. **Microsoft Delta Report:**
   ```bash
   python scripts/aggregate_microsoft_report.py > tasks/004-rubric-v3-refinements/artifacts/microsoft_post_refinement.json
   # Compare with Task 003 baseline
   ```

---

## Success Thresholds

### Must-Pass Gates (Hard Requirements)
- TDD: 4 tests pass after implementation
- Coverage: ≥95% line & branch on CP
- Type Safety: 0 mypy --strict errors
- Complexity: CCN ≤10, Cognitive ≤15
- Docs: ≥95% interrogate on CP
- Determinism: 100% (0 violations)

### Target Metrics (Success Criteria)
- Exact Match: ≥85% (≥20/23 tests)
- Violations: 0
- Warnings: ≤2

### Acceptable Fallback
- Exact Match: ≥78% (≥18/23 tests)
- Violations: 0
- Warnings: ≤4

---

## Differential Testing

### Sensitivity Analysis
**Objective:** Confirm refinements don't break existing correct scores

1. Run differential suite on **baseline scorer** (Task 003):
   - Capture 1,200 fuzz case outputs → `baseline_outputs.json`

2. Run differential suite on **refined scorer** (Task 004):
   - Capture 1,200 fuzz case outputs → `refined_outputs.json`

3. Compare outputs:
   ```python
   delta_count = sum(baseline[i] != refined[i] for i in range(1200))
   print(f"Changed scores: {delta_count}/1200 ({delta_count/1200*100:.1f}%)")
   ```

4. Investigate deltas:
   - Review all changed scores for correctness
   - Document intentional improvements vs unintended regressions

### Domain Method Validation
**Objective:** Validate against rubric specification

- Cross-reference each refinement against official `esg_maturity_rubricv3.md` stage descriptors
- Confirm pattern changes align with rubric language
- Document alignment in delta report

---

## Deliverables

1. **Context Artifacts:** hypothesis.md, design.md, evidence.json, data_sources.json, adr.md, assumptions.md, cp_paths.json
2. **TDD Tests:** `tests/test_rubric_v3_refinements.py` (4 failure-path tests marked `@pytest.mark.cp`)
3. **Refined Scorer:** `agents/scoring/rubric_v3_scorer.py` (4 method modifications)
4. **Validation Artifacts:** 8 QA reports in `tasks/004-rubric-v3-refinements/qa/`
5. **Delta Report:** `tasks/004-rubric-v3-refinements/reports/REFINEMENT_DELTA_REPORT.md`
6. **Traceability:** run_log.txt, run_manifest.json, run_events.jsonl

---

**Design Approved:** Ready for TDD implementation under SCA Protocol v13.8
