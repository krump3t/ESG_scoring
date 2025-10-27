# Task 006: Multi-Source Data Ingestion - Architecture Decision Records

**Task ID**: 006-multi-source-ingestion
**Date**: 2025-10-22
**Protocol**: SCA v13.8-MEA

---

## ADR-001: Use Provider Pattern for Multi-Source Architecture

**Date**: 2025-10-22
**Status**: Accepted

**Context**:
The ESG prospecting engine requires ingesting reports from multiple heterogeneous sources (CDP Climate API, SEC EDGAR, GRI Database, company IR websites, etc.). Each source has different API formats, authentication requirements, and rate limits.

**Decision**:
Implement a Provider Pattern with an abstract base class (`BaseDataProvider`) and concrete implementations for each source (`CDPClimateProvider`, `SECEdgarProvider`, etc.).

**Consequences**:
- ✅ **Pros**: Uniform interface for all sources, easy to add new providers, testable in isolation
- ✅ **Pros**: Encapsulates source-specific logic (API endpoints, authentication, parsing)
- ⚠️ **Cons**: Requires maintaining multiple provider implementations
- ⚠️ **Cons**: Shared metadata schema may not capture all source-specific fields

**Alternatives Considered**:
1. Monolithic crawler with conditional logic → Rejected: unmaintainable for 7+ sources
2. Individual scripts per source → Rejected: no shared abstractions, code duplication

---

## ADR-002: Prioritize Public APIs Over Web Scraping

**Date**: 2025-10-22
**Status**: Accepted

**Context**:
Initial implementation relied on direct PDF URL crawling (e.g., `https://www.apple.com/.../2023-ESG-Report.pdf`). This approach had 50% failure rate (Unilever 403, Walmart 404, Tesla robots.txt blocked) and is fragile to URL changes.

**Decision**:
Prioritize verified public APIs (CDP Climate, SEC EDGAR) as Tier 1 sources. Use web scraping only as fallback (Tiers 3-4).

**Consequences**:
- ✅ **Pros**: Stable, versioned APIs with documented schemas
- ✅ **Pros**: No robots.txt restrictions, proper rate limiting
- ✅ **Pros**: Structured JSON data (quantitative metrics, metadata)
- ⚠️ **Cons**: Limited to companies covered by APIs (~13K CDP, ~10K SEC)
- ⚠️ **Cons**: Dependent on API availability (mitigated by fallback tiers)

**Alternatives Considered**:
1. Web scraping only → Rejected: fragile, 50% failure rate, robots.txt restrictions
2. Manual downloads → Rejected: not scalable to 100+ companies

---

## ADR-003: Implement 4-Tier Cascading Fallback

**Date**: 2025-10-22
**Status**: Accepted

**Context**:
No single data source has 100% coverage. CDP has 13K+ companies but may miss recent reports; SEC EDGAR covers U.S.-only; GRI Database may have outdated entries.

**Decision**:
Implement 4-tier cascading fallback logic:
1. **Tier 1**: Public APIs (CDP, SEC EDGAR)
2. **Tier 2**: Comprehensive databases (GRI, CSRHub)
3. **Tier 3**: Direct company IR websites
4. **Tier 4**: Aggregators (SustainabilityReports.com, TCFD Hub)

**Consequences**:
- ✅ **Pros**: Improves data availability from 60% (single source) to 95%+ (research-backed)
- ✅ **Pros**: Graceful degradation if primary sources fail
- ⚠️ **Cons**: Increased complexity (must try multiple sources)
- ⚠️ **Cons**: Slower first-download for companies not in Tier 1

**Alternatives Considered**:
1. Single source only → Rejected: 60% availability insufficient
2. Parallel requests to all sources → Rejected: wastes API quota, rate limit issues

---

## ADR-004: Use Unified CompanyReport Metadata Schema

**Date**: 2025-10-22
**Status**: Accepted

**Context**:
Each data source returns different metadata formats:
- CDP: JSON with `company_name`, `year`, `ghg_scope1`, `ghg_scope2`, etc.
- SEC EDGAR: JSON with `cik`, `fiscalYear`, `form`, `accessionNumber`, etc.
- GRI: HTML with inconsistent field names

**Decision**:
Define a unified `CompanyReport` dataclass with standardized fields:
- `company_name`, `company_id`, `year`, `report_type`, `download_url`, `file_format`, `source`, `source_metadata`, `date_published`, `date_retrieved`

**Consequences**:
- ✅ **Pros**: Consistent interface for downstream processing (extraction, scoring)
- ✅ **Pros**: Easy to compare reports from different sources
- ✅ **Pros**: Source-specific fields preserved in `source_metadata` dict
- ⚠️ **Cons**: Must map each source's schema to unified format

**Alternatives Considered**:
1. Pass-through source-specific formats → Rejected: downstream code must handle 7+ formats
2. Separate schemas per source → Rejected: no standardization

---

## ADR-005: Enforce Per-Provider Rate Limits

**Date**: 2025-10-22
**Status**: Accepted

**Context**:
CDP and SEC EDGAR both enforce 10 requests/second rate limits. Exceeding limits results in 429 errors and temporary bans.

**Decision**:
Implement per-provider rate limiting with configurable `rate_limit` parameter (default 0.1s = 10 req/sec). Use exponential backoff on 429 responses (initial 2s, max 60s, with jitter).

**Consequences**:
- ✅ **Pros**: Respects API ToS, prevents temporary bans
- ✅ **Pros**: Configurable per provider (some may allow higher rates)
- ⚠️ **Cons**: Slower bulk downloads (100 companies × 0.1s = 10 seconds minimum)
- ⚠️ **Cons**: Must implement retry logic for transient failures

**Alternatives Considered**:
1. No rate limiting → Rejected: violates API ToS, causes 429 bans
2. Global rate limit → Rejected: some providers may allow higher rates

---

## ADR-006: Exclude GRI/CSRHub from Phase 1 (Deferred to Task 007)

**Date**: 2025-10-22
**Status**: Accepted

**Context**:
GRI Database requires web scraping (no public API). CSRHub API requires paid subscription. Task 006 focuses on verifying the multi-source architecture with public APIs first.

**Decision**:
Implement only CDP and SEC EDGAR providers in Task 006. Defer GRI and CSRHub to Task 007.

**Consequences**:
- ✅ **Pros**: Faster validation (no web scraping complexity)
- ✅ **Pros**: No authentication/subscription required
- ✅ **Pros**: Proves multi-source architecture with 2 sources
- ⚠️ **Cons**: Limited to Tier 1 fallback testing (no Tier 2 validation yet)
- ⚠️ **Cons**: May require architectural changes when adding Tier 2

**Alternatives Considered**:
1. Implement all 7 sources in Task 006 → Rejected: too large for single task
2. Implement GRI only → Rejected: requires web scraping infrastructure

---

## ADR-007: Use Requests Library for HTTP (Not Playwright)

**Date**: 2025-10-22
**Status**: Accepted

**Context**:
Initial crawler used Playwright for browser automation. When navigating to direct PDF URLs, Playwright triggered download events but `page.goto()` conflicted with `expect_download()`.

**Decision**:
Use Python `requests` library for direct API calls and PDF downloads. Reserve Playwright for future web scraping (Tier 3-4).

**Consequences**:
- ✅ **Pros**: Simpler, no browser dependencies
- ✅ **Pros**: Faster (no browser startup overhead)
- ✅ **Pros**: Easier to test (mock HTTP requests)
- ⚠️ **Cons**: Cannot handle JavaScript-rendered content (not needed for APIs)

**Alternatives Considered**:
1. Fix Playwright download handling → Rejected: unnecessary complexity for APIs
2. Use `urllib` → Rejected: `requests` has better API and error handling

---

**End of ADR**
