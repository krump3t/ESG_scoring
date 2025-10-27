# Phase 7b PART-2 Implementation Plan

## Status
- **PART-1**: ✅ Complete (12 tests passing, 6 xfailed as expected)
- **PART-2**: ⏳ Pending (this document)

## Objective
Complete the demo pipeline with full retrieval→ranking→scoring→parity validation flow.

## Implementation Tasks

### 1. Complete `apps/pipeline/demo_flow.run_score()`

**Current State**: Returns minimal skeleton with deterministic trace_id

**Target State**: Execute full pipeline:

```python
def run_score(
    company: str,
    year: int,
    query: str,
    alpha: float = 0.6,
    k: int = 10,
    seed: int = 42
) -> Dict[str, Any]:
    """
    Run scoring pipeline for company query.

    Pipeline stages:
    1. Load company data from artifacts/demo/companies.json
    2. Read bronze Parquet for company+year
    3. Prefilter documents (company+year match)
    4. Lexical retrieval (BM25/TF-IDF)
    5. CrossEncoder ranking on top-N lexical
    6. Semantic KNN retrieval (if semantic_enabled)
    7. α-Fusion of lexical + semantic (if semantic_enabled)
    8. RubricV3 scoring on fused top-k
    9. Parity validation: evidence doc_ids ⊆ fused top-k
    10. Write parity artifact to artifacts/pipeline_validation/demo_topk_vs_evidence.json
    11. Increment esg_parity_break_total if violation

    Returns:
        Score response with:
        - company, year, query
        - scores: [{pillar, score, evidence: [{doc_id, text, score}]}]
        - model_version, rubric_version
        - trace_id (deterministic SHA256)
    """
```

**Implementation Steps**:
1. Load `artifacts/demo/companies.json`, find company+year record
2. Read bronze Parquet from record["bronze"]
3. Build corpus: `List[{doc_id, text, company, year}]`
4. Prefilter: `[doc for doc in corpus if doc["company"]==company and doc["year"]==year]`
5. Lexical retrieval:
   - Use `libs.retrieval.lexical.bm25_retriever` or TF-IDF
   - Get top-N lexical scores: `{doc_id: score}`
6. CrossEncoder ranking (if enabled):
   - Use `libs.retrieval.crossencoder_ranker` on lexical top-N
   - Return reranked scores
7. Semantic retrieval (if `semantic_enabled` flag):
   - Load index from `artifacts/demo/index_snapshot.json`
   - Embed query using DeterministicEmbedder
   - KNN search for top-k semantic: `{doc_id: score}`
8. α-Fusion (if semantic_enabled):
   - Use `libs.retrieval.hybrid_semantic.fuse_lex_sem(lex_scores, sem_scores, alpha)`
   - Sort by (-score, doc_id)
9. RubricV3 scoring:
   - Use `libs.scoring.rubric_v3_scorer.score_documents(query, top_k_docs)`
   - Returns: `[{pillar, score, evidence: [{doc_id, text, score}]}]`
10. Parity validation:
    - Extract all evidence doc_ids from scores
    - Check: `all(doc_id in fused_top_k_ids for doc_id in evidence_ids)`
    - If violation: increment `esg_parity_break_total`
11. Write parity artifact:
    ```json
    {
      "query": "...",
      "company": "...",
      "year": 2024,
      "fused_top_k": ["doc1", "doc2", ...],
      "evidence_ids": ["doc1", "doc3", ...],
      "parity_ok": true,
      "trace_id": "sha256:..."
    }
    ```
12. Return full score response

**Files Modified**:
- `apps/pipeline/demo_flow.py` (~100 lines added to `run_score()`)

**Tests Fixed**:
- ✅ `test_embed_deterministic_mode`
- ✅ `test_missing_pdf_raises_error`
- ✅ `test_invalid_year_raises_error`

---

### 2. Wire Metrics in CLI Scripts

**Locations**:
- `scripts/ingest_company.py`
- `scripts/embed_and_index.py`
- `apps/pipeline/demo_flow.py`

**Changes**:

#### `scripts/ingest_company.py`:
```python
from apps.api.metrics import esg_demo_ingest_total

def ingest_pdf(company: str, year: int, pdf_path: Path) -> Dict[str, Any]:
    # ... existing code ...

    # Increment metric
    esg_demo_ingest_total.labels(source="pdf").inc()

    return record

def ingest_parquet(company: str, year: int, parquet_path: Path) -> Dict[str, Any]:
    # ... existing code ...

    # Increment metric
    esg_demo_ingest_total.labels(source="parquet").inc()

    return record
```

#### `scripts/embed_and_index.py`:
```python
from apps.api.metrics import esg_demo_index_size

def main() -> int:
    # ... existing code ...

    # Set gauge after building index
    snapshot = create_index_snapshot(vectors, corpus, args.dim, args.alpha, args.k, args.backend)
    esg_demo_index_size.labels(backend=args.backend).set(snapshot["total_docs"])

    # ... write snapshot ...
```

#### `apps/pipeline/demo_flow.py`:
```python
from apps.api.metrics import esg_demo_score_latency_seconds, esg_parity_break_total
import time

def run_score(...) -> Dict[str, Any]:
    start_time = time.time()

    # ... execute pipeline ...

    # Check parity
    parity_ok = all(doc_id in fused_top_k_ids for doc_id in evidence_ids)
    if not parity_ok:
        esg_parity_break_total.inc()

    # Record latency
    latency = time.time() - start_time
    esg_demo_score_latency_seconds.observe(latency)

    return response
```

**Tests Fixed**:
- All metrics tests already passing (they check metric existence, not values)

---

### 3. Enhance `apps/api/main.py` with Demo Company Lookup

**Current State**: No company lookup, basic /score endpoint

**Target State**: Company-aware scoring with query params

**Changes**:

```python
from pathlib import Path
import json
from typing import Optional, Dict, Any, List
from fastapi import HTTPException, Query

# Load companies at startup
COMPANIES_MANIFEST: List[Dict[str, Any]] = []

@app.on_event("startup")
def load_companies():
    global COMPANIES_MANIFEST
    companies_path = Path("artifacts/demo/companies.json")
    if companies_path.exists():
        COMPANIES_MANIFEST = json.loads(companies_path.read_text())

def get_company_record(company: str, year: int) -> Optional[Dict[str, Any]]:
    """Lookup company record from manifest."""
    for rec in COMPANIES_MANIFEST:
        if rec["company"] == company and rec["year"] == year:
            return rec
    return None

@app.post("/score")
def score_documents(
    request: ScoreRequest,
    semantic: int = Query(default=0, ge=0, le=1, description="Enable semantic retrieval (0 or 1)"),
    k: int = Query(default=10, ge=1, le=100, description="Top-k results"),
    alpha: float = Query(default=0.6, ge=0.0, le=1.0, description="Fusion parameter (0.0-1.0)")
) -> ScoreResponse:
    """
    Score documents against ESG rubric with optional semantic retrieval.

    Query params:
    - semantic: 1 to enable semantic, 0 for lexical only
    - k: Top-k results (default 10)
    - alpha: Fusion weight (default 0.6 = 60% lexical, 40% semantic)

    Returns 404 if company not found in manifest.
    Returns 422 if validation errors.
    """
    # Lookup company
    company_rec = get_company_record(request.company, request.year)
    if not company_rec:
        raise HTTPException(
            status_code=404,
            detail=f"Company '{request.company}' with year {request.year} not found in manifest"
        )

    # Override semantic flag from query param
    semantic_enabled = bool(semantic)

    # Call demo_flow with params
    from apps.pipeline.demo_flow import run_score
    result = run_score(
        company=request.company,
        year=request.year,
        query=request.query,
        alpha=alpha,
        k=k,
        seed=42  # Fixed for determinism
    )

    # Convert to ScoreResponse
    return ScoreResponse(**result)
```

**Validation**:
- FastAPI automatically validates query params (ge, le constraints)
- Returns 422 if query params out of range
- Returns 404 if company not found

**Tests Fixed**:
- ✅ `test_unknown_company_returns_404`
- ✅ `test_deterministic_trace_id_three_runs` (API contract test)
- ✅ `test_score_returns_required_schema_fields`

---

### 4. Parity Artifact Writing

**Location**: `apps/pipeline/demo_flow.run_score()`

**Implementation**:

```python
def run_score(...) -> Dict[str, Any]:
    # ... execute pipeline ...

    # Extract fused top-k doc_ids
    fused_top_k_ids = [doc_id for doc_id, score in fused_results[:k]]

    # Extract evidence doc_ids from rubric scores
    evidence_ids = []
    for pillar_score in rubric_scores:
        for evidence in pillar_score.get("evidence", []):
            evidence_ids.append(evidence["doc_id"])
    evidence_ids = list(set(evidence_ids))  # Deduplicate

    # Check parity
    parity_ok = all(doc_id in fused_top_k_ids for doc_id in evidence_ids)

    # Write artifact
    parity_artifact = {
        "query": query,
        "company": company,
        "year": year,
        "alpha": alpha,
        "k": k,
        "fused_top_k": fused_top_k_ids,
        "evidence_ids": sorted(evidence_ids),
        "parity_ok": parity_ok,
        "trace_id": trace_id,
        "timestamp": time.time()
    }

    parity_dir = Path("artifacts/pipeline_validation")
    parity_dir.mkdir(parents=True, exist_ok=True)
    parity_path = parity_dir / "demo_topk_vs_evidence.json"
    parity_path.write_text(json.dumps(parity_artifact, indent=2, sort_keys=True))

    # Increment counter if violation
    if not parity_ok:
        from apps.api.metrics import esg_parity_break_total
        esg_parity_break_total.inc()

    # ... return response ...
```

**Artifact Schema**:
```json
{
  "alpha": 0.6,
  "company": "Headlam Group Plc",
  "evidence_ids": ["doc_0001", "doc_0003"],
  "fused_top_k": ["doc_0001", "doc_0002", "doc_0003", "doc_0004", "doc_0005"],
  "k": 5,
  "parity_ok": true,
  "query": "What are the company's climate commitments?",
  "timestamp": 1698765432.123,
  "trace_id": "sha256:1a2b3c4d5e6f7890",
  "year": 2025
}
```

**Tests Fixed**:
- ✅ `test_evidence_subset_of_fused_top5` (already passing, validates artifact)

---

### 5. Subprocess CLI Tests

**Remaining xfailed tests** (3 tests):
- `test_ingest_pdf_creates_parquet_and_companies_json`
- `test_embed_creates_index_snapshot`
- `test_embed_deterministic_produces_identical_output`

**Issue**: These tests use `subprocess.run()` to invoke CLI scripts

**Solution**: CLI scripts already implemented, tests should pass once subprocess calls succeed

**Verification**:
```python
# Example from test_embed_index_cli_cp.py
def test_ingest_pdf_creates_parquet_and_companies_json(self):
    result = subprocess.run(
        ["python", "scripts/ingest_company.py",
         "--company", "TestCo", "--year", "2024",
         "--pdf", "artifacts/raw/LSE_HEAD_2025.pdf"],
        capture_output=True, text=True, cwd=PROJ
    )
    assert result.returncode == 0
    assert Path("artifacts/demo/companies.json").exists()
    assert Path("artifacts/bronze/testco_2024.parquet").exists()
```

**Expected**: These tests should flip to pass once PART-2 artifacts are in place

---

## Validation & Artifacts

After PART-2 implementation, run full validation:

### 1. Run Tests with Coverage
```bash
pytest tests/demo/ tests/api/test_score_demo_contract_cp.py \
       tests/retrieval/test_parity_invariant_cp.py \
       tests/pipeline/ tests/metrics/ \
       --cov=apps.pipeline --cov=scripts --cov=apps.api \
       --cov-branch --cov-report=json:qa/coverage_phase7b.json \
       --cov-report=term -v
```

**Expected**: 28 tests passing, 0 xfailed, coverage ≥95% on CP files

### 2. Type Safety
```bash
mypy --strict apps/pipeline/demo_flow.py scripts/ingest_company.py scripts/embed_and_index.py
```

**Expected**: 0 errors

### 3. Determinism Report
Run scoring pipeline 3× with identical inputs, verify identical trace_id:

```bash
python -c "
from apps.pipeline.demo_flow import run_score
import json

results = []
for i in range(3):
    r = run_score('Headlam Group Plc', 2025, 'climate commitments', alpha=0.6, k=5, seed=42)
    results.append(r)

# Verify identical trace_ids
assert results[0]['trace_id'] == results[1]['trace_id'] == results[2]['trace_id']

# Write report
report = {
    'runs': 3,
    'trace_ids': [r['trace_id'] for r in results],
    'determinism_ok': len(set(r['trace_id'] for r in results)) == 1
}
with open('artifacts/determinism_report.json', 'w') as f:
    json.dump(report, f, indent=2)
"
```

**Expected**: `determinism_ok: true`

### 4. Coverage Summary
```bash
python -c "
import json
from pathlib import Path

cov = json.loads(Path('qa/coverage_phase7b.json').read_text())
summary = {
    'line_rate': cov['totals']['percent_covered'] / 100.0,
    'branch_rate': cov['totals']['percent_covered_branches'] / 100.0,
    'cp_files': {
        'apps/pipeline/demo_flow.py': cov['files']['apps/pipeline/demo_flow.py']['summary']['percent_covered'],
        'scripts/ingest_company.py': cov['files']['scripts/ingest_company.py']['summary']['percent_covered'],
        'scripts/embed_and_index.py': cov['files']['scripts/embed_and_index.py']['summary']['percent_covered']
    }
}
with open('artifacts/coverage_summary.json', 'w') as f:
    json.dump(summary, f, indent=2)
"
```

**Expected**: `line_rate ≥ 0.95`, `branch_rate ≥ 0.95`

### 5. OpenAPI Export
```bash
python -c "
from apps.api.main import app
import json

schema = app.openapi()
with open('artifacts/api/openapi.json', 'w') as f:
    json.dump(schema, f, indent=2)
"
```

**Expected**: Valid OpenAPI 3.x schema with `/score` endpoint documented

### 6. Snapshot Manifest
Create `artifacts/phase7b_manifest.json`:

```json
{
  "phase": "7b-REALDATA-DEMO-PART2",
  "timestamp": "2025-01-15T12:00:00Z",
  "files": {
    "apps/pipeline/demo_flow.py": {
      "sha256": "...",
      "lines": 210,
      "role": "CP"
    },
    "scripts/ingest_company.py": {
      "sha256": "...",
      "lines": 220,
      "role": "CP"
    },
    "scripts/embed_and_index.py": {
      "sha256": "...",
      "lines": 190,
      "role": "CP"
    },
    "apps/api/main.py": {
      "sha256": "...",
      "lines": 85,
      "role": "CP"
    },
    "apps/api/metrics.py": {
      "sha256": "...",
      "lines": 117,
      "role": "support"
    }
  },
  "tests": {
    "total": 28,
    "passed": 28,
    "xfailed": 0,
    "coverage_cp": 0.97
  },
  "validation": {
    "mypy_strict": "pass",
    "determinism_3x": "pass",
    "parity_ok": true
  }
}
```

---

## Demo Runbook

Create `tasks/010-hybrid-ingestion-phase1/DEMO_RUNBOOK.md`:

```markdown
# Phase 7b Demo Runbook

## Prerequisites
- Python 3.11+ with venv at `C:\projects\Work Projects\.venv`
- Headlam PDF at `artifacts/raw/LSE_HEAD_2025.pdf`

## Step 1: Ingest Company Data
```bash
.venv/Scripts/python scripts/ingest_company.py \
  --company "Headlam Group Plc" \
  --year 2025 \
  --pdf artifacts/raw/LSE_HEAD_2025.pdf
```

**Expected Output**:
```
✓ Ingested PDF: Headlam Group Plc (2025)
✓ Updated companies manifest: headlam_group_plc
```

**Artifacts Created**:
- `artifacts/raw/LSE_HEAD_2025.pdf` (copied)
- `artifacts/bronze/headlam_group_plc_2025.parquet`
- `artifacts/demo/companies.json`

## Step 2: Build Embeddings & Index
```bash
.venv/Scripts/python scripts/embed_and_index.py \
  --mode deterministic \
  --backend in_memory \
  --alpha 0.6 \
  --k 10 \
  --dim 128
```

**Expected Output**:
```
Loading companies manifest...
✓ Found 1 companies
Loading corpus from bronze files...
✓ Loaded 1 documents
Building deterministic embeddings (dim=128, seed=42)...
✓ Generated 1 vectors
Creating index snapshot...
✓ Saved index snapshot: artifacts/demo/index_snapshot.json
  Digest: a1b2c3d4e5f67890
  Backend: in_memory
  Docs: 1
```

**Artifacts Created**:
- `artifacts/demo/index_snapshot.json`

## Step 3: Run Scoring Pipeline
```bash
.venv/Scripts/python -c "
from apps.pipeline.demo_flow import run_score
import json

result = run_score(
    company='Headlam Group Plc',
    year=2025,
    query='What are the company\\'s climate commitments?',
    alpha=0.6,
    k=5,
    seed=42
)

print(json.dumps(result, indent=2))
"
```

**Expected Output** (PART-2):
```json
{
  "company": "Headlam Group Plc",
  "year": 2025,
  "query": "What are the company's climate commitments?",
  "scores": [
    {
      "pillar": "Environmental",
      "score": 0.75,
      "evidence": [
        {
          "doc_id": "doc_0001",
          "text": "We commit to net-zero emissions by 2040...",
          "score": 0.85
        }
      ]
    }
  ],
  "model_version": "v1.0",
  "rubric_version": "3.0",
  "trace_id": "sha256:1a2b3c4d5e6f7890"
}
```

**Artifacts Created**:
- `artifacts/pipeline_validation/demo_topk_vs_evidence.json`

## Step 4: Query API with Semantic Retrieval
```bash
curl -X POST "http://localhost:8000/score?semantic=1&k=5&alpha=0.7" \
  -H "Content-Type: application/json" \
  -d '{
    "company": "Headlam Group Plc",
    "year": 2025,
    "query": "What are the company'\''s climate commitments?"
  }'
```

**Expected Response**:
```json
{
  "company": "Headlam Group Plc",
  "year": 2025,
  "scores": [...],
  "trace_id": "sha256:1a2b3c4d5e6f7890"
}
```

## Step 5: Check Prometheus Metrics
```bash
curl http://localhost:8000/metrics | grep esg_demo
```

**Expected Output**:
```
# HELP esg_demo_ingest_total Total number of demo company ingestions
# TYPE esg_demo_ingest_total counter
esg_demo_ingest_total{source="pdf"} 1.0

# HELP esg_demo_index_size Number of documents in demo index
# TYPE esg_demo_index_size gauge
esg_demo_index_size{backend="in_memory"} 1.0

# HELP esg_demo_score_latency_seconds Latency of demo scoring requests in seconds
# TYPE esg_demo_score_latency_seconds histogram
esg_demo_score_latency_seconds_bucket{le="0.05"} 1.0
esg_demo_score_latency_seconds_sum 0.032
esg_demo_score_latency_seconds_count 1.0

# HELP esg_parity_break Total number of evidence parity violations
# TYPE esg_parity_break counter
esg_parity_break_total 0.0
```
```

---

## Success Criteria

**PART-2 Complete When**:
1. ✅ All 28 tests passing (0 xfailed)
2. ✅ `mypy --strict` = 0 errors on all CP files
3. ✅ Coverage ≥95% line & branch on CP files
4. ✅ Determinism report shows 3× identical trace_ids
5. ✅ Parity artifact written with `parity_ok: true`
6. ✅ Prometheus metrics incremented and exposed at `/metrics`
7. ✅ OpenAPI schema exported to `artifacts/api/openapi.json`
8. ✅ Snapshot manifest created with SHA256 hashes
9. ✅ Demo runbook executable end-to-end

**Contract Fulfilled When**:
- Output-Contract JSON emitted with `status: "ok"`
- All validation gates pass (context, TDD, coverage, type safety, security, traceability)
- Snapshot saved to `artifacts/state.json` and `reports/phase7b_snapshot.md`

---

## Estimated LOC for PART-2

| File | PART-1 LOC | PART-2 Added | Total |
|------|------------|--------------|-------|
| `apps/pipeline/demo_flow.py` | 155 | +100 | ~255 |
| `scripts/ingest_company.py` | 220 | +15 (metrics) | ~235 |
| `scripts/embed_and_index.py` | 190 | +10 (metrics) | ~200 |
| `apps/api/main.py` | 60 | +40 (company lookup) | ~100 |
| `apps/api/metrics.py` | 117 | 0 (already done) | 117 |
| **Total** | **742** | **+165** | **~907** |

**Tests**: 28 (all already written in PART-1 TDD batch)

**Artifacts**: 6 new files (coverage_summary.json, determinism_report.json, openapi.json, phase7b_manifest.json, demo_topk_vs_evidence.json, DEMO_RUNBOOK.md)

---

## References

- **Phase 7a**: Deterministic embedder, vector index, hybrid fusion (completed)
- **SCA Protocol v13.8**: CLAUDE.md, full_protocol.md
- **MEA Loop**: validate-only.ps1, snapshot-save.ps1
- **Headlam PDF**: `artifacts/raw/LSE_HEAD_2025.pdf` (real demo fixture)
- **Integration Flags**: `configs/integration_flags.json` (semantic_enabled defaults to false)

---

**End of PART-2 Implementation Plan**
