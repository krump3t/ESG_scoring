# Design - Rubric v3.0 Implementation

**Task ID:** 003-rubric-v3-implementation
**Date:** 2025-10-22

---

## Architecture Overview

### Data Flow

```
Bronze Layer (Real Reports)
    ↓
Silver Layer (Normalized Findings) [MCPNormalizerAgent]
    ↓
Gold Layer (7-Dimensional Scores) [RubricV3Scorer → MCPScoringAgent]
    ↓
Validation & Cross-Check (External ESG Ratings)
```

---

## Component Design

### 1. RubricV3Scorer (`agents/scoring/rubric_v3_scorer.py`)

**Purpose:** Authentic implementation of 7-dimensional rubric per `rubrics/esg_maturity_rubricv3.md`

**Core Methods:**
- `score_all_dimensions(finding) → Dict[str, DimensionScore]`
- `score_tsp(text, framework) → DimensionScore`  # Target Setting & Planning
- `score_osp(text, framework) → DimensionScore`  # Operational Structure
- `score_dm(text, framework) → DimensionScore`   # Data Maturity
- `score_ghg(text, framework) → DimensionScore`  # GHG Accounting
- `score_rd(text, framework) → DimensionScore`   # Reporting & Disclosure
- `score_ei(text, framework) → DimensionScore`   # Energy Intelligence
- `score_rmm(text, framework) → DimensionScore`  # Risk Management
- `calculate_overall_maturity(scores) → (float, str)`

**Evidence Patterns:**
- Each dimension has 4-5 regex patterns per stage (0-4)
- Patterns match rubric specification evidence criteria
- No hardcoded scores - all evidence-based

**DimensionScore dataclass:**
```python
@dataclass
class DimensionScore:
    score: int  # 0-4
    evidence: str  # Matched text snippet
    confidence: float  # 0.0-1.0
    stage_descriptor: str  # Human-readable stage
```

---

### 2. Gold Schema (`iceberg/tables/gold_schema.py`)

**Schema Changes:**
- **Added:** 28 fields for 7 dimensions (4 fields per dimension)
  - `{dim}_score` (int32, 0-4)
  - `{dim}_evidence` (large_string)
  - `{dim}_confidence` (float64, 0.0-1.0)
  - `{dim}_stage_descriptor` (string)

- **Updated:**
  - `overall_maturity` (float64, 0.0-4.0) - average of 7 dimensions
  - `maturity_label` (string) - mapped via `overall_maturity_to_label()`

**Validation:**
- Checks all 7 dimension scores in 0-4 range
- Validates overall_maturity = avg(7 dimensions)
- Ensures confidence values in 0.0-1.0 range

---

### 3. MCP Scoring Agent (`agents/scoring/mcp_scoring.py`)

**Integration:**
- Instantiates `RubricV3Scorer` in `__init__`
- `score_finding()` calls `rubric_scorer.score_all_dimensions()`
- Populates all 28 dimension fields in gold record
- Generates dimension-aware evidence summary and reasoning

**Helper Methods:**
- `_extract_best_evidence_summary(dimension_scores)` - Uses highest-scoring dimension
- `_generate_reasoning_v3(dimension_scores, overall_maturity)` - Explains 7-dimensional breakdown with strengths/gaps

---

## Data Strategy

### Data Splits

**Training Data:** N/A (rule-based scoring, not ML)

**Validation Data:**
- **Primary:** Microsoft, Shell, ExxonMobil (real sustainability reports)
- **Secondary:** External ESG ratings (MSCI, CDP, DJSI)

**Test Data:**
- Differential testing: Perturbed versions of real findings
- Edge cases: Missing dimensions, conflicting evidence

### Normalization

**Input Normalization:**
- Text lowercased for pattern matching
- Unicode normalized
- No stemming/lemmatization (preserve exact terms like "SBTi validated")

**Output Normalization:**
- All scores integer (0-4) or float (0.0-4.0)
- Confidence always float (0.0-1.0)
- Evidence truncated to max 200 chars

### Leakage Guards

**Not Applicable:** Rule-based system with no training phase

**Data Isolation:**
- Bronze/Silver/Gold layers strictly separated
- No feedback loop from gold scores to bronze/silver
- External validation performed offline (no online learning)

---

## Verification Plan

### 1. Differential Testing

**Tool:** `scripts/test_differential_scoring.py`

**Tests:**
- **Consistency:** Same input → same output (10 iterations)
- **Perturbation:** Small text changes → similar scores (±1 stage tolerance)
- **Monotonicity:** More evidence → higher or equal score
- **Sensitivity:** Framework mentions → predictable score impact

**Requirements:**
- >= 1,200 test cases
- Unique ratio >= 0.5
- No crashes or exceptions

### 2. Sensitivity Analysis

**Variables:**
- Evidence strength (weak/moderate/strong keywords)
- Framework presence (no framework, TCFD, SBTi, etc.)
- Text length (50 words, 200 words, 500 words)

**Expected Behavior:**
- SBTi validated → TSP score 4
- TCFD aligned → RD score >= 2
- Scope 1/2/3 mentioned → GHG score >= 2

### 3. Cross-Validation (External Ratings)

**Sources:**
- **MSCI ESG Rating:** AAA (Leader) for Microsoft
- **CDP Climate Score:** A- (Leadership) for Microsoft
- **DJSI Member:** Yes for Microsoft

**Validation Method:**
- Map external ratings to our 0-4 scale:
  - MSCI AAA → Overall 3.6-4.0 (Leading)
  - CDP A- → Overall 3.0-3.5 (Advanced)
- Calculate Pearson correlation
- Document discrepancies and methodology differences

### 4. Domain Method Verification

**Rubric Specification Compliance:**
- Each dimension scorer implements exact stage criteria from `rubrics/esg_maturity_rubricv3.md`
- Evidence patterns validated against actual sustainability reports
- Stage descriptors match rubric language

**Expert Review:**
- ESG domain expert reviews dimension scores for Microsoft
- Validates evidence snippets match score justifications
- Confirms overall maturity aligns with industry benchmarks

---

## Success Thresholds

### Functional Requirements

1. ✅ **7 Dimensions Scored:** All findings produce scores for TSP, OSP, DM, GHG, RD, EI, RMM
2. ✅ **Valid Range:** Each dimension 0-4, overall 0.0-4.0
3. ✅ **Schema Compliant:** Gold records validate successfully
4. ⏳ **Performance:** < 500ms per finding

### Quality Requirements

5. ⏳ **External Validation:** Microsoft overall maturity 3.0-4.0 (matches MSCI AAA)
6. ⏳ **Correlation:** Pearson r >= 0.7 with external ratings
7. ⏳ **Evidence Accuracy:** >= 90% correct stage detection for known patterns

### SCA Protocol Compliance

8. ✅ **No Placeholders:** Zero TODO/FIXME/PLACEHOLDER in CP files
9. ⏳ **Failure-Path Tests:** All CP files have exception tests
10. ⏳ **Differential Testing:** >= 1,200 cases executed
11. ⏳ **Traceability:** run_log.txt, manifests, events present

---

## Risk Mitigation

### Technical Risks

**R1: Pattern Matching False Positives**
- **Mitigation:** Context extraction validates matched snippets
- **Test:** Differential testing with adversarial examples

**R2: Dimension Score Imbalance**
- **Mitigation:** Aggregate across multiple findings per organization
- **Test:** Coverage rate tracking (>= 4 of 7 dimensions)

### Process Risks

**R3: Schema Migration Complexity**
- **Mitigation:** All previous test results explicitly invalidated
- **Test:** Fresh pipeline run with new schema

**R4: External Rating Misalignment**
- **Mitigation:** Document methodology differences, tune patterns
- **Test:** Correlation analysis, expert review

---

## Determinism Strategy

### Reproducibility Requirements

1. **Fixed Seeds:** N/A (no randomness in rule-based scorer)
2. **Pinned Dependencies:**
   - Python 3.11
   - regex >= 2024.4.16
   - pyarrow >= 14.0.0

3. **REPRODUCIBILITY.md:** (TO BE CREATED)
   - Environment specifications
   - Execution instructions
   - Expected output hashes

### Cache Strategy

**Evidence Pattern Cache:**
- Compiled regex patterns cached at scorer initialization
- No runtime compilation
- Deterministic matching order (stage 4 → 3 → 2 → 1)

---

## Phase Execution Plan

### Phase 1: Implementation ✅ COMPLETE
- Created `rubric_v3_scorer.py`
- Updated `gold_schema.py`
- Updated `mcp_scoring.py`
- Created test suite

### Phase 2: Validation ⏳ IN PROGRESS
- Add failure-path tests
- Scan and remove placeholders
- Execute differential testing
- Create state persistence

### Phase 3: Cross-Validation ⏳ PENDING
- Re-run pipeline with real data
- Compare Microsoft scores to MSCI AAA
- Calculate correlation coefficients
- Document findings

### Phase 4: Hardening ⏳ PENDING
- Performance optimization
- Error handling improvements
- Documentation updates
- REPRODUCIBILITY.md creation

---

**Version:** Design v1.0 for Rubric v3.0 Implementation
**Last Updated:** 2025-10-22
