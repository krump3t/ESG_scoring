# Task 006: Multi-Source Data Ingestion - Hypothesis

**Task ID**: 006-multi-source-ingestion
**Date**: 2025-10-22
**Protocol**: SCA v13.8-MEA

---

## Primary Hypothesis

**Implementing a multi-source data provider architecture with verified public APIs (CDP Climate, SEC EDGAR) will enable reliable, scalable ESG report ingestion with ≥95% data availability through intelligent 4-tier fallback logic.**

---

## Primary Metrics & Thresholds

| Metric | Baseline (Direct URLs) | Target (Multi-Source) | Success Threshold |
|--------|------------------------|----------------------|-------------------|
| **Data Availability** | 50% (3/6 Phase 1 companies) | ≥95% | ≥90% |
| **API Response Time** | N/A | <5 seconds per request | <10 seconds |
| **Fallback Success Rate** | 0% (no fallback) | ≥80% on Tier 2+ fallback | ≥70% |
| **Provider Coverage** | 1 source | ≥2 primary sources (CDP + SEC) | ≥2 |
| **Test Coverage (CP)** | 0% (no tests) | ≥95% line & branch | ≥95% |
| **Type Safety (CP)** | N/A | 0 mypy --strict errors | 0 errors |
| **Complexity (CP)** | N/A | CCN ≤10 per function | CCN ≤10 |

---

## Critical Path (CP) Definition

**CP Files** (code that MUST meet authenticity gates):
1. `agents/crawler/data_providers/base_provider.py` — Common interface
2. `agents/crawler/data_providers/cdp_provider.py` — CDP Climate API integration
3. `agents/crawler/data_providers/sec_edgar_provider.py` — SEC EDGAR API integration
4. `agents/crawler/multi_source_crawler.py` — Multi-provider orchestrator

**Entry Points**:
- `CDPClimateProvider.search_company()` — Search CDP for company climate data
- `SECEdgarProvider.search_company()` — Search SEC EDGAR for 10-K filings
- `MultiSourceCrawler.download_best_report()` — Intelligent fallback download

---

## Exclusions

**Out of Scope for Task 006:**
- GRI Database provider (web scraping) — deferred to Task 007
- CSRHub API provider — deferred to Task 007
- Bulk download workflows (100+ companies) — deferred to Phase 2
- Integration with enhanced PDF extractor — Task 005 already complete

---

## Power Analysis & Confidence Intervals

**Sample Size**:
- **Phase 1 Test**: 6 companies (Apple, Unilever, ExxonMobil, Walmart, JPMorgan Chase, Tesla)
- **Success Criteria**: ≥5/6 companies (83%) successfully download reports from any source

**Confidence Interval**:
- Target: 95% availability ± 5% (90-100% CI)
- Phase 1 provides preliminary validation; Phase 2 (100+ companies) for statistical significance

---

## Risks & Mitigations

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| **API rate limiting** | High | Medium | Implement rate limiting (0.1s/req), respect limits |
| **API endpoint changes** | High | Low | Version API endpoints, monitor for breaking changes |
| **Authentication required** | Medium | Low | CDP/SEC are public; document if auth needed |
| **Data format changes** | Medium | Medium | Use versioned parsers, validate schema |
| **Network failures** | Low | Medium | Retry logic (3 attempts), exponential backoff |

---

## Success Criteria

**PASS Conditions:**
1. ✅ All 4 CP files have ≥95% test coverage
2. ✅ 0 `mypy --strict` errors on CP files
3. ✅ All CP functions have CCN ≤10
4. ✅ ≥5/6 Phase 1 companies successfully download reports
5. ✅ CDP API successfully retrieves climate data for ≥3 companies
6. ✅ SEC EDGAR API successfully retrieves 10-K for ≥2 U.S. companies
7. ✅ Fallback logic successfully attempts Tier 2+ when Tier 1 fails

**FAIL Conditions:**
- <4/6 Phase 1 companies succeed
- Any CP file <95% coverage
- Any mypy --strict errors
- Any CP function CCN >10
- API responses >10 seconds consistently

---

## Validation Plan

**Phase 1 (Unit Tests)**:
- Test each provider independently
- Mock API responses for determinism
- Test fallback logic with simulated failures

**Phase 2 (Integration Tests)**:
- Test with real API endpoints (CDP, SEC)
- Validate response parsing
- Test rate limiting

**Phase 3 (End-to-End Tests)**:
- Download Phase 1 companies
- Validate file integrity (SHA256)
- Measure data availability %

**Phase 4 (Differential Validation)**:
- Compare CDP quantitative data with manual audit
- Compare SEC 10-K extraction with manual review
- Validate metadata accuracy
