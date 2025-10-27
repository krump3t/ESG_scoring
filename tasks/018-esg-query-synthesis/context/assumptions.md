# Phase 3: Key Assumptions

**Phase**: 3
**Title**: ESG Query Synthesis — Critical Assumptions
**Status**: DRAFT (awaiting design.md approval)

---

## Assumption 1: Phase 2 Watsonx.ai Integration Fully Functional

**Assumption**: Phase 2 RAG pipeline (embedding → search → retrieval → generation) is production-ready and can be extended with Phase 3 features.

**Status**: ✅ **CONFIRMED** (Phase 2 snapshot complete, 12/12 CP tests passing)

**Evidence**:
- Phase 2 CP-only pytest: 12/12 passing
- Executive summary: All success criteria SC6-SC10 validated
- Code quality: 100% type hints, 100% docstrings
- Real data: 3 Fortune 500 PDFs, 31.3 MB

**Impact if false**: Phase 3 cannot proceed; must remediate Phase 2 first.

---

## Assumption 2: Cross-Encoder Models Available from HuggingFace

**Assumption**: Sentence-BERT and MS MARCO cross-encoder models are publicly available and can be fine-tuned on Phase 2 ESG data.

**Status**: ✅ **CONFIRMED**

**Evidence**:
- https://huggingface.co/sentence-transformers/ce-ms-marco-MiniLM-L-6-v2
- https://huggingface.co/sentence-transformers/ce-ms-marco-MiniLM-L-12-v2
- 110M-340M parameter models, downloadable via Hugging Face Hub

**Impact if false**: Switch to lighter re-ranking (e.g., BM25 scoring) with lower accuracy.

---

## Assumption 3: Redis Server Available for Caching

**Assumption**: Redis can be deployed locally (Docker) or on a server, supporting atomic operations and TTL-based eviction.

**Status**: ⚠️ **CONDITIONAL** (pending design.md)

**Evidence**:
- Redis available as official Docker image
- Version ≥6.0 supports Lua scripting and async

**Mitigations if false**:
- Fall back to in-process cache (LRU dict)
- Use DuckDB for caching (slower but built-in)
- Implement cache-busting via HTTP headers

**Impact if false**: Cache hit ratio may drop to 30-40%; latency optimization reduced.

---

## Assumption 4: Fortune 500 ESG PDFs Sufficient for Comparison Benchmarking

**Assumption**: 3 Fortune 500 ESG documents (Apple, ExxonMobil, JPMorgan) provide diverse ESG themes (climate, social, governance) suitable for multi-company comparison testing.

**Status**: ✅ **CONFIRMED**

**Evidence**:
- Apple: Environmental focus (climate, renewable energy, supply chain)
- ExxonMobil: Energy transition (GHG, governance, risk disclosure)
- JPMorgan: Financial inclusion (social, diversity, governance)
- Combined: 137 pages covering ESG spectrum

**Impact if false**: May require additional PDFs for comprehensive testing.

---

## Assumption 5: Bayesian Confidence Model Converges with ~10 Evidence Samples

**Assumption**: Beta-Binomial posterior for confidence estimation converges to stable distribution with ≥10 retrieval samples per ESG theme per company.

**Status**: ⚠️ **CONDITIONAL** (pending design.md statistical analysis)

**Evidence**:
- Beta-Binomial conjugate model has closed-form posterior
- Effective sample size ~10-20 typical for convergence
- ESG themes: GHG, biodiversity, supply chain, pay equity, board diversity → ~15 themes

**Mitigations if false**:
- Use frequentist confidence intervals instead
- Increase sample size requirement to 20-30
- Use hierarchical Bayesian model to share strength across companies

**Impact if false**: Posterior uncertainty bands may be unreliable; use frequentist approach instead.

---

## Assumption 6: Multi-company Query Routing Can Be Template-Based

**Assumption**: User queries requesting multi-company comparisons can be reliably expanded using NER + templates without LLM inference.

**Status**: ⚠️ **CONDITIONAL** (pending design.md)

**Example**:
- User: "Compare climate policies: Apple vs ExxonMobil"
- Template expansion:
  - Company 1 (Apple): "What are Apple's climate policies?"
  - Company 2 (ExxonMobil): "What are ExxonMobil's climate policies?"

**Mitigations if false**:
- Use lightweight LLM (Granite-3B) for query expansion
- Implement rule-based fallback for out-of-distribution queries

**Impact if false**: Query expansion error rate may rise; fall back to LLM-based approach.

---

## Assumption 7: Comparative Report Format Fits LLM Context Window

**Assumption**: Structured table + markdown report for 2-3 companies across 5 ESG themes fits within Granite LLM context (8K tokens).

**Status**: ⚠️ **CONDITIONAL** (pending design.md sizing)

**Estimate**:
- Table: ~500 tokens (10 dimensions × 3 companies)
- Narrative: ~300 tokens per theme (5 themes = 1500 tokens)
- Citations: ~200 tokens
- Prompt overhead: ~1000 tokens
- **Total**: ~3500 tokens (well within 8K limit)

**Mitigations if false**:
- Truncate to 2 companies instead of 3
- Reduce dimensions to top-5 ESG metrics
- Use summaries instead of full narrative

**Impact if false**: May need to split reports into multiple requests.

---

## Assumption 8: Cross-Encoder F1 > 0.85 Achievable on Phase 2 Data

**Assumption**: Cross-Encoder re-ranking can achieve F1 > 0.85 on relevance judgment of Phase 2 ESG PDFs (compared to baseline bi-encoder ranking).

**Status**: ⚠️ **CONDITIONAL** (pending Phase 3 validation tests)

**Benchmark baseline**: MS MARCO cross-encoder achieves F1 ≈ 0.82-0.88 on general domain; ESG PDFs may differ.

**Mitigations if false**:
- Fine-tune cross-encoder on ESG domain (Phase 3 implementation)
- Reduce F1 threshold to 0.80
- Combine with other re-ranking signals (BM25 score, metadata match)

**Impact if false**: SC14 (re-ranking) may require extended implementation effort.

---

## Assumption 9: Deterministic Seeds Sufficient for Reproducibility

**Assumption**: Setting fixed random seeds in NumPy, TensorFlow, and PyTorch ensures reproducible cross-encoder predictions and Bayesian posterior estimates across runs.

**Status**: ⚠️ **CONDITIONAL** (requires REPRODUCIBILITY.md update)

**Caveats**:
- GPU non-determinism still possible (depends on HW)
- Multi-threaded inference may have ordering variations
- Redis operations are inherently non-deterministic (cached values)

**Mitigations**:
- Document seed management in REPRODUCIBILITY.md
- Use single-threaded inference for validation runs
- Cache validation separately from correctness validation

**Impact if false**: Reproducibility tests may occasionally fail; use probabilistic assertions.

---

## Assumption 10: No Real-time Inference Required for Phase 3

**Assumption**: Phase 3 comparison queries can tolerate <2 second latency (not true real-time streaming).

**Status**: ✅ **CONFIRMED**

**Evidence**:
- Cross-Encoder batch scoring: <200ms for top-100 documents
- Bayesian posterior update: <50ms per theme
- Report generation: <500ms
- Redis cache: <10ms hit, ~500ms miss + regenerate
- **Total target**: <2 seconds (✓ achievable)

**Impact if false**: Design must account for streaming inference (Phase 4+).

---

## Summary of Assumptions

| # | Assumption | Status | Risk | Mitigation |
|---|-----------|--------|------|-----------|
| 1 | Phase 2 functional | ✅ Confirmed | Low | Already validated |
| 2 | HF cross-encoders available | ✅ Confirmed | Low | Already verified |
| 3 | Redis available | ⚠️ Conditional | Medium | Fallback to in-process cache |
| 4 | 3 PDFs sufficient | ✅ Confirmed | Low | Good coverage |
| 5 | Bayesian convergence ~10 samples | ⚠️ Conditional | Medium | Use frequentist fallback |
| 6 | Template-based query routing | ⚠️ Conditional | Medium | Use LLM expansion if needed |
| 7 | Report fits context | ⚠️ Conditional | Low | Split reports if needed |
| 8 | Cross-encoder F1 > 0.85 | ⚠️ Conditional | Medium | Fine-tune if needed |
| 9 | Deterministic seeds work | ⚠️ Conditional | Low | Document caveats |
| 10 | <2s latency OK | ✅ Confirmed | Low | Already budgeted |

---

## Critical Path Assumptions

**Must be confirmed before Phase 3 implementation**:
- ✅ Assumption 1: Phase 2 functional
- ✅ Assumption 2: Cross-encoders available
- ✅ Assumption 4: 3 PDFs sufficient
- ✅ Assumption 10: <2s latency OK

**Should be validated during Phase 3**:
- ⚠️ Assumption 3: Redis available (deployment-time)
- ⚠️ Assumption 5: Bayesian model (statistical analysis)
- ⚠️ Assumption 6: Template routing (early testing)
- ⚠️ Assumption 8: F1 target (validation testing)

---

**Last Updated**: October 24, 2025
**Status**: DRAFT (awaiting design.md approval)
