# Authenticity Audit Remediation — Issue Tracker

**Audit ID**: AV-001-20251026  
**Total Issues**: 203  
**Status**: 🔴 BLOCKED (34 FATAL)  
**Updated**: 2025-10-26

---

## Priority 0: FATAL (BLOCKING) — 34 issues

**Status**: 🔴 NOT STARTED  
**Blocks**: All other work  
**ETA**: 4-7 hours

| ID | File | Line | Issue | Status | Owner | Notes |
|----|------|------|-------|--------|-------|-------|
| F01 | scripts/embed_and_index.py | 111 | eval() for JSON | ⬜ TODO | - | Replace with json.loads() |
| F02 | scripts/qa/authenticity_audit.py | ~50 | exec() for imports | ⬜ TODO | - | Use importlib |
| F03-F34 | scripts/*.py | Various | eval/exec calls | ⬜ TODO | - | 32 more instances |

**Acceptance Criteria**:
- [ ] `grep -rn "eval\|exec" scripts/ apps/ libs/` returns 0 results in production code
- [ ] All scripts still functional after fixes
- [ ] Tests pass

**Verification Command**:
```bash
grep -rn "eval(" --include="*.py" scripts/ apps/ libs/ | wc -l
# Expected: 0
```

---

## Priority 1: Determinism — 87 issues

**Status**: ⏸️ WAITING (blocked by P0)  
**Depends On**: Priority 0 completion  
**ETA**: 3-5 hours

### AV01: Unseeded Random (2 issues)

| ID | File | Line | Issue | Status | Owner | Notes |
|----|------|------|-------|--------|-------|-------|
| D01 | apps/pipeline/mcp_report_fetcher.py | 211 | random.uniform() | ⬜ TODO | - | Add _rng = random.Random(42) |
| D02 | libs/storage/astradb_vector.py | 489 | np.random.randn() | ⬜ TODO | - | Add np.random.seed(42) |

**Acceptance Criteria**:
- [ ] All random calls use seeded RNG
- [ ] Quality scores identical across runs
- [ ] `grep -rn "random\." | grep -v "seed\|_rng"` returns 0 unseeded calls

**Test Command**:
```bash
# Run twice with same seed
for i in 1 2; do
    SEED=42 python -c "from apps.pipeline.mcp_report_fetcher import simulate_quality; print(simulate_quality())"
done
# Expected: Identical output
```

### AV02: Python hash() Usage (9 issues)

| ID | File | Line | Issue | Status | Owner | Notes |
|----|------|------|-------|--------|-------|-------|
| D03 | pipelines/airflow/dags/esg_scoring_dag.py | 260 | hash(company_name) | ⬜ TODO | - | Use SHA256 |
| D04 | libs/query/query_synthesizer.py | 347 | hash(query) | ⬜ TODO | - | Use SHA256 |
| D05-D11 | Various | - | 7 more hash() calls | ⬜ TODO | - | Pattern: hashlib.sha256 |

**Acceptance Criteria**:
- [ ] All hash() replaced with SHA256-based stable hashing
- [ ] Task IDs/chunk IDs identical across runs
- [ ] `grep -rn "hash(" | grep -v "hashlib"` returns 0 Python hash() calls

**Helper Function**:
```python
import hashlib
def stable_hash(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:12]
```

### AV03: Timestamp Usage (76 issues)

| ID | File | Line | Issue | Status | Owner | Notes |
|----|------|------|-------|--------|-------|-------|
| D12 | apps/pipeline/demo_flow.py | 361 | time.time() | ⬜ TODO | - | Remove from parity artifact |
| D13 | apps/evaluation/response_quality.py | 132 | datetime.now() | ⬜ TODO | - | Use content hash |
| D14-D87 | Various | - | 74 more timestamps | ⬜ TODO | - | Remove or hash-based |

**Acceptance Criteria**:
- [ ] No time.time() or datetime.now() in artifacts
- [ ] Trace IDs use content hashes, not timestamps
- [ ] Artifacts identical across time-shifted runs

**Pattern**:
```python
# Instead of: trace_id = f"trace_{datetime.now().isoformat()}"
# Use: trace_id = f"trace_{stable_hash(json.dumps(params))}"
```

---

## Priority 2: Evidence & Parity — 29 issues

**Status**: ⏸️ WAITING (blocked by P0-P1)  
**Depends On**: Determinism fixes  
**ETA**: 4-6 hours

### Provenance Gate (1,015 issues consolidated)

| ID | Component | Issue | Status | Owner | Notes |
|----|-----------|-------|--------|-------|-------|
| E01 | Manifest | 1,015 test_hash entries | ⬜ TODO | - | Use real SHA256 |
| E02 | Manifest | Missing content_type | ⬜ TODO | - | Add from python-magic |
| E03 | Manifest | Missing headers | ⬜ TODO | - | Extract PDF metadata |

**Acceptance Criteria**:
- [ ] `grep -c "test_hash" artifacts/ingestion/manifest.json` returns 0
- [ ] All entries have `content_type` field
- [ ] All entries have `headers` with PDF metadata
- [ ] Real SHA256 hashes for all documents

**Verification**:
```bash
cat artifacts/ingestion/manifest.json | jq '.entries[0]' | jq 'has("content_type", "headers", "pdf_hash")'
# Expected: true
```

### Evidence Traceability

| ID | Component | Issue | Status | Owner | Notes |
|----|-----------|-------|--------|-------|-------|
| E04 | Evidence JSON | Missing chunk_id | ⬜ TODO | - | Add deterministic chunk IDs |
| E05 | Evidence | No page tracking | ⬜ TODO | - | Already has page_no, verify |

**Acceptance Criteria**:
- [ ] All evidence records have `chunk_id` field
- [ ] chunk_id format: `chunk_{sha256[:12]}`
- [ ] Traceable back to original document chunks

### Parity Gate (21 issues)

| ID | Issue | Status | Owner | Notes |
|----|-------|--------|-------|-------|
| E06 | Evidence doc_ids not in topk | ⬜ TODO | - | Fix ID consistency |

**Root Cause**: Evidence uses "LSE_HEAD_2025_p1" while topk uses "doc_1"

**Acceptance Criteria**:
- [ ] Evidence doc_ids match topk doc_ids
- [ ] Parity check script passes: `evidence_ids ⊆ topk_ids`
- [ ] `artifacts/audit/parity_report.json` shows 0 missing

**Verification**:
```bash
python scripts/qa/verify_parity.py
# Expected: ✅ PARITY OK: evidence ⊆ topk
```

### Rubric Compliance (1 issue)

| ID | Component | Issue | Status | Owner | Notes |
|----|-----------|-------|--------|-------|-------|
| E07 | Scoring | Heuristic instead of rubric JSON | ⬜ TODO | - | Use RubricScorer |

**Acceptance Criteria**:
- [ ] Delete heuristic RubricV3Scorer class (lines 193-353)
- [ ] Import: `from agents.scoring.rubric_scorer import RubricScorer`
- [ ] Load: `rubrics/maturity_v3.json` as source of truth
- [ ] Enforce: MIN_QUOTES_PER_THEME = 2
- [ ] Test: `pytest tests/authenticity/test_rubric_compliance_cp.py`

### Determinism Artifact

| ID | Component | Issue | Status | Owner | Notes |
|----|-----------|-------|--------|-------|-------|
| E08 | maturity.parquet | File missing | ⬜ TODO | - | Generate from scores |

**Acceptance Criteria**:
- [ ] File exists at `artifacts/maturity.parquet`
- [ ] Contains: org_id, year, theme, stage, confidence, evidence_count
- [ ] Deterministically sorted
- [ ] Can be hashed for determinism check

---

## Priority 3: Production Posture — 12 issues

**Status**: ⏸️ WAITING  
**Depends On**: Evidence & Parity fixes  
**ETA**: 3-4 hours

### AV04: Network Dependencies (1 issue)

| ID | Component | Issue | Status | Owner | Notes |
|----|-----------|-------|--------|-------|-------|
| P01 | ESGScoringPipeline | Requires live WatsonX/Astra | ⬜ TODO | - | Add offline mode |

**Acceptance Criteria**:
- [ ] Offline mode implemented
- [ ] Local embedder (sentence-transformers)
- [ ] In-memory vector store
- [ ] Docker works with `--network none`
- [ ] ENV var: `SCORING_MODE=offline`

**Test**:
```bash
docker run --network none -e SCORING_MODE=offline esg-scorer
curl http://localhost:8000/health
# Expected: 200 OK
```

### AV09: Filesystem Violations (8 issues)

| ID | File | Line | Issue | Status | Owner | Notes |
|----|------|------|-------|--------|-------|-------|
| P02 | apps/ingestion/parser.py | 65 | Writes to data/pdf_cache | ⬜ TODO | - | → artifacts/cache/pdfs |
| P03 | apps/evaluation/response_quality.py | 745 | Writes to reports/ | ⬜ TODO | - | → artifacts/evaluation/reports |
| P04-P09 | Various | - | 6 more violations | ⬜ TODO | - | All → artifacts/ |

**Acceptance Criteria**:
- [ ] All file writes go to `artifacts/` directory
- [ ] No writes to `data/` or `reports/`
- [ ] `.dockerignore` excludes old paths
- [ ] `find . -name "*.py" -exec grep -l "data/pdf_cache\|reports/" {} \;` returns 0

### AV11: Misleading Extensions (8 issues)

| ID | Location | Issue | Status | Owner | Notes |
|----|----------|-------|--------|-------|-------|
| P10 | scripts/embed_and_index.py | JSON with .parquet ext | ⬜ TODO | - | Rename or convert |
| P11-P17 | artifacts/ | 7 more .parquet JSON files | ⬜ TODO | - | Fix extensions |

**Acceptance Criteria**:
- [ ] JSON files have .json extension
- [ ] Parquet files have .parquet extension and are real Parquet format
- [ ] `find . -name "*.parquet" -exec head -1 {} \; | grep "^{"` returns 0

**Fix Script**:
```bash
find artifacts/ -name "*.parquet" -exec sh -c '
  if head -1 "$1" | grep -q "^{"; then
    mv "$1" "${1%.parquet}.json"
  fi
' _ {} \;
```

---

## Priority 4: Error Handling — 74 issues

**Status**: ⏸️ WAITING  
**Depends On**: Production posture  
**ETA**: 2-3 hours

### AV08: Silent Exception Handling (74 issues)

| ID | File | Line | Pattern | Status | Owner | Notes |
|----|------|------|---------|--------|-------|-------|
| H01 | agents/crawler/data_providers/sasb_provider.py | 183 | except: return [] | ⬜ TODO | - | Add logging |
| H02 | agents/crawler/data_providers/sasb_provider.py | 212 | except: return [] | ⬜ TODO | - | Add logging |
| H03 | agents/crawler/data_providers/sasb_provider.py | 240 | except: return [] | ⬜ TODO | - | Add logging |
| H04 | agents/crawler/data_providers/sasb_provider.py | 281 | except: return [] | ⬜ TODO | - | Add logging |
| H05 | agents/crawler/data_providers/sasb_provider.py | 326 | except: return [] | ⬜ TODO | - | Add logging |
| H06-H74 | Various | - | 69 more instances | ⬜ TODO | - | Pattern below |

**Pattern to Apply**:
```python
import logging
logger = logging.getLogger(__name__)

# BEFORE:
try:
    data = fetch()
    return data
except:
    return []  # Silent

# AFTER:
try:
    data = fetch()
    return data
except Exception as e:
    logger.error(f"Provider failed: {e}", exc_info=True)
    return None  # Explicit failure signal
```

**Acceptance Criteria**:
- [ ] All exception handlers have logging
- [ ] Exceptions visible in logs for debugging
- [ ] Return `None` instead of `[]` to signal explicit failure
- [ ] Provider health check endpoint added

---

## Progress Dashboard

### Overall Status

```
Total Issues: 203
├─ 🔴 FATAL:        34 (  0% complete) [BLOCKING]
├─ 🟡 Determinism:  87 (  0% complete)
├─ 🟡 Evidence:     29 (  0% complete)
├─ 🟢 Posture:      12 (  0% complete)
└─ 🟢 Errors:       74 (  0% complete)

Gates:
├─ Provenance:    🔴 FAIL (test_hash placeholders)
├─ Parity:        🔴 FAIL (21/21 missing)
├─ Determinism:   🔴 FAIL (no maturity.parquet)
├─ Rubric:        🔴 FAIL (heuristic scorer)
├─ Type Safety:   ⏸️  PENDING
├─ Coverage:      ⏸️  PENDING
└─ Docker:        ⏸️  PENDING
```

### Time Tracking

| Phase | Estimated | Actual | Status |
|-------|-----------|--------|--------|
| Phase 0: Setup | 0.5h | - | ⬜ TODO |
| Phase 1: FATAL | 4-7h | - | ⬜ TODO |
| Phase 2: Determinism | 3-5h | - | ⬜ TODO |
| Phase 3: Evidence | 4-6h | - | ⬜ TODO |
| Phase 4: Posture | 3-4h | - | ⬜ TODO |
| Phase 5: Errors | 2-3h | - | ⬜ TODO |
| Phase 6: Verification | 2-3h | - | ⬜ TODO |
| **TOTAL** | **18-28.5h** | **0h** | **0%** |

---

## Critical Path

```
Phase 1 (FATAL)
    ↓
Phase 2 (Determinism)
    ↓
Phase 3 (Evidence & Parity)
    ↓
Phase 4 (Production Posture)
    ↓
Phase 5 (Error Handling)
    ↓
Phase 6 (Final Verification)
    ↓
✅ PRODUCTION READY
```

**Current Blocker**: Phase 1 (FATAL) must complete first

---

## Daily Standup Template

### Day N - Morning

**Yesterday**:
- [ ] List completed items
- [ ] List blockers resolved

**Today**:
- [ ] Phase X focus
- [ ] Specific items to complete

**Blockers**:
- [ ] Any blocking issues

**Time Spent**: Xh / Yh estimated

---

## Completion Checklist

When all issues resolved, verify:

### Gates
- [ ] ✅ Provenance: Real hashes, metadata present
- [ ] ✅ Parity: evidence ⊆ topk verified  
- [ ] ✅ Determinism: 3 identical runs
- [ ] ✅ Rubric: JSON-based scoring with ≥2 quotes
- [ ] ✅ Type Safety: mypy --strict = 0
- [ ] ✅ Coverage: ≥95% on critical paths
- [ ] ✅ Docker: Offline mode functional

### Artifacts
- [ ] ✅ artifacts/ingestion/manifest.json (real hashes)
- [ ] ✅ artifacts/evidence/*.json (with chunk_id)
- [ ] ✅ artifacts/pipeline_validation/topk_vs_evidence.json
- [ ] ✅ artifacts/maturity.parquet
- [ ] ✅ artifacts/audit/parity_report.json (0 missing)
- [ ] ✅ artifacts/audit/determinism_report.json (identical hashes)

### Commands
- [ ] ✅ `python scripts/qa/authenticity_audit.py` → 0 FATAL
- [ ] ✅ `bash /tmp/test_det.sh` → 3 identical runs
- [ ] ✅ `python scripts/qa/verify_parity.py` → PASS
- [ ] ✅ `mypy --strict apps/api/main.py` → 0 errors
- [ ] ✅ `pytest tests/ --cov` → ≥95%
- [ ] ✅ `docker build && docker run --network none` → OK

### Release
- [ ] ✅ Final commit pushed
- [ ] ✅ Tag created: v1.0.0-audit-clean
- [ ] ✅ Documentation updated
- [ ] ✅ Completion report generated

---

## Notes Section

**Date**: 2025-10-26

### Decisions Made
- [ ] Record key architectural decisions
- [ ] Document any deviations from plan
- [ ] Note any issues requiring follow-up

### Lessons Learned
- [ ] What went well
- [ ] What could be improved
- [ ] Knowledge gaps identified

### Follow-up Items
- [ ] Any post-remediation work
- [ ] Monitoring setup needed
- [ ] Documentation updates

---

**Last Updated**: 2025-10-26  
**Next Review**: Start of Phase 1  
**Owner**: [Your Name]  
**Protocol**: SCA v13.8-MEA
