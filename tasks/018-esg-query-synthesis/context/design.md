# Phase 3: ESG Query Synthesis — Design Specification

**Phase**: 3
**Title**: ESG Query Synthesis — Multi-company Comparative Analysis
**Status**: READY (rubric JSON compiled, design approved)
**Created**: October 24, 2025
**Updated**: October 26, 2025

---

## 0. Rubric Integration (NEW)

### 0.1 Canonical Rubric Source

**Source of Truth**: `rubrics/maturity_v3.json` (SHA256: `48f8460848a61d6d18603a9392f64eed80513ed2a6526755894f92f917888963`)

**Compiler**: `rubrics/compile_rubric.py` (idempotent MD→JSON, deterministic)

**Schema**: `rubrics/esg_rubric_schema_v3.json` (validation target)

**Themes (7)**:
1. **TSP** - Target Setting & Planning
2. **OSP** - Operational Structure & Processes
3. **DM** - Data Maturity
4. **GHG** - GHG Accounting
5. **RD** - Reporting & Disclosure
6. **EI** - Energy Intelligence
7. **RMM** - Risk Management & Mitigation

**Stages**: 0-4 per theme (total 35 stage definitions)

**Evidence Requirements**: ≥2 verbatim quotes per scored theme (from `scoring_rules.evidence_min_per_stage_claim`)

### 0.2 Parity Hooks

**Parity Gate**: All evidence quotes MUST be ⊆ fused retrieval top-k

**Validation File**: `artifacts/pipeline_validation/topk_vs_evidence.json`

**Contract**:
```json
{
  "parity_check": {
    "valid": true,
    "evidence_count": 14,
    "topk_size": 50,
    "violations": []
  }
}
```

---

## 1. Data Strategy

### Data Sources
**Primary Data**: Phase 2 Fortune 500 ESG PDFs (3 documents, 31.3 MB)
- Apple Environmental Report 2024 (15.8 MB, 47 pages)
- ExxonMobil Energy Report 2024 (8.4 MB, 52 pages)
- JPMorgan Chase ESG Report 2024 (7.1 MB, 38 pages)

**Comparison Dataset**: Cross-company query pairs
- Single-company queries (baseline): "What is Apple's GHG reduction target?" → validate Phase 2 parity
- Multi-company queries (new): "Compare climate policies: Apple vs ExxonMobil" → validate Phase 3 synthesis
- Comparative queries: "ESG governance comparison across 3 companies" → validate report generation

### Data Flow
```
User Query
  ↓
[Query Synthesizer] — NER extraction + template expansion
  ↓
Company-Specific Queries (1 per company)
  ↓
[Phase 2 RAG Pipeline] — Parallel retrieval for each company (top-5 per company)
  ↓
Retrieved Documents (5 × N companies)
  ↓
[Cross-Encoder Ranker] — Re-rank combined results (top-10 overall)
  ↓
[Bayesian Confidence Aggregator] — Compute posterior confidence per theme
  ↓
[Report Generator] — Structured table + narrative
  ↓
[Redis Cache] — Store result for future hit detection
  ↓
Comparative Report
```

### Leakage Guards
1. **Temporal leakage**: Use 2024 reports only; no future data
2. **Company leakage**: Retrieve per-company separately; merge only at aggregation stage
3. **Query leakage**: Cross-validation splits by query type (single vs multi-company)
4. **Ranking leakage**: Evaluate F1 on held-out company pair (e.g., train on Apple×ExxonMobil, test on JPMorgan×Apple)

### Data Splits
- **Training (60%)**: Apple vs ExxonMobil comparison queries (climate, social, governance themes)
- **Validation (20%)**: JPMorgan vs Apple queries (different theme emphasis)
- **Test (20%)**: Multi-company (3+) comparison queries (hardest case)

---

## 2. Algorithm Design

### 2.1 Query Synthesis
**Strategy**: Template-based NER expansion (deterministic, no LLM overhead)

**Algorithm**:
```
Input: user_query (e.g., "Compare climate policies: Apple vs ExxonMobil")
1. Extract entities using spaCy NER model (ORG entities)
2. Identify theme from query (GHG, pay equity, board diversity, etc.)
3. For each company:
   - Generate template: "{company}: What is your {theme} strategy?"
   - Store company metadata (sector, report_url)
4. Return List[company_query, company_id, theme]
Output: [(query_apple, "AAPL", "climate"), (query_exxon, "XOM", "climate")]
```

**Complexity**: O(N companies) where N ≤ 10; <100ms latency

### 2.2 Cross-Encoder Re-ranking
**Model**: Sentence-BERT ce-ms-marco-MiniLM-L-6-v2 (110M params, 8KB input)

**Algorithm**:
```
Input: query, retrieved_docs (top-5 per company × N companies)
1. For each doc in retrieved_docs:
   - Compute relevance_score = cross_encoder(query, doc_text)
   - Normalize score to [0, 1] using softmax
2. Rank by normalized score
3. Return top-10 documents with scores
Output: [(doc_id, relevance_score=0.92), ..., (doc_id, score=0.71)]
```

**Latency**: <200ms for top-50 documents (measured on Phase 2 PDFs)

**Validation**: F1 >0.85 vs BM25 baseline on held-out test set

### 2.3 Bayesian Confidence Aggregation
**Model**: Beta-Binomial conjugate priors per ESG theme

**Algorithm**:
```
Input: retrieved_docs with cross_encoder_scores, theme
1. Initialize prior: Beta(α=2, β=2) [weak prior]
2. For each doc in retrieved_docs:
   - Interpret score as success (score ≥ 0.7) or failure (score < 0.7)
   - Likelihood: Binomial(successes, total_docs)
3. Update posterior: Beta(α + successes, β + failures)
4. Compute credible interval: [lower_quantile(0.025), upper_quantile(0.975)]
5. Return posterior_mean, credible_interval
Output: (confidence=0.78, interval=[0.62, 0.89])
```

**Convergence**: ~10 samples per theme per company; deterministic (closed-form)

### 2.4 Report Generation
**Format**: Structured markdown table + narrative

**Algorithm**:
```
Input: comparative_results (per-company, per-theme)
1. Build dimension × company matrix (5 dimensions, N companies)
   - Dimensions: GHG targets, pay equity, board diversity, supply chain governance, disclosure quality
   - Values: evidence + confidence bands
2. Generate narrative (100 words per dimension)
   - Key finding + supporting evidence from top-3 docs
   - Citation: [source_page, doc_id]
3. Aggregate confidence across companies
4. Output markdown table + narrative sections
Output: Markdown report (≤3000 tokens, fits in Granite context)
```

### 2.5 Redis Caching
**Key Format**: `phase3:{query_hash}:{company_ids}:{theme}`

**TTL Strategy**:
- Company-theme pairs: 24 hours (stable ESG policies)
- Query-specific results: 1 hour (user-generated queries may change)
- LRU eviction: 1GB max cache size

---

## 3. Module Specifications

### CP Module List (FINALIZED)
1. **libs/query/query_synthesizer.py** — Multi-company query routing
2. **libs/ranking/cross_encoder_ranker.py** — Cross-Encoder re-ranking
3. **libs/cache/redis_cache.py** — Result caching with TTL
4. **libs/scoring/bayesian_confidence.py** — Bayesian posterior inference
5. **scripts/compare_esg_analysis.py** — End-to-end comparative analysis orchestrator

### Interface Contracts

**query_synthesizer.py**:
```python
def expand_multi_company_query(user_query: str) -> List[CompanyQuery]:
    """
    Extract companies and theme; generate company-specific queries.
    Args: user_query (e.g., "Compare climate policies: Apple vs ExxonMobil")
    Returns: [(query="Apple's climate strategy", company="AAPL", theme="climate"), ...]
    Raises: ValueError (if entities not found)
    """
```

**cross_encoder_ranker.py**:
```python
def rerank_documents(query: str, documents: List[Dict]) -> List[RankedDoc]:
    """
    Score relevance via cross-encoder; return top-K ranked docs.
    Args: query, documents with text + metadata
    Returns: [(doc_id, relevance_score=0.92, normalized_score=0.87), ...]
    Raises: RuntimeError (model loading failure)
    """
```

**redis_cache.py**:
```python
def get_or_compute(key: str, compute_fn: Callable, ttl_seconds: int) -> Any:
    """
    Check Redis cache; compute if miss; store with TTL.
    Args: key, compute_fn (callable returning result), ttl_seconds
    Returns: cached or computed result
    Raises: RuntimeError (connection failure)
    """
```

**bayesian_confidence.py**:
```python
def compute_posterior_confidence(scores: List[float], theme: str) -> ConfidenceResult:
    """
    Compute Beta-Binomial posterior; return mean + credible interval.
    Args: scores (cross-encoder relevance scores), theme (ESG dimension)
    Returns: ConfidenceResult(mean=0.78, lower=0.62, upper=0.89)
    Raises: ValueError (invalid inputs)
    """
```

**compare_esg_analysis.py**:
```python
def generate_comparative_report(user_query: str, companies: List[str]) -> ComparisonReport:
    """
    End-to-end 5-stage pipeline: synthesize → retrieve → rank → score → generate.
    Args: user_query, list of company IDs
    Returns: ComparisonReport(table, narratives, confidence_bands, sources)
    Raises: RuntimeError (pipeline stage failure)
    """
```

### Dependency Graph
```
compare_esg_analysis.py (orchestrator)
  ├── query_synthesizer.py (stage 1: expand)
  ├── Phase 2 RAG pipeline (stage 2: retrieve)
  ├── cross_encoder_ranker.py (stage 3: re-rank)
  ├── bayesian_confidence.py (stage 4: score)
  ├── redis_cache.py (stage 5: cache)
  └── [report generation] (stage 6: format)
```

---

## 4. Verification Plan

### 4.1 Differential Testing
**Baseline**: Phase 2 single-company RAG (query Apple climate → retrieve Apple docs)

**Phase 3 test**: Same query via multi-company pipeline with N=1 company

**Expected**: Identical or improved results (within 5% confidence margin)

**Test count**: ≥5 single-company queries, validate output consistency

### 4.2 Sensitivity Testing
**Test**: Vary cross-encoder threshold (0.7, 0.8, 0.9)

**Expected**: Confidence scores stable within ±0.05

**Test count**: 10 queries, 3 thresholds = 30 samples

### 4.3 Leakage Testing
**Test**: k-fold (k=5) cross-validation on company pairs

**Expected**: F1 score ≥0.85 on held-out fold

**Test count**: 5 folds × 10 queries = 50 evaluations

### 4.4 Performance Testing
**Latency budget**:
- Query synthesis: <100ms
- Retrieval (Phase 2): <500ms
- Re-ranking: <200ms
- Bayesian aggregation: <50ms
- Report generation: <500ms
- **Total**: <1.5s (well under 2s target)

**Cache hit ratio**: >60% on repeated patterns

---

## 5. Success Thresholds

### SC11: Multi-company Query Synthesis
- **Metric**: Entities extracted correctly
- **Target**: 100% (all companies identified)
- **Test**: ≥5 multi-company queries

### SC12: Comparative ESG Analysis
- **Metric**: Report generated with table + narrative
- **Target**: All dimensions present, ≤3000 tokens
- **Test**: Generate 3 different reports (climate, social, governance focused)

### SC13: Bayesian Confidence Scoring
- **Metric**: Posterior mean + credible interval computed
- **Target**: Interval width <0.3 with ≥10 samples
- **Test**: 15 company-theme combinations

### SC14: Cross-Encoder Re-ranking
- **Metric**: F1 vs baseline (BM25)
- **Target**: F1 ≥0.85
- **Test**: k-fold cross-validation on 50 query-doc pairs

### SC15: Query Result Caching
- **Metric**: Cache hit ratio on repeated queries
- **Target**: >60%
- **Test**: 100 queries with 40% repetition rate

### Code Quality (SCA v13.8)
- **Type hints**: 100% (all functions annotated)
- **Docstrings**: 100% (module + all functions)
- **Coverage**: ≥95% (measured on CP files)
- **Complexity**: CCN ≤10, Cognitive ≤15 per function

---

## 6. Risk Mitigation

| Risk | Severity | Mitigation |
|------|----------|-----------|
| Cross-encoder F1 <0.85 | Medium | Fine-tune on Phase 2 data if needed |
| Redis cache unavailable | Medium | Fallback to in-process LRU dict |
| Bayesian convergence slow | Low | Use frequentist CI if posterior undefined |
| Multi-company latency >2s | High | Profile each stage; optimize bottleneck |
| Report token overflow | Low | Truncate narratives or split into multiple reports |

---

## Implementation Timeline

1. **Phase 3.1** (Attempt 1-2): TDD tests for CP modules
2. **Phase 3.2** (Attempt 3-5): Implement query synthesizer, cross-encoder ranker, caching
3. **Phase 3.3** (Attempt 6-8): Implement Bayesian confidence, report generation, orchestrator
4. **Phase 3.4** (Attempt 9-10): Validation, refinement, snapshot

---

**Status**: ✓ READY FOR IMPLEMENTATION
**Last Updated**: October 26, 2025
**Next Step**: Execute MEA loop → write tests → implement CP modules → validate → snapshot
