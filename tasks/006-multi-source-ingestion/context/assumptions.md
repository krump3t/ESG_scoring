# Task 006: Multi-Source Data Ingestion - Assumptions

**Task ID**: 006-multi-source-ingestion
**Date**: 2025-10-22
**Protocol**: SCA v13.8-MEA

---

## API Availability Assumptions

### CDP Climate Change API

**Assumption 1**: CDP Open Data Portal remains publicly accessible without authentication
- **Rationale**: CDP's Open Data Portal (`https://data.cdp.net/`) is explicitly public with no API key requirement documented
- **Risk**: CDP could introduce authentication requirements
- **Mitigation**: Monitor API responses for 401/403 errors; document authentication if introduced
- **Validation**: Test API access without credentials in Phase 1

**Assumption 2**: CDP OData v4 API schema remains stable
- **Rationale**: OData v4 is a versioned standard; CDP has maintained v4 endpoint since 2018
- **Risk**: CDP could change field names or structure
- **Mitigation**: Version API endpoint in registry; implement schema validation; log warnings on unexpected fields
- **Validation**: Compare API response to documented schema in evidence.json

**Assumption 3**: CDP rate limit of 10 requests/second is enforced but not documented
- **Rationale**: Standard OData rate limit; observed in similar public APIs
- **Risk**: Actual rate limit could be lower or higher
- **Mitigation**: Implement configurable rate limiting (default 0.1s); adjust based on 429 responses
- **Validation**: Monitor 429 errors during Phase 1 testing

---

## SEC EDGAR API Assumptions

**Assumption 4**: SEC EDGAR API remains publicly accessible with User-Agent requirement
- **Rationale**: SEC explicitly documents User-Agent requirement at `https://www.sec.gov/os/accessing-edgar-data`
- **Risk**: SEC could introduce authentication or IP-based access controls
- **Mitigation**: Implement User-Agent with contact email; monitor 403 errors
- **Validation**: Test API access with compliant User-Agent in Phase 1

**Assumption 5**: SEC 10-K filings contain Item 1A (Risk Factors) with ESG disclosures
- **Rationale**: Item 1A is mandatory for all 10-K filings per SEC rules
- **Risk**: Risk Factors section may not mention ESG/climate risks for all companies
- **Mitigation**: Extract full Item 1A text; flag if no ESG keywords found
- **Validation**: Manual review of ≥3 companies in Phase 1

**Assumption 6**: SEC rate limit of 10 requests/second is documented and enforced
- **Rationale**: SEC explicitly documents this limit at `https://www.sec.gov/os/accessing-edgar-data`
- **Risk**: SEC could lower limit or implement burst limits
- **Mitigation**: Implement 0.11s delay (9 req/sec) for safety margin; exponential backoff on 429
- **Validation**: Monitor 429 errors during Phase 1 testing

---

## Data Quality Assumptions

**Assumption 7**: Phase 1 companies (6 diverse companies) provide representative test coverage
- **Rationale**: Selected companies span industries (tech, consumer goods, energy, retail, finance, automotive), geographies (U.S., U.K.), and sizes ($50B-$2T market cap)
- **Risk**: Phase 1 may not represent edge cases (small companies, non-English reports, developing markets)
- **Mitigation**: Phase 2 expands to 100+ companies for statistical significance
- **Validation**: ≥5/6 companies (83%) must successfully download in Phase 1

**Assumption 8**: CDP and SEC combined provide ≥90% coverage for Phase 1 companies
- **Rationale**: All Phase 1 companies are large public companies likely to report to CDP or SEC
- **Risk**: Some companies may not report to either source
- **Mitigation**: Implement fallback to Tier 2 sources (GRI, CSRHub) in Task 007
- **Validation**: Measure actual coverage in Phase 1 testing

**Assumption 9**: Quantitative metrics from CDP (GHG emissions) are self-reported and not audited
- **Rationale**: CDP data comes from company self-reported surveys
- **Risk**: Data may be inaccurate or incomplete
- **Mitigation**: Flag CDP data as "self-reported" in metadata; implement differential validation (compare to 10-K disclosures)
- **Validation**: Manual audit of ≥3 companies in Phase 1 (compare CDP vs. 10-K)

---

## Network and Infrastructure Assumptions

**Assumption 10**: Network latency for API requests is <2 seconds per request
- **Rationale**: CDP and SEC servers are in U.S.; typical latency for REST APIs is <1s
- **Risk**: Network congestion or server load could increase latency
- **Mitigation**: Set timeout to 10 seconds; implement retry logic (3 attempts)
- **Validation**: Measure 95th percentile response time in Phase 1 (target <5s)

**Assumption 11**: PDF files are <50 MB for most ESG reports
- **Rationale**: Apple's 2023 ESG report is 15 MB (114 pages); typical reports are 50-200 pages
- **Risk**: Some companies publish 500+ page reports (e.g., integrated annual reports)
- **Mitigation**: Set download size limit to 100 MB; log warnings for large files
- **Validation**: Monitor file sizes in Phase 1 testing

**Assumption 12**: Disk space for `data/pdf_cache/` is sufficient for 100+ reports
- **Rationale**: 100 reports × 20 MB average = 2 GB
- **Risk**: Disk space could fill up over time
- **Mitigation**: Implement optional cleanup of old files; document storage requirements
- **Validation**: Monitor disk usage during Phase 1

---

## Testing and Validation Assumptions

**Assumption 13**: Mocked API responses are sufficient for unit tests
- **Rationale**: Unit tests should be deterministic and not depend on external APIs
- **Risk**: Mocked responses may diverge from real API responses
- **Mitigation**: Use real API responses captured in integration tests as mock fixtures
- **Validation**: Run integration tests with real APIs weekly

**Assumption 14**: Property tests with Hypothesis can generate valid company names
- **Rationale**: Hypothesis can generate arbitrary strings; most company names are ASCII-compatible
- **Risk**: Generated names may not match real companies in APIs
- **Mitigation**: Use `@given(st.sampled_from(['Apple', 'ExxonMobil', ...]))` for realistic tests
- **Validation**: Review Hypothesis output for edge cases

**Assumption 15**: Failure-path tests can simulate API errors (429, 503, timeout)
- **Rationale**: Unit tests can mock HTTP responses with error status codes
- **Risk**: Real API errors may have different response formats
- **Mitigation**: Capture real error responses in integration tests
- **Validation**: Trigger intentional rate limit violation in integration test

---

## Protocol Compliance Assumptions

**Assumption 16**: Task 006 can achieve ≥95% test coverage on CP files
- **Rationale**: CP files are well-defined (base_provider, cdp_provider, sec_edgar_provider, multi_source_crawler)
- **Risk**: Some edge cases may be hard to cover (network errors, malformed API responses)
- **Mitigation**: Use mocked responses to simulate edge cases
- **Validation**: Run pytest-cov after test suite complete

**Assumption 17**: Multi-source crawler implementation passes mypy --strict with 0 errors
- **Rationale**: All CP files use type hints; BaseDataProvider is fully typed
- **Risk**: Third-party library types (requests, urllib) may cause mypy errors
- **Mitigation**: Add `# type: ignore` comments only where necessary; use stubs if available
- **Validation**: Run mypy --strict on CP files

**Assumption 18**: All CP functions have cyclomatic complexity (CCN) ≤10
- **Rationale**: Functions are well-factored; most API calls are <20 lines
- **Risk**: Some functions (e.g., fallback logic) may have high branching
- **Mitigation**: Refactor complex functions into smaller helpers
- **Validation**: Run lizard analysis on CP files

---

**End of Assumptions**
