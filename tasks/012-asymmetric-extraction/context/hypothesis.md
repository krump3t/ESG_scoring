# Phase 3 Hypothesis - Asymmetric Extraction Paths (v3 Enhancement #2)

**Task ID**: 012-asymmetric-extraction
**SCA Version**: v13.8-MEA
**Phase**: Context Gate
**Date**: 2025-10-24

---

## Core Hypothesis

**H1**: Content-type-based routing enables asymmetric extraction paths where structured data (JSON/XBRL) achieves ≥98% extraction accuracy via Pydantic parsing, while unstructured data (PDF/HTML) achieves ≥85% extraction accuracy via LLM-based extraction.

**H2**: 1:1 Pydantic-Parquet schema parity ensures type-safe data contracts prevent runtime errors during write operations to data lake, with 100% schema compatibility verified via property-based tests.

**H3**: Extraction quality metrics (field completeness, type correctness, value range validation) enable measurable data quality assessment with ≥95% confidence intervals on accuracy estimates.

---

## Success Criteria (Testable)

### SC-1: Content-Type Router (100% Coverage)
- **Metric**: Router correctly dispatches to StructuredExtractor for `application/json` and `application/vnd.xbrl` content types
- **Threshold**: 100% routing accuracy (all test cases route to correct extractor)
- **Measurement**: Unit tests with mocked extractors verify router.extract() calls correct extractor class

### SC-2: Structured Extraction Accuracy (≥98%)
- **Metric**: Pydantic model parsing of SEC EDGAR JSON/XBRL files extracts all required fields with correct types
- **Threshold**: ≥98% field extraction accuracy on test corpus (10 SEC EDGAR files)
- **Measurement**: Compare extracted Pydantic models against ground truth annotations, calculate precision/recall per field

### SC-3: LLM Extraction Accuracy (≥85%)
- **Metric**: LLM-based extraction of ESG metrics from PDF/HTML reports matches ground truth within tolerance
- **Threshold**: ≥85% field extraction accuracy, ≥80% value accuracy (within 10% of ground truth for numeric fields)
- **Measurement**: Differential tests comparing LLM extraction vs manual annotations on 5 test PDFs

### SC-4: Schema Parity (100%)
- **Metric**: Pydantic ESGMetrics model fields map 1:1 to Parquet schema columns with matching types
- **Threshold**: 100% schema compatibility (no type mismatches, no missing fields)
- **Measurement**: Property-based tests generate random Pydantic instances, serialize to Parquet, deserialize, assert equality

### SC-5: Extraction Quality Metrics (≥95% Completeness)
- **Metric**: ExtractionQuality dataclass tracks field_completeness (% fields populated), type_correctness (% fields with valid types), value_validity (% fields within expected ranges)
- **Threshold**: ≥95% field completeness on structured data, ≥70% on unstructured
- **Measurement**: Aggregate quality metrics across test corpus, calculate mean/std per source type

### SC-6: Error Handling Coverage (100%)
- **Metric**: Extraction handles malformed JSON, invalid Pydantic schemas, LLM API failures, empty PDFs
- **Threshold**: 100% of failure scenarios handled gracefully (no unhandled exceptions)
- **Measurement**: Failure-path tests verify extraction returns ExtractionResult with error metadata instead of raising

### SC-7: TDD Compliance (Tests Before Code)
- **Metric**: Git commit timestamps prove tests committed before implementation
- **Threshold**: All CP file modifications preceded by test commits
- **Measurement**: Git log analysis comparing test file timestamps vs implementation file timestamps

### SC-8: Coverage on CP Files (≥95%)
- **Metric**: Line and branch coverage on extraction_router.py, structured_extractor.py, llm_extractor.py, esg_metrics.py
- **Threshold**: ≥95% line coverage, ≥95% branch coverage on all CP files
- **Measurement**: pytest-cov with .coveragerc filtering to CP files only

### SC-9: Type Safety (0 Mypy Errors)
- **Metric**: Mypy --strict passes with 0 errors on CP files
- **Threshold**: 0 type errors
- **Measurement**: mypy --strict extraction_router.py structured_extractor.py llm_extractor.py esg_metrics.py

### SC-10: Property-Based Schema Tests (≥50 Examples)
- **Metric**: Hypothesis property tests generate ≥50 random ESGMetrics instances, verify Parquet round-trip
- **Threshold**: 100% of generated instances survive round-trip without data loss
- **Measurement**: Hypothesis test with @settings(max_examples=50)

---

## Critical Path (CP) Files

**CP-1**: `agents/extraction/extraction_router.py`
- Content-type-based routing logic (routes to StructuredExtractor vs LLMExtractor)
- **Complexity Target**: CCN ≤5 (simple if/else routing)
- **Coverage Target**: ≥95% line, ≥95% branch

**CP-2**: `agents/extraction/structured_extractor.py`
- Pydantic parsing of JSON/XBRL → ESGMetrics
- **Complexity Target**: CCN ≤8 (error handling adds branches)
- **Coverage Target**: ≥95% line, ≥95% branch

**CP-3**: `agents/extraction/llm_extractor.py`
- LLM-based extraction from PDF/HTML → ESGMetrics
- **Complexity Target**: CCN ≤10 (prompt engineering, retry logic)
- **Coverage Target**: ≥95% line, ≥95% branch

**CP-4**: `libs/models/esg_metrics.py`
- Pydantic model for ESG metrics with Parquet schema compatibility
- **Complexity Target**: CCN ≤5 (declarative model)
- **Coverage Target**: ≥95% line, ≥95% branch

---

## Exclusions (Non-CP)

- **LLM API Integration**: Mock LLM responses in tests (Phase 3 focuses on orchestration, not LLM tuning)
- **Parquet Write Performance**: Not measured in Phase 3 (focus on correctness, not performance)
- **Multi-file Batch Processing**: Phase 3 processes single files; batch processing deferred to Phase 4
- **Real PDF Parsing**: Use PyMuPDF for text extraction, but mock in most tests to avoid file I/O overhead

---

## Statistical Power & Confidence Intervals

### Structured Extraction (Pydantic Parsing)
- **Sample Size**: 10 SEC EDGAR JSON/XBRL files (Apple, Microsoft, Tesla, etc.)
- **Power**: 95% confidence to detect ≥2% accuracy difference from baseline
- **Confidence Interval**: ±3% at 95% CI (e.g., 98% ± 3% → [95%, 100%])

### Unstructured Extraction (LLM-Based)
- **Sample Size**: 5 PDF sustainability reports (manually annotated ground truth)
- **Power**: 90% confidence to detect ≥5% accuracy difference
- **Confidence Interval**: ±5% at 90% CI (e.g., 85% ± 5% → [80%, 90%])

### Schema Parity (Property-Based)
- **Sample Size**: 50 randomly generated ESGMetrics instances (Hypothesis)
- **Power**: 99% confidence to detect schema mismatches (deterministic test)
- **Confidence Interval**: 100% compatibility (no tolerance for schema errors)

---

## Risks & Mitigations

### R1: LLM Extraction Variability (HIGH)
- **Risk**: LLM responses non-deterministic, may fail extraction quality threshold
- **Mitigation**: Use temperature=0 for deterministic outputs, implement retry logic with exponential backoff, cache LLM responses for test reproducibility
- **Contingency**: If LLM accuracy <85%, use hybrid approach (Pydantic + LLM fallback)

### R2: Pydantic-Parquet Type Mismatches (MEDIUM)
- **Risk**: Parquet schema incompatible with Pydantic Optional[float] fields (null handling)
- **Mitigation**: Use pyarrow schemas with nullable=True, property tests verify round-trip integrity
- **Contingency**: Implement custom Parquet serializer if pyarrow auto-conversion fails

### R3: PDF Text Extraction Quality (MEDIUM)
- **Risk**: PyMuPDF may extract garbled text from scanned PDFs (OCR required)
- **Mitigation**: Phase 3 uses born-digital PDFs only (SEC EDGAR), OCR deferred to Phase 3b
- **Contingency**: Fallback to pytesseract OCR if PyMuPDF text quality <80%

### R4: Schema Evolution Brittleness (LOW)
- **Risk**: Adding new ESG metrics breaks existing Parquet files
- **Mitigation**: Schema versioning (ESGMetrics_v1, ESGMetrics_v2), backward compatibility tests
- **Contingency**: Implement schema migration scripts if breaking changes required

---

## Data Sources & Leakage Guards

### Training Data (Ground Truth Annotations)
- **Source**: Manual annotations of 10 SEC EDGAR files + 5 sustainability PDFs
- **PII Flag**: FALSE (public SEC filings)
- **Leakage Guard**: Test set held out from development (no peeking at ground truth during implementation)

### LLM Responses (For Testing)
- **Source**: Cached LLM responses (OpenAI GPT-4) with temperature=0
- **PII Flag**: FALSE (synthetic test data)
- **Leakage Guard**: Use fixed random seed for Hypothesis tests, cache LLM responses to avoid non-deterministic test failures

### Parquet Schema (PyArrow)
- **Source**: pyarrow.parquet API documentation
- **PII Flag**: FALSE (public documentation)
- **Leakage Guard**: N/A (deterministic library behavior)

---

## Phase Dependencies

**Upstream (Phase 2 - Multi-Source Crawler)**:
- SourceRef.content_type field enables routing
- CompanyReport.local_path provides file path for extraction
- Phase 2 integration tests verify Phase 1 SEC EDGAR provider works with Phase 2 crawler

**Downstream (Phase 4 - Data Lake Integration)**:
- Phase 3 ESGMetrics Parquet files feed into Iceberg silver/gold layers
- Phase 3 extraction quality metrics inform data quality dashboards
- Phase 3 schema parity ensures Iceberg table compatibility

---

## Verification Plan

### Differential Tests (Phase 2 vs Phase 3)
- **Test**: Extract same SEC EDGAR file using Phase 1 provider + Phase 3 extractor
- **Assert**: Extracted ESGMetrics matches expected schema
- **Purpose**: Verify Phase 2 CompanyReport integrates with Phase 3 extraction

### Sensitivity Tests (Content-Type Perturbations)
- **Test**: Modify SourceRef.content_type to invalid values, verify router raises clear error
- **Assert**: Router.extract() raises ValueError with descriptive message
- **Purpose**: Test robustness to unexpected content types

### Property Tests (Schema Round-Trip)
- **Test**: Generate random ESGMetrics with Hypothesis, serialize to Parquet, deserialize, assert equality
- **Assert**: 100% of instances survive round-trip
- **Purpose**: Prove schema parity with ≥50 random examples

---

**Document Prepared By**: Scientific Coding Agent v13.8-MEA
**Review Status**: Draft (Context Gate)
**Next Action**: Create design.md with detailed architecture
