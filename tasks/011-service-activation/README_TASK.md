# Task 011: Service Activation & Live Wiring

**Task ID:** 011-service-activation
**Protocol:** SCA v13.8-MEA
**Date:** 2025-11-19
**Depends On:** Task 010 (PDF Boundary Definition - COMPLETE)

---

## Objective

Convert the ESG pipeline from "Read-Only Demo" to "Live Ingestion Service" with automatic offline/online mode detection based on `ALLOW_NETWORK` environment variable.

**Current State:** API uses demo_flow (offline only), PipelineOrchestrator has uninitialized crawler
**Target State:** API auto-detects mode, orchestrator wired with MultiSourceCrawler via adapter

---

## Success Criteria

1. ✅ CrawlerAdapter bridges MultiSourceCrawler API to PipelineOrchestrator interface
2. ✅ PipelineOrchestrator initializes crawler (no more `self.crawler = None`)
3. ✅ API `/score` endpoint auto-detects ALLOW_NETWORK and routes appropriately:
   - `ALLOW_NETWORK=false` → demo_flow (offline, deterministic)
   - `ALLOW_NETWORK=true` → PipelineOrchestrator (live ingestion)
4. ✅ All Docker configurations aligned to default `ALLOW_NETWORK=true`
5. ✅ Full test coverage (adapter 100%, routing 100%)
6. ✅ Smoke tests pass for both offline and online modes

---

## Architecture Decisions

### 1. Adapter Pattern
**Decision:** Create `CrawlerAdapter` class to bridge API incompatibility
**Rationale:**
- PipelineOrchestrator expects: `crawler.crawl_company(company_cik, fiscal_year) → dict`
- MultiSourceCrawler provides: `search_company_reports(company_name, year) → dict[str, list[CompanyReport]]`
- Adapter keeps both classes unchanged, follows Open/Closed Principle

### 2. Auto-Detection Routing
**Decision:** Single `/score` endpoint with runtime mode detection
**Rationale:**
- Simpler UX (one endpoint instead of /score and /score-live)
- Environment-driven behavior (ALLOW_NETWORK controls mode)
- Preserves offline determinism for CI/CD and demos
- Enables live ingestion for production

### 3. Configuration Alignment
**Decision:** All Docker configs default to `ALLOW_NETWORK=true`
**Rationale:**
- Production-first philosophy
- Live service is primary use case
- Offline mode available via explicit env var override

---

## Phases

| Phase | Description | Status |
|:------|:------------|:-------|
| 1 | Context & Scaffolding | ✅ |
| 2 | Adapter Layer (TDD) | 🔄 |
| 3 | Configuration Alignment | ⏸️ |
| 4 | Orchestrator Wiring (TDD) | ⏸️ |
| 5 | API Auto-Detection (TDD) | ⏸️ |
| 6 | Integration Testing | ⏸️ |
| 7 | Validation & Documentation | ⏸️ |
| 8 | Commit & Persistence | ⏸️ |

---

## Dependencies

**Required:**
- MultiSourceCrawler (`agents/crawler/multi_source_crawler.py`)
- PipelineOrchestrator (`apps/pipeline_orchestrator.py`)
- Demo Flow (`apps/pipeline/demo_flow.py`)
- Data Source Registry (`configs/data_source_registry.json`)

**Validated:**
- ✅ MultiSourceCrawler class exists
- ✅ Registry file exists
- ✅ Demo flow functional
- ✅ Orchestrator structure ready for wiring

---

## Protocol Compliance

**SCA v13.8-MEA Requirements:**
- ✅ Context gate: hypothesis, design, evidence, ADR, assumptions, cp_paths
- 🔄 TDD guard: Tests before implementation
- ⏸️ Coverage: ≥95% on CP files
- ⏸️ Type safety: mypy --strict on adapter, orchestrator, API
- ⏸️ Security: detect-secrets, no hardcoded credentials
- ⏸️ Traceability: HANDOFF.md, validation artifacts

---

**Task Status:** IN PROGRESS
**Ready for Execution:** YES
