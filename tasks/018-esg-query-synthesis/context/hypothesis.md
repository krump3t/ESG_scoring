# Phase 3: ESG Query Synthesis — Hypothesis & Metrics

**Phase**: 3
**Title**: ESG Query Synthesis — Advanced Multi-company Analysis
**Status**: BLOCKED (awaiting design approval)
**Dependencies**: Phase 2 (watsonx.ai integration) ✓ COMPLETE

---

## Primary Claim

**Phase 3 will extend Phase 2 RAG pipeline with advanced query synthesis for multi-company ESG comparisons, enabling comparative analysis across multiple organizations with confidence scoring and re-ranking.**

---

## Success Criteria (SC11-SC15)

| SC | Criterion | Target | Validation Method |
|----|-----------|--------|-------------------|
| SC11 | Multi-company query synthesis | Query 2+ companies in single request | TBD: design.md |
| SC12 | Comparative ESG analysis | Generate comparison reports (climate, social, governance) | TBD: design.md |
| SC13 | Confidence scoring refinement | Bayesian posterior inference on retrieval confidence | TBD: design.md |
| SC14 | Retrieval re-ranking | Cross-Encoder model integration for re-ranking | TBD: design.md |
| SC15 | Query result caching | Redis caching for frequently queried patterns | TBD: design.md |

---

## Key Metrics

### Functional Metrics
- **Query synthesis latency**: <2 seconds for 2-company comparison
- **Re-ranking accuracy**: F1 > 0.85 vs baseline RAG
- **Cache hit ratio**: >60% on repeated patterns
- **Batch comparison throughput**: 5+ comparisons per minute

### Quality Metrics
- **Type hints coverage**: 100% on CP files
- **Docstring coverage**: 100% (module + function)
- **Test coverage**: ≥95% on CP files
- **Cyclomatic complexity**: ≤10 per function
- **Cognitive complexity**: ≤15 per function

### Authenticity Metrics
- **Real cross-encoder model**: Sentence-BERT or similar (no mocks)
- **Real Redis backend**: Actual caching (not in-memory stubs)
- **Real data**: Use Phase 2 Fortune 500 PDFs for comparison
- **Real inference**: Actual model predictions, not synthetic scores

---

## Critical Path (CP) Modules — DRAFT

**Tentative CP files** (to be confirmed in design.md):

1. **libs/query/query_synthesizer.py** — Multi-company query construction
   - Multi-query routing (single user query → multiple retrieved queries)
   - Query expansion with company metadata
   - Prompt construction for comparison workflows
   - Type hints: 100% | Docstrings: complete

2. **libs/ranking/cross_encoder_ranker.py** — Retrieval re-ranking
   - Cross-Encoder model loading (Sentence-BERT or HuggingFace)
   - Batch scoring of retrieved documents
   - Score normalization and aggregation
   - Type hints: 100% | Docstrings: complete

3. **libs/cache/redis_cache.py** — Query result caching
   - Redis client initialization
   - Key generation from query patterns
   - TTL management (configurable per query type)
   - Atomic batch operations
   - Type hints: 100% | Docstrings: complete

4. **scripts/compare_esg_analysis.py** — Comparative analysis orchestrator
   - 2+ company ESG comparison workflow
   - Bayesian confidence aggregation
   - Comparative report generation
   - Provenance tracking across companies
   - Type hints: 100% | Docstrings: complete

5. **libs/scoring/bayesian_confidence.py** — Confidence refinement
   - Posterior inference on retrieval confidence
   - Beta distribution priors per ESG theme
   - Update rules from multiple retrievals
   - Credible interval calculation
   - Type hints: 100% | Docstrings: complete

---

## Assumptions

- Phase 2 watsonx.ai integration is fully functional (✓ confirmed)
- Cross-Encoder models available from HuggingFace (sentence-transformers/ce-ms-marco-MiniLM-L-6-v2 or similar)
- Redis server available for caching (Docker or local)
- Fortune 500 ESG PDFs from Phase 2 sufficient for comparison benchmarking
- Bayesian confidence model converges with ≥10 evidence samples per theme

---

## Exclusions

- ❌ Multi-modal (image + text) analysis — Phase 4+
- ❌ Real-time streaming queries — Phase 5+
- ❌ Custom LLM fine-tuning — Phase 6+
- ❌ Distributed caching across nodes — Phase 7+
- ❌ Mobile/web UI — Out of scope (backend only)

---

## Risk Mitigation

| Risk | Severity | Mitigation |
|------|----------|-----------|
| Cross-Encoder model performance | Medium | Benchmark F1 on Phase 2 data; fallback to BM25 if <0.75 |
| Redis cache misses | Low | Implement LRU fallback; log miss rates |
| Bayesian convergence failure | Medium | Use frequentist fallback if posterior undefined |
| Latency regression vs Phase 2 | High | Profile each stage; target <2s total |
| Model memory constraints | Medium | Use quantized models (fp8/int8); batch size tuning |

---

## Design Review Checklist

Before proceeding to implementation, design.md must address:

- [ ] CP module list finalized and signed off
- [ ] Query synthesis algorithm detailed (query expansion strategy)
- [ ] Cross-Encoder model selection justified (BERT variant, size, inference cost)
- [ ] Redis key space design (collision avoidance, TTL strategy)
- [ ] Bayesian model specification (priors, update rules, convergence criteria)
- [ ] Comparative report format defined (tables, visualizations, citations)
- [ ] Data flow diagrams (query → synthesis → ranking → comparison → cache)
- [ ] Success thresholds specified (latency, accuracy, cache hit ratio)
- [ ] Leakage guards documented (cross-validation strategy for ranking)
- [ ] Reproducibility plan (seed management, deterministic inference)

---

## Next Steps

1. **Design Review** — design.md must be written and approved
2. **Evidence Gathering** — Identify 3+ primary sources on cross-encoder ranking, Bayesian confidence
3. **Data Strategy** — Use Phase 2 Fortune 500 PDFs; plan comparison benchmarks
4. **Implementation** — TDD first; write tests before code
5. **Validation** — Run Phase 3 validate-only.ps1

**Status**: ⏸️ BLOCKED until design.md complete

---

**Last Updated**: October 24, 2025
**Phase Status**: BLOCKED (awaiting design approval)
**Next Review**: Upon design.md completion
