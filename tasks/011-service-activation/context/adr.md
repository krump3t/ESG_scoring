# Architectural Decision Records: Task 011

**Task:** 011-service-activation
**Protocol:** SCA v13.8-MEA
**Date:** 2025-11-19

---

## ADR-011-001: Use Adapter Pattern for Crawler Integration

**Status:** Accepted
**Date:** 2025-11-19
**Deciders:** Lead Architect, SCA Agent

### Context

PipelineOrchestrator expects crawler interface:
```python
crawler.crawl_company(company_cik: str, fiscal_year: int) → dict
```

MultiSourceCrawler provides different interface:
```python
crawler.search_company_reports(company_name: str, year: int) → dict[str, list[CompanyReport]]
```

### Decision

Create `CrawlerAdapter` class that:
1. Wraps MultiSourceCrawler instance
2. Provides `crawl_company()` method expected by orchestrator
3. Translates CIK → company name via TickerLookupProvider
4. Delegates to `search_company_reports()` with translated parameters

### Rationale

**Alternatives Considered:**

| Option | Pros | Cons | Decision |
|:-------|:-----|:-----|:---------|
| **Adapter Pattern** | • No changes to MultiSourceCrawler<br>• No changes to PipelineOrchestrator<br>• Single Responsibility Principle | • Extra layer of indirection | ✅ **SELECTED** |
| Refactor Orchestrator | • Direct integration<br>• Fewer classes | • Breaks existing orchestrator interface<br>• Ripple effects to callers | ❌ Rejected |
| Add method to Crawler | • Simple alias | • Pollutes MultiSourceCrawler API<br>• Violates Interface Segregation | ❌ Rejected |

**Benefits:**
- Open/Closed Principle: Both classes remain unchanged
- Testability: Adapter can be unit tested in isolation
- Flexibility: Easy to swap crawler implementation later

### Consequences

**Positive:**
- Clean separation of concerns
- 100% backward compatible
- Easy to mock for testing

**Negative:**
- Extra class to maintain
- Slight performance overhead (negligible)

**Risks:**
- CIK lookup failure → Adapter must handle gracefully (return empty dict)

---

## ADR-011-002: Single /score Endpoint with Auto-Detection

**Status:** Accepted
**Date:** 2025-11-19
**Deciders:** Lead Architect, SCA Agent

### Context

Current state: `/score` endpoint hardcoded to demo_flow (offline only)
Need: Support live ingestion without breaking offline mode

### Decision

Implement auto-detection routing within single `/score` endpoint:
```python
if os.getenv("ALLOW_NETWORK") == "true":
    use PipelineOrchestrator  # Live mode
else:
    use demo_flow             # Offline mode
```

### Rationale

**Alternatives Considered:**

| Option | Pros | Cons | Decision |
|:-------|:-----|:-----|:---------|
| **Auto-Detection (Single Endpoint)** | • Simple UX (one endpoint)<br>• Environment-driven<br>• No client changes | • Less explicit mode selection | ✅ **SELECTED** |
| Dual Endpoints (/score, /score-live) | • Explicit mode choice<br>• Clear intent | • Client must know which to call<br>• Duplicated logic | ❌ Rejected |
| Replace demo_flow | • Simpler code | • Loses offline capability<br>• Breaks CI/CD | ❌ Rejected |

**Benefits:**
- Zero client-side changes required
- Offline determinism preserved for testing
- Live ingestion available for production
- Configuration-driven behavior

### Consequences

**Positive:**
- Seamless transition between modes
- CI/CD uses offline (ALLOW_NETWORK=false) for reproducibility
- Production uses online (ALLOW_NETWORK=true) for fresh data

**Negative:**
- Mode not explicit in API contract (must check logs/config)
- Potential confusion if ALLOW_NETWORK misconfigured

**Mitigations:**
- Log mode clearly: "Offline mode: Using demo_flow" or "Live mode: Using PipelineOrchestrator"
- Include mode in response metadata: `{"mode": "live", "data": {...}}`

---

## ADR-011-003: Default ALLOW_NETWORK=true in All Configs

**Status:** Accepted
**Date:** 2025-11-19
**Deciders:** Lead Architect, SCA Agent

### Context

Current inconsistency:
- `docker-compose.yml`: ALLOW_NETWORK=true
- `docker-compose.live.yml`: ALLOW_NETWORK=${ALLOW_NETWORK:-false} (defaults false!)
- `Dockerfile`: ENV ALLOW_NETWORK=false
- `.env.example`: ALLOW_NETWORK=false

Confusion: Is live mode the default or not?

### Decision

Align ALL configuration files to default `ALLOW_NETWORK=true`:
- Dockerfile: `ENV ALLOW_NETWORK=true`
- docker-compose.live.yml: `ALLOW_NETWORK: ${ALLOW_NETWORK:-true}`
- .env.example: `ALLOW_NETWORK=true`

Users wanting offline mode explicitly set `.env` override: `ALLOW_NETWORK=false`

### Rationale

**Production-First Philosophy:**
- Live service is the primary use case (Task 011 goal: "Service Activation")
- Offline mode is for CI/CD and demos (special case)
- Default should support production deployment

**Alternatives Considered:**

| Option | Pros | Cons | Decision |
|:-------|:-----|:-----|:---------|
| **Default to true** | • Production-ready out-of-box<br>• Aligns with "live service" goal | • CI/CD must override to false | ✅ **SELECTED** |
| Default to false | • Safe for testing | • Extra config for production<br>• Not "live service" | ❌ Rejected |
| No default (require explicit) | • Forces conscious choice | • More config burden | ❌ Rejected |

### Consequences

**Positive:**
- Clear intent: "Live service by default"
- Consistency: All files agree
- Less surprise for production deployments

**Negative:**
- CI/CD must explicitly set `ALLOW_NETWORK=false` in test environments
- Accidental live API calls in development (minor risk)

**Mitigations:**
- Document in README: "Set ALLOW_NETWORK=false for offline mode"
- CI/CD pipeline explicitly sets env vars (not relying on defaults)

---

## ADR-011-004: Full SCA v13.8-MEA Protocol Compliance

**Status:** Accepted
**Date:** 2025-11-19
**Deciders:** Lead Architect

### Context

User selected "Full SCA v13.8-MEA" protocol compliance for Task 011, not minimal wiring.

### Decision

Implement with full rigor:
- ✅ Context files (hypothesis, design, evidence, ADR, assumptions, cp_paths)
- ✅ TDD: Tests before implementation
- ✅ Coverage: ≥95% on critical path (adapter, orchestrator, API)
- ✅ Type safety: mypy --strict
- ✅ Security: detect-secrets, no hardcoded credentials
- ✅ Integration tests: Smoke tests for offline and online modes
- ✅ Documentation: HANDOFF.md with usage guide

### Rationale

**Production Readiness:**
- Task 011 is infrastructure-critical (enables core service)
- Bugs in routing or adapter could cause production outages
- Full testing reduces deployment risk

**Alternatives Considered:**

| Option | Pros | Cons | Decision |
|:-------|:-----|:-----|:---------|
| **Full SCA Protocol** | • Production-ready<br>• High confidence<br>• Documented | • Slower iteration | ✅ **SELECTED** |
| Minimal wiring | • Fast prototyping | • Untested, risky<br>• Technical debt | ❌ Rejected |
| Hybrid (wire + defer tests) | • Medium speed | • Partial coverage, gaps | ❌ Rejected |

### Consequences

**Positive:**
- High confidence in service activation
- Future maintainability
- Clear documentation for future developers

**Negative:**
- Longer initial development time (~4-6 hours vs ~1 hour minimal)
- More files to maintain

**Trade-off:** Accept longer development time for production safety.

---

## ADR-011-005: CIK Translation via TickerLookupProvider

**Status:** Accepted
**Date:** 2025-11-19
**Deciders:** SCA Agent

### Context

Adapter needs to translate CIK (e.g., "0000320193") to company name (e.g., "Apple Inc") to call MultiSourceCrawler.

### Decision

Use `agents/crawler/data_providers/ticker_lookup.py` TickerLookupProvider for CIK resolution.

### Rationale

**Alternatives Considered:**

| Option | Pros | Cons | Decision |
|:-------|:-----|:-----|:---------|
| **TickerLookupProvider** | • Already exists<br>• Tested<br>• Handles CIK lookup | • None | ✅ **SELECTED** |
| Hardcode mapping | • Simple | • Not scalable<br>• Maintenance burden | ❌ Rejected |
| External API (sec.gov) | • Always up-to-date | • Network dependency<br>• Latency | ❌ Rejected |

### Consequences

**Positive:**
- Reuses existing code
- No new dependencies

**Negative:**
- Limited to companies in provider's database

**Mitigation:**
- Return empty dict if CIK not found (graceful degradation)
- Log warning for unknown CIKs

---

**ADRs Status:** Complete
**Review Date:** 2025-11-19
**Next Review:** After Task 011 completion
