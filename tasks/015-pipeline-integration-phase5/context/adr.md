# Architecture Decision Records - Phase 5: End-to-End Pipeline Integration

**Task ID**: 015-pipeline-integration-phase5
**Phase**: 5
**Date**: 2025-10-24
**SCA Protocol**: v13.8-MEA

---

## ADR-001: Sequential Execution (No Parallelism)

**Status**: Accepted
**Date**: 2025-10-24
**Deciders**: SCA v13.8-MEA

### Context
Phase 5 coordinates three phases (2→3→4) which must execute in order (data dependency).

### Decision
Execute phases sequentially (Phase 2 → Phase 3 → Phase 4) with no parallelism.

### Rationale
1. **Data Dependencies**: Phase 3 input = Phase 2 output; Phase 4 input = Phase 3 output
2. **Simplicity**: Sequential execution is easier to debug, log, and validate
3. **PoC Scope**: Single-company processing; parallelism deferred to Phase 6
4. **Error Handling**: Fail-fast propagation clear in sequential execution

### Alternatives Considered
- **Parallel execution (Airflow/Dask)**: Over-engineered for PoC, adds external dependency
- **Async execution (asyncio)**: Improves throughput but complicates error handling
- **Queue-based (Celery)**: Distributed setup, overkill for single company

### Consequences
- **Positive**: Deterministic execution, clear causality, easy debugging
- **Negative**: Slower throughput (no parallelism), sub-optimal resource utilization
- **Mitigation**: Phase 6 will implement parallel processing for multi-company scale

---

## ADR-002: Fail-Fast on Critical Errors

**Status**: Accepted
**Date**: 2025-10-24
**Deciders**: SCA v13.8-MEA

### Context
Errors can occur at each phase (crawler, extractor, writer, reader). Need strategy for error propagation.

### Decision
Fail-fast on critical errors; log-and-continue on warnings.

**Critical Errors** (stop pipeline):
- Phase 2: Crawler cannot download report (404, 429 after retries, network error)
- Phase 3: Extractor cannot parse report (malformed JSON, unsupported format)
- Phase 4 Write: Parquet write fails (disk full, permission error)
- Phase 4 Query: DuckDB fails (schema mismatch, invalid SQL)

**Warnings** (log but continue):
- Phase 3: Some metrics are null (expected for many companies)
- Phase 4 Query: Completeness <95% but >80% (document and continue)

### Rationale
1. **Authenticity**: No masking errors; transparent failure modes
2. **Debugging**: Early detection of integration issues
3. **User Feedback**: Clear error messages for root cause analysis
4. **Safety**: Prevents silent data corruption (invalid data stops pipeline)

### Alternatives Considered
- **Retry all errors**: Could mask transient issues vs persistent failures
- **Default values**: Violates authentic computation (no fabrication)
- **Partial success**: Ambiguous state (did pipeline succeed or not?)

### Consequences
- **Positive**: High confidence in output quality, easy debugging
- **Negative**: Pipeline may fail on transient errors (no auto-recovery)
- **Mitigation**: Implement exponential backoff retry for transient errors (429, timeout)

---

## ADR-003: In-Process Error Handling (No External Services)

**Status**: Accepted
**Date**: 2025-10-24
**Deciders**: SCA v13.8-MEA

### Context
Orchestrator must handle errors from Phase 2-4 components.

### Decision
Handle all errors in-process within PipelineOrchestrator. No external error services (Sentry, DataDog).

### Rationale
1. **PoC Simplicity**: No external service dependencies
2. **Self-Contained**: Pipeline is standalone, no infrastructure assumptions
3. **Phase 3-4 Pattern**: Phases 3-4 already use in-process logging
4. **Determinism**: File-based logs are reproducible and version-controllable

### Consequences
- **Positive**: No external dependencies, fully reproducible
- **Negative**: No real-time alerting, no distributed tracing
- **Mitigation**: Phase 6 will add monitoring/alerting infrastructure

---

## ADR-004: Use Existing Phase 2-3-4 Components (No Rewrites)

**Status**: Accepted
**Date**: 2025-10-24
**Deciders**: SCA v13.8-MEA

### Context
Phase 5 must integrate Phase 2 (crawler), Phase 3 (extractor), and Phase 4 (data lake).

### Decision
Use existing implementations of Phase 2-4 components as-is. No rewrites or refactoring.

### Rationale
1. **DRY Principle**: Avoid code duplication
2. **Proven Components**: Each phase has been independently tested and validated
3. **Risk Reduction**: No new implementation complexity
4. **Traceability**: Clear separation of concerns (orchestrator ≠ implementation)

### Consequences
- **Positive**: Low risk, reuses proven code, faster implementation
- **Negative**: Orchestrator must adapt to Phase 2-4 interfaces (no interface changes)
- **Mitigation**: Document all interface expectations in design.md

---

## ADR-005: Real Data (Not Mocks or Fixtures)

**Status**: Accepted
**Date**: 2025-10-24
**Deciders**: SCA v13.8-MEA

### Context
Phase 5 validates end-to-end pipeline with real data.

### Decision
Use REAL Microsoft & Tesla SEC 10-K filings. Cache responses for replay tests.

### Rationale
1. **Authenticity Mandate**: SCA v13.8 requires real computation (no mocks)
2. **Hidden Issues**: Real data exposes integration bugs that fixtures hide
3. **Stakeholder Confidence**: Proof that system works with actual company data
4. **Generalization**: Two companies test that extraction works across industries

### Alternatives Considered
- **Synthetic data**: Faster but violates authentic computation
- **Single company**: Faster but doesn't validate generalization
- **Fixtures only**: Removes real API testing burden

### Consequences
- **Positive**: Maximum confidence in system, real-world validation
- **Negative**: Slower tests (SEC API throttling), network dependency
- **Mitigation**: Cache real responses in data/raw/sec_edgar/* for replay tests

---

## ADR-006: Ground Truth Validation (±1% Tolerance)

**Status**: Accepted
**Date**: 2025-10-24
**Deciders**: SCA v13.8-MEA

### Context
Need to validate that extracted metrics are correct (SC4: ground truth match).

### Decision
Manually extract ground truth from SEC 10-K filings. Validate extracted metrics with ±1% tolerance.

### Rationale
1. **High Confidence**: Manual extraction is gold standard
2. **Traceability**: Ground truth is version-controlled, auditable
3. **Reasonable Tolerance**: ±1% accounts for rounding, unit conversions, date variations
4. **Practical**: Cannot achieve 0% error (legitimate variations exist)

### Tolerance Justification
- SEC filings have multiple ways to report same metric (consolidated vs non-consolidated)
- Rounding: Financial statements round to millions/billions
- Unit conversions: Some metrics in different units (metric tons, thousands)
- Date variations: FY end dates vary by company (calendar vs fiscal)

### Consequences
- **Positive**: High confidence in accuracy, validates end-to-end correctness
- **Negative**: Manual effort to extract ground truth for each company
- **Mitigation**: Ground truth captured once per company, reused in tests

---

## ADR-007: 60-Second Performance Target (Achievable Goal)

**Status**: Accepted
**Date**: 2025-10-24
**Deciders**: SCA v13.8-MEA

### Context
Phase 5 includes performance target (SC5). What is realistic latency?

### Decision
Target <60 seconds for complete pipeline (crawl → query).

### Rationale
1. **API Throttling**: SEC EDGAR limited to ~10 RPS; we use 1 RPS = ~20-40s per company
2. **Extraction**: Structured extraction is fast (~5s), LLM extraction slower (~10s)
3. **Storage**: Parquet write is fast (<5s)
4. **Query**: DuckDB query is fast (<5s)
5. **Total**: 20-40s (crawl) + 5s (extract) + 5s (write) + 5s (query) ≈ 35-60s

### Breakdown
- Phase 2 (crawl): 20-40s (dominated by SEC API throttle)
- Phase 3 (extract): 5-15s (depends on content size and extraction method)
- Phase 4 (write): <5s (local Parquet write)
- Phase 4 (query): <5s (in-memory DuckDB)

### Consequences
- **Positive**: Realistic target, achieves PoC goals
- **Negative**: Not optimized (parallelization would help)
- **Mitigation**: Measure actual latencies, adjust target based on results

---

## ADR-008: Separate Validator Component (Concerns Separation)

**Status**: Accepted
**Date**: 2025-10-24
**Deciders**: SCA v13.8-MEA

### Context
Orchestrator coordinates phases; validator checks output. Mix or separate?

### Decision
Separate IntegrationValidator from PipelineOrchestrator.

### Rationale
1. **Single Responsibility**: Orchestrator orchestrates; Validator validates
2. **Reusability**: Validator can be used independently (e.g., in other pipelines)
3. **Testability**: Validator can be tested separately from orchestration logic
4. **Clarity**: Clear separation of concerns

### Consequences
- **Positive**: Clean architecture, reusable components
- **Negative**: Slightly more code, additional file
- **Mitigation**: Validator is lightweight (~100 lines), low maintenance burden

---

**Prepared By**: Scientific Coding Agent v13.8-MEA
**Status**: Phase 5 Architecture Decisions Complete
**Next**: Create assumptions.md
