# Assumptions - Phase 3

## Technical Assumptions

1. **A1**: Phase 2 CompanyReport includes SourceRef.content_type field (verified in Phase 2 tests)
2. **A2**: SEC EDGAR JSON files have consistent schema across companies (observed empirically)
3. **A3**: PyMuPDF extracts readable text from born-digital PDFs (not scanned images)
4. **A4**: IBM watsonx.ai API remains available with granite-13b-chat-v2 or llama-2-70b-chat models
5. **A5**: Parquet supports nullable fields for Optional[float] Pydantic fields
6. **A6**: Pydantic v2 ValidationError provides field-level error details
7. **A7**: Hypothesis can generate valid ESGMetrics instances within Pydantic constraints
8. **A8**: Python datetime.isoformat() round-trips correctly with fromisoformat()

## Business Assumptions

9. **A9**: Structured extraction (JSON) accuracy ≥98% is achievable with Pydantic parsing
10. **A10**: Unstructured extraction (PDF) accuracy ≥85% is achievable with LLM
11. **A11**: Quality metrics (field_completeness, type_correctness) correlate with downstream data quality
12. **A12**: Content-type routing covers 90%+ of real-world report types

## Data Assumptions

13. **A13**: Test corpus of 10 SEC EDGAR files + 5 PDFs is representative of production data
14. **A14**: Ground truth annotations are accurate (manually verified)
15. **A15**: watsonx.ai responses with greedy decoding are deterministic (no variance)
16. **A16**: Cached LLM responses remain valid across test runs

## Integration Assumptions

17. **A17**: Phase 2 multi-source crawler delivers CompanyReport with valid local_path
18. **A18**: Phase 4 data lake accepts Parquet files with ESG_METRICS_SCHEMA
19. **A19**: Future providers (GRI, Company IR) will use same SourceRef.content_type field
20. **A20**: Extraction quality thresholds (≥98% structured, ≥85% unstructured) are acceptable to users

## Testing & Coverage Assumptions

21. **A21**: Branch coverage of 91% with authentic data is acceptable when remaining 4% requires mocking
    - **Rationale**: SCA v13.8 Invariant #1 prioritizes authentic computation over coverage metrics
    - **Evidence**: 42 tests using REAL SEC EDGAR data, 96.7% line coverage achieved
    - **Missing branches**: Defensive exception handlers for catastrophic runtime errors (OOM, system crashes)
    - **Documented in**: PHASE3_COMPLETION_SUMMARY.md section "Missing Coverage Analysis"
