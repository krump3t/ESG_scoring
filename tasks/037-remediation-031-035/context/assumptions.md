# Task 037 Assumptions

## Technical Assumptions

### 1. Infrastructure Availability

**Assumption:** AstraDB service accessible with valid credentials during E2E testing.
- **Validation:** Test AstraDB connection during setup phase
- **Fallback:** Mock AstraDB client for offline development and unit tests
- **Risk:** Medium - External service dependency
- **Mitigation:** Maintain mock implementation for CI/CD environments

**Assumption:** HuggingFace model hub accessible for initial model download.
- **Validation:** Verify model cached locally before E2E runs
- **Fallback:** Pre-download model to project artifacts
- **Risk:** Low - One-time download, then cached
- **Mitigation:** Include model in Docker image or provide download script

### 2. Dependency Versions

**Assumption:** `langgraph>=0.2.0` with `checkpoint.sqlite` module available.
- **Validation:** Import test during dependency installation
- **Fallback:** Pin exact working version if module structure changes
- **Risk:** Medium - Package API changes
- **Mitigation:** requirements.txt with exact versions

**Assumption:** `docling>=2.6.0` (with required vision models cached) is available.
- **Validation:** Import test during environment bootstrap plus converter smoke test
- **Fallback:** Provide installation script and local model cache
- **Risk:** Medium - Models require download/caching
- **Mitigation:** Mirror Docling wheel/models in internal artifact registry

### 3. Data Assumptions

**Assumption:** `artifacts/ingestion/chunks.parquet` exists from Task 031.
- **Validation:** File existence check before retrieval
- **Fallback:** Regenerate from source PDFs if missing
- **Risk:** Low - Can regenerate
- **Mitigation:** Document regeneration command

**Assumption:** PDF files in `data/raw/` are valid, non-corrupted.
- **Validation:** Docling conversion smoke test prior to chunking
- **Fallback:** Skip corrupted files, log warnings
- **Risk:** Low - Public documents
- **Mitigation:** SHA256 verification of source files

### 4. Environment Assumptions

**Assumption:** Python 3.9+ with pip available.
- **Validation:** sys.version_info check
- **Fallback:** Document Python version requirement
- **Risk:** Very low - Standard environment
- **Mitigation:** requirements.txt specifies python_requires

**Assumption:** Disk space ≥2GB available for models and artifacts.
- **Validation:** Check available disk space before model download
- **Fallback:** Provide cleanup script
- **Risk:** Low - Reasonable requirement
- **Mitigation:** Document disk requirements

**Assumption:** UTF-8 encoding supported for all text operations.
- **Validation:** Set PYTHONIOENCODING=utf-8 in environment
- **Fallback:** Explicit encoding in all file operations
- **Risk:** Very low - Standard in Python 3
- **Mitigation:** Environment variable check

### 5. Determinism Assumptions

**Assumption:** Setting SEED=42 and PYTHONHASHSEED=0 ensures reproducibility.
- **Validation:** 3-run hash comparison
- **Fallback:** Document non-deterministic components
- **Risk:** Medium - Some libraries may ignore seed
- **Mitigation:** Test each component for determinism independently

**Assumption:** LLM with temperature=0 produces deterministic outputs.
- **Validation:** Multiple router calls with same query must match
- **Fallback:** Cache router decisions for queries
- **Risk:** Medium - LLM implementation dependent
- **Mitigation:** Use deterministic model (e.g., local rule-based router as fallback)

### 6. Performance Assumptions

**Assumption:** Docling chunking completes in <60 seconds per document (vision model latency).
- **Validation:** Performance benchmarking during tests
- **Fallback:** Add timeout with graceful degradation
- **Risk:** Medium - Vision models slower than PyMuPDF
- **Mitigation:** Cache Docling outputs; allow offline preprocessing

**Assumption:** Hybrid retrieval completes in <10 seconds per query.
- **Validation:** Latency monitoring during E2E tests
- **Fallback:** Cache results, reduce k values
- **Risk:** Medium - Depends on AstraDB latency
- **Mitigation:** Connection pooling, retry logic

### 7. Testing Assumptions

**Assumption:** pytest with coverage plugin produces reliable coverage metrics.
- **Validation:** Coverage reports match manual code review
- **Fallback:** Manual coverage verification
- **Risk:** Very low - Mature tooling
- **Mitigation:** Cross-validate with multiple coverage tools if needed

**Assumption:** Hypothesis property tests terminate in reasonable time.
- **Validation:** Set max_examples=50 to limit execution time
- **Fallback:** Reduce max_examples for slow tests
- **Risk:** Low - Configurable
- **Mitigation:** Profile strategy documented in test comments

## Business Assumptions

### 8. Scope Assumptions

**Assumption:** Task 037 completes remediation of Tasks 031-035 only.
- **Validation:** Explicit scope definition in hypothesis.md
- **Fallback:** Create Task 038 for any additional scope
- **Risk:** Low - Clear boundaries
- **Mitigation:** Strict adherence to scope

**Assumption:** Task 036 (resilience & async orchestration) remains explicitly DEFERRED to future task.
- **Validation:** Task 036 cp_paths.json shows status=DEFERRED
- **Fallback:** Document Task 036 requirements separately
- **Risk:** Very low - Explicit architectural decision
- **Mitigation:** See detailed Task 036 Deferral section below

### 9. Quality Assumptions

**Assumption:** 95% code coverage is sufficient quality threshold.
- **Validation:** Industry standard for critical systems
- **Fallback:** Increase to 98% if insufficient
- **Risk:** Low - Well-established practice
- **Mitigation:** Focus coverage on critical paths

**Assumption:** 3-run determinism test is statistically sufficient.
- **Validation:** Binomial probability p<0.01 for detecting non-determinism
- **Fallback:** Increase to 5 runs if concerns arise
- **Risk:** Very low - Standard practice
- **Mitigation:** Can increase runs at minimal cost

### 10. Timeline Assumptions

**Assumption:** 40 hours implementation effort is realistic.
- **Validation:** Based on similar prior tasks
- **Fallback:** Adjust scope or extend timeline
- **Risk:** Medium - Estimates may be optimistic
- **Mitigation:** Track actual hours, adjust as needed

**Assumption:** All dependencies can be installed without conflicts.
- **Validation:** Fresh virtual environment install test
- **Fallback:** Resolve conflicts, pin versions
- **Risk:** Medium - Dependency hell possible
- **Mitigation:** Document exact working environment

## Assumption Validation Plan

**Pre-Implementation Validation:**
1. Verify AstraDB connection
2. Download and cache embedding model
3. Install all dependencies in fresh venv
4. Check disk space and Python version
5. Verify source data exists

**During Implementation:**
1. Test each component for determinism independently
2. Monitor performance benchmarks
3. Track coverage metrics continuously
4. Validate assumptions as they become relevant

**Post-Implementation:**
1. Run full E2E 3-run determinism test
2. Verify all coverage thresholds met
3. Check all infrastructure integrations
4. Validate documentation accuracy

## Assumption Change Log

**2025-11-04:** Initial assumptions documented
- All assumptions marked as "unvalidated"
- Validation plan established
- Risk assessments documented

**Future updates:** Track assumption validation results and any changes to assumptions during implementation.

---

**Total Assumptions:** 10 technical + 2 business = 12
**Risk Profile:** 2 medium-risk, 8 low-risk, 2 very-low-risk
**Validation Status:** All pending validation during implementation

---

## Task 036 Deferral

### Status
Task 036 (resilience-performance-e2e) is **explicitly DEFERRED** and not included in Task 037 remediation scope.

### Rationale
**Architectural Decision**: Task 037 focuses on establishing a stable, validated **synchronous retrieval pipeline** (BM25 + vector + RRF) as the foundational layer. Adding async orchestration, resilience infrastructure (backoff policies, rate limiters, DLQ writers, chaos testing) would introduce significant additional complexity that should be addressed separately after the synchronous foundation is proven.

**Scope Separation**:
- **Task 037 (In Scope)**: Authentic implementations of structure-aware chunking, hybrid retrieval, and synchronous LangGraph orchestration with determinism validation
- **Task 036 (Deferred)**: Async orchestration, resilience patterns, chaos engineering, performance optimization under load

### Implementation Dependencies
Task 036 requires:
1. `libs/resilience/backoff_policy.py` - Exponential backoff for retries
2. `libs/resilience/rate_limiter.py` - Token bucket rate limiting
3. `libs/resilience/dlq_writer.py` - Dead letter queue for failed operations
4. `libs/resilience/chaos_injector.py` - Fault injection for chaos testing
5. `agents/e2e/full_pipeline.py` - End-to-end async pipeline orchestration
6. Comprehensive chaos test suite with failure scenarios

### Future Work
Task 036 will be implemented in a **future async implementation phase** once:
- Task 037 validation completes successfully (all gates pass)
- Synchronous retrieval pipeline is promoted to PROVEN status
- Baseline performance metrics are established
- Infrastructure monitoring is in place

### Documentation Consistency
- **cp_paths.json**: `tasks/036-resilience-performance-e2e/context/cp_paths.json` shows `"status": "DEFERRED"`
- **hypothesis.md**: Line 70 lists Task 036 as out of scope
- **claims_index.json**: Documents Task 036 exclusion with rationale
- **EXECUTION_PLAN.md**: V3 gate checks Task 036 status consistency

### Impact on Task 037
**No Impact**: Task 037 deliverables (structure-aware chunker, hybrid retriever, synchronous orchestration) are completely independent of Task 036 resilience infrastructure. All Task 037 validation gates can be satisfied without Task 036 implementation.

---
