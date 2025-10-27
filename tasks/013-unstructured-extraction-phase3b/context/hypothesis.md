# Hypothesis - Phase 3B: Unstructured Extraction with LLM

**Task ID**: 013-unstructured-extraction-phase3b
**Phase**: 3B (Completes Phase 3 Asymmetric Extraction)
**Date**: 2025-10-24
**SCA Protocol**: v13.8-MEA

---

## Research Question

Can we achieve ≥85% extraction accuracy on ESG metrics from unstructured data (PDF reports) using IBM watsonx.ai LLM with REAL sustainability reports?

---

## Success Criteria (Testable)

### SC1: LLM Extraction Accuracy
- **Metric**: Extraction accuracy on ESG metrics from PDFs
- **Target**: ≥85% accuracy (within ±10% of ground truth)
- **Data**: 3+ real ESG PDF reports (Apple, Microsoft, Tesla)
- **Method**: Compare LLM-extracted values against manually verified ground truth

### SC2: PDF Text Extraction
- **Metric**: Text extraction completeness from born-digital PDFs
- **Target**: ≥95% of text extracted (no missing pages)
- **Data**: Real Apple Sustainability Report 2024 PDF
- **Method**: Compare extracted text length to expected length

### SC3: LLMExtractor Implementation
- **Metric**: Critical path file implementation with real domain logic
- **Target**: LLMExtractor class with prompt engineering, retry logic, response parsing
- **Exclusions**: No placeholders, no hardcoded metric values
- **Method**: Code review + AST analysis

### SC4: watsonx.ai Integration
- **Metric**: Successful API calls to IBM watsonx.ai granite-13b-chat-v2
- **Target**: 100% of test calls succeed (with retry logic)
- **Data**: Real API credentials (project_id + IAM key)
- **Method**: Integration tests with real API

### SC5: Response Caching (Determinism)
- **Metric**: Cached LLM responses for deterministic testing
- **Target**: All tests use cached responses (no live API calls in CI)
- **Method**: Response cache file exists, tests replay cached responses

### SC6: TDD Compliance
- **Metric**: Tests written BEFORE implementation
- **Target**: All CP tests committed before CP code (git timestamps)
- **Method**: Git log verification

### SC7: Test Coverage (CP)
- **Metric**: Line and branch coverage on CP files
- **Target**: ≥95% line coverage, ≥95% branch coverage
- **Files**: `llm_extractor.py`, `pdf_text_extractor.py`
- **Method**: pytest-cov with .coveragerc

### SC8: Test Suite (TDD)
- **Metric**: Number of tests with authentic data
- **Target**: ≥25 tests, all using REAL PDF data or cached LLM responses
- **Tests**: `test_llm_extractor_phase3b.py`, `test_pdf_text_extractor_phase3b.py`
- **Marks**: All tests marked `@pytest.mark.cp`

### SC9: Failure Path Testing
- **Metric**: Error handling for malformed PDFs, API failures, invalid responses
- **Target**: ≥5 failure-path tests asserting exceptions
- **Method**: pytest with `pytest.raises`

### SC10: End-to-End Validation
- **Metric**: Full pipeline test with REAL PDF
- **Target**: Extract Apple Sustainability Report → validate against ground truth → assert ≥85% accuracy
- **Data**: Real Apple PDF + manually verified ground truth
- **Method**: Integration test (may require API, can use cached response)

---

## Critical Path (CP) Files

1. **`agents/extraction/llm_extractor.py`** (~120 lines)
   - LLMExtractor class
   - IBM watsonx.ai API integration
   - Prompt engineering for ESG extraction
   - Response parsing and validation

2. **`agents/extraction/pdf_text_extractor.py`** (~80 lines)
   - PDF text extraction using PyMuPDF (fitz)
   - Text cleaning and normalization
   - Page-level extraction with error handling

---

## Exclusions (Out of Scope)

- ❌ OCR for scanned PDFs (assume born-digital only)
- ❌ HTML extraction (Phase 3 design includes it, but defer to future)
- ❌ Fine-tuning watsonx.ai models (use pre-trained granite-13b-chat-v2)
- ❌ Multi-language support (English only)
- ❌ Table extraction from PDFs (defer to future if needed)

---

## Power Analysis (Test Data Requirements)

### Minimum Test Corpus
- **3 real ESG PDF reports**: Apple, Microsoft, Tesla
- **Ground truth**: Manual verification of 10-15 metrics per company
- **Response cache**: 10-15 cached LLM responses for deterministic tests

### Statistical Power
- With 3 companies × 10 metrics = 30 data points
- Expected accuracy: 85% (25.5 correct, 4.5 incorrect)
- Margin of error: ±10% (accounts for LLM variability)

---

## Confidence Intervals

### Extraction Accuracy CI
- **Target**: 85% ± 10%
- **Acceptable Range**: 75%-95% accuracy
- **Below 75%**: Investigation required (prompt engineering, model selection)

### API Success Rate CI
- **Target**: 100% success with retry logic
- **Acceptable**: ≥98% (1-2 retries allowed)

---

## Assumptions & Risks

### A1: watsonx.ai API Access
- **Assumption**: User provides valid project_id and IAM API key
- **Risk**: API access denied or rate-limited
- **Mitigation**: Response caching for tests, retry logic with exponential backoff

### A2: PDF Availability
- **Assumption**: Real ESG PDFs are publicly downloadable (Apple, Microsoft, Tesla)
- **Risk**: PDFs behind paywalls or unavailable
- **Mitigation**: Use SEC 10-K sustainability sections as fallback

### A3: LLM Extraction Quality
- **Assumption**: granite-13b-chat-v2 can extract ESG metrics with ≥85% accuracy
- **Risk**: Model hallucinations or poor parsing
- **Mitigation**: Structured prompts with JSON schema, validation against Pydantic model

### A4: PyMuPDF Text Extraction
- **Assumption**: PyMuPDF extracts ≥95% of text from born-digital PDFs
- **Risk**: Complex PDF layouts cause text extraction failures
- **Mitigation**: Test on multiple PDFs, validate text length

### A5: Deterministic Testing
- **Assumption**: Cached LLM responses enable deterministic tests without live API calls
- **Risk**: Cache invalidation or response format changes
- **Mitigation**: Version cached responses, include metadata (model_id, timestamp)

---

## Expected Outcomes

### Primary Outcome
✅ **LLMExtractor achieves ≥85% extraction accuracy on REAL ESG PDFs**
- Validated against manually verified ground truth
- Uses IBM watsonx.ai granite-13b-chat-v2
- Full TDD with ≥25 tests

### Secondary Outcomes
✅ **Complete Phase 3 asymmetric extraction design**
- Structured path (SEC EDGAR JSON) ✅ from Phase 3
- Unstructured path (PDF via LLM) ✅ from Phase 3B

✅ **Authentic computation demonstrated**
- Real Apple/Microsoft/Tesla sustainability PDFs
- Real watsonx.ai API integration
- Zero mocks, zero fabricated metrics

✅ **Foundation for Phase 4 (Data Lake)**
- Both extraction paths validated
- Ready to write metrics to Parquet

---

## Validation Plan

### Differential Testing
- Compare LLM extraction vs. manual ground truth
- Assert metric values within ±10% tolerance

### Sensitivity Testing
- Test with different PDF formats (Apple vs. Microsoft vs. Tesla)
- Test with different prompt variations (if accuracy <85%)

### Failure Mode Testing
- Malformed PDF (corrupted file)
- Empty PDF (no text)
- API failure (network error, rate limit)
- Invalid LLM response (non-JSON, missing fields)

---

**Prepared By**: Scientific Coding Agent v13.8-MEA
**Status**: Ready for Implementation
**Next**: Create design.md and evidence.json
