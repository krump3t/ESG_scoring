# Task 026: Docling PDF Structure Extraction

**Status**: 🟡 Context Gate (Awaiting Validation)
**Priority**: High
**Dependencies**: Phase E→F (Page-Aware Extraction) ✅ COMPLETE
**Estimated Effort**: 12-16 hours (2-3 days, single developer)
**SCA Compliance**: v13.8-MEA

---

## Quick Links

- **Hypothesis**: [context/hypothesis.md](context/hypothesis.md) — Success criteria, metrics, CP modules
- **Design**: [context/design.md](context/design.md) — Architecture, data strategy, verification plan
- **Evidence**: [context/evidence.json](context/evidence.json) — Primary sources (Docling, PyMuPDF, SCA protocol)
- **ADR**: [context/adr.md](context/adr.md) — Decision rationale, alternatives considered
- **Assumptions**: [context/assumptions.md](context/assumptions.md) — Risk mitigations

---

## Objective

Integrate **Docling 0.12.0** for advanced PDF structure extraction (tables, layout, OCR), improving ESG evidence quality by **15-20%** while maintaining **100% determinism** and **full backward compatibility**.

---

## Success Criteria

| SC | Criterion | Target | Status |
|----|-----------|--------|--------|
| SC26.1 | **Determinism** | 3 runs → identical SHA256 | ⏳ Pending |
| SC26.2 | **Table extraction** | 100% preservation as markdown | ⏳ Pending |
| SC26.3 | **Evidence quality** | +15-20% richness improvement | ⏳ Pending |
| SC26.4 | **Backward compatibility** | Default backend unchanged | ⏳ Pending |
| SC26.5 | **CP test coverage** | ≥95% line & branch | ⏳ Pending |
| SC26.6 | **Alignment audit** | All quotes validated | ⏳ Pending |
| SC26.7 | **Docker build** | Image builds & runs CP tests | ⏳ Pending |
| SC26.8 | **CI/CD integration** | GitHub Actions passes | ⏳ Pending |

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│              Parallel Backend Selection                  │
│  ┌────────────────────────────────────────────────┐    │
│  │ PARSER_BACKEND environment variable            │    │
│  └───────┬──────────────────────────┬─────────────┘    │
│          │                          │                   │
│  ┌───────▼───────┐          ┌──────▼────────┐         │
│  │    default    │          │    docling    │         │
│  │   PyMuPDF     │          │ Vision Models │         │
│  │  (Fast, Text) │          │(Slow, Tables) │         │
│  └───────┬───────┘          └──────┬────────┘         │
│          │                          │                   │
│          └──────────┬───────────────┘                   │
│                     │                                    │
│            ┌────────▼─────────┐                         │
│            │ Silver Locator   │                         │
│            │ (Dynamic Paths)  │                         │
│            └──────────────────┘                         │
└─────────────────────────────────────────────────────────┘
```

**Key Design**:
- **Parallel directories**: `data/silver/` (default) vs `data/silver_docling/` (Docling)
- **Protocol-based**: `PDFParserBackend` interface for type safety
- **Feature-flag**: `PARSER_BACKEND=docling` or `default`
- **Instant rollback**: Set env var to `default` → reverts immediately

---

## Critical Path (CP) Modules

1. **`libs/extraction/parser_backend.py`** — Protocol interface (~80 LOC)
2. **`libs/extraction/backend_default.py`** — PyMuPDF wrapper (~120 LOC)
3. **`libs/extraction/backend_docling.py`** — Docling wrapper (~180 LOC)
4. **`libs/retrieval/silver_locator.py`** — Path resolver (~60 LOC)
5. **`libs/extraction/text_clean.py`** — Quality assessment (~100 LOC)
6. **`scripts/pdf_to_silver.py`** — CLI converter (~220 LOC)
7. **`scripts/alignment_audit.py`** — Quote validator (~180 LOC)

**Total**: 940 LOC across 7 CP files

---

## Quick Start

### Prerequisites

```powershell
# Navigate to project root
cd "C:\projects\Work Projects\ibm-projects\ESG Evaluation\prospecting-engine"

# Activate virtual environment
.\.venv\Scripts\Activate.ps1

# Install dependencies
pip install docling==0.12.0 pymupdf==1.24.10 pillow>=10.0.0
```

### Environment Configuration

```powershell
# Set backend (default or docling)
$env:PARSER_BACKEND="docling"

# Set deterministic seeds
$env:SEED="42"
$env:PYTHONHASHSEED="0"

# Configure Docling for determinism
$env:DOCLING_THREADS="1"
$env:DOCLING_DISABLE_GPU="1"
$env:DOCLING_CACHE_DIR="./artifacts/cache/docling"

# Enable offline mode (no model downloads)
$env:HF_HUB_OFFLINE="1"
$env:TRANSFORMERS_OFFLINE="1"
```

### Extract PDF

```powershell
# Extract with Docling backend
python scripts/pdf_to_silver.py \
    --org_id LSE_HEAD \
    --year 2025 \
    --doc_id LSE_HEAD_2025 \
    --backend docling

# Output: data/silver_docling/org_id=LSE_HEAD/year=2025/LSE_HEAD_2025_chunks.parquet
```

### Validate Extraction

```powershell
# Run CP tests
pytest -v tests/cp/test_docling_determinism.py

# Run alignment audit
python scripts/alignment_audit.py

# Check determinism (3 runs)
for ($i=1; $i -le 3; $i++) {
    python scripts/pdf_to_silver.py --backend docling --doc_id LSE_HEAD_2025
    $hash = (Get-FileHash data/silver_docling/org_id=LSE_HEAD/year=2025/LSE_HEAD_2025_chunks.parquet).Hash
    Write-Output "Run $i: $hash"
}
```

---

## Rollback Procedure

If issues arise, instantly revert to default backend:

```powershell
# Step 1: Set backend to default
$env:PARSER_BACKEND="default"

# Step 2: Verify default backend works
python scripts/pdf_to_silver.py --backend default --doc_id LSE_HEAD_2025
pytest tests/cp/test_cp_gates.py

# Step 3: Clean Docling artifacts (optional)
Remove-Item -Recurse -Force data/silver_docling
```

**Recovery Time**: <20 minutes

---

## Implementation Phases

| Phase | Focus | Effort | Deliverables |
|-------|-------|--------|--------------|
| **Context Gate** | Validate all context/ files | 1h | Context approved by validator |
| **Phase 1** | Protocol + Default Backend | 3h | `parser_backend.py`, `backend_default.py` + tests |
| **Phase 2** | Docling Backend | 4h | `backend_docling.py` + determinism tests |
| **Phase 3** | Locator + Utilities | 2h | `silver_locator.py`, `text_clean.py` + tests |
| **Phase 4** | Scripts + Audit | 3h | `pdf_to_silver.py`, `alignment_audit.py` |
| **Phase 5** | Testing + CI | 2h | CP tests, Docker, GitHub Actions |
| **Phase 6** | Validation | 2h | Triple determinism, alignment, coverage |

---

## Key Metrics

### Performance

- **Default backend**: ~1-2s per document (baseline)
- **Docling backend**: ~3-6s per document (2-3x slower, acceptable)
- **Target**: <30s per document

### Quality

- **Extraction parity**: ≥85% (Jaccard similarity of text content)
- **Table capture**: 100% (all tables preserved as markdown)
- **Evidence richness**: +15-20% (measured via token count + structure metadata)

### Reliability

- **Determinism**: 100% (3 runs → identical SHA256)
- **Alignment**: 100% (all quotes found on claimed pages)
- **Coverage**: ≥95% (line & branch on CP modules)

---

## Testing Strategy

### Unit Tests

- **Protocol compliance**: Verify backends implement `PDFParserBackend`
- **Schema validation**: Check output matches expected schema
- **Failure paths**: Non-existent PDF, empty PDF, malformed PDF

### Property Tests (Hypothesis)

- **Seed determinism**: Same seed → same output
- **Text quality**: Binary detection, cleaning correctness

### Integration Tests

- **Determinism**: 3 runs → identical hashes
- **Alignment**: Evidence quotes found on claimed pages
- **Parity**: Default vs Docling content overlap ≥85%

### System Tests

- **Docker build**: Image builds successfully
- **CI/CD**: GitHub Actions passes all CP gates
- **Rollback**: Switch to default backend, verify functionality

---

## Dependencies

### Upstream (Complete)

- ✅ **Phase E→F** — Page-aware extraction with provenance tracking
- ✅ **Authenticity infrastructure** — Determinism, traceability, alignment

### Downstream (Blocked)

- **Enhanced scoring** — Table-based metric extraction
- **Advanced retrieval** — Structure-aware search
- **Report generation** — Richer evidence quotes with tables

---

## Risk Matrix

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| **Non-determinism** | Medium | High | CPU-only, single-threaded, torch config |
| **Model download failures** | Low | High | Pre-cache models, offline mode |
| **Performance unacceptable** | Low | Medium | Rollback to default, optimize later |
| **Breaking changes** | Very Low | Critical | Protocol interface + parallel directories |

---

## References

- **Docling GitHub**: https://github.com/DS4SD/docling
- **PyMuPDF Docs**: https://pymupdf.readthedocs.io/
- **SCA Protocol**: `C:\projects\Work Projects\.claude\full_protocol.md`
- **Phase E→F Report**: `artifacts/determinism_proof/phase_e_to_f_closeout.md`

---

## Status Legend

- 🟢 **Complete** — All success criteria met
- 🟡 **In Progress** — Active development
- 🔴 **Blocked** — Dependency or issue blocking progress
- ⏳ **Pending** — Not yet started

---

**Last Updated**: 2025-10-30
**Task Owner**: ESG Evaluation Project Team
**SCA Compliance**: v13.8-MEA

---

## Next Steps

1. ✅ **Context Gate Validation** — Validate all context/ files with SCA validator
2. 🟡 **Begin Phase 1** — Implement `parser_backend.py` with TDD
3. ⏳ **Triple Determinism** — Validate Docling reproducibility
4. ⏳ **Alignment Audit** — Verify evidence quote accuracy
5. ⏳ **CI/CD Integration** — Deploy to GitHub Actions

---

**For questions or issues, consult `context/` directory or contact project team.**
