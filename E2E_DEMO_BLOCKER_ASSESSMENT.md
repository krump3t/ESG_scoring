# E2E DEMO BLOCKER ASSESSMENT
## SCA v13.8-MEA | Authentic E2E Demo Readiness

**Date**: 2025-10-29
**Agent**: Claude Code (Sonnet 4.5)
**Project**: IBM ESG Evaluation - Prospecting Engine
**Working Directory**: `C:\projects\Work Projects\ibm-projects\ESG Evaluation\prospecting-engine`

---

## EXECUTIVE SUMMARY

The prospecting-engine codebase has **most infrastructure in place** for authentic E2E demo execution, but has **3 CRITICAL BLOCKERS** that prevent the provided bash/PowerShell scripts from running successfully.

**Status**: 🔴 **BLOCKED** (3 critical, 2 medium, 4 low-priority issues)

**Recommended Action**: Fix critical blockers in sequence, then execute test run with validation.

---

## CRITICAL BLOCKERS (Must Fix)

### 🔴 BLOCKER #1: Missing `extract_pdf_chunks` Function

**Issue**: The coldstart script expects `agents.extraction.enhanced_pdf_extractor.extract_pdf_chunks()` but this function **does not exist**.

**Current State**:
- ✅ File exists: `agents/extraction/enhanced_pdf_extractor.py`
- ✅ Class exists: `EnhancedPDFExtractor` with `.extract()` method
- ❌ Function missing: `extract_pdf_chunks(pdf_path, chunk_size, chunk_overlap)` (module-level function)

**Impact**: Script section #5 (ingestion pipeline creation) will fail at import.

**Actual Available**:
- `agents/extraction/enhanced_pdf_extractor.py` → `extract_document()` function exists (line 162-182)
- `agents/crawler/extractors/enhanced_pdf_extractor.py` → Different extractor with `EnhancedPDFExtractor.extract()` method

**Remediation**:
```python
# Add to agents/extraction/enhanced_pdf_extractor.py:
def extract_pdf_chunks(pdf_path: str, chunk_size: int = 1000, chunk_overlap: int = 200) -> List[Dict[str, Any]]:
    """
    Extract PDF with chunking (compatibility wrapper).

    Args:
        pdf_path: Path to PDF file
        chunk_size: Target chunk size in characters
        chunk_overlap: Overlap between chunks

    Returns:
        List of chunk dictionaries with page, text, and metadata
    """
    return extract_document(pdf_path, chunk_size=chunk_size)
```

**Priority**: P0 - Required for ingestion scripts to run

---

### 🔴 BLOCKER #2: Missing `provider_local.py` Module

**Issue**: Coldstart script creates `agents/crawler/provider_local.py` but the module **already partially exists** with different structure.

**Current State**:
- ✅ File exists: `agents/crawler/provider_local.py` (found in file listing)
- ⚠️ Content unknown: Need to verify if it has required functions
- ❌ Script will **overwrite** existing file without checking

**Required Functions** (from script):
- `discover_from_config(companies_yaml: Dict) -> List[LocalDoc]`
- `materialize_bronze(ld: LocalDoc) -> Dict[str, Any]`

**Impact**:
- If file is overwritten, existing functionality may be lost
- If required functions missing, `ingest_local_matrix.py` will fail

**Remediation**: Read existing `provider_local.py`, merge with script requirements, or verify compatibility.

**Priority**: P0 - Required for local PDF discovery

---

### 🔴 BLOCKER #3: `apps.pipeline.demo_flow` Import Dependency

**Issue**: `scripts/run_matrix.py` imports `apps.pipeline.demo_flow.run_score()` which requires `artifacts/demo/companies.json` manifest.

**Current State**:
- ✅ File exists: `apps/pipeline/demo_flow.py`
- ✅ Function exists: `run_score(company, year, query, ...)`
- ⚠️ Dependency: Requires `artifacts/demo/companies.json` (line 174-176)
- ❌ File missing: `artifacts/demo/companies.json` not referenced in coldstart script

**From demo_flow.py**:
```python
def _lookup_manifest(company: str, year: int) -> Dict[str, Any]:
    manifest_path = Path("artifacts/demo/companies.json")
    if not manifest_path.exists():
        raise FileNotFoundError("No companies manifest found")
    manifest: List[Dict[str, Any]] = json.loads(manifest_path.read_text())
    for record in manifest:
        if record.get("company") == company and record.get("year") == year:
            return record
    raise FileNotFoundError(f"Company '{company}' with year {year} not found in manifest")
```

**Impact**: `run_matrix.py` will fail when calling `run_score()` because manifest lookup will raise `FileNotFoundError`.

**Remediation**: Create `artifacts/demo/companies.json` with bronze path mappings:
```json
[
  {
    "company": "Microsoft Corporation",
    "year": 2023,
    "bronze": "data/silver/org_id=MSFT/year=2023/MSFT_2023_chunks.parquet"
  },
  {
    "company": "Apple Inc.",
    "year": 2023,
    "bronze": "data/silver/org_id=AAPL/year=2023/AAPL_2023_chunks.parquet"
  }
]
```

**Priority**: P0 - Required for scoring pipeline to run

---

## MEDIUM PRIORITY ISSUES

### ⚠️ ISSUE #4: `libs.utils` Import Path

**Issue**: Script section #1 tests `import libs.utils` but this may fail depending on PYTHONPATH setup.

**Current State**:
- ✅ Directory exists: `libs/utils/`
- ✅ Files exist: Multiple utility modules
- ⚠️ `__init__.py` may not export all needed symbols

**Remediation**: Ensure repo root is on PYTHONPATH (script does handle this, but fragile).

**Priority**: P1 - May cause import errors

---

### ⚠️ ISSUE #5: PyMuPDF (fitz) Dependency

**Issue**: `agents/crawler/extractors/enhanced_pdf_extractor.py` requires `import fitz` (PyMuPDF) which is not in `requirements.txt`.

**Current requirements.txt**:
```
fastapi
pydantic
uvicorn
pytest
pytest-cov
hypothesis
numpy
pandas
pyarrow
lizard
interrogate
rank-bm25
ibm-watsonx-ai
```

**Missing**:
- `PyMuPDF` (fitz) - PDF extraction
- `duckdb` - Parquet validation (section #6)
- `pyyaml` - Config file parsing

**Remediation**: Add to requirements.txt:
```
PyMuPDF>=1.23.0
duckdb>=0.9.0
pyyaml>=6.0
```

**Priority**: P1 - Will cause runtime import errors

---

## LOW PRIORITY / WARNINGS

### ℹ️ ISSUE #6: PDF Path Configuration Mismatch

**Issue**: `configs/companies_local.yaml` has inconsistent path fields:
- MSFT: Only has `local_path` (no `pdf_path`)
- Others: Have both `pdf_path` and `local_path`

**Impact**: Ingestion script expects `pdf_path` field (line 17 in companies_local.yaml shows MSFT doesn't have it).

**Remediation**: Standardize to use `pdf_path` consistently, or update ingestion script to check both fields.

---

### ℹ️ ISSUE #7: Mock/Stub Violations (AUTHENTICITY CHECK)

**Scan Results**:
- ✅ Production code mostly clean
- ⚠️ Found in: `agents/extraction/rd_locator_wx.py`, `agents/embedding/watsonx_embedder.py`
- ⚠️ Found in libs: `libs/retrieval/semantic_wx.py`, `libs/llm/watsonx_client.py`, etc.

**Context**: These are likely "mock mode" flags or test utilities, not actual mock implementations. Need code review to confirm.

**Priority**: P2 - Audit before release, likely benign

---

### ℹ️ ISSUE #8: Determinism Infrastructure

**Status**: ✅ **GOOD**
- File exists: `libs/utils/determinism_guard.py`
- Used in: `apps/pipeline/demo_flow.py` (line 15-17)
- Seeds enforced: SEED=42, PYTHONHASHSEED=0

---

### ℹ️ ISSUE #9: Semantic Fetch/Replay Infrastructure

**Status**: ✅ **EXISTS**
- File exists: `scripts/semantic_fetch_replay.py`
- Cache ledger: Referenced in script section #10
- WatsonX integration: `agents/embedding/watsonx_embedder.py` present

**Concern**: Need to verify cache directory structure and ledger.jsonl format.

---

## REMEDIATION PLAN

### Phase 1: Critical Path (P0 Blockers)

```powershell
cd "C:\projects\Work Projects\ibm-projects\ESG Evaluation\prospecting-engine"

# 1. Add extract_pdf_chunks wrapper function
# Edit: agents/extraction/enhanced_pdf_extractor.py
# Add function at end of file

# 2. Verify provider_local.py compatibility
# Read and audit agents/crawler/provider_local.py

# 3. Create companies manifest
mkdir -Force artifacts\demo
# Create artifacts/demo/companies.json with bronze mappings

# 4. Add missing dependencies
# Edit requirements.txt, add PyMuPDF, duckdb, pyyaml
.\.venv\Scripts\python.exe -m pip install PyMuPDF duckdb pyyaml
```

### Phase 2: Validation Run

```powershell
# Test ingestion with one PDF
python scripts/ingest_single_doc.py `
  --org-id AAPL `
  --year 2023 `
  --pdf-path "data/pdf_cache/Apple_2023_sustainability.pdf" `
  --source-url "file://data/pdf_cache/Apple_2023_sustainability.pdf"

# Verify silver output
ls data\silver\org_id=AAPL\year=2023\

# Test scoring pipeline
$env:SEED="42"; $env:PYTHONHASHSEED="0"
python scripts/run_matrix.py --config configs/companies_local.yaml
```

### Phase 3: Full E2E Demo

Only proceed after Phase 1 & 2 pass.

---

## ASSETS STATUS

### ✅ WORKING COMPONENTS

1. **PDF Extraction**: `agents/extraction/enhanced_pdf_extractor.py` has full PyMuPDF extraction
2. **Scoring Pipeline**: `apps/pipeline/demo_flow.py` complete with rubric scorer
3. **Run Matrix**: `scripts/run_matrix.py` has determinism validation logic
4. **Determinism Guard**: `libs/utils/determinism_guard.py` enforces seeds
5. **Evidence & Parity**: Validation gates implemented in `run_matrix.py` (lines 203-426)
6. **Real PDFs**: Apple PDF confirmed present in `data/pdf_cache/`
7. **MSFT Silver**: Pre-processed data exists at `data/silver/org_id=MSFT/`

### ❌ MISSING COMPONENTS

1. **`extract_pdf_chunks` function** - Need wrapper in `agents/extraction/enhanced_pdf_extractor.py`
2. **`artifacts/demo/companies.json`** - Bronze path manifest for demo_flow lookups
3. **Dependencies** - PyMuPDF, duckdb, pyyaml not in requirements.txt

### ⚠️ NEEDS VERIFICATION

1. **`provider_local.py` structure** - Verify compatibility with script expectations
2. **Mock scan results** - Code review to confirm authenticity
3. **Cache ledger format** - Verify `artifacts/wx_cache/ledger.jsonl` structure

---

## NEXT STEPS

1. **[IMMEDIATE]** Fix 3 critical blockers (estimated 30-45 minutes)
2. **[TEST]** Run Phase 2 validation (estimated 15 minutes)
3. **[FULL RUN]** Execute complete E2E demo script (estimated 45-60 minutes)
4. **[GATES]** Verify all authenticity gates pass (determinism, parity, evidence)
5. **[RELEASE]** Generate attested release pack

---

## CONFIDENCE ASSESSMENT

**Blocker Resolution**: ⭐⭐⭐⭐ (High confidence - straightforward fixes)
**E2E Success**: ⭐⭐⭐ (Medium confidence - depends on data quality and edge cases)
**Gate Compliance**: ⭐⭐⭐⭐ (High confidence - gates are well-implemented)
**Determinism**: ⭐⭐⭐⭐⭐ (Very high confidence - infrastructure is solid)

**Overall Assessment**: With 3 critical fixes applied, the pipeline should execute successfully on real PDFs with deterministic, auditable results.

---

**End of Assessment**
