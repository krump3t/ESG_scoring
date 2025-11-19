# Task 006: Scoring Integration - Hypothesis

**Task ID:** 006-scoring-integration
**Date:** 2025-11-19
**Protocol:** SCA v13.8-MEA
**Depends On:** Task 005 (Retrieval Integration - SUCCESS)

---

## Hypothesis

**Primary Claim:**
The RubricV3Scorer can consume retrieval results from Task 005 and output valid ESG maturity scores across all rubric dimensions, producing a final aggregated maturity rating for Apple Inc. based on 10-K evidence.

**Specific Predictions:**

1. **Input Adaptation:**
   - Retrieval results from Task 005 can be formatted as scorer input
   - Chunk text converted to "finding_text" field
   - Metadata preserved for traceability

2. **Scoring Execution:**
   - RubricV3Scorer processes finding text without errors
   - Returns dimension scores for all themes (Climate, Governance, etc.)
   - Computes overall maturity level (0-5 scale)

3. **Output Validity:**
   - Maturity level is float between 0.0 and 5.0
   - Maturity label is string descriptor ("Minimal", "Developing", etc.)
   - Confidence score between 0.0 and 1.0
   - Dimension breakdown includes all rubric themes

4. **Semantic Relevance:**
   - Climate-related evidence yields higher Climate dimension scores
   - Non-climate text yields lower Climate dimension scores
   - Overall maturity reflects evidence quality

---

## Success Criteria

### Must Pass (Blocking)

1. ✅ **Input Loading**
   - Load retrieval results from `tasks/005-retrieval-integration/artifacts/retrieval_results.json`
   - Parse JSON without errors
   - Extract text from top-ranked chunks

2. ✅ **Scorer Initialization**
   - Import RubricV3Scorer successfully
   - Initialize with default rubric
   - No import or initialization errors

3. ✅ **Score Computation**
   - Call `scorer.score_finding({"finding_text": "..."})` successfully
   - Returns dict with required fields
   - No exceptions or crashes

4. ✅ **Output Validation**
   - `maturity_level` is float in range [0.0, 5.0]
   - `maturity_label` is non-empty string
   - `confidence` is float in range [0.0, 1.0]
   - `dimension_breakdown` is dict with ≥ 1 theme

### Should Pass (Quality)

5. ⚠️ **Score Reasonableness**
   - Climate evidence yields maturity_level > 0.0
   - Score reflects keyword presence (higher keywords = higher score)
   - Confidence > 0.0 for non-empty findings

6. ⚠️ **Dimension Differentiation**
   - Climate dimension score ≠ Governance dimension score
   - Climate-related evidence scores higher on Climate dimension
   - Dimension breakdown shows variation across themes

7. ⚠️ **Provenance Tracking**
   - Output includes source metadata (chunk IDs, URLs)
   - Traceability to Task 005 retrieval results
   - Company and year information preserved

---

## Test Data

**Source:** Task 005 Retrieval Results
- **Path:** `tasks/005-retrieval-integration/artifacts/retrieval_results.json`
- **Queries Available:** 3 ("climate risk", "environmental regulations", "carbon emissions")
- **Total Results:** 9 chunks with scores and metadata

**Test Finding Structure:**
```json
{
  "rank": 1,
  "chunk_id": "chunk_0012",
  "score": 0.500,
  "text_snippet": "...",
  "metadata": {
    "page": 8,
    "source_url": "https://www.sec.gov/...",
    "provider": "SECEdgarProvider",
    "doc_hash": "24a830a0f1256e37"
  }
}
```

**Adaptation to Scorer Format:**
```python
{
  "finding_text": "climate risk factors include...",
  "framework": "SEC 10-K Item 1A",
  "source_metadata": {...}
}
```

---

## Test Scenarios

### Scenario 1: High-Relevance Climate Evidence
**Input:** Top result from "climate risk" query (chunk_0012, score 0.500)
**Expected:** Climate dimension score ≥ 2, maturity_level > 1.0

### Scenario 2: Medium-Relevance Environmental Evidence
**Input:** Top result from "environmental regulations" query (chunk_0049, score 0.200)
**Expected:** Climate/Governance dimension scores ≥ 1, maturity_level > 0.0

### Scenario 3: No-Relevance XBRL Metadata
**Input:** Zero-score result (chunk_0000, XBRL taxonomy data)
**Expected:** All dimension scores = 0, maturity_level = 0.0

### Scenario 4: Aggregated Evidence
**Input:** Concatenated text from top-3 "climate risk" results
**Expected:** Higher maturity_level than individual chunks

---

## Risks & Mitigations

### Risk 1: Rubric Not Loaded
**Issue:** RubricV3Scorer may require external rubric file (JSON/YAML)
**Likelihood:** Medium
**Mitigation:**
- Check `agents/scoring/rubric_loader.py` for default rubric path
- Verify rubric file exists (e.g., `rubrics/esg_rubric_v3.json`)
- Use RubricLoader to load rubric explicitly

### Risk 2: Input Format Mismatch
**Issue:** Scorer may require additional fields beyond "finding_text"
**Likelihood:** Low (code shows only "finding_text" and optional "framework")
**Mitigation:**
- Adapt retrieval results to expected format
- Include minimal required fields only
- Add metadata separately if needed

### Risk 3: Zero Scores for All Dimensions
**Issue:** Keyword matching may fail if chunks lack rubric keywords
**Likelihood:** Medium (XBRL chunks, financial data)
**Mitigation:**
- Test with multiple chunks (climate-relevant vs non-climate)
- Accept zero scores as valid if evidence is non-ESG
- Document score distribution

### Risk 4: Dimension Code Names Unknown
**Issue:** Rubric theme codes may not be intuitive (e.g., "CLM" vs "Climate")
**Likelihood:** Low
**Mitigation:**
- Inspect rubric file to identify theme codes
- Map codes to human-readable names in output
- Document code-to-name mapping

---

## Exclusions

**Out of Scope for Task 006:**

1. **Multi-Company Scoring**
   - Only Apple 10-K evidence
   - No comparative scoring (Apple vs Microsoft)
   - Single-company proof-of-concept

2. **LLM-Based Scoring**
   - No watsonx.ai integration
   - No GPT-based assessment
   - Keyword-based scoring only (rubric v3.0 algorithm)

3. **Score Validation Against Ground Truth**
   - No manual ESG ratings for comparison
   - No third-party ESG scores (MSCI, Sustainalytics)
   - No quantitative validation

4. **Temporal Trends**
   - No year-over-year comparison
   - Single year (2024) only
   - No maturity progression analysis

5. **Detailed Evidence Extraction**
   - No sentence-level evidence mapping
   - No evidence table generation
   - Chunk-level evidence only

---

## Critical Path

**CP Files for Task 006:**
- `agents/scoring/rubric_v3_scorer.py` - Main scorer class
- `agents/scoring/rubric_loader.py` - Rubric file loader
- `agents/scoring/rubric_models.py` - Data models (MaturityRubric, Theme, Stage)
- `rubrics/esg_rubric_v3.json` - Rubric definition (if exists)

**Non-CP:**
- Task 005 artifact (static test data)
- Logging, configuration, utilities

---

## Power Analysis

**Sample Size:** 9 retrieval results (from 3 queries × 3 results)
**Effect Size:** Large (scoring works or doesn't - binary validation)
**Confidence:** High (deterministic keyword matching)

**Justification:**
- Proof-of-concept phase
- Deterministic rubric algorithm (no ML randomness)
- Multiple test scenarios cover range (high/medium/zero relevance)
- 9 results sufficient to validate scoring mechanics

---

## Verification Plan

### Phase 2: Red (Expected Failure)
1. Write `verify_scoring.py` script
2. Load Task 005 retrieval results
3. Format as scorer input
4. Attempt to call `scorer.score_finding()`
5. Document failure mode:
   - Rubric not found?
   - Input format issue?
   - Method signature mismatch?

### Phase 3: Green (Fix & Pass)
1. Analyze failure (if any)
2. Create adapter if needed (retrieval results → scorer input)
3. Load rubric explicitly if file path required
4. Re-run verification
5. Iterate until all "Must Pass" criteria met

### Phase 4: Validation
1. Run verify_scoring.py (Must PASS)
2. Test all 3 query result sets
3. Generate score summary for Apple 2024
4. Save to `artifacts/apple_2024_score.json`
5. Document in HANDOFF.md

---

## Compliance

**SCA Protocol Gates:**
- ✅ Context: This hypothesis.md + evidence.json + cp_paths.json
- ✅ Authenticity: Real Apple 10-K evidence from Tasks 003-005
- ✅ Determinism: Keyword-based rubric algorithm (deterministic)
- ✅ Traceability: All steps documented in scripts and HANDOFF.md

**Task Dependencies:**
- ✅ Task 005: Retrieval Integration (COMPLETE - 9 results available)
- ✅ Task 004: Extraction Integration (COMPLETE - chunks validated)
- ✅ Task 003: Live Ingestion (COMPLETE - authentic Apple 10-K)

---

**Hypothesis Generated:** 2025-11-19
**Ready for Phase 2:** TDD Harness (Red)
