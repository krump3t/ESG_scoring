# Task 026: Docling PDF Structure Extraction — Hypothesis & Metrics

**Task ID**: 026-docling-pdf-structure
**Phase**: Enhancement (PDF Processing Layer)
**Status**: Context Gate (awaiting validation)
**Dependencies**: Phase E→F (Page-Aware Extraction) ✓ COMPLETE

---

## Primary Claim

**Task 026 will integrate Docling 0.12.0 for advanced PDF structure extraction (tables, layout, OCR), improving ESG evidence quality by 15-20% while maintaining 100% determinism (3-run hash identity) and full backward compatibility with the existing PyMuPDF extraction pipeline.**

---

## Success Criteria (SC26.1-SC26.8)

| SC | Criterion | Target | Validation Method |
|----|-----------|--------|-------------------|
| SC26.1 | Determinism | 3 runs with SEED=42 produce identical SHA256 hashes | Triple validation: compare parquet file hashes |
| SC26.2 | Table extraction | 100% of PDF tables preserved as markdown | Manual review + table count comparison |
| SC26.3 | Evidence quality | ≥15% increase in evidence richness score | Comparison: default vs Docling evidence metrics |
| SC26.4 | Backward compatibility | `PARSER_BACKEND=default` produces identical output to pre-Docling | Differential test: compare silver/ artifacts |
| SC26.5 | CP test coverage | ≥95% line & branch coverage on new CP modules | pytest-cov report |
| SC26.6 | Alignment audit | 100% of evidence quotes found on claimed pages | Run alignment_audit.py (fail-closed) |
| SC26.7 | Docker build | Image builds successfully and runs CP tests | `docker build && docker run` |
| SC26.8 | CI/CD integration | GitHub Actions workflow passes CP gates | .github/workflows/ci-cp-gates.yml |

---

## Key Metrics

### Functional Metrics (PDF Extraction Quality)

- **Extraction parity**: ≥85% overlap between default and Docling page content
  - Measured via Jaccard similarity of text chunks
  - Threshold ensures Docling extracts same source content

- **Table capture rate**: 100% of tables in test PDFs preserved
  - Baseline (PyMuPDF): 0% (tables → narrative text)
  - Target (Docling): 100% (tables → markdown with structure)
  - Test corpus: 5 ESG reports with ≥3 tables each

- **Determinism validation**: 3 consecutive runs → identical output
  - Method: SHA256 hash comparison of parquet files
  - Environment: SEED=42, PYTHONHASHSEED=0, DOCLING_THREADS=1, DOCLING_DISABLE_GPU=1
  - Success: All 3 hashes match byte-for-byte

- **Evidence richness improvement**: 15-20% increase
  - Metric: (Docling evidence tokens + structure metadata) / (Default evidence tokens)
  - Structure metadata: table rows, headers, cell formatting
  - Measured across 5-company test set

### Quality Metrics (Infrastructure Modules)

- **Type hints coverage**: 100% on CP files
  - All 7 CP modules fully type-hinted with `mypy --strict` compliance

- **Docstring coverage**: 100% (interrogate ≥95%)
  - Module-level, class-level, and function-level docstrings
  - Google-style format with Args/Returns/Raises sections

- **Test coverage**: ≥95% line & branch on CP files
  - Includes: protocol compliance, determinism, failure paths, property tests
  - pytest-cov with branch coverage enabled

- **Cyclomatic complexity**: ≤10 per function (lizard)
  - Single-responsibility principle enforced
  - Complex logic decomposed into helper functions

- **Cognitive complexity**: ≤15 per function
  - Minimal nesting, early returns, clear control flow

### Authenticity Metrics

- **Real extraction**: Actual Docling library calls (no mocks in production)
  - Vision models loaded and executed
  - Document structure analysis performed

- **Real differential testing**: Side-by-side comparison of backends
  - Default vs Docling outputs compared
  - Parity score computed from actual extractions

- **Real alignment validation**: Quotes verified against source PDFs
  - PyMuPDF used to extract ground-truth page text
  - String containment check (quote ∈ page_text)
  - Per-page SHA256 hashes for provenance

- **Real determinism validation**: Execute full pipeline 3 times
  - Same PDF → same parquet → same hash
  - No fabricated hashes or hardcoded values

---

## Critical Path (CP) Modules

**Extraction Layer** (parallel backend architecture):

### 1. **libs/extraction/parser_backend.py** — PDF Parser Protocol
   - `PDFParserBackend` Protocol class defining extraction interface
   - `parse_pdf_to_pages(pdf_path: str, doc_id: str) -> List[Dict]` signature
   - `_mk_chunk_id(doc_id, page, idx)` helper for deterministic IDs
   - Type hints: 100% | Docstrings: complete
   - **LOC estimate**: ~80

### 2. **libs/extraction/backend_default.py** — Default Backend (PyMuPDF)
   - `DefaultBackend` class implementing `PDFParserBackend`
   - Maintains existing PyMuPDF extraction behavior
   - Returns standardized schema: `{doc_id, page, text, chunk_id, source: "default"}`
   - Error handling: non-existent PDF → empty list (logged)
   - Type hints: 100% | Docstrings: complete
   - **LOC estimate**: ~120

### 3. **libs/extraction/backend_docling.py** — Docling Backend
   - `DoclingBackend` class implementing `PDFParserBackend`
   - Uses `DocumentConverter` from Docling library
   - Determinism configuration: torch seeds, CPU-only, single-threaded
   - Returns standardized schema with `source: "docling"`
   - Table extraction: preserves as markdown in text field
   - Type hints: 100% | Docstrings: complete
   - **LOC estimate**: ~180

### 4. **libs/retrieval/silver_locator.py** — Dynamic Path Resolution
   - `locate_chunks_parquet(doc_id, org_id, year)` function
   - Strategy: prefer `silver_docling/` if `PARSER_BACKEND=docling`, else `silver/`
   - Thread-safe: read-only environment variable access
   - Fallback logic: try preferred directory, then default
   - Type hints: 100% | Docstrings: complete
   - **LOC estimate**: ~60

### 5. **libs/extraction/text_clean.py** — Text Quality Module
   - `is_binary_like(text: str) -> bool` — detect non-text content
   - `clean_text(text: str) -> str` — remove control chars, normalize whitespace
   - `quality_score(text: str) -> float` — compute 0.0-1.0 quality metric
   - `extract_clean_quote(text, max_length)` — cleaned + scored quotes
   - Type hints: 100% | Docstrings: complete
   - **LOC estimate**: ~100

### 6. **scripts/pdf_to_silver.py** — PDF to Parquet Converter (CP)
   - `pick_backend(name: str) -> PDFParserBackend` — backend factory
   - `write_parquet(rows, out_path)` — standardized Parquet writer
   - `sha256_file(path)` — provenance hash computation
   - `main()` — CLI entry point with argparse
   - Provenance sidecar generation: `*.parquet.prov.json` with SHA256, backend, metadata
   - Type hints: 100% | Docstrings: complete
   - **LOC estimate**: ~220

### 7. **scripts/alignment_audit.py** — Evidence Alignment Validator (CP)
   - `page_text(pdf_path, page_num)` — extract ground-truth page text
   - `sha256_text(text)` — compute page content hash
   - `main()` — iterate all evidence_audit.json files, validate quotes
   - Fail-closed: mismatched quotes → exit code 2, write failures to JSON
   - Page hash manifest: all pages hashed for provenance
   - Type hints: 100% | Docstrings: complete
   - **LOC estimate**: ~180

---

## Exclusions & Exemptions

### Out of Scope

1. **Vision model training/fine-tuning**: Use Docling pre-trained models only
2. **GPU acceleration**: Disabled for determinism (CPU-only mode)
3. **Real-time processing**: Batch extraction acceptable (2-3x slower than PyMuPDF)
4. **Custom table parsing**: Rely on Docling's built-in table extraction
5. **OCR optimization**: Use Docling defaults for scanned PDFs

### Approved Exclusions

- **Performance optimization**: No caching layer in initial implementation
- **Parallel processing**: Single-threaded for determinism (can parallelize later)
- **Model selection**: No model comparison (use Docling default vision model)

---

## Power Analysis & Confidence Intervals

### Sample Size
- **Test corpus**: 5 ESG reports (LSE_HEAD_2025, AAPL_2023, JPM_2023, XOM_2023, MSFT_2023)
- **Determinism runs**: 3 runs per document = 15 total samples
- **Table validation**: ≥15 tables across 5 documents (3 per document minimum)

### Expected Outcomes
- **Extraction parity**: 85-95% (some formatting differences acceptable)
- **Table capture**: 100% (all tables detected and preserved)
- **Determinism**: 100% (all 15 samples produce identical hashes)
- **Evidence quality**: 15-20% improvement (measured via token count + structure metadata)

### Confidence Level
- **Determinism**: 100% confidence (deterministic process, not statistical)
- **Parity**: 95% confidence (measured via Jaccard similarity)
- **Quality improvement**: 90% confidence (measured on 5-doc sample, generalizable to ESG report domain)

### Risk Mitigation
- **Non-determinism detected**: Fail CI/CD, investigate torch/GPU configuration
- **Parity below threshold**: Review Docling extraction logic, adjust cleaning
- **Quality no improvement**: Validate table detection, check evidence selection

---

## Inputs & Outputs

### Inputs

1. **Test PDFs**: 5 ESG annual reports
   - `data/raw/LSE_HEAD_2025.pdf` — Primary test document (Headlam Group)
   - `data/raw/AAPL_2023.pdf` — Apple 10-K (financial tables)
   - `data/raw/JPM_2023.pdf` — JPMorgan 10-K (risk tables)
   - `data/raw/XOM_2023.pdf` — ExxonMobil 10-K (GHG tables)
   - `tests/fixtures/sample_report.pdf` — Synthetic test fixture (5-10 pages)

2. **Existing Silver Data**: Baseline for comparison
   - `data/silver/org_id=*/year=*/*_chunks.parquet` — Default backend outputs

3. **Evidence Audit Data**: For alignment validation
   - `artifacts/matrix/*/pipeline_validation/evidence_audit.json` — Evidence with quotes + pages

### Outputs

1. **Infrastructure Modules**: 7 CP files
   - `libs/extraction/{parser_backend, backend_default, backend_docling}.py`
   - `libs/retrieval/silver_locator.py`
   - `libs/extraction/text_clean.py`
   - `scripts/{pdf_to_silver, alignment_audit}.py`

2. **Docling Silver Data**: Parallel extraction outputs
   - `data/silver_docling/org_id=*/year=*/*_chunks.parquet` — Docling extractions
   - `data/silver_docling/org_id=*/year=*/*_chunks.parquet.prov.json` — Provenance sidecars

3. **Validation Artifacts**:
   - `artifacts/qa/page_text_hashes.json` — Per-page SHA256 manifest
   - `artifacts/qa/alignment_failures.json` — Quote mismatches (if any)
   - `artifacts/qa/tooling_provenance.json` — Docling version, env vars
   - `artifacts/determinism/docling_triple_validation.json` — 3-run hash comparison

4. **Test Suite**:
   - `tests/cp/test_docling_determinism.py` — Determinism, protocol, failure tests
   - Updated `tests/cp/test_cp_gates.py` — Evidence, parity, provenance gates

5. **CI/CD Integration**:
   - `.github/workflows/ci-cp-gates.yml` — CP test workflow
   - `Dockerfile` — Updated with Docling dependencies

---

## Verification Strategy

### 1. Determinism Test (SC26.1)

**Procedure**:
```powershell
$env:SEED=42
$env:PYTHONHASHSEED=0
$env:PARSER_BACKEND="docling"

# Run 1
python scripts/pdf_to_silver.py --org_id LSE_HEAD --year 2025 --doc_id LSE_HEAD_2025 --backend docling
$hash1 = (Get-FileHash data/silver_docling/org_id=LSE_HEAD/year=2025/LSE_HEAD_2025_chunks.parquet).Hash

# Run 2
Remove-Item data/silver_docling/org_id=LSE_HEAD/year=2025/LSE_HEAD_2025_chunks.parquet
python scripts/pdf_to_silver.py --org_id LSE_HEAD --year 2025 --doc_id LSE_HEAD_2025 --backend docling
$hash2 = (Get-FileHash data/silver_docling/org_id=LSE_HEAD/year=2025/LSE_HEAD_2025_chunks.parquet).Hash

# Run 3
Remove-Item data/silver_docling/org_id=LSE_HEAD/year=2025/LSE_HEAD_2025_chunks.parquet
python scripts/pdf_to_silver.py --org_id LSE_HEAD --year 2025 --doc_id LSE_HEAD_2025 --backend docling
$hash3 = (Get-FileHash data/silver_docling/org_id=LSE_HEAD/year=2025/LSE_HEAD_2025_chunks.parquet).Hash

# Validate
if ($hash1 -eq $hash2 -and $hash2 -eq $hash3) {
    Write-Host "✅ Determinism PASS"
} else {
    Write-Host "❌ Determinism FAIL"
}
```

**Acceptance**: All 3 hashes identical

---

### 2. Table Extraction Test (SC26.2)

**Procedure**:
```powershell
# Extract with default backend
python scripts/pdf_to_silver.py --org_id LSE_HEAD --year 2025 --doc_id LSE_HEAD_2025 --backend default
$default_df = Import-Csv (python -c "import pandas as pd; df=pd.read_parquet('data/silver/org_id=LSE_HEAD/year=2025/LSE_HEAD_2025_chunks.parquet'); print(df.to_csv())")

# Extract with Docling backend
python scripts/pdf_to_silver.py --org_id LSE_HEAD --year 2025 --doc_id LSE_HEAD_2025 --backend docling
$docling_df = Import-Csv (python -c "import pandas as pd; df=pd.read_parquet('data/silver_docling/org_id=LSE_HEAD/year=2025/LSE_HEAD_2025_chunks.parquet'); print(df.to_csv())")

# Count markdown tables in Docling output
$table_count = ($docling_df.text | Select-String "\|.*\|" | Measure-Object).Count

Write-Host "Tables found: $table_count"
```

**Acceptance**: ≥3 markdown tables found in Docling output (manual verification: all tables preserved)

---

### 3. Alignment Audit Test (SC26.6)

**Procedure**:
```powershell
# Run alignment audit
python scripts/alignment_audit.py

# Check exit code
if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Alignment audit PASS"
} else {
    Write-Host "❌ Alignment audit FAIL"
    Get-Content artifacts/qa/alignment_failures.json
}
```

**Acceptance**: Exit code 0, no failures in `alignment_failures.json`

---

### 4. Backward Compatibility Test (SC26.4)

**Procedure**:
```powershell
# Extract with default backend (before Docling integration)
git checkout HEAD~1  # Previous commit (pre-Docling)
python scripts/pdf_to_silver.py --org_id LSE_HEAD --year 2025 --doc_id LSE_HEAD_2025 --backend default
$baseline_hash = (Get-FileHash data/silver/org_id=LSE_HEAD/year=2025/LSE_HEAD_2025_chunks.parquet).Hash

# Extract with default backend (after Docling integration)
git checkout HEAD
$env:PARSER_BACKEND="default"
python scripts/pdf_to_silver.py --org_id LSE_HEAD --year 2025 --doc_id LSE_HEAD_2025 --backend default
$current_hash = (Get-FileHash data/silver/org_id=LSE_HEAD/year=2025/LSE_HEAD_2025_chunks.parquet).Hash

# Compare
if ($baseline_hash -eq $current_hash) {
    Write-Host "✅ Backward compatibility PASS"
} else {
    Write-Host "❌ Backward compatibility FAIL"
}
```

**Acceptance**: Hashes identical (default backend unchanged)

---

### 5. CP Test Coverage (SC26.5)

**Procedure**:
```powershell
pytest tests/cp/test_docling_determinism.py --cov=libs/extraction --cov=libs/retrieval --cov=scripts --cov-branch --cov-report=term-missing
```

**Acceptance**: ≥95% line & branch coverage on all CP modules

---

### 6. Docker Build Test (SC26.7)

**Procedure**:
```powershell
docker build -t esg-scoring:docling-test .
docker run --rm esg-scoring:docling-test pytest -q tests/cp/test_docling_determinism.py
```

**Acceptance**: Build succeeds, CP tests pass in container

---

### 7. CI/CD Integration Test (SC26.8)

**Procedure**:
```bash
# Push to feature branch
git checkout -b feature/docling-integration
git add .
git commit -m "feat: Docling PDF structure extraction (Task 026)"
git push origin feature/docling-integration

# Create PR and wait for CI
gh pr create --title "Docling PDF Structure Extraction" --body "Task 026"
```

**Acceptance**: GitHub Actions workflow passes all CP gates

---

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| **Docling non-determinism** | Medium | High | CPU-only, single-threaded, torch deterministic mode |
| **Vision model download at runtime** | Low | High | Pre-cache models in Docker, enforce offline mode |
| **Schema mismatch** | Low | Medium | Schema guards in silver_locator, column normalization |
| **Table extraction fails** | Low | High | Docling extensively tested on ESG reports; manual verification |
| **Performance degradation** | High | Low | Acceptable trade-off; can rollback to default |
| **Docker image size bloat** | Medium | Low | Use slim base image, multi-stage build |
| **CI timeout** | Low | Medium | Cache Docker layers, optimize model loading |
| **Evidence quality regression** | Low | High | Alignment audit fails-closed; manual review if needed |

---

## Timeline & Phases

**Total Effort**: 12-16 hours (2-3 days, single developer)

| Phase | Focus | Effort | Deliverables |
|-------|-------|--------|--------------|
| **Context Gate** | Validate hypothesis, design, evidence | 1h | All context/ files approved |
| **Phase 1: Protocol & Default Backend** | parser_backend.py, backend_default.py | 3h | Protocol + tests, default backend + tests |
| **Phase 2: Docling Backend** | backend_docling.py | 4h | Docling integration + determinism tests |
| **Phase 3: Locator & Utilities** | silver_locator.py, text_clean.py | 2h | Path resolution + text quality |
| **Phase 4: Scripts & Audit** | pdf_to_silver.py, alignment_audit.py | 3h | Conversion script + validation |
| **Phase 5: Testing & CI** | CP tests, Docker, GitHub Actions | 2h | Full test suite + CI workflow |
| **Phase 6: Validation** | Triple determinism, alignment, coverage | 2h | All SC criteria met |

---

## Dependencies

### Upstream (must be complete before Task 026)

- ✅ **Phase E→F (Page-Aware Extraction)** — COMPLETE (2025-10-29)
  - Established page-level tracking
  - Provenance infrastructure
  - Evidence audit with page numbers

### Downstream (blocked until Task 026 complete)

- **Enhanced ESG Scoring**: Can leverage tabular data for metric extraction
- **Advanced Retrieval**: Structure-aware search (table cells, sections)
- **Report Generation**: Richer evidence quotes with table formatting

---

**End of hypothesis.md**
