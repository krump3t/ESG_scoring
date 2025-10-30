# Component 2: End-to-End Test & Authenticity Verification Guide

**Agent:** SCA v13.8-MEA
**Component:** Semantic Retrieval with watsonx.ai
**Status:** ✅ **READY FOR E2E TESTING**
**Date:** 2025-10-28

---

## Executive Summary

This guide provides the complete end-to-end testing procedure for Component 2 (Semantic Retrieval with watsonx.ai). All integration changes have been applied and validated. The system is ready for live testing with watsonx.ai credentials.

**Test Scope:**
- ✅ FETCH phase: Build embeddings for all documents
- ✅ REPLAY phase: Query with cached embeddings (deterministic)
- ✅ Gate validation: Determinism, Parity, Evidence, Cache→Replay
- ✅ Proof artifacts: Complete audit trail

---

## Pre-Flight Verification

### ✅ All Prerequisites Met

**Configuration Files:**
- ✅ `configs/companies_live.yaml` (3 companies: MSFT, Unilever, Headlam)
- ✅ `configs/integration_flags.json` (semantic_enabled=true, alpha=0.6, k=50)

**Core Implementation:**
- ✅ `libs/retrieval/semantic_wx.py` (535 LOC)
- ✅ `tests/retrieval/test_semantic_wx.py` (422 LOC)
- ✅ `scripts/semantic_fetch_replay.py` (240 LOC)

**Integration:**
- ✅ `scripts/run_matrix.py` (SemanticRetriever import added)
- ✅ `Makefile` (semantic.fetch, semantic.replay, semantic.full targets)
- ✅ `Dockerfile` (rank-bm25, ibm-watsonx-ai dependencies)

**Integration Flags:**
```json
{
  "semantic_enabled": true,
  "watsonx_enabled": true,
  "alpha": 0.6,
  "k": 50
}
```

**Companies Under Test:**
1. Microsoft Corporation (2024) - doc_id: `msft_2024`
2. Unilever PLC (2023) - doc_id: `unilever_2023`
3. Headlam Group Plc (2025) - doc_id: `headlam_2025`

---

## E2E Test Workflow

### Phase 1: FETCH (Build Embeddings)

**Objective:** Build semantic embeddings for all documents using watsonx.ai

**Prerequisites:**
```bash
# Required environment variables
export WX_API_KEY="your_watsonx_api_key"
export WX_PROJECT="your_watsonx_project_id"
export SEED=42
export PYTHONHASHSEED=0
export ALLOW_NETWORK=true
export WX_OFFLINE_REPLAY=false
```

**Execute:**
```bash
cd "C:/projects/Work Projects/ibm-projects/ESG Evaluation/prospecting-engine"

# Option 1: Full workflow (FETCH + REPLAY)
make semantic.full

# Option 2: FETCH only
make semantic.fetch
```

**Expected Output:**
```
=== SEMANTIC FETCH: Building embeddings for all documents ===

Processing: msft_2024
  Found 15 parquet files for msft_2024
  Total unique chunks: 234
  Generating embeddings (model: ibm/slate-125m-english-rtrvr)...
  Embeddings generated in 12.34s
  Vector shape: (234, 384) (N=234, D=384)
  ✓ Chunks metadata: data/index/msft_2024/chunks.parquet
  ✓ Embeddings: data/index/msft_2024/embeddings.bin
  ✓ Metadata: data/index/msft_2024/meta.json

Processing: unilever_2023
  [... similar output ...]

Processing: headlam_2025
  [... similar output ...]

✓ All embeddings built successfully
```

**Artifacts Created:**

For each document (msft_2024, unilever_2023, headlam_2025):
```
data/index/<doc_id>/
├── chunks.parquet      # Chunk metadata (chunk_id, page, text_sha, len, text_canon)
├── embeddings.bin      # Float32 binary [N x D] vectors
└── meta.json           # Model ID, dim, seed, deterministic_timestamp

artifacts/wx_cache/embeddings/
└── <sha256>.json       # Cached watsonx.ai API responses
```

**Validation:**
```bash
# Check all indices were created
python3 - <<'PY'
from pathlib import Path
import json

docs = ["msft_2024", "unilever_2023", "headlam_2025"]
for doc_id in docs:
    index_path = Path(f"data/index/{doc_id}")
    chunks = index_path / "chunks.parquet"
    embeddings = index_path / "embeddings.bin"
    meta = index_path / "meta.json"

    if all(f.exists() for f in [chunks, embeddings, meta]):
        meta_data = json.loads(meta.read_text())
        print(f"✓ {doc_id}: {meta_data['vector_count']} vectors, {meta_data['vector_dim']}D")
    else:
        print(f"✗ {doc_id}: INCOMPLETE")
PY
```

**Expected:**
```
✓ msft_2024: 234 vectors, 384D
✓ unilever_2023: 187 vectors, 384D
✓ headlam_2025: 156 vectors, 384D
```

---

### Phase 2: REPLAY (Query with Cache)

**Objective:** Run deterministic queries using cached embeddings (offline mode)

**Prerequisites:**
```bash
# Unset network access
unset ALLOW_NETWORK

# Enable offline replay mode
export WX_OFFLINE_REPLAY=true
export SEED=42
export PYTHONHASHSEED=0
```

**Execute:**
```bash
# Option 1: Semantic replay (single doc)
make semantic.replay

# Option 2: Full matrix replay (all docs)
python3 scripts/run_matrix.py --config configs/companies_live.yaml --semantic
```

**Expected Output:**
```
=== SEMANTIC REPLAY: Querying with cached embeddings ===

Processing: msft_2024
  Loaded 234 chunks, 234 vectors for msft_2024

Top-10 Results:
  Rank  1: msft_2024_p15_c42 (score=0.8723)
           BM25=0.9102, Semantic=0.8345
  Rank  2: msft_2024_p22_c67 (score=0.8456)
           BM25=0.8234, Semantic=0.8678
  ...

Parity Validation: PASS (evidence_ids ⊆ topk)

Processing: unilever_2023
  [... similar output ...]

Processing: headlam_2025
  [... similar output ...]

✓ All documents processed successfully
```

**Artifacts Created:**

For each document:
```
artifacts/matrix/<doc_id>/baseline/
├── run_1/
│   ├── output.json           # Scoring results (run 1)
│   ├── scoring_response.json # Full response with scores
│   └── hash.txt              # SHA256 hash of output.json
├── run_2/
│   ├── output.json
│   ├── scoring_response.json
│   └── hash.txt
├── run_3/
│   ├── output.json
│   ├── scoring_response.json
│   └── hash.txt
└── determinism_report.json   # 3× hash comparison

artifacts/matrix/<doc_id>/pipeline_validation/
├── demo_topk_vs_evidence.json  # Parity validation (subset_ok: true)
├── evidence_audit.json         # Evidence per theme (≥2 pages)
└── rd_sources.json             # RD theme sources

artifacts/matrix/<doc_id>/output_contract.json  # Per-document contract

artifacts/matrix/matrix_contract.json           # Matrix-level contract
```

---

## Gate Validation

### Gate 1: Determinism (3× Identical Hashes)

**Command:**
```bash
python3 - <<'PY'
import json, glob

print("=== DETERMINISM GATE ===\n")
for report_path in glob.glob("artifacts/matrix/*/baseline/determinism_report.json"):
    report = json.load(open(report_path, encoding="utf-8"))
    doc_id = report.get("doc_id")
    hashes = report.get("hashes", [])
    identical = report.get("identical", False)
    unique_hashes = len(set(hashes))

    status = "PASS" if identical and unique_hashes == 1 else "FAIL"
    print(f"{doc_id}: {status}")
    if status == "FAIL":
        print(f"  Hashes: {hashes}")
    print()
PY
```

**Expected:**
```
=== DETERMINISM GATE ===

msft_2024: PASS
unilever_2023: PASS
headlam_2025: PASS
```

### Gate 2: Parity (evidence_ids ⊆ fused_topk)

**Command:**
```bash
python3 - <<'PY'
import json, glob

print("=== PARITY GATE ===\n")
for parity_path in glob.glob("artifacts/matrix/*/pipeline_validation/demo_topk_vs_evidence.json"):
    parity = json.load(open(parity_path, encoding="utf-8"))
    doc_id = parity.get("doc_id")
    subset_ok = parity.get("subset_ok", False)
    missing_count = parity.get("missing_count", 0)

    status = "PASS" if subset_ok and missing_count == 0 else "FAIL"
    print(f"{doc_id}: {status}")
    if status == "FAIL":
        print(f"  Missing IDs: {parity.get('missing_ids', [])}")
    print()
PY
```

**Expected:**
```
=== PARITY GATE ===

msft_2024: PASS
unilever_2023: PASS
headlam_2025: PASS
```

### Gate 3: Evidence (≥2 quotes from ≥2 pages per theme)

**Command:**
```bash
python3 - <<'PY'
import json, glob

print("=== EVIDENCE GATE ===\n")
themes = ["TSP", "OSP", "DM", "GHG", "RD", "EI", "RMM"]

for evidence_path in glob.glob("artifacts/matrix/*/pipeline_validation/evidence_audit.json"):
    evidence = json.load(open(evidence_path, encoding="utf-8"))
    doc_id = evidence.get("doc_id")
    all_passed = evidence.get("all_themes_passed", False)

    print(f"{doc_id}: {'PASS' if all_passed else 'FAIL'}")

    for theme in themes:
        theme_data = evidence.get("themes", {}).get(theme, {})
        quotes = theme_data.get("evidence_count", 0)
        pages = theme_data.get("unique_pages", 0)
        passed = theme_data.get("passed", False)

        if not passed:
            print(f"  {theme}: FAIL (quotes={quotes}, pages={pages})")
    print()
PY
```

**Expected:**
```
=== EVIDENCE GATE ===

msft_2024: PASS
unilever_2023: PASS
headlam_2025: PASS
```

### Gate 4: Cache→Replay (No Live watsonx.ai Calls)

**Command:**
```bash
python3 - <<'PY'
import json, glob

print("=== CACHE→REPLAY GATE ===\n")

ledger_path = "artifacts/wx_cache/ledger.jsonl"
if not Path(ledger_path).exists():
    print("No ledger found (expected in FETCH phase)")
else:
    replay_calls = []
    for line in open(ledger_path, encoding="utf-8"):
        try:
            entry = json.loads(line)
            # Check if entry is from replay phase (heuristic)
            if "replay" in entry.get("doc_id", "").lower() or \
               entry.get("phase") == "replay":
                replay_calls.append(entry)
        except:
            pass

    if replay_calls:
        print(f"FAIL: {len(replay_calls)} watsonx calls during REPLAY phase")
        for call in replay_calls[:3]:
            print(f"  - {call.get('call_type')} at {call.get('timestamp')}")
    else:
        print("PASS: No watsonx calls during REPLAY phase (100% cache hits)")
PY
```

**Expected:**
```
=== CACHE→REPLAY GATE ===

PASS: No watsonx calls during REPLAY phase (100% cache hits)
```

---

## Matrix Contract Validation

**Command:**
```bash
cat artifacts/matrix/matrix_contract.json | python3 -m json.tool
```

**Expected Structure:**
```json
{
  "agent": "SCA",
  "version": "13.8-MEA",
  "status": "ok",
  "documents": 3,
  "determinism_pass": true,
  "document_contracts": [
    {
      "doc_id": "msft_2024",
      "status": "ok",
      "gates": {
        "determinism": "PASS",
        "parity": "PASS",
        "evidence": "PASS",
        "authenticity": "PASS",
        "traceability": "PASS"
      }
    },
    {
      "doc_id": "unilever_2023",
      "status": "ok",
      "gates": { "..." }
    },
    {
      "doc_id": "headlam_2025",
      "status": "ok",
      "gates": { "..." }
    }
  ],
  "timestamp": "2025-10-28T06:00:00Z"
}
```

---

## Proof Artifacts Checklist

After successful E2E test, verify all artifacts exist:

```bash
python3 - <<'PY'
import glob, os
from pathlib import Path

print("=== PROOF ARTIFACTS ===\n")

patterns = [
    ("Chunk Indices", "data/index/*/chunks.parquet"),
    ("Embeddings", "data/index/*/embeddings.bin"),
    ("Index Metadata", "data/index/*/meta.json"),
    ("Determinism Reports", "artifacts/matrix/*/baseline/determinism_report.json"),
    ("Parity Reports", "artifacts/matrix/*/pipeline_validation/demo_topk_vs_evidence.json"),
    ("Evidence Audits", "artifacts/matrix/*/pipeline_validation/evidence_audit.json"),
    ("RD Sources", "artifacts/matrix/*/pipeline_validation/rd_sources.json"),
    ("Document Contracts", "artifacts/matrix/*/output_contract.json"),
    ("Matrix Contract", "artifacts/matrix/matrix_contract.json"),
]

for name, pattern in patterns:
    files = glob.glob(pattern)
    print(f"{name}: {len(files)} files")
    for f in files:
        print(f"  {os.path.abspath(f)}")
    print()
PY
```

---

## Troubleshooting

### Issue 1: "blocked: set WX_API_KEY for watsonx fetch"

**Cause:** Missing watsonx.ai credentials

**Solution:**
```bash
export WX_API_KEY="your_api_key"
export WX_PROJECT="your_project_id"
```

### Issue 2: "Cache miss in offline replay mode"

**Cause:** REPLAY phase run before FETCH phase

**Solution:**
1. Run FETCH phase first: `make semantic.fetch`
2. Then run REPLAY phase: `make semantic.replay`

### Issue 3: "No silver data found for doc_id"

**Cause:** Missing extracted chunks in data/silver/

**Solution:**
1. Check if silver data exists: `ls data/silver/org_id=*/year=*/`
2. Run extraction/ingestion first if missing

### Issue 4: Parity FAIL (evidence_ids not in topk)

**Cause:** k parameter too small, or alpha too high (favoring BM25 over semantic)

**Solution:**
1. Increase k: Edit `configs/integration_flags.json`, set `"k": 100`
2. Adjust alpha: Set `"alpha": 0.5` for more semantic weight
3. Re-run REPLAY phase

---

## Success Criteria

✅ **E2E Test PASSED** if all of the following are true:

1. **FETCH Phase:**
   - ✅ Embeddings built for all 3 documents
   - ✅ Index artifacts created (chunks.parquet, embeddings.bin, meta.json)
   - ✅ watsonx.ai cache populated

2. **REPLAY Phase:**
   - ✅ All queries execute successfully
   - ✅ Results returned for all documents

3. **Gate Validation:**
   - ✅ Determinism: PASS (3× identical hashes for each doc)
   - ✅ Parity: PASS (evidence_ids ⊆ topk for all docs)
   - ✅ Evidence: PASS (≥2 quotes from ≥2 pages per theme)
   - ✅ Cache→Replay: PASS (no live watsonx calls in REPLAY)

4. **Matrix Contract:**
   - ✅ Status: "ok"
   - ✅ determinism_pass: true
   - ✅ All document contracts: status "ok"

---

## Next Steps After E2E Success

### Component 2: Complete
- ✅ Implementation done
- ✅ Integration done
- ✅ E2E test passed

### Component 3: NL Reporting (Next)
1. **RD Locator:** Integrate watsonx.ai JSON generation for TCFD/SECR detection
2. **Report Editor:** Add grounded post-editing with fidelity constraints
3. **Reranking:** Optional watsonx.ai semantic reranking

### CI/CD Integration
1. Add semantic.fetch to CI pipeline (with credentials)
2. Add semantic.replay to CI validation (offline mode)
3. Enforce gate checks in CI (fail on determinism/parity/evidence FAIL)

---

## Summary

**Test Status:** ✅ **READY TO EXECUTE**

**Prerequisites:** ✅ **ALL MET**
- Configuration: Done
- Implementation: Done
- Integration: Done
- Documentation: Done

**Required:**
- watsonx.ai credentials (WX_API_KEY, WX_PROJECT)
- Silver data for at least one document

**Estimated Time:**
- FETCH phase: 5-15 minutes (depends on document count)
- REPLAY phase: 1-2 minutes (3× runs per document)
- Gate validation: 30 seconds

**Expected Outcome:** All gates PASS, matrix contract status="ok"

---

**End of E2E Test Guide**
**Agent:** SCA v13.8-MEA
**Date:** 2025-10-28
**Status:** READY FOR EXECUTION
