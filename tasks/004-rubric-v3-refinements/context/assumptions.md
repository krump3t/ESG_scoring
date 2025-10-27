# Assumptions - Task 004: Rubric v3.0 Refinements

**Task ID:** 004-rubric-v3-refinements
**Date:** 2025-10-22

---

## Scoring Assumptions

### A1: Pattern Matching is Sufficient for Precision Improvements
**Assumption:** Refining regex patterns can achieve ≥85% exact match rate without requiring ML/NLP approaches

**Justification:** Current 91.3% acceptable rate indicates pattern logic is fundamentally sound; targeted refinements address specific known failures

**Risk if Wrong:** May plateau below 85% target; would require algorithmic redesign

**Validation:** Track exact match rate improvement; if <78% after refinements, escalate to redesign

---

### A2: Text Length Discriminates Promotional vs Substantive Content
**Assumption:** Brochure/promotional text is typically <200 characters; real ESG reports exceed this

**Justification:** Manual review of validation test cases shows promotional text averages 50-150 chars, while substantive disclosures average 300+ chars

**Risk if Wrong:** May misclassify short substantive statements as promotional

**Validation:** Test on Microsoft findings (all >200 chars); monitor for false Stage 0 classifications

---

### A3: "Limited Assurance" Always Precedes "Reasonable Assurance" in Maturity
**Assumption:** Companies progress from limited → reasonable assurance; won't skip to reasonable without first having limited

**Justification:** Assurance standards (ISAE 3000, AA1000AS) define limited as lower level than reasonable

**Risk if Wrong:** May under-score companies that jump directly to reasonable assurance

**Validation:** Check Microsoft findings for any "reasonable" without prior "limited" mention

---

### A4: TCFD Pillar Disclosure Implies Risk Framework Exists (Stage 2)
**Assumption:** Companies disclosing all 4 TCFD pillars (governance, strategy, risk, metrics) have defined risk taxonomy

**Justification:** TCFD framework requires periodic assessment across pillars; implies Stage 2 "periodic assessments"

**Risk if Wrong:** May over-score companies with narrative-only disclosure (no actual framework)

**Validation:** Lower confidence (0.70) for implicit detection; place after explicit Stage 4/3 checks

---

### A5: Framework Parameter Accuracy
**Assumption:** Framework parameter (e.g., `framework="TCFD"`) is reliable metadata from upstream extraction

**Justification:** Parameter comes from validated extraction pipeline in bronze/silver layers

**Risk if Wrong:** Over-reliance on metadata vs text content

**Validation:** Require text evidence IN ADDITION to parameter for framework boost

---

## Testing Assumptions

### A6: 23 Test Cases Provide Sufficient Coverage
**Assumption:** Current validation suite (23 test cases) covers representative rubric scenarios for all 7 dimensions

**Justification:** Task 003 validation selected test cases directly from rubric specification stage descriptors + real Microsoft findings

**Risk if Wrong:** May have blind spots for edge cases not in test suite

**Validation:** Monitor production scoring for unexpected patterns; expand test suite in future tasks if needed

---

### A7: Determinism Preservation Under Additive Changes
**Assumption:** Adding new patterns (early returns) won't introduce non-deterministic behavior

**Justification:** All changes are regex pattern matching (no randomness, no external API calls, no time-based logic)

**Risk if Wrong:** Violates SCA v13.8 authenticity invariant

**Validation:** Re-run differential suite (2,447 cases, 10 iterations each) to confirm 100% determinism

---

### A8: Microsoft Findings Represent Production Use Cases
**Assumption:** 8 Microsoft findings from 2023 report are representative of real-world corporate ESG disclosures

**Justification:** Microsoft is MSCI AAA / CDP A- rated; findings sourced from actual published sustainability report

**Risk if Wrong:** May be biased toward high-maturity companies; may not generalize to lower-maturity companies

**Validation:** Document delta changes for Microsoft findings; note if scores change significantly (>1 stage)

---

## Implementation Assumptions

### A9: No Breaking Changes to Existing API
**Assumption:** Refinements don't change method signatures, return types, or external interfaces

**Justification:** All changes are internal to scoring methods; DimensionScore dataclass unchanged

**Risk if Wrong:** Breaks downstream consumers (aggregation, MCP endpoints)

**Validation:** Run full E2E test suite after implementation

---

### A10: Coverage Will Remain ≥95% After Refinements
**Assumption:** Adding new code paths won't drop coverage below 95% threshold

**Justification:** All new patterns will be covered by 4 new TDD tests

**Risk if Wrong:** Fails SCA coverage gate

**Validation:** Run coverage immediately after implementation; add tests if <95%

---

## Validation Assumptions

### A11: Rubric Specification is Stable (No v3.1 Updates Mid-Task)
**Assumption:** `esg_maturity_rubricv3.md` won't be updated during Task 004 implementation

**Justification:** Rubric v3.0 is stable since Task 003 completion; no planned updates

**Risk if Wrong:** Refinements may target outdated specification

**Validation:** Check rubric file modification date before starting implementation

---

### A12: Differential Suite Represents Production Input Distribution
**Assumption:** 1,200 fuzz cases from Task 003 cover diverse text patterns seen in production

**Justification:** Fuzz cases generated from templates spanning all 7 dimensions, all stages, various text lengths

**Risk if Wrong:** May miss production edge cases not in fuzz suite

**Validation:** Monitor production errors; expand fuzz suite if new patterns emerge

---

## Constraints

### C1: No External Dependencies
**Constraint:** Refinements must not introduce new library dependencies (e.g., spaCy, NLTK)

**Rationale:** Keep scorer lightweight, deterministic, and audit-friendly

---

### C2: Backward Compatibility
**Constraint:** Refinements must not break existing valid test cases from Task 003

**Rationale:** Regression prevention; maintain trust in scorer

**Validation:** Re-run Task 003 validation suites as regression tests

---

### C3: Execution Time Budget
**Constraint:** Refinements must not increase scoring time per finding by >10%

**Rationale:** Maintain production performance (currently <10ms per finding)

**Validation:** Benchmark scoring time before/after refinements

---

**Assumptions Complete:** 12 assumptions + 3 constraints documented
