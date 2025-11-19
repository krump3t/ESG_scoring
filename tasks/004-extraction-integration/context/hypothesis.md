# Task 004: Extraction Integration - Hypothesis

**Task ID:** 004-extraction-integration
**Date:** 2025-11-19
**Protocol:** SCA v13.8-MEA
**Depends On:** Task 003 (Live Ingestion Pilot - SUCCESS)

---

## Hypothesis

**Primary Claim:**
The ExtractionRouter can correctly identify and parse "Item 1A: Risk Factors" from the authentic Apple Inc. 2024 10-K HTML filing (1.43 MB, downloaded in Task 003).

**Specific Predictions:**

1. **File Handling:**
   - ExtractionRouter can load and parse 1.43 MB HTML file without memory errors
   - HTML parser can handle SEC EDGAR's single-file format (inline CSS, large tables)

2. **Section Identification:**
   - Router correctly identifies "Item 1A" (Risk Factors) section
   - Section boundaries are properly detected (start/end markers)
   - Metadata includes section headers and structural information

3. **Content Extraction:**
   - Extracted findings include ESG-relevant risk disclosures
   - Text contains climate/environmental risk keywords (e.g., "climate", "environmental", "carbon")
   - Findings are not empty or truncated

4. **Output Structure:**
   - Returns structured findings (list/dict format)
   - Each finding includes text content and metadata
   - Output is serializable to JSON

---

## Success Criteria

### Must Pass (Blocking)

1. ✅ **File Exists Check**
   - Target file: `data/raw/sec_edgar/AAPL_2024_10K.htm`
   - File size: 1,503,780 bytes (±1%)
   - SHA256: `24a830a0f1256e371d36a1f7f72e5e85a38037d1de2f6f966eb8457db42ff6d6`

2. ✅ **Extraction Success**
   - `router.extract(file_path)` completes without exceptions
   - Returns non-empty result
   - `len(findings) > 0`

3. ✅ **Content Validation**
   - At least one finding contains "climate" OR "risk" (case-insensitive)
   - Text length > 100 characters (not stub data)
   - No parser error messages in output

4. ✅ **Metadata Presence**
   - Metadata includes section identifier ("Item 1A" or equivalent)
   - Metadata includes document source information
   - Metadata is structured (dict/object, not string blob)

### Should Pass (Quality)

5. ⚠️ **ESG Keyword Coverage**
   - Findings include at least 3 of: ["climate", "environmental", "carbon", "emissions", "sustainability", "renewable"]
   - Indicates proper ESG-relevant content extraction

6. ⚠️ **Parsing Efficiency**
   - Extraction completes in < 30 seconds
   - Memory usage < 500 MB
   - No warnings about oversized regex matches

7. ⚠️ **Output Completeness**
   - Multiple findings (not just single text blob)
   - Section structure preserved (paragraphs, headings)
   - Tables or lists properly formatted

---

## Test Data

**Source File:** Apple Inc. 2024 10-K (Task 003 Artifact)
- **Path:** `data/raw/sec_edgar/AAPL_2024_10K.htm`
- **Size:** 1,503,780 bytes (1.43 MB)
- **Format:** HTML (SEC EDGAR single-file format)
- **SHA256:** `24a830a0f1256e371d36a1f7f72e5e85a38037d1de2f6f966eb8457db42ff6d6`
- **Source URL:** `https://www.sec.gov/Archives/edgar/data/320193/000032019324000123/aapl-20240928.htm`
- **Filing Date:** 2024-11-01
- **Report Date:** 2024-09-28
- **CIK:** 0000320193

**Expected Content Sections:**
- Item 1: Business
- Item 1A: Risk Factors (PRIMARY TARGET)
- Item 7: Management's Discussion and Analysis
- Item 8: Financial Statements

**Known ESG Risks in Apple 10-K (Historical):**
- Climate change impact on supply chain
- Environmental regulations
- Product recycling and e-waste
- Energy consumption in data centers
- Supplier environmental compliance

---

## Risks & Mitigations

### Risk 1: Large File Parsing
**Issue:** 1.43 MB HTML file may cause memory issues or regex timeout
**Likelihood:** Medium
**Mitigation:**
- Use streaming parsers (BeautifulSoup with lxml)
- Limit regex scope to section boundaries
- Chunk large documents before parsing

### Risk 2: SEC HTML Format Changes
**Issue:** SEC EDGAR HTML structure may differ from expected format
**Likelihood:** Low (standardized format)
**Mitigation:**
- Inspect actual HTML structure before writing parser
- Use flexible selectors (multiple fallback patterns)
- Log parser warnings for manual review

### Risk 3: Item 1A Not Detected
**Issue:** Section header format may not match expected patterns
**Likelihood:** Medium
**Mitigation:**
- Test with multiple header patterns: "Item 1A", "ITEM 1A", "Item&#160;1A"
- Use regex with whitespace normalization
- Fallback to table-of-contents parsing

### Risk 4: Empty Extraction
**Issue:** Parser runs but extracts no meaningful content
**Likelihood:** Low
**Mitigation:**
- Validate extraction on known-good sample first
- Log intermediate steps (section detection, text extraction)
- Fail fast with clear error messages

---

## Exclusions

**Out of Scope for Task 004:**

1. **Multi-Document Processing**
   - Only testing single Apple 10-K file
   - Batch processing deferred to later task

2. **Advanced NLP Analysis**
   - No sentiment analysis, entity extraction, or topic modeling
   - Focus on structural parsing only

3. **Database Storage**
   - No persistence to vector store or graph database
   - Outputs to JSON file only

4. **Extraction Quality Scoring**
   - No rubric-based scoring or validation
   - Simple keyword presence checks only

5. **Performance Optimization**
   - No benchmarking or profiling
   - Acceptable range: < 30 seconds, < 500 MB

---

## Critical Path

**CP Files for Task 004:**
- `agents/extraction/extraction_router.py` - Main router logic
- `agents/extraction/html_parser.py` - HTML parsing (if exists)
- `agents/extraction/structured_extractor.py` - Section extraction
- `libs/extraction/backend_*.py` - Extraction backends

**Non-CP:**
- `data/raw/sec_edgar/AAPL_2024_10K.htm` - Test data (static artifact)
- Logging, configuration, utilities

---

## Power Analysis

**Sample Size:** N=1 (single Apple 10-K file)
**Effect Size:** Large (binary pass/fail - either extracts or doesn't)
**Confidence:** High (deterministic parser, no stochastic elements)

**Justification for N=1:**
- Proof-of-concept phase
- Deterministic extraction (no randomness)
- Single file sufficient to validate integration
- Multi-file validation in later task

---

## Verification Plan

### Phase 2: Red (Expected Failure)
1. Write `verify_extraction.py` script
2. Run against Apple 10-K
3. Document failure mode (if any):
   - Parser error? HTML format issue? Section detection?
   - Memory/timeout? Empty extraction?

### Phase 3: Green (Fix & Pass)
1. Analyze failure root cause
2. Patch extraction components (Option C: Script Generator)
3. Re-run verification
4. Iterate until all "Must Pass" criteria met

### Phase 4: Artifact Capture
1. Save extraction output to `artifacts/apple_2024_findings.json`
2. Capture metadata, timing, memory usage
3. Document findings in `HANDOFF.md`

---

## Compliance

**SCA Protocol Gates:**
- ✅ Context: This hypothesis.md + cp_paths.json
- ✅ Authenticity: Real Apple 10-K from Task 003 (SHA256 verified)
- ✅ Determinism: Single file, deterministic parser, fixed input
- ✅ Traceability: All steps documented in scripts and HANDOFF.md

**Task Dependencies:**
- ✅ Task 003: Live Ingestion Pilot (COMPLETE - Apple 10-K downloaded)
- ✅ Forensic Audit 000: Ground truth established (ExtractionRouter exists)

---

**Hypothesis Generated:** 2025-11-19
**Ready for Phase 2:** TDD Harness (Red)
