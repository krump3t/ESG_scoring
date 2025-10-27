# Phase 2: watsonx.ai Integration - Hypothesis (SCA v13.8)

**Task ID**: 017-watsonx-integration-phase2
**Date**: 2025-10-24
**Protocol**: SCA v13.8-MEA
**Status**: PLANNING → EXECUTION

---

## Executive Summary

Phase 2 integrates real IBM watsonx.ai APIs (Granite LLM + Slate embeddings) with authentic ESG document processing. Real documents ingested → Real embeddings generated → Real vector storage → Real RAG pipeline.

---

## Success Criteria (SC6-SC10)

### SC6: Real Embeddings Generated (384-dimensional Slate)
**Claim**: Slate 125m embeddings API generates authentic 384-dimensional vectors

**Metrics**:
- Embedding dimensionality: exactly 384
- Batch processing: 10+ documents per request
- Latency: <5 seconds per document
- Quality: Cosine similarity validates semantic clustering

**Test**: `test_slate_embeddings_dimensionality()`, `test_batch_embeddings_latency()`

---

### SC7: Granite LLM Inference Functional
**Claim**: Granite 3.0-8B-Instruct generates coherent ESG analysis

**Metrics**:
- Response length: 100-500 tokens
- Quality: Semantic coherence (no hallucinations detected)
- Latency: <10 seconds per query
- Consistency: Same prompt → same semantic content

**Test**: `test_granite_inference_coherence()`, `test_granite_latency_threshold()`

---

### SC8: Batch Document Processing (Real ESG Reports)
**Claim**: Process 10+ real ESG documents through full pipeline

**Metrics**:
- Documents processed: minimum 10
- Format: PDF/text extracted
- Success rate: 100% completion
- Storage: All metadata captured

**Test**: `test_ingest_esg_documents_batch()`, `test_document_extraction_quality()`

---

### SC9: Vector Storage in AstraDB
**Claim**: Embeddings stored and queryable in AstraDB

**Metrics**:
- Collection: esg_documents (created)
- Records: 10+ embeddings + metadata
- Query latency: <500ms similarity search
- Integrity: SHA256 verification

**Test**: `test_astradb_upsert_vectors()`, `test_astradb_similarity_search()`

---

### SC10: RAG Pipeline End-to-End
**Claim**: Query → Embedding → ANN Search → LLM Context → Response

**Metrics**:
- Query processing: <20 seconds total
- Retrieval: Top-5 relevant documents
- Context: Concatenated with prompt
- Response: LLM generates analysis from context

**Test**: `test_rag_pipeline_e2e()`, `test_retrieval_augmented_generation_quality()`

---

## Critical Path Files (7 files)

1. `libs/llm/watsonx_client.py` - Granite LLM interface
2. `libs/embedding/watsonx_embedder.py` - Slate embeddings
3. `libs/storage/astradb_vector.py` - Vector storage operations
4. `scripts/ingest_esg_documents.py` - Real document ingestion
5. `scripts/generate_esg_analysis.py` - RAG pipeline orchestration
6. `tests/integration/test_watsonx_integration.py` - 20+ integration tests
7. `.env.production` updates - watsonx.ai rate limiting config

---

## Power Analysis

**Sample Size**: 10 ESG documents
**Embedding Dimension**: 384
**Batch Size**: 5 documents
**CI**: 95%
**Statistical Tests**: Cosine similarity distributions, KS test for embedding quality

---

## Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|-----------|
| API Rate Limiting | HIGH | Implement exponential backoff, queue management |
| Token Context Limits | MEDIUM | Truncate context window, top-K retrieval optimization |
| Embedding Quality | MEDIUM | Validate cosine similarities, semantic coherence testing |
| AstraDB Connection | MEDIUM | Connection pooling, health checks per SC1 |
| Document Extraction | MEDIUM | PDF parsing fallback, manual text validation |

---

## Exclusions & Out-of-Scope

- Fine-tuning Granite/Slate models (use pre-trained only)
- Custom vector search algorithms (use AstraDB SAI)
- LLM prompt engineering optimization (baseline prompts only)
- Multi-turn conversation history (single-turn RAG)

---

## Test Markers (TDD Guard)

- `@pytest.mark.cp` - 20+ critical path tests
- `@pytest.mark.cloud` - 15+ tests requiring watsonx.ai API
- `@pytest.mark.integration` - All 20+ tests
- `@pytest.mark.property` - 3+ property-based tests (@given)
- `@pytest.mark.failure_path` - 5+ exception handling tests
- `@pytest.mark.slow` - Real API calls (5-15 seconds each)

---

## Authenticity Mandate (SCA v13.8)

✓ Real IBM watsonx.ai API calls (not mocked)
✓ Real Slate embeddings (384-dim output)
✓ Real Granite LLM inference
✓ Real ESG documents (5+ actual reports)
✓ Real AstraDB vector storage
✓ Real similarity search (ANN)
✗ NO MOCKS, STUBS, OR FABRICATED DATA

---

## Success Threshold

**PASS**: All SC6-SC10 validated with authentic fixtures, SCA validator "ok" status

**FAIL THRESHOLD**: Any SC not validated or gate failure on 3rd MEA iteration

---

## Next Phase (Phase 3)

AstraDB Vector Store optimization:
- SAI tuning for similarity search
- Metadata filtering
- Batch vector operations
- Collection lifecycle management
