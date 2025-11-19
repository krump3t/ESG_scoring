# Task 007: Pipeline Orchestration - Hypothesis

**Task ID:** 007-pipeline-orchestration
**Date:** 2025-11-19
**Protocol:** SCA v13.8-MEA
**Depends On:** Tasks 003-006 (ALL COMPLETE)

---

## Hypothesis

**Primary Claim:**
The verified components from Tasks 003-006 can be orchestrated into a single, cohesive pipeline that transforms a ticker symbol into a complete ESG maturity assessment without mocks or placeholders.

**Specific Predictions:**

1. **Component Integration:**
   - Task 003 artifact (Apple 10-K HTML) can be loaded from disk
   - Task 004 EnhancedPDFExtractor can process the file
   - Task 005 VectorStore can index and retrieve evidence
   - Task 006 RubricV3Scorer can score the retrieved evidence

2. **Data Flow:**
   - HTML file (1.43 MB) → 129 chunks (Task 004 validated)
   - 129 chunks → 50 indexed vectors (Task 005 sample)
   - 3 ESG queries → 9 retrieval results (Task 005 validated)
   - 9 results → 3 scored findings → 1 aggregate score (Task 006 validated)

3. **Output Validity:**
   - Final score matches Task 006 schema
   - Aggregate maturity level ∈ [0.0, 5.0]
   - Confidence ∈ [0.0, 1.0]
   - Full provenance chain maintained

4. **Performance:**
   - Total execution time < 60 seconds
   - No network calls (uses local Task 003 artifact)
   - Deterministic output (same input → same score)

---

## Success Criteria

### Must Pass (Blocking)

1. ✅ **File Loading**
   - Load `data/raw/sec_edgar/AAPL_2024_10K.htm` successfully
   - File size: 1.43 MB (verified in Task 003)
   - No file not found errors

2. ✅ **Extraction Step**
   - Call `EnhancedPDFExtractor.extract_from_file()`
   - Returns 100+ chunks
   - Each chunk has text, metadata, doc_id

3. ✅ **Indexing Step**
   - Create VectorStore instance
   - Index all chunks with keyword-based vectors
   - Store returns success for all chunks

4. ✅ **Retrieval Step**
   - Query: "climate risk" (validated in Task 005)
   - Returns top 3 results
   - Results include text_snippet, score, metadata

5. ✅ **Scoring Step**
   - Format retrieval results as RubricV3Scorer input
   - Call `scorer.score_finding()` for each result
   - Returns maturity_level, confidence, dimension_breakdown

6. ✅ **Aggregation**
   - Average maturity across findings
   - Calculate aggregate confidence
   - Generate dimension breakdown

7. ✅ **Output Generation**
   - Save to `artifacts/pipeline_output.json`
   - Schema matches Task 006 output
   - Includes full provenance chain

### Should Pass (Quality)

8. ⚠️ **Score Consistency**
   - Aggregate maturity ≈ 1.91 (Task 006 result)
   - Confidence ≈ 0.691 (Task 006 result)
   - Top dimensions: OSP, DM, GHG

9. ⚠️ **Provenance Tracking**
   - SEC EDGAR URL preserved
   - Document hash matches Task 003
   - All intermediate artifacts linked

10. ⚠️ **Error Handling**
    - Graceful failures with clear messages
    - No unhandled exceptions
    - Logging at each pipeline stage

---

## Test Scenarios

### Scenario 1: Happy Path (Apple 2024 10-K)
**Input:**
- Ticker: AAPL
- Year: 2024
- File: `data/raw/sec_edgar/AAPL_2024_10K.htm`

**Expected Output:**
```json
{
  "company": "Apple Inc.",
  "ticker": "AAPL",
  "year": 2024,
  "aggregate_score": {
    "maturity_level": 1.91,
    "maturity_label": "Advanced",
    "confidence": 0.691
  },
  "findings_scored": 3,
  "execution_timestamp": "2025-11-19T...",
  "success": true
}
```

### Scenario 2: Missing Input File
**Input:**
- File: `data/raw/sec_edgar/NONEXISTENT.htm`

**Expected Behavior:**
- Pipeline raises `FileNotFoundError`
- Clear error message: "Raw input file not found: ..."
- Exits with code 1

### Scenario 3: Empty Query Results
**Input:**
- Query: "nonexistent keyword xyz"

**Expected Behavior:**
- Retrieval returns 0 results
- Scoring step skipped or returns default score
- Output includes `findings_scored: 0`

---

## Risks & Mitigations

### Risk 1: API Signature Mismatch
**Issue:** Component APIs may differ from verification scripts
**Likelihood:** Medium
**Mitigation:**
- Review Task 004/005/006 verification scripts for exact method calls
- Use same parameters and data structures
- Test each component individually before chaining

### Risk 2: File Path Issues
**Issue:** Task 003 artifact may be in different location
**Likelihood:** Low (we verified the path)
**Mitigation:**
- Check file existence before processing
- Use absolute paths or Path objects
- Document expected file location in README

### Risk 3: Memory Constraints
**Issue:** Loading 129 chunks into memory may be slow
**Likelihood:** Low (small dataset)
**Mitigation:**
- Process in batches if needed
- Monitor memory usage
- Limit vector store to top-k chunks

### Risk 4: Score Variance
**Issue:** Orchestrated score may differ from Task 006 due to different data flow
**Likelihood:** Medium
**Mitigation:**
- Use identical query ("climate risk", "environmental regulations", "carbon emissions")
- Use same top-k retrieval (k=3)
- Document any differences in HANDOFF.md

---

## Exclusions

**Out of Scope for Task 007:**

1. **Multi-Company Pipeline**
   - Only Apple 10-K
   - No batch processing
   - Single-company proof-of-concept

2. **Live Ingestion**
   - Uses Task 003 artifact (already downloaded)
   - No SEC EDGAR API calls
   - Offline-only execution

3. **Advanced Retrieval**
   - Keyword-based vectorization only (Task 005 method)
   - No semantic embeddings (watsonx.ai)
   - No re-ranking

4. **LLM-Based Scoring**
   - RubricV3Scorer only (keyword-based)
   - No watsonx.ai integration
   - No GPT-based assessment

5. **UI/API**
   - Command-line script only
   - No REST API
   - No web interface

---

## Critical Path

**CP Files for Task 007:**
- `tasks/007-pipeline-orchestration/scripts/orchestrate_pipeline.py` - Main orchestrator
- (Dependencies from Tasks 003-006 already verified)

**Non-CP:**
- Logging, configuration, utilities
- Error handling wrappers
- Output formatting helpers

---

## Verification Plan

### Phase 1: Scaffolding (COMPLETE)
1. Create task directory structure
2. Generate hypothesis.md, cp_paths.json, evidence.json
3. Create README_TASK.md

### Phase 2: Implementation
1. Write `orchestrate_pipeline.py`
2. Import verified components from Tasks 003-006
3. Chain data flow: Load → Extract → Retrieve → Score
4. Add logging at each stage
5. Generate output JSON

### Phase 3: Execution
1. Run orchestrator: `python scripts/orchestrate_pipeline.py`
2. Validate output schema
3. Compare aggregate score to Task 006 (expect ≈1.91)
4. Verify provenance chain

### Phase 4: Validation & HANDOFF
1. Document execution results
2. Save output to `artifacts/pipeline_output.json`
3. Create HANDOFF.md
4. Commit Task 007 to repository

---

## Compliance

**SCA Protocol v13.8-MEA Gates:**
- ✅ Context: This hypothesis.md + cp_paths.json + evidence.json
- ✅ Authenticity: Uses verified components from Tasks 003-006
- ✅ Determinism: Keyword-based scoring (deterministic)
- ✅ Traceability: Full provenance chain from SEC EDGAR to score

**Task Dependencies:**
- ✅ Task 003: Live Ingestion (COMPLETE - Apple 10-K downloaded)
- ✅ Task 004: Extraction Integration (COMPLETE - 129 chunks validated)
- ✅ Task 005: Retrieval Integration (COMPLETE - vector search working)
- ✅ Task 006: Scoring Integration (COMPLETE - maturity scores generated)

---

**Hypothesis Generated:** 2025-11-19
**Ready for Phase 2:** Implementation
