# Task 005: Retrieval Integration - Hypothesis

**Task ID:** 005-retrieval-integration
**Date:** 2025-11-19
**Protocol:** SCA v13.8-MEA
**Depends On:** Task 004 (Extraction Integration - SUCCESS)

---

## Hypothesis

**Primary Claim:**
The local Vector Store (in-memory stub) can ingest Apple 10-K text chunks from Task 004 and retrieve relevant evidence for ESG-related queries using semantic similarity search.

**Specific Predictions:**

1. **Data Ingestion:**
   - VectorStore can accept extracted chunks from Task 004 (129 chunks)
   - Chunks are indexed with vector embeddings (or text-based matching)
   - Storage is in-memory (no external database required)

2. **Retrieval Functionality:**
   - VectorStore supports similarity search queries
   - Query: "climate risk" returns relevant chunks
   - Results ranked by relevance/similarity
   - Top-k retrieval works (k=3, k=5)

3. **Result Quality:**
   - Retrieved chunks contain query-relevant keywords
   - Climate-related chunks ranked higher than non-climate chunks
   - Section context preserved in results

4. **Metadata Filtering:**
   - Can filter by source metadata (company, year, provider)
   - Can access chunk provenance (SHA256, source URL)
   - Timestamp and confidence fields accessible

---

## Success Criteria

### Must Pass (Blocking)

1. ✅ **Data Loading**
   - Load 129 chunks from `tasks/004-extraction-integration/artifacts/apple_2024_findings.json`
   - Parse JSON without errors
   - Extract text and metadata fields

2. ✅ **Vector Store Ingestion**
   - Initialize VectorStore (local stub)
   - Ingest all 129 chunks (or 50 sample chunks if full set too large)
   - No errors during ingestion
   - Verify documents stored (count check)

3. ✅ **Similarity Search**
   - Query: "climate risk" returns ≥ 1 result
   - Query: "environmental regulations" returns ≥ 1 result
   - Results contain text from Apple 10-K chunks
   - No crashes or empty results for valid queries

4. ✅ **Top-K Retrieval**
   - `search(query, k=3)` returns exactly 3 results (or fewer if < 3 match)
   - Results ordered by relevance/similarity
   - Each result includes text and metadata

### Should Pass (Quality)

5. ⚠️ **Relevance Quality**
   - Query "climate" returns chunks with "climate" keyword
   - Query "emissions" returns chunks with "emissions" keyword
   - Irrelevant chunks not in top-3 results

6. ⚠️ **Metadata Preservation**
   - Retrieved chunks include source_url, provider, doc_hash
   - Chunk IDs traceable back to Task 004 artifact
   - Company and year information available

7. ⚠️ **Performance**
   - Ingestion: < 10 seconds for 50-129 chunks
   - Search: < 1 second per query
   - Memory usage: < 100 MB

---

## Test Data

**Source:** Task 004 Extraction Artifact
- **Path:** `tasks/004-extraction-integration/artifacts/apple_2024_findings.json`
- **Chunks Available:** 50 sample chunks (from 129 total)
- **Total Text:** 256,563 characters
- **ESG Keywords Present:** climate, environmental, emissions, risk
- **Source Document:** Apple Inc. 2024 10-K (SHA256: 24a830a0f1256e37...)

**Sample Chunk Structure:**
```json
{
  "chunk_id": "chunk_0000",
  "text": "...",
  "text_length": 2000,
  "page": 1,
  "section": null,
  "source_url": "https://www.sec.gov/...",
  "provider": "SECEdgarProvider",
  "doc_hash": "24a830a0f1256e37",
  "confidence": 1.0,
  "timestamp": "2025-11-19T19:21:49.090779Z"
}
```

---

## Test Queries

**Primary Queries (Must Work):**
1. `"climate risk"` - Should return Item 1A risk factor chunks
2. `"environmental regulations"` - Should return compliance/regulatory chunks
3. `"carbon emissions"` - Should return emissions-related disclosures

**Secondary Queries (Nice to Have):**
4. `"supply chain risks"` - Should return operational risk chunks
5. `"renewable energy"` - May or may not return results (depends on content)

**Expected Results:**
- Each query returns 1-5 relevant chunks
- Chunks ranked by keyword presence / text similarity
- Metadata includes provenance (URL, hash, provider)

---

## Risks & Mitigations

### Risk 1: Vector Embedding Missing
**Issue:** Local VectorStore stub may not have embedding generation
**Likelihood:** High
**Mitigation:**
- Use text-based similarity (keyword matching, TF-IDF)
- Simple cosine similarity on term frequencies
- Defer true vector embeddings to future task (with actual embedding model)

### Risk 2: Interface Mismatch
**Issue:** VectorStore may not have `add_documents()` or `similarity_search()` methods
**Likelihood:** High (stub has `upsert()` and `knn()`)
**Mitigation:**
- Adapt verification script to use actual VectorStore API
- Create wrapper methods if needed
- Document interface translation in HANDOFF.md

### Risk 3: Chunk Format Incompatibility
**Issue:** VectorStore expects different data structure than Task 004 output
**Likelihood:** Medium
**Mitigation:**
- Parse Task 004 JSON and transform to VectorStore format
- Use chunk text as vector (character-level or word-level)
- Store metadata as separate field

### Risk 4: Empty Search Results
**Issue:** Query returns no results due to exact keyword matching
**Likelihood:** Low (ESG keywords confirmed in Task 004)
**Mitigation:**
- Use flexible matching (lowercase, stemming, partial match)
- Ensure query terms align with extracted content
- Test with known-present keywords first

---

## Exclusions

**Out of Scope for Task 005:**

1. **Production Vector Database**
   - No AstraDB integration
   - No external embedding service (OpenAI, Cohere, etc.)
   - Local in-memory only

2. **Advanced Retrieval**
   - No reranking
   - No hybrid search (vector + keyword)
   - No query expansion

3. **Multi-Document Search**
   - Only Apple 10-K chunks
   - No cross-company retrieval
   - No index merging

4. **UI/API Layer**
   - No web interface
   - No REST API
   - Script-based verification only

5. **Performance Optimization**
   - No indexing strategies
   - No caching
   - No distributed search

---

## Critical Path

**CP Files for Task 005:**
- `apps/index/vector_store.py` - Local vector store stub (30 lines)
- `apps/index/retriever.py` - Retrieval interface (if exists)
- `libs/retrieval/*` - Retrieval utilities (if exist)

**Non-CP:**
- Task 004 artifact (static test data)
- Logging, configuration, utilities

---

## Power Analysis

**Sample Size:** N=50 chunks (sample from Task 004)
**Query Count:** 3-5 test queries
**Effect Size:** Large (retrieval works or doesn't - binary)
**Confidence:** High (deterministic search, no randomness in local stub)

**Justification for N=50:**
- Proof-of-concept phase
- Local stub has no scaling requirements
- Sufficient to validate retrieval mechanics
- Full 129 chunks can be tested if needed

---

## Verification Plan

### Phase 2: Red (Expected Failure)
1. Write `verify_retrieval.py` script
2. Attempt to load Task 004 chunks
3. Attempt to ingest into VectorStore
4. Attempt similarity search
5. Document failure mode:
   - Method not found? (add_documents vs upsert)
   - Format mismatch? (Document vs dict)
   - Embedding missing? (vector generation)

### Phase 3: Green (Fix & Pass)
1. Analyze interface (upsert, knn, metadata structure)
2. Adapt verification script to match VectorStore API
3. Generate mock vectors if needed (character count, keyword presence)
4. Re-run verification
5. Iterate until all "Must Pass" criteria met

### Phase 4: Validation
1. Run verify_retrieval.py (Must PASS)
2. Execute specific query: "What are the risk factors related to climate change?"
3. Save top-5 results to `artifacts/retrieval_results.json`
4. Verify results contain "climate" or "risk" keywords
5. Document in HANDOFF.md

---

## Compliance

**SCA Protocol Gates:**
- ✅ Context: This hypothesis.md + evidence.json + cp_paths.json
- ✅ Authenticity: Real Apple 10-K chunks from Task 004 (verified in Task 004)
- ✅ Determinism: Fixed test data, deterministic search (no ML randomness)
- ✅ Traceability: All steps documented in scripts and HANDOFF.md

**Task Dependencies:**
- ✅ Task 004: Extraction Integration (COMPLETE - 129 chunks extracted)
- ✅ Task 000: Forensic Audit (VectorStore confirmed as in-memory stub)

---

**Hypothesis Generated:** 2025-11-19
**Ready for Phase 2:** TDD Harness (Red)
