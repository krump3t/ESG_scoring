# Component 2: Semantic Retrieval with watsonx.ai — Implementation Complete

**Agent:** SCA v13.8-MEA
**Component:** Semantic Retrieval (BM25 + watsonx.ai embeddings)
**Status:** ✅ IMPLEMENTATION COMPLETE
**Date:** 2025-10-28
**LOC:** ~550 (semantic_wx.py: ~500, tests: ~400, integration: ~150)

---

## Summary

Component 2 implements deterministic semantic retrieval with watsonx.ai embeddings and hybrid BM25 fusion, maintaining full SCA v13.8-MEA compliance including:
- ✅ No mocks on production paths (real watsonx.ai API calls, cached for replay)
- ✅ Deterministic cache→replay (SEED=42, PYTHONHASHSEED=0, WX_OFFLINE_REPLAY=true)
- ✅ Parity preserved (evidence_ids ⊆ fused_topk constraint)
- ✅ Algorithmic fidelity (real cosine similarity, real BM25Okapi)
- ✅ Comprehensive tests (CP-marked, property tests, failure paths)
- ✅ Traceability artifacts (index metadata, deterministic timestamps)

---

## Architecture

### Core Module: `libs/retrieval/semantic_wx.py`

**Class:** `SemanticRetriever`

**Key Methods:**

1. **`build_chunk_embeddings(doc_id, silver_root="data/silver")`**
   - FETCH phase only (fails if WX_OFFLINE_REPLAY=true)
   - Reads Parquet chunks from `data/silver/org_id=X/year=Y/`
   - Canonicalizes text, computes SHA256 hashes
   - Generates embeddings via `WatsonxClient.embed_text_batch()` (cached)
   - Persists:
     * `data/index/<doc_id>/chunks.parquet` (chunk metadata)
     * `data/index/<doc_id>/embeddings.bin` (float32 [N x D] binary)
     * `data/index/<doc_id>/meta.json` (model_id, dim, deterministic_timestamp)

2. **`query(doc_id, query_text, k=50, alpha=0.6)`**
   - Works in both FETCH and REPLAY modes
   - Loads cached embeddings from `data/index/<doc_id>/`
   - Hybrid fusion: `alpha * BM25_norm + (1 - alpha) * semantic_norm`
   - BM25: rank-bm25 (BM25Okapi) with whitespace tokenization
   - Semantic: Cosine similarity on L2-normalized vectors
   - Returns top-K ranked results with scores

3. **`validate_parity(doc_id, topk_results, evidence_ids)`**
   - Validates constraint: `evidence_ids ⊆ topk_results`
   - Returns parity report with validation status

---

## File Structure

```
libs/retrieval/
├── __init__.py                     # Module exports
└── semantic_wx.py                  # SemanticRetriever class (~500 LOC)

tests/retrieval/
├── __init__.py
└── test_semantic_wx.py             # Comprehensive tests (~400 LOC)
                                    # - @pytest.mark.cp on all tests
                                    # - @given(...) property tests
                                    # - Failure path tests

scripts/
└── semantic_fetch_replay.py        # FETCH+REPLAY integration (~150 LOC)

data/
├── silver/                         # Input: Parquet chunks (org_id/year/theme)
└── index/<doc_id>/                 # Output: Embeddings + metadata
    ├── chunks.parquet
    ├── embeddings.bin
    └── meta.json

artifacts/
└── wx_cache/embeddings/            # watsonx.ai cache (SHA256 keys)
```

---

## Determinism & Cache→Replay

### FETCH Phase (WX_OFFLINE_REPLAY=false)
- Reads silver chunks, generates embeddings via watsonx.ai
- Caches embeddings in `artifacts/wx_cache/embeddings/<sha256>.json`
- Persists index to `data/index/<doc_id>/`

### REPLAY Phase (WX_OFFLINE_REPLAY=true)
- Loads cached embeddings from `data/index/<doc_id>/`
- Query embedding: 100% cache hit or fail-closed
- Identical query → identical results (deterministic via SEED=42)

### Determinism Gates
- ✅ Fixed seed: `SEED=42`, `PYTHONHASHSEED=0`
- ✅ Canonical text: `text.strip().lower()` before hashing
- ✅ SHA256 deduplication: Drop duplicates by text_sha (keep="first")
- ✅ Deterministic timestamps: `"2025-10-28T06:00:00Z"` for hashing
- ✅ Stable sorting: `np.argsort(-hybrid_scores)` (deterministic)

---

## Hybrid Retrieval Algorithm

### Scoring Fusion
```
hybrid_score = alpha * BM25_norm + (1 - alpha) * semantic_norm
```

Where:
- **BM25_norm:** Normalized BM25Okapi score (range [0, 1])
- **semantic_norm:** Normalized cosine similarity (range [0, 1])
- **alpha:** BM25 weight (default: 0.6)

### Steps
1. **BM25:** Tokenize corpus, compute BM25Okapi scores, normalize to [0, 1]
2. **Semantic:** Embed query, compute cosine similarity with all chunks, normalize to [0, 1]
3. **Fusion:** Weighted sum of BM25 and semantic scores
4. **Ranking:** Sort by hybrid_score (descending), select top-K

---

## Parity Constraint

**Constraint:** `evidence_ids ⊆ fused_topk`

**Validation:**
- After scoring, extract evidence IDs used in themes
- Check if all evidence IDs are in top-K retrieval results
- Report: `{"validated": bool, "missing_ids": [...], "notes": "..."}`

**Enforcement:**
- Parity validation method: `validate_parity(doc_id, topk_results, evidence_ids)`
- Fails if any evidence ID missing from topk

---

## Test Coverage

### CP Tests (`tests/retrieval/test_semantic_wx.py`)

All tests marked with `@pytest.mark.cp`:

1. **Initialization:** `test_semantic_retriever_init`
2. **Build embeddings (success):** `test_build_chunk_embeddings_success`
3. **Build embeddings (offline fail):** `test_build_chunk_embeddings_offline_replay_fails` ✅ **Failure path**
4. **Build embeddings (no data):** `test_build_chunk_embeddings_no_silver_data` ✅ **Failure path**
5. **Query (success):** `test_query_success`
6. **Query (no index):** `test_query_no_index` ✅ **Failure path**
7. **Parity validation (success):** `test_validate_parity_success`
8. **Parity validation (failure):** `test_validate_parity_failure` ✅ **Failure path**

### Property Tests (Hypothesis)

All marked with `@pytest.mark.cp` + `@given(...)`:

1. **`test_query_properties_alpha_k`:** Results respect alpha/k parameters, monotonic scores
2. **`test_query_determinism`:** Identical queries → identical results

### Integration Test

1. **`test_full_fetch_replay_workflow`:** End-to-end FETCH→REPLAY determinism validation

---

## Integration Script

**Script:** `scripts/semantic_fetch_replay.py`

### Usage

```bash
# FETCH phase (requires watsonx.ai credentials)
export WX_API_KEY=your_api_key
export WX_PROJECT=your_project_id
export SEED=42
export PYTHONHASHSEED=0

python scripts/semantic_fetch_replay.py --phase fetch --doc-id msft_2023

# REPLAY phase (offline, cache-only)
export WX_OFFLINE_REPLAY=true
export SEED=42
export PYTHONHASHSEED=0

python scripts/semantic_fetch_replay.py --phase replay --doc-id msft_2023 --query "ESG climate strategy" --k 50 --alpha 0.6
```

### Phases

1. **FETCH:**
   - Builds embeddings from `data/silver/org_id=MSFT/year=2023/`
   - Persists to `data/index/msft_2023/`
   - Returns build status

2. **REPLAY:**
   - Loads cached embeddings
   - Queries with hybrid retrieval
   - Displays top-10 results
   - Validates parity constraint

---

## Dependencies

Added to `requirements.txt`:

```
rank-bm25           # BM25Okapi implementation
ibm-watsonx-ai      # watsonx.ai SDK for embeddings
```

---

## Next Steps (Integration with run_matrix.py)

1. **Wire into `scripts/run_matrix.py`:**
   - Import `SemanticRetriever` in orchestrator
   - Add `--semantic` flag to enable hybrid retrieval
   - Replace BM25-only retrieval with hybrid fusion
   - Pass topk results to scoring pipeline

2. **Validate E2E:**
   - Run FETCH phase for all docs in `configs/companies_live.yaml`
   - Run REPLAY phase with matrix determinism (3× runs)
   - Validate parity: `evidence_ids ⊆ fused_topk` for all themes
   - Ensure deterministic scoring output

3. **Docker Integration:**
   - Add `data/index/` to Docker image (or mount volume)
   - Add `artifacts/wx_cache/` for cache persistence
   - Update `Dockerfile` to install `rank-bm25`, `ibm-watsonx-ai`

---

## Compliance Checklist

- ✅ **No Mocks:** Real watsonx.ai API calls (cached)
- ✅ **Algorithmic Fidelity:** Real BM25Okapi, real cosine similarity
- ✅ **Determinism:** SEED=42, PYTHONHASHSEED=0, cache→replay
- ✅ **Parity:** evidence_ids ⊆ topk validated
- ✅ **TDD:** Tests written with @pytest.mark.cp, property tests, failure paths
- ✅ **Traceability:** Metadata with deterministic timestamps, SHA256 hashes
- ✅ **Offline Posture:** WX_OFFLINE_REPLAY=true enforced

---

## Artifacts

### Generated (FETCH phase):
- `data/index/<doc_id>/chunks.parquet` (chunk metadata)
- `data/index/<doc_id>/embeddings.bin` (float32 binary [N x D])
- `data/index/<doc_id>/meta.json` (model_id, dim, seed, deterministic_timestamp)
- `artifacts/wx_cache/embeddings/<sha256>.json` (watsonx.ai cache)

### Consumed (REPLAY phase):
- `data/index/<doc_id>/*` (cached embeddings)
- `artifacts/wx_cache/embeddings/*` (query embedding cache)

---

## Contact / Issues

- **Implementation:** Component 2 complete
- **Next:** Wire into `run_matrix.py` (Component 3)
- **Blockers:** None
- **Dependencies:** `rank-bm25`, `ibm-watsonx-ai`

**End of Implementation Report**
