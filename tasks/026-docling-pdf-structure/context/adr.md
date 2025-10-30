# Architecture Decision Record: Docling Integration for PDF Structure Extraction

## Metadata

- **Status**: Proposed
- **Date**: 2025-10-30
- **Deciders**: ESG Evaluation Project Team, SCA Protocol Authority
- **Technical Story**: Task 026 - Docling PDF Structure Extraction

---

## Context

### Current State (As of Phase E→F Completion)

The prospecting-engine currently uses **PyMuPDF (fitz)** + **pdfplumber** for PDF text extraction:

**Strengths**:
- Fast extraction (~1-2 seconds per document)
- Deterministic (proven via triple validation: 3/3 runs identical)
- Page-aware with provenance tracking
- Mature, stable libraries

**Limitations**:
- **No table structure preservation**: Tables converted to narrative text, losing metrics data
  - Example: GHG emissions table becomes "Scope 1 2023 1234 Scope 2 2023 5678" instead of structured rows/columns
- **No layout analysis**: Multi-column layouts, headers, sections not detected
- **No OCR**: Cannot process scanned PDFs or image-embedded tables
- **No multi-modal linking**: Images and text treated independently

### Business Impact

**ESG Scoring Quality**: Evidence quotes lack richness
- Current: "The company reported emissions data." (vague reference)
- Desired: "| Scope | 2023 | 2022 | Change |\n|-------|------|------|--------|\n| Scope 1 | 1,234 | 1,567 | -21% |" (structured metric)

**Evidence Validation**: Hard to verify numeric claims
- Reviewers must manually cross-reference PDFs to validate metrics
- No automated table-based evidence extraction

**Competitive Disadvantage**: Industry tools (Bloomberg ESG, MSCI) use structured extraction
- Our text-only approach limits scoring accuracy
- Cannot compete on data richness

---

## Decision

**We will integrate Docling 0.12.0 as a parallel extraction backend** using a feature-flag architecture.

### Core Design

1. **Parallel Backend Pattern**
   - Two independent extraction backends: `default` (PyMuPDF) and `docling` (Docling)
   - Selection via `PARSER_BACKEND` environment variable
   - Separate output directories: `data/silver/` (default) vs `data/silver_docling/` (Docling)

2. **Protocol-Based Interface**
   - Define `PDFParserBackend` Protocol (PEP 544) with single method: `parse_pdf_to_pages()`
   - Both backends implement same interface, return standardized schema
   - Dynamic path resolution via `silver_locator.py`

3. **Determinism-First Configuration**
   - CPU-only mode (`DOCLING_DISABLE_GPU=1`)
   - Single-threaded execution (`DOCLING_THREADS=1`)
   - PyTorch deterministic algorithms (`torch.use_deterministic_algorithms(True)`)
   - Fixed seeds (`SEED=42`, `PYTHONHASHSEED=0`)

4. **Fail-Closed Validation**
   - Alignment audit: Verify evidence quotes found on claimed pages
   - Triple determinism: 3 runs → identical SHA256 hashes
   - CP tests: Protocol compliance, failure paths, property tests

5. **Instant Rollback**
   - Set `PARSER_BACKEND=default` to revert
   - Default backend unchanged and fully functional
   - No breaking changes to downstream consumers

---

## Alternatives Considered

### Alternative 1: Replace PyMuPDF Entirely

**Approach**: Remove PyMuPDF, use only Docling

**Pros**:
- Simpler architecture (single extraction path)
- No dual maintenance

**Cons**:
- **HIGH RISK**: No rollback if Docling issues discovered
- Breaking change to existing pipeline
- All downstream code must be updated simultaneously
- Determinism regression risk

**Verdict**: **REJECTED** (too risky, violates SCA fail-safe principles)

---

### Alternative 2: Apache Tika

**Approach**: Use Apache Tika for structure extraction

**Pros**:
- Mature, widely used (Elasticsearch, Solr)
- Supports 1000+ file formats
- Active community

**Cons**:
- **Java dependency**: Requires JVM, increases Docker image size
- **No vision models**: Limited table extraction, no OCR for scanned PDFs
- **Configuration complexity**: XML-based config, less Python-native
- **Slower**: HTTP server overhead (py4j bridge)

**Verdict**: **REJECTED** (Java dependency, inferior table extraction vs Docling)

---

### Alternative 3: Unstructured.io

**Approach**: Use Unstructured library for document parsing

**Pros**:
- Python-native
- Supports multiple formats (PDF, Word, HTML)
- Active development

**Cons**:
- **Commercial license**: Requires paid API key for advanced features (table extraction)
- **Less deterministic**: API-based extraction, network dependency
- **No offline mode**: Cannot guarantee reproducibility
- **Cost**: Per-page pricing model

**Verdict**: **REJECTED** (commercial license incompatible with SCA authenticity requirements)

---

### Alternative 4: Custom Table Extraction (OpenCV + Tesseract)

**Approach**: Build custom table extraction using:
- OpenCV for line detection
- Tesseract for OCR
- Custom logic for cell boundary detection

**Pros**:
- Full control over logic
- No external dependencies (beyond OpenCV/Tesseract)
- Lightweight

**Cons**:
- **Reinventing the wheel**: Docling already solves this problem
- **High maintenance burden**: Complex logic, edge cases
- **No vision models**: Limited to rule-based detection
- **Development time**: Estimated 80-120 hours vs 12-16 hours for Docling integration

**Verdict**: **REJECTED** (poor ROI, maintenance burden)

---

### Alternative 5: Tabula-py

**Approach**: Use Tabula-py for table extraction

**Pros**:
- Specialized for table extraction
- Fast, deterministic

**Cons**:
- **Java dependency**: Requires JVM (similar to Tika)
- **Tables only**: No layout analysis, no OCR, no multi-modal
- **No vision models**: Rule-based extraction (fragile on complex layouts)
- **Narrow scope**: Would need additional library for non-table content

**Verdict**: **REJECTED** (incomplete solution, Java dependency)

---

## Consequences

### Positive Consequences

1. **Evidence Quality Improvement** (+15-20%)
   - Tables preserved as markdown with structure
   - Metrics directly extractable (no regex parsing needed)
   - Better evidence validation (table cells linked to themes)

2. **Scanned PDF Support**
   - Docling's OCR layer handles image-based PDFs
   - Expands coverage to older ESG reports (pre-2010)

3. **Competitive Parity**
   - Matches industry tools (Bloomberg ESG, MSCI) on data richness
   - Enables advanced features (table-based anomaly detection)

4. **Backward Compatibility**
   - Default backend remains unchanged
   - Existing pipelines continue working
   - No breaking changes

5. **Reproducibility Maintained**
   - Determinism validated via triple run + hash comparison
   - Provenance sidecars track extraction method, environment

### Negative Consequences

1. **Performance Regression** (2-3x slower)
   - Default: ~1-2s per document
   - Docling: ~3-6s per document
   - **Mitigation**: Acceptable trade-off for quality; batch processing feasible

2. **Docker Image Size Increase** (~500MB)
   - Docling models add ~500MB to image
   - **Mitigation**: Use slim base image, multi-stage build, model caching

3. **Determinism Complexity**
   - Vision models require careful configuration (CPU-only, single-threaded)
   - **Mitigation**: Extensive testing (triple validation, sensitivity analysis)

4. **Maintenance Burden** (dual backends)
   - Must maintain both default and Docling paths
   - **Mitigation**: Protocol interface minimizes duplication; automated tests catch regressions

5. **Dependency Risk**
   - Docling is relatively new (released 2024)
   - **Mitigation**: Pin exact version (0.12.0); rollback strategy in place

### Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| **Docling non-determinism** | Medium | High | CPU-only, single-threaded, torch.use_deterministic_algorithms(True) |
| **Model download failures** | Low | High | Pre-cache models in Docker, enforce offline mode (HF_HUB_OFFLINE=1) |
| **Parity below threshold** | Low | High | Differential testing (Jaccard ≥0.85); alignment audit (fail-closed) |
| **Performance unacceptable** | Low | Medium | Rollback to default; optimize later if needed |
| **Breaking change** | Very Low | Critical | Protocol interface + separate directories ensure isolation |

---

## Implementation Strategy

### Phase 1: Foundation (3 hours)
- Define `PDFParserBackend` Protocol
- Implement `DefaultBackend` (wrap existing PyMuPDF)
- Write CP tests (protocol compliance, determinism)

### Phase 2: Docling Integration (4 hours)
- Implement `DoclingBackend` with determinism config
- Write CP tests (determinism, failure paths, property tests)
- Validate triple run (3× → identical hashes)

### Phase 3: Infrastructure (2 hours)
- Implement `silver_locator.py` (dynamic path resolution)
- Implement `text_clean.py` (binary detection, quality scoring)
- Write CP tests (locator logic, text quality)

### Phase 4: Scripts & Validation (3 hours)
- Implement `pdf_to_silver.py` (CLI converter)
- Implement `alignment_audit.py` (quote validation)
- Generate provenance sidecars (SHA256, metadata)

### Phase 5: Testing & CI (2 hours)
- Update `test_cp_gates.py` (provenance, parity, alignment)
- Create `.github/workflows/ci-cp-gates.yml`
- Update `Dockerfile` with Docling dependencies

### Phase 6: Validation (2 hours)
- Run triple determinism test (5 companies × 3 runs)
- Run alignment audit (all evidence quotes)
- Measure parity score (default vs Docling)
- Compute evidence quality delta (+15-20%)

---

## Success Metrics

| Metric | Target | Status |
|--------|--------|--------|
| **Determinism** | 3 runs → identical SHA256 | TBD (Phase 2) |
| **Parity** | ≥85% Jaccard similarity | TBD (Phase 6) |
| **Table capture** | 100% preserved as markdown | TBD (Phase 6) |
| **Evidence quality** | +15-20% richness | TBD (Phase 6) |
| **Alignment** | 100% quotes validated | TBD (Phase 4) |
| **Coverage** | ≥95% on CP modules | TBD (Phase 5) |
| **CI passing** | All CP gates green | TBD (Phase 5) |
| **Rollback time** | <20 minutes | TBD (Phase 6) |

---

## Review and Approval

**Proposed by**: Scientific Coding Agent (SCA)
**Review date**: 2025-10-30
**Approval status**: Pending (awaiting context gate validation)

**Stakeholders**:
- ESG Evaluation Project Team (implementation)
- SCA Protocol Authority (compliance validation)
- Downstream consumers (retrieval, scoring, evidence extraction)

**Next Steps**:
1. Validate context gate (all context/ files complete)
2. Begin Phase 1 implementation (parser_backend.py)
3. Execute MEA loop (write → validate → fix → snapshot)

---

**End of ADR**
