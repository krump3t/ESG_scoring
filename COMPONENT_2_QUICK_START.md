# Component 2: Quick Start Guide

**Component:** Semantic Retrieval with watsonx.ai
**Status:** ✅ READY FOR EXECUTION (blocked on credentials)
**Agent:** SCA v13.8-MEA
**Date:** 2025-10-28

---

## TL;DR

Component 2 is **100% complete** (implementation + integration + documentation). To run E2E test:

```bash
# 1. Set credentials
export WX_API_KEY='your_api_key'
export WX_PROJECT='your_project_id'

# 2. Navigate to project
cd "C:/projects/Work Projects/ibm-projects/ESG Evaluation/prospecting-engine"

# 3. Run E2E test (10-20 minutes)
bash RUN_E2E_WITH_CREDENTIALS.sh
```

**Expected Result:** All gates PASS (determinism, parity, evidence, cache→replay)

---

## What's Complete

### Implementation (1,197 LOC)
- ✅ `libs/retrieval/semantic_wx.py` (535 LOC) - Core retrieval module
- ✅ `tests/retrieval/test_semantic_wx.py` (422 LOC) - Comprehensive tests
- ✅ `scripts/semantic_fetch_replay.py` (240 LOC) - FETCH+REPLAY script

### Integration (4 files modified)
- ✅ `scripts/run_matrix.py` - SemanticRetriever import added
- ✅ `Makefile` - semantic.fetch, semantic.replay, semantic.full targets
- ✅ `Dockerfile` - rank-bm25, ibm-watsonx-ai dependencies
- ✅ `configs/integration_flags.json` - alpha=0.6, k=50 parameters

### Documentation (7 comprehensive guides, ~3,100 lines)
- ✅ COMPONENT_2_IMPLEMENTATION_COMPLETE.md (272 lines)
- ✅ COMPONENT_2_INTEGRATION_GUIDE.md (422 lines)
- ✅ COMPONENT_2_FINAL_REPORT.md (477 lines)
- ✅ COMPONENT_2_INTEGRATION_COMPLETE.md (457 lines)
- ✅ COMPONENT_2_E2E_TEST_GUIDE.md (565 lines)
- ✅ COMPONENT_2_FINAL_STATUS.md (458 lines)
- ✅ COMPONENT_2_E2E_EXECUTION_STATUS.md (423 lines)

---

## Manual Execution (Alternative)

If you prefer manual control:

### Step 1: Set Environment
```bash
export WX_API_KEY='your_key'
export WX_PROJECT='your_project'
export SEED=42
export PYTHONHASHSEED=0
```

### Step 2: FETCH Phase (5-15 min)
```bash
export ALLOW_NETWORK=true
make semantic.fetch
```

**Expected Artifacts:**
- `data/index/msft_2023/chunks.parquet`
- `data/index/msft_2023/embeddings.bin`
- `data/index/msft_2023/meta.json`

### Step 3: REPLAY Phase (1-2 min)
```bash
unset ALLOW_NETWORK
export WX_OFFLINE_REPLAY=true
make semantic.replay
```

**Expected Artifacts:**
- `artifacts/matrix/msft_2023/baseline/determinism_report.json` (3 identical hashes)
- `artifacts/matrix/msft_2023/pipeline_validation/demo_topk_vs_evidence.json` (subset_ok: true)
- `artifacts/matrix/msft_2023/pipeline_validation/evidence_audit.json` (all_themes_passed: true)

### Step 4: Validate Gates (30 sec)
```bash
python3 - <<'PY'
import json, glob

# Determinism
for f in glob.glob("artifacts/matrix/*/baseline/determinism_report.json"):
    d = json.load(open(f))
    print(f"Determinism: {'PASS' if d.get('identical') else 'FAIL'}")

# Parity
for f in glob.glob("artifacts/matrix/*/pipeline_validation/demo_topk_vs_evidence.json"):
    d = json.load(open(f))
    print(f"Parity: {'PASS' if d.get('subset_ok') else 'FAIL'}")

# Evidence
for f in glob.glob("artifacts/matrix/*/pipeline_validation/evidence_audit.json"):
    d = json.load(open(f))
    print(f"Evidence: {'PASS' if d.get('all_themes_passed') else 'FAIL'}")
PY
```

---

## Without Credentials

Can't run E2E test, but you can:

### Option 1: Run Unit Tests (Offline)
```bash
cd "C:/projects/Work Projects/ibm-projects/ESG Evaluation/prospecting-engine"
pytest tests/retrieval/test_semantic_wx.py -v --tb=short -m cp
```

**Expected:** 13 tests PASS (all CP-marked, 2 property tests, 4 failure paths)

### Option 2: Review Implementation
```bash
# Core retrieval module (535 LOC)
cat libs/retrieval/semantic_wx.py

# Test suite (422 LOC)
cat tests/retrieval/test_semantic_wx.py

# Integration script (240 LOC)
cat scripts/semantic_fetch_replay.py
```

### Option 3: Review Documentation
All documentation is in the project root:
- `COMPONENT_2_IMPLEMENTATION_COMPLETE.md` - Architecture & algorithms
- `COMPONENT_2_INTEGRATION_GUIDE.md` - Integration procedures
- `COMPONENT_2_E2E_TEST_GUIDE.md` - Complete E2E test procedures
- `COMPONENT_2_E2E_EXECUTION_STATUS.md` - Current execution status

---

## Key Features

### Hybrid Retrieval
- **BM25:** Lexical retrieval (rank-bm25 BM25Okapi)
- **Semantic:** watsonx.ai embeddings (ibm/slate-125m-english-rtrvr)
- **Fusion:** α*BM25 + (1-α)*semantic where α=0.6 (default)

### Determinism
- Fixed seeds: SEED=42, PYTHONHASHSEED=0
- Text canonicalization: text.strip().lower()
- SHA256 deduplication with keep="first"
- Stable sorting: np.argsort(-scores)
- Deterministic timestamps for hashing

### Cache→Replay
- FETCH: Online mode with watsonx.ai API calls (cached)
- REPLAY: Offline mode with 100% cache hits (enforced)
- Environment control: WX_OFFLINE_REPLAY=true/false

### Parity Constraint
- evidence_ids ⊆ fused_topk (validated)
- Ensures all evidence comes from top-K results
- Prevents cherry-picking from outside retrieval set

---

## Troubleshooting

### Issue: "blocked: set WX_API_KEY for watsonx fetch"
**Solution:** Set credentials:
```bash
export WX_API_KEY='your_key'
export WX_PROJECT='your_project'
```

### Issue: "Cache miss in offline replay mode"
**Solution:** Run FETCH before REPLAY:
```bash
export ALLOW_NETWORK=true
make semantic.fetch

unset ALLOW_NETWORK
export WX_OFFLINE_REPLAY=true
make semantic.replay
```

### Issue: Parity gate FAIL (evidence_ids not in topk)
**Solution:** Increase k or adjust alpha:
```bash
# Edit configs/integration_flags.json
{
  "k": 100,        # Increase from 50
  "alpha": 0.5     # More semantic weight (was 0.6)
}
```

### Issue: "No silver data found"
**Solution:** Check silver data exists:
```bash
ls data/silver/org_id=*/year=*
```

If missing, run ingestion/extraction pipeline first.

---

## Success Criteria

✅ **E2E Test PASSED** when ALL of the following are true:

1. **FETCH Phase:**
   - Embeddings built for all documents
   - Index artifacts created (chunks, embeddings, metadata)
   - watsonx.ai cache populated

2. **REPLAY Phase:**
   - All queries execute successfully (offline)
   - Results returned for all documents

3. **Gate Validation:**
   - Determinism: 3× identical hashes ✅
   - Parity: evidence_ids ⊆ topk ✅
   - Evidence: ≥2 quotes from ≥2 pages per theme ✅
   - Cache→Replay: no live watsonx calls in REPLAY ✅

4. **Contracts:**
   - Matrix contract status: "ok"
   - All document contracts status: "ok"

---

## File Locations

**Project Root:**
```
C:/projects/Work Projects/ibm-projects/ESG Evaluation/prospecting-engine/
```

**Implementation:**
- `libs/retrieval/semantic_wx.py`
- `tests/retrieval/test_semantic_wx.py`
- `scripts/semantic_fetch_replay.py`

**Configuration:**
- `configs/integration_flags.json`
- `configs/companies_live.yaml`

**Documentation:**
- `COMPONENT_2_*.md` (7 files in project root)

**Execution Script:**
- `RUN_E2E_WITH_CREDENTIALS.sh`

---

## Next Steps

### Immediate (This Session)
1. ✅ Implementation complete
2. ✅ Integration complete
3. ✅ Documentation complete
4. ⚠️ **BLOCKED:** Obtain watsonx.ai credentials

### Next Session (With Credentials)
1. Set WX_API_KEY and WX_PROJECT
2. Run: `bash RUN_E2E_WITH_CREDENTIALS.sh`
3. Verify all gates PASS
4. Review proof artifacts
5. Expand to additional documents (Unilever, Headlam)

### Future (Component 3)
1. **RD Locator:** watsonx.ai JSON generation for TCFD/SECR detection
2. **Report Editor:** Grounded post-editing with fidelity constraints
3. **Reranking:** Optional watsonx.ai semantic reranking

---

## Summary

**Status:** ✅ **READY FOR E2E EXECUTION** (blocked on credentials)

Component 2 is fully implemented, integrated, and documented. All code (1,197 LOC), tests (422 LOC with CP marks + property tests + failure paths), integration changes (4 files), and documentation (~3,100 lines across 7 guides) are complete.

**To execute:** Set watsonx.ai credentials and run `bash RUN_E2E_WITH_CREDENTIALS.sh`

**Expected duration:** 10-20 minutes

**Expected outcome:** All authenticity gates PASS with reviewer-ready proof artifacts

---

**Quick Start Guide**
**Date:** 2025-10-28
**Agent:** SCA v13.8-MEA
**Component:** Semantic Retrieval with watsonx.ai
**Status:** READY (awaiting credentials)
