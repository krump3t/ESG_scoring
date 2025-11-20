# Hypothesis: Service Activation & Auto-Detection

**Task:** 011-service-activation
**Protocol:** SCA v13.8-MEA
**Date:** 2025-11-19

---

## Primary Hypothesis

**Claim:** Auto-detection routing based on `ALLOW_NETWORK` enables seamless switching between offline (deterministic) and online (live ingestion) modes without API changes or deployment disruption.

**Prediction:** A single `/score` endpoint that inspects `ALLOW_NETWORK` environment variable will:
1. Route to `demo_flow` when `ALLOW_NETWORK=false` → deterministic, offline scores
2. Route to `PipelineOrchestrator` when `ALLOW_NETWORK=true` → live SEC EDGAR ingestion
3. Maintain identical output schema regardless of routing path
4. Require zero client-side changes

---

## Secondary Hypotheses

### H1: Adapter Pattern Resolves API Incompatibility

**Claim:** A thin `CrawlerAdapter` class can bridge the method signature gap between:
- PipelineOrchestrator expectation: `crawler.crawl_company(cik: str, year: int) → dict`
- MultiSourceCrawler interface: `search_company_reports(name: str, year: int) → dict[str, list[CompanyReport]]`

**Test:** Unit tests with mocked MultiSourceCrawler verify adapter:
- Translates CIK to company name via lookup
- Calls `search_company_reports` with correct parameters
- Transforms `list[CompanyReport]` to orchestrator-expected `dict`
- Handles missing company gracefully (returns empty dict)

**Success Metric:** 100% test coverage on adapter, no runtime errors in integration tests

---

### H2: Configuration Alignment Improves Clarity

**Claim:** Unifying `ALLOW_NETWORK` defaults across all Docker configuration files (Dockerfile, docker-compose.yml, docker-compose.live.yml, .env.example) to `true` reduces confusion and aligns with production-first intent.

**Current State (Inconsistent):**
- `docker-compose.yml`: `ALLOW_NETWORK: "true"`
- `docker-compose.live.yml`: `ALLOW_NETWORK: ${ALLOW_NETWORK:-false}` (defaults to false!)
- `Dockerfile`: `ENV ALLOW_NETWORK=false`
- `.env.example`: `ALLOW_NETWORK=false`

**Expected Outcome:** All configs default to `true`. Offline mode explicitly enabled via `.env` override.

**Verification:** Script checks all files for consistent defaults.

---

### H3: Orchestrator Initialization Prevents Runtime Failures

**Claim:** Initializing `PipelineOrchestrator.crawler` with `CrawlerAdapter(MultiSourceCrawler(...))` instead of `None` prevents AttributeError when `run_pipeline()` calls `self.crawler.crawl_company()`.

**Current Blocker:** Line 229 of `apps/pipeline_orchestrator.py`:
```python
crawl_result = self.crawler.crawl_company(company_cik, fiscal_year)
# ❌ AttributeError: 'NoneType' object has no attribute 'crawl_company'
```

**Fix:** Initialize in `__init__()`:
```python
self.crawler = CrawlerAdapter(
    MultiSourceCrawler(registry_path="configs/data_source_registry.json")
)
```

**Test:** Integration test calls `orchestrator.run_pipeline("0000320193", 2024)` and verifies no AttributeError.

---

## Metrics & Thresholds

| Metric | Threshold | Measurement |
|:-------|:----------|:------------|
| **Adapter Test Coverage** | ≥95% | pytest --cov=agents/crawler/crawler_adapter.py |
| **Routing Test Coverage** | ≥95% | pytest --cov=apps/api/main.py |
| **Type Safety** | 0 errors | mypy --strict on adapter, orchestrator, API |
| **Offline Mode Score** | Deterministic | 3 runs → same SHA256 hash |
| **Online Mode Success** | ≥80% | Smoke test with live SEC EDGAR (network flakiness) |
| **Config Alignment** | 100% | All 4 files default to ALLOW_NETWORK=true |

---

## Critical Path

Files marked as Critical Path (CP) for validation gates:
1. `agents/crawler/crawler_adapter.py` - Core adapter logic
2. `apps/pipeline_orchestrator.py` - Crawler initialization
3. `apps/api/main.py` - Routing logic

Non-CP:
- Context files (documentation)
- Integration tests (validation only)
- Docker configs (infrastructure)

---

## Exclusions

**Out of Scope for Task 011:**
- PDF extraction fixes (Task 010 documented this gap)
- Vector store migration (in-memory search remains)
- Scoring algorithm changes
- UI integration

**Deferred to Future Tasks:**
- Background job processing (async ingestion)
- Progress tracking / status endpoints
- Crawler performance optimization
- Multi-tenancy / rate limiting

---

## Power Analysis & Confidence Intervals

**Sample Size for Determinism Validation:**
- N = 3 runs with `ALLOW_NETWORK=false`
- Expected: SHA256(run1) == SHA256(run2) == SHA256(run3)
- Confidence: 99% (deterministic systems should have 0% variance)

**Sample Size for Live Mode Validation:**
- N = 5 attempts with `ALLOW_NETWORK=true`
- Expected success rate: ≥80% (allows for network failures)
- Confidence Interval: [60%, 100%] at 95% CI

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|:-----|:-----------|:-------|:-----------|
| Adapter logic error | Medium | High | TDD with 100% coverage |
| Config drift | Low | Medium | Verification script in CI |
| Live mode network timeout | High | Low | Timeout handling + fallback |
| Routing logic bug | Low | High | Integration tests both paths |
| CIK lookup failure | Medium | Medium | Return 404 with clear error message |

---

## Hypothesis Validation Plan

### Phase 1: Unit Tests (TDD Red-Green-Refactor)
1. Write failing test: `test_adapter_translates_cik_to_search()`
2. Implement adapter minimum viable code
3. Assert test passes
4. Repeat for all adapter methods

### Phase 2: Integration Tests
1. Mock MultiSourceCrawler in orchestrator test
2. Verify `run_pipeline()` calls adapter correctly
3. Mock demo_flow and orchestrator in API test
4. Verify routing based on ALLOW_NETWORK

### Phase 3: Smoke Tests
1. Start Docker with `ALLOW_NETWORK=false`
2. POST to `/score` with Apple CIK
3. Verify demo_flow used (check logs)
4. Restart with `ALLOW_NETWORK=true`
5. POST to `/score` with Apple CIK
6. Verify orchestrator used (check logs)

### Phase 4: Determinism Validation
1. Run offline mode 3 times
2. Compare output JSON hashes
3. Assert identical (deterministic)

---

**Hypothesis Status:** Ready for Testing
**Validation Method:** TDD + Integration + Smoke Tests
**Expected Duration:** ~4-6 hours (full implementation + tests + validation)
