# Architecture Decision Records - Task 037

## ADR-037-001: Authentic Implementation Over Wrapper Pattern

**Status:** Accepted
**Date:** 2025-11-04
**Deciders:** SCA v13.8-MEA

### Context
Tasks 031-035 initially delivered with simple wrapper/stub implementations that lacked real algorithms and infrastructure integration. Previous validation identified these as EXPERIMENTAL, unable to pass E2E determinism tests.

### Decision
Replace all wrapper/stub code with authentic, production-grade implementations:
- Docling-only backend for structure-aware chunking
- Real BM25 index building and AstraDB connections for hybrid retrieval
- Real LangGraph StateGraph with SQLite checkpointing for orchestration

### Consequences
**Positive:**
- Modules can be promoted to PROVEN status after validation
- E2E determinism achievable with proper infrastructure
- Production-ready code suitable for deployment

**Negative:**
- Significant implementation effort (~40 hours vs ~4 hours for wrappers)
- Dependency on external services (AstraDB)
- Requires proper error handling and infrastructure management

**Mitigations:**
- Mock external services for offline testing
- Comprehensive error handling with graceful degradation
- Detailed documentation for infrastructure setup

---

## ADR-037-002: Docling for PDF Structure Detection

**Status:** Accepted
**Date:** 2025-11-04
**Deciders:** SCA v13.8-MEA

### Context
Need structure-aware chunking that preserves semantic boundaries (headers, tables, lists, paragraphs) rather than naive text splitting.

### Alternatives Considered
1. **PyMuPDF (fitz):** Font metrics and layout info, but limited table semantics
2. **pdfplumber:** Good table extraction but limited heading detection
3. **PyPDF2:** Basic text extraction, no structure detection
4. **Docling:** Vision-based PDF understanding with markdown export and table preservation

### Decision
Adopt Docling as the authoritative ingestion backend; retire PyMuPDF.

### Rationale
- Docling outputs markdown with headings, tables, and layout metadata
- Provides page-level segmentation suitable for downstream chunking
- Supports deterministic runs via environment flags (single-threaded CPU mode)
- Consolidates ingestion with Task 026 Docling outcomes (single backend)
- Eliminates PyMuPDF binary dependency

### Consequences
**Positive:**
- Richer table and layout preservation than PyMuPDF
- Consistent ingestion backend across tasks (026 and 037)
- Deterministic markdown outputs when configured for offline mode
- Removes C++ dependency and aligns with IBM tooling

**Negative:**
- Larger initial setup (model downloads, cached assets)
- Slower per-document processing (~3-6s vs PyMuPDF <1s)
- Requires managing Docling model cache and offline flags

**Mitigations:**
- Cache Docling models/artifacts inside build images
- Provide bulk preprocessing script to amortize latency
- Maintain regression tests comparing legacy PyMuPDF output for confidence

---

## ADR-037-003: Sentence-Transformers for Local Embeddings

**Status:** Accepted
**Date:** 2025-11-04
**Deciders:** SCA v13.8-MEA

### Context
Need deterministic, offline-capable embeddings for vector search without external API dependencies (pivot from IBM Watsonx per prior decisions).

### Alternatives Considered
1. **OpenAI embeddings:** High quality but external API, non-deterministic, cost
2. **Watsonx embeddings:** Previously rejected due to reproducibility issues
3. **Sentence-Transformers (all-mpnet-base-v2):** Local, deterministic, state-of-the-art
4. **FastText:** Fast but lower quality for semantic similarity

### Decision
Use Sentence-Transformers `all-mpnet-base-v2` model.

### Rationale
- Deterministic with seed control (`torch.manual_seed(42)`)
- Offline mode supported (model cached locally)
- State-of-the-art quality (768-dim embeddings)
- No external API calls or costs
- Widely validated in production

### Consequences
**Positive:**
- Full determinism for E2E tests
- No network dependency after initial download
- No per-query costs
- Production-ready performance

**Negative:**
- ~420MB model download required
- GPU beneficial but not required
- Slightly slower than API-based solutions

---

## ADR-037-004: LangGraph with SQLite Checkpointing

**Status:** Accepted
**Date:** 2025-11-04
**Deciders:** SCA v13.8-MEA

### Context
Need orchestration layer that routes queries to appropriate retrieval strategies (keyword/semantic/hybrid) with deterministic behavior and state persistence.

### Alternatives Considered
1. **Custom state machine:** Full control but high maintenance
2. **Airflow/Prefect:** Overkill for simple routing
3. **LangChain chains:** Simpler but no state persistence
4. **LangGraph with checkpointing:** Stateful, deterministic, built for LLM workflows

### Decision
Use LangGraph StateGraph with SqliteSaver for checkpointing.

### Rationale
- Designed specifically for LLM-based workflows
- SqliteSaver provides deterministic state persistence
- Conditional edges enable query routing
- Temperature=0 for LLM router ensures determinism
- Thread-safe for concurrent queries
- Extensive documentation and examples

### Consequences
**Positive:**
- Deterministic routing and execution
- State persistence enables resumption
- Clear graph visualization for debugging
- Production-ready with checkpoint recovery

**Negative:**
- Requires langgraph package with checkpoint.sqlite module
- Adds SQLite database dependency
- Learning curve for graph paradigm

**Mitigations:**
- Pin exact langgraph version: `langgraph[sqlite]>=0.2.0`
- Document graph structure thoroughly
- Provide checkpoint cleanup utilities

---

## ADR-037-005: RRF for Hybrid Fusion

**Status:** Accepted
**Date:** 2025-11-04
**Deciders:** SCA v13.8-MEA

### Context
Need to fuse BM25 (lexical) and vector (semantic) search results when scores are not directly comparable.

### Alternatives Considered
1. **Score normalization + weighted sum:** Requires score calibration, fragile
2. **Round-robin interleaving:** Ignores ranking quality
3. **Reciprocal Rank Fusion (RRF):** Rank-based, parameter-free (except k)
4. **Learning-to-rank:** Requires training data

### Decision
Use Reciprocal Rank Fusion (RRF) with k=60 (standard parameter).

### Rationale
- RRF formula: `score(d) = sum(1/(k + rank_i(d)))` handles incomparable scores
- Parameter k=60 is well-validated in literature
- No training data required
- Simple, deterministic, reproducible
- Outperforms score-based fusion in comparative studies

### Consequences
**Positive:**
- Robust to score scale differences
- No calibration required
- Deterministic (rank-based)
- Proven in production systems

**Negative:**
- Discards absolute score information
- Parameter k=60 not tunable per-query
- May underweight very high-scoring items

---

## ADR-037-006: Utility Scripts for Automation

**Status:** Accepted
**Date:** 2025-11-04
**Deciders:** SCA v13.8-MEA

### Context
Need to automate repetitive tasks: CLI generation, CP manifest updates, documentation synchronization, validation reporting.

### Decision
Implement 8 utility scripts to automate remediation workflow:
1. `generate_cli_wrapper.py` - CLI generation
2. `update_cp_manifest.py` - Manifest updates
3. `context_report_assembler.py` - Documentation assembly
4. `update_design_refs.py` - Design doc updates
5. `reconcile_plan.py` - Plan validation
6. `qa_sweep.py` - QA automation
7. `emit_contract.py` - Contract generation
8. `finalize_validation.py` - Final report generation

### Rationale
- Reduces manual errors
- Ensures consistency across tasks
- Makes remediation reproducible
- Supports future tasks
- DRY principle (Don't Repeat Yourself)

### Consequences
**Positive:**
- Faster iteration on remediation
- Consistent output formats
- Reusable for future tasks
- Reduces cognitive load

**Negative:**
- Upfront implementation cost (~4 hours)
- Additional code to maintain
- May over-engineer simple tasks

**Mitigations:**
- Keep scripts simple and focused
- Comprehensive docstrings
- CLI help messages for discoverability

---

## ADR-037-007: Fail-Closed Promotion Decision

**Status:** Accepted
**Date:** 2025-11-04
**Deciders:** SCA v13.8-MEA

### Context
Need clear criteria for promoting modules from EXPERIMENTAL to PROVEN status.

### Decision
Modules remain EXPERIMENTAL unless ALL gates pass:
1. Test coverage ≥95%
2. E2E 3-run determinism PASS
3. CLI functionality verified
4. Infrastructure integration working
5. Documentation aligned

### Rationale
- Prevents premature promotion
- Enforces quality standards
- Aligns with SYSTEM_MICRO fail-closed directive
- Protects production from untested code

### Consequences
**Positive:**
- High confidence in PROVEN modules
- Clear quality bar
- Explicit remediation requirements

**Negative:**
- May delay deployment
- Requires comprehensive testing infrastructure

---

## Summary

**Total ADRs:** 7
**Status:** All Accepted
**Key Themes:** Authenticity, determinism, automation, fail-closed quality gates

These decisions ensure Task 037 delivers production-ready implementations that can be promoted to PROVEN status with confidence.
