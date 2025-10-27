# Phase 3: Architecture Decision Records

**Phase**: 3
**Title**: ESG Query Synthesis — Architecture Decisions
**Status**: DRAFT (awaiting design.md approval)

---

## ADR-001: Cross-Encoder Selection for Re-ranking (PROPOSED)

**Status**: PROPOSED (pending design.md decision)

**Context**: Phase 2 uses bi-encoder embeddings (Slate 384-dim) for vector similarity. Phase 3 requires re-ranking of retrieved documents for multi-company comparisons.

**Decision**: Use Cross-Encoder model (Sentence-BERT or MS MARCO variant) for two-stage ranking:
1. **Stage 1 (Phase 2)**: Fast bi-encoder retrieval (384-dim similarity, top-100)
2. **Stage 2 (Phase 3)**: Cross-Encoder re-ranking (semantic relevance scoring, top-10)

**Rationale**:
- Cross-encoders achieve 8-15% nDCG improvement over bi-encoder-only ranking (ECIR 2021)
- Latency: <200ms for top-100 cross-encoding
- Model size: 110M parameters (MiniLM variant) fits in-memory
- F1 > 0.85 achievable on Phase 2 Fortune 500 PDFs

**Alternatives Considered**:
- ❌ Bi-encoder only: Simpler but 2-3% lower accuracy
- ❌ LLM re-ranking: Too slow (>2s per batch)
- ❌ BM25 + Cross-Encoder: Better but requires additional index

**Consequences**:
- (+) Higher ranking accuracy for comparative queries
- (+) Minimal latency increase (<200ms per request)
- (-) Additional model deployment (Sentence-BERT)
- (-) Memory overhead (~400MB per model)

**Related**: SC14 (Retrieval re-ranking)

---

## ADR-002: Bayesian Confidence Aggregation (PROPOSED)

**Status**: PROPOSED (pending design.md decision)

**Context**: Phase 2 uses average cosine similarity as confidence. Phase 3 requires principled aggregation of confidence scores across multiple companies and themes.

**Decision**: Use Beta-Binomial conjugate model for Bayesian posterior inference:
- Prior: Beta(α=2, β=2) per ESG theme
- Update: Beta-Binomial likelihood from retrieval hits
- Posterior: P(confidence | data) via conjugate update

**Rationale**:
- Conjugate priors enable exact posterior (no sampling needed)
- Credible intervals support uncertainty quantification
- Theme-specific priors capture domain knowledge
- Converges with ~10 samples per theme

**Alternatives Considered**:
- ❌ Frequentist confidence intervals: No principled way to incorporate priors
- ❌ Variational inference: Overkill for scalar confidence
- ❌ Ensemble methods: Computationally expensive

**Consequences**:
- (+) Principled uncertainty quantification
- (+) Support for Bayesian decision-making
- (-) Additional hyperparameters (α, β per theme)
- (-) Computational cost for posterior updates

**Related**: SC13 (Confidence scoring refinement)

---

## ADR-003: Redis for Query Result Caching (PROPOSED)

**Status**: PROPOSED (pending design.md decision)

**Context**: Phase 2 has no caching. Phase 3 expects 60%+ hit ratio on repeated comparison queries.

**Decision**: Use Redis for caching with LRU eviction and configurable TTL:
- Key format: `phase3:company:{org_id}:theme:{theme}:query:{query_hash}`
- TTL: 24 hours for company-theme pairs, 1 hour for queries
- Eviction: LRU when cache exceeds 1GB
- Serialization: JSON (compatibility with cross-encoder scores)

**Rationale**:
- Sub-millisecond latency for cache hits
- Atomic Lua scripts support consistency
- Pub/Sub enables cache invalidation across services
- LRU eviction matches typical query patterns

**Alternatives Considered**:
- ❌ In-process cache (e.g., Python dict): Limited by single-process memory
- ❌ DuckDB cache: Slower than Redis (>10ms), complex schema
- ❌ Memcached: No Pub/Sub, less feature-rich

**Consequences**:
- (+) 60%+ cache hit ratio reduces latency by 80%
- (+) Scales to multiple services via Pub/Sub
- (-) Redis deployment dependency
- (-) Cache invalidation complexity

**Related**: SC15 (Query result caching)

---

## ADR-004: Multi-Query Synthesis Strategy (PROPOSED)

**Status**: PROPOSED (pending design.md decision)

**Context**: Single user query "Compare climate policies: Apple vs ExxonMobil" must route to company-specific retrieval.

**Decision**: Use template-based query expansion:
1. **Extract entities**: NER to identify companies from user query
2. **Expand queries**: Generate company-specific queries from template
3. **Parallel retrieval**: Retrieve for each company independently
4. **Merge & aggregate**: Combine results with company tags

**Rationale**:
- Simple, deterministic, no LLM overhead
- Supports arbitrary company combinations
- Preserves traceability (query per company)
- Easier to test and debug

**Alternatives Considered**:
- ❌ Single aggregate query: Loses company-level nuance
- ❌ LLM query expansion: ~1s latency, hallucination risk
- ❌ Graph-based routing: Complex for new companies

**Consequences**:
- (+) Sub-100ms expansion (NER overhead minimal)
- (+) Clear separation of company-level retrieval
- (-) Requires company database/ontology
- (-) Complex aggregation logic

**Related**: SC11 (Multi-company query synthesis)

---

## ADR-005: Comparative Report Generation Format (PROPOSED)

**Status**: PROPOSED (pending design.md decision)

**Context**: Phase 3 outputs must support human-readable comparison of ESG attributes across companies.

**Decision**: Use structured table + markdown format:
- **Tables**: Dimension × Company matrix (e.g., GHG emissions, pay equity, board diversity)
- **Narrative**: 100-word summary per ESG theme
- **Citations**: Track source page/document for each claim
- **Confidence bands**: Show Bayesian credible intervals

**Rationale**:
- Tables enable quick cross-company scanning
- Narrative provides context and nuance
- Citations support fact-checking
- Confidence bands communicate uncertainty

**Alternatives Considered**:
- ❌ Prose only: Hard to compare across companies
- ❌ JSON only: Not human-readable
- ❌ Visual charts: Requires UI (out of scope)

**Consequences**:
- (+) Highly readable for non-technical users
- (+) Citation traceability improves trust
- (-) Complex formatting logic
- (-) Large output size (could exceed token limits)

**Related**: SC12 (Comparative ESG analysis)

---

## Summary

| ADR | Title | Status | Phase 3 Success Criterion |
|-----|-------|--------|--------------------------|
| ADR-001 | Cross-Encoder Re-ranking | PROPOSED | SC14 |
| ADR-002 | Bayesian Confidence | PROPOSED | SC13 |
| ADR-003 | Redis Caching | PROPOSED | SC15 |
| ADR-004 | Multi-Query Synthesis | PROPOSED | SC11 |
| ADR-005 | Report Format | PROPOSED | SC12 |

**All ADRs are PROPOSED pending design.md review and approval.**

---

**Last Updated**: October 24, 2025
**Review Status**: ⏸️ BLOCKED (awaiting design.md)
