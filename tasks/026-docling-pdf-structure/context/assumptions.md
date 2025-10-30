# Assumptions - Task 026: Docling PDF Structure Extraction

**Task ID**: 026-docling-pdf-structure
**Date**: 2025-10-30
**Status**: Context Gate (Awaiting Validation)

---

## Technical Assumptions

### Assumption 1: Docling Determinism Achievable

**Statement**: Docling's vision models can be made fully deterministic (byte-for-byte reproducibility) via:
- CPU-only mode (`DOCLING_DISABLE_GPU=1`)
- Single-threaded execution (`DOCLING_THREADS=1`)
- PyTorch deterministic algorithms (`torch.use_deterministic_algorithms(True)`)
- Fixed seeds (`SEED=42`, `PYTHONHASHSEED=0`)

**Confidence**: High (80%)

**Evidence**:
- PyTorch documentation confirms deterministic algorithms available for CPU
- Docling 0.12.0 release notes mention reproducibility improvements
- Similar patterns used successfully in ML reproducibility research

**Risk if False**:
- **Impact**: CRITICAL (SC26.1 fails, task blocked)
- **Detection**: Triple determinism test (Phase 2)
- **Mitigation**: If non-deterministic, fall back to default backend, investigate GPU/threading config

---

### Assumption 2: Model Availability Offline

**Statement**: Docling's pre-trained models (vision transformers, table detection) can be pre-cached and used offline without runtime downloads.

**Confidence**: High (85%)

**Evidence**:
- Transformers library supports `HF_HUB_OFFLINE=1` for offline operation
- Docling documentation mentions model caching via `DOCLING_CACHE_DIR`
- Standard practice in enterprise ML deployments

**Risk if False**:
- **Impact**: HIGH (Docker builds fail, CI unstable)
- **Detection**: Docker build test with network isolation (Phase 5)
- **Mitigation**: If offline fails, pre-download models during Docker build, bake into image

---

### Assumption 3: Performance Acceptable

**Statement**: 2-3x slower extraction (3-6s per document vs 1-2s) is acceptable for the quality improvement gained from structure preservation.

**Confidence**: Medium (70%)

**Evidence**:
- Batch processing use case (not real-time)
- Quality improvement (+15-20% evidence richness) justifies latency
- Similar trade-offs accepted in industry (Bloomberg ESG uses slower, higher-quality extraction)

**Risk if False**:
- **Impact**: MEDIUM (adoption resistance, rollback pressure)
- **Detection**: User feedback, pipeline latency monitoring (Phase 6)
- **Mitigation**: If unacceptable, optimize (caching, parallelization) or make Docling opt-in per document

---

### Assumption 4: Schema Compatibility

**Statement**: Docling's page-level text output (with markdown tables) is compatible with the existing parquet schema (`doc_id, page, text, chunk_id`).

**Confidence**: Very High (95%)

**Evidence**:
- Docling's `plain_text` attribute returns string (same type as PyMuPDF)
- Markdown tables are valid strings (no special encoding needed)
- Schema guards handle column name variations

**Risk if False**:
- **Impact**: LOW (fixable with schema transformation)
- **Detection**: Unit tests (Phase 1)
- **Mitigation**: Add schema transformation layer in `backend_docling.py`

---

## Operational Assumptions

### Assumption 5: Rollback Safety

**Statement**: Setting `PARSER_BACKEND=default` instantly reverts to the original PyMuPDF extraction with no data loss or pipeline breakage.

**Confidence**: Very High (95%)

**Evidence**:
- Parallel directory design (`silver/` vs `silver_docling/`)
- Default backend implementation wraps existing PyMuPDF logic
- No breaking changes to default path

**Risk if False**:
- **Impact**: CRITICAL (production outage)
- **Detection**: Backward compatibility test (Phase 6)
- **Mitigation**: If rollback fails, emergency fix + hotfix release

---

### Assumption 6: Test Fixture Availability

**Statement**: A suitable test PDF fixture (`tests/fixtures/sample_report.pdf`, 5-10 pages, 2-3 tables) can be created or sourced before Phase 1 implementation.

**Confidence**: Very High (95%)

**Evidence**:
- Team has access to multiple ESG reports
- Can generate synthetic PDF with Python (reportlab library)
- Minimal requirements (basic table, text)

**Risk if False**:
- **Impact**: LOW (delays unit tests, not blocking)
- **Detection**: Test discovery (Phase 1)
- **Mitigation**: Use existing LSE_HEAD_2025.pdf as fixture (larger, but functional)

---

### Assumption 7: CI/CD Capacity

**Statement**: GitHub Actions runners have sufficient:
- Disk space for Docling models (~500MB)
- Memory for vision model inference (~2GB RAM)
- Timeout limits adequate (<10 min for CP tests)

**Confidence**: High (80%)

**Evidence**:
- GitHub Actions standard runner: 7GB RAM, 14GB disk
- Docling models are relatively small (~500MB total)
- CP tests run on single document (LSE_HEAD_2025.pdf), should complete in <5 min

**Risk if False**:
- **Impact**: MEDIUM (CI fails, manual testing required)
- **Detection**: First CI run (Phase 5)
- **Mitigation**: Use self-hosted runner with more resources, or cache models, or reduce test document size

---

## Domain Assumptions

### Assumption 8: ESG Reports Have Meaningful Structure

**Statement**: Target ESG reports (annual reports, 10-K filings, sustainability reports) contain meaningful structure to preserve:
- Tables with metrics (GHG emissions, diversity, financials)
- Section headers (H1/H2/H3) indicating themes
- Multi-column layouts
- At least some text layer (not pure scanned images)

**Confidence**: Very High (95%)

**Evidence**:
- Manual review of LSE_HEAD_2025.pdf: 15+ tables, clear sections
- SEC 10-K filings standardized format with tables
- Modern ESG reports (post-2015) predominantly digital-native PDFs

**Risk if False**:
- **Impact**: HIGH (Docling provides no benefit)
- **Detection**: Manual review + table count (Phase 6)
- **Mitigation**: If no structure, revert to default backend for those documents

---

### Assumption 9: Evidence Improvement Measurable

**Statement**: Evidence quality improvement can be quantified via:
- Token count (Docling extracts more detail from tables)
- Structure metadata (table rows, headers detected)
- Manual review (human assessment of evidence richness)

**Confidence**: High (85%)

**Evidence**:
- Prior evidence audits measured page span, theme coverage
- Can extend to measure table presence, cell count
- Established methodology from Phase E→F

**Risk if False**:
- **Impact**: LOW (harder to justify, but qualitative improvement still visible)
- **Detection**: Evidence quality analysis (Phase 6)
- **Mitigation**: Use qualitative assessment + user feedback if quantitative metrics unclear

---

## Risk Mitigations

### Assumption 10: Non-Determinism Detected Early

**Mitigation Strategy**: Triple determinism test in Phase 2 (before heavy integration work)

**Rationale**: If Docling is non-deterministic, we want to know immediately, not after full implementation.

**Implementation**:
```powershell
# Phase 2: Run determinism test 3 times
for ($i=1; $i -le 3; $i++) {
    python scripts/pdf_to_silver.py --backend docling --doc_id LSE_HEAD_2025
    $hash = (Get-FileHash output.parquet).Hash
    Write-Output "Run $i: $hash"
}
# If hashes differ, STOP and investigate
```

---

### Assumption 11: Performance Regression Monitored

**Mitigation Strategy**: Latency logging + performance profiling (Phase 6)

**Rationale**: If extraction takes >30s per document, this may be unacceptable for batch processing.

**Implementation**:
```python
import time

start = time.time()
result = backend.parse_pdf_to_pages(pdf_path, doc_id)
elapsed = time.time() - start

logger.info(f"Extracted {doc_id} in {elapsed:.2f}s (backend: {backend_name})")
```

**Threshold**: >30s → investigate optimization or make Docling opt-in

---

### Assumption 12: Model Unavailability Handled Gracefully

**Mitigation Strategy**: Graceful degradation (fallback to default backend if Docling unavailable)

**Rationale**: If Docling models fail to load (e.g., disk full, corrupted cache), system should not crash.

**Implementation**:
```python
class DoclingBackend:
    def __init__(self):
        try:
            from docling.document_converter import DocumentConverter
            self.converter = DocumentConverter()
        except ImportError as e:
            raise RuntimeError(f"Docling not available: {e}. Install: pip install docling")
        except Exception as e:
            logger.error(f"Failed to initialize Docling: {e}")
            raise RuntimeError(f"Docling initialization failed: {e}")
```

**Fallback**: If `DoclingBackend()` raises, `pdf_to_silver.py` should suggest installing Docling or using default backend.

---

### Assumption 13: Schema Mismatch Detected by Tests

**Mitigation Strategy**: Schema validation in unit tests (Phase 1)

**Rationale**: If Docling returns unexpected schema, we want test failure, not silent data corruption.

**Implementation**:
```python
@pytest.mark.cp
def test_docling_schema_compliance():
    backend = DoclingBackend()
    result = backend.parse_pdf_to_pages("tests/fixtures/sample_report.pdf", "TEST_DOC")

    assert len(result) > 0, "Empty result"

    for row in result:
        assert "doc_id" in row
        assert "page" in row
        assert "text" in row
        assert "chunk_id" in row
        assert isinstance(row["page"], int)
        assert row["page"] >= 1
```

---

### Assumption 14: Alignment Failures Fail-Closed

**Mitigation Strategy**: Alignment audit exits with code 2 on any quote mismatch (Phase 4)

**Rationale**: If evidence quotes don't appear on claimed pages, this indicates extraction quality regression.

**Implementation**:
```python
if failures:
    with open("artifacts/qa/alignment_failures.json", "w") as f:
        json.dump(failures, f, indent=2)
    print(f"❌ ALIGNMENT FAIL: {len(failures)} mismatches")
    sys.exit(2)  # Non-zero exit blocks CI
```

**CI Integration**: GitHub Actions marks PR as failed if alignment audit fails.

---

## Summary

| Assumption | Confidence | Risk if False | Mitigation Phase |
|-----------|-----------|---------------|------------------|
| 1. Docling determinism achievable | High (80%) | CRITICAL | Phase 2 (triple test) |
| 2. Model availability offline | High (85%) | HIGH | Phase 5 (Docker build) |
| 3. Performance acceptable | Medium (70%) | MEDIUM | Phase 6 (latency monitoring) |
| 4. Schema compatibility | Very High (95%) | LOW | Phase 1 (unit tests) |
| 5. Rollback safety | Very High (95%) | CRITICAL | Phase 6 (backward compat test) |
| 6. Test fixture availability | Very High (95%) | LOW | Phase 1 (fixture creation) |
| 7. CI/CD capacity | High (80%) | MEDIUM | Phase 5 (first CI run) |
| 8. ESG reports have structure | Very High (95%) | HIGH | Phase 6 (table count) |
| 9. Evidence improvement measurable | High (85%) | LOW | Phase 6 (quality analysis) |
| 10. Non-determinism detected early | N/A (mitigation) | N/A | Phase 2 |
| 11. Performance monitored | N/A (mitigation) | N/A | Phase 6 |
| 12. Model unavailability handled | N/A (mitigation) | N/A | Phase 2 |
| 13. Schema mismatch detected | N/A (mitigation) | N/A | Phase 1 |
| 14. Alignment failures fail-closed | N/A (mitigation) | N/A | Phase 4 |

**Overall Risk**: MEDIUM-LOW (most assumptions high confidence, mitigations in place)

---

**End of assumptions.md**
