# Assumptions

**Task**: 007-tier2-data-providers
**Date**: 2025-10-22
**Protocol**: SCA v13.8-MEA

---

## Data Source Assumptions

### A1: GRI Database Accessibility
**Assumption**: GRI Sustainability Disclosure Database (database.globalreporting.org) provides programmatic access via API or structured HTML parsing.

**Basis**:
- GRI's mission is transparency and public disclosure
- Database searchable via web interface (suggests queryable backend)
- Evidence.json confirms 13,000+ reports publicly available

**Risk**: High
- GRI may require registration or authentication
- Search functionality may be client-side JavaScript (no API)
- Rate limits may be stricter than estimated (1 req/sec)

**Mitigation**:
- Test GRI website during Phase 1 implementation
- If no API, implement HTML parsing with BeautifulSoup
- If rate limits too strict, cache results for 90 days (retention policy)

**Validation**: Phase 1 unit test will attempt actual GRI query and verify response structure.

---

### A2: SASB Navigator Provides Company-Specific Guidance
**Assumption**: SASB Standards Navigator provides actionable company-specific material issue guidance, not just industry-level framework documentation.

**Basis**:
- Evidence.json mentions "company_examples" in expected fields
- SASB designed for investor use (requires company-level applicability)
- Many companies reference SASB in SEC filings (suggests linkage exists)

**Risk**: Medium
- SASB may only provide industry categories, not company mappings
- Material issue guidance may be qualitative, not linked to actual reports

**Mitigation**:
- If SASB doesn't provide company links, use SASB as metadata only
- Combine SASB material issues with SEC EDGAR full-text search
- Rely on GRI Database + Ticker Lookup to reach 90% threshold

**Validation**: Phase 1 test will query SASB for specific company and verify output includes actionable report links or disclosure guidance.

---

### A3: Free Ticker APIs Remain Available
**Assumption**: Yahoo Finance Symbol Search API and AlphaVantage free tier remain accessible without authentication (Yahoo) or with free API key (AlphaVantage) through Phase 2 testing.

**Basis**:
- Yahoo Finance API widely used in open-source projects (yfinance library)
- AlphaVantage free tier documented as stable since 2017
- No indication of pending API deprecations

**Risk**: Medium
- Yahoo Finance API is unofficial (no published terms)
- AlphaVantage may change rate limits or retire free tier
- APIs may return stale data or incorrect matches

**Mitigation**:
- Implement two-tier fallback (Yahoo primary, AlphaVantage secondary)
- Cache ticker lookups for 30 days to reduce API dependency
- Validate ticker → CIK mappings against SEC official dataset (company_tickers.json)

**Validation**: Phase 1 test will query both APIs and validate results against SEC ground truth. Phase 2 will measure ticker lookup success rate (target ≥95%).

---

## Temporal Assumptions

### A4: 2023 Sustainability Reports Published by Test Date
**Assumption**: Companies in Phase 2 test set have published 2023 sustainability reports by October 2025 (current test date).

**Basis**:
- Corporate sustainability reports typically published 3-12 months after fiscal year end
- October 2025 = 10 months after 2023 fiscal year end (most companies)
- GRI database shows continuous report additions through 2025

**Risk**: Low
- Some companies may delay ESG reporting (resource constraints, materiality changes)
- Fiscal year differences (Japan fiscal year ends March, reports in summer)

**Mitigation**:
- Phase 2 test set includes companies with known robust ESG programs
- Accept 2022 reports if 2023 not available (±1 year tolerance per hypothesis.md)
- Measure "latest available report" not strictly "2023 report"

**Validation**: Phase 2 results will report distribution of report years (2023, 2022, 2021).

---

### A5: SEC company_tickers.json Updated Daily
**Assumption**: SEC maintains daily update cadence for company_tickers.json (ticker → CIK mapping), as documented in data_sources.json.

**Basis**:
- SEC documentation states dataset updated daily
- Task 006 successfully used this dataset with fresh data

**Risk**: Low (SEC is authoritative source)

**Mitigation**:
- Cache for 24 hours as specified in retention policy
- If stale CIK detected, refetch immediately
- Implement fallback to SEC CIK lookup API if dataset unavailable

**Validation**: Phase 1 test will verify dataset timestamp is within last 24 hours.

---

## Technical Assumptions

### A6: Company Names Consistent Across Platforms
**Assumption**: Company names are sufficiently consistent across data sources (SEC, GRI, ticker APIs) that fuzzy matching + ticker lookup resolves ≥95% of edge cases.

**Basis**:
- Task 006 fuzzy matching resolved "ExxonMobil" → "Exxon Mobil Corp"
- Ticker symbols provide unambiguous fallback
- SEC CIK is universal identifier for public companies

**Risk**: Medium
- International companies may use localized names (e.g., "Société Générale" vs "Societe Generale")
- Parent/subsidiary entities may require manual mapping (JPMorgan Chase edge case)
- Private companies lack ticker symbols

**Mitigation**:
- Implement Levenshtein distance matching (threshold <3 edits)
- Use ticker lookup for public companies to resolve ambiguities
- For private companies, rely on GRI Database exact/fuzzy matching only

**Validation**: Phase 2 test will measure company name match success rate per provider. Target ≥95% unambiguous matches.

---

### A7: Response Time <5s Maintained with Tier 2 Providers
**Assumption**: Adding 3 new Tier 2 providers (GRI, SASB, Ticker Lookup) will not degrade P95 response time beyond 5-second threshold.

**Basis**:
- Task 006 P95 = 4.37s (56% margin below 5s)
- Multi-tier orchestration uses sequential queries with early exit (not parallel)
- Most companies resolve with Tier 1 (SEC) in first query

**Risk**: Medium
- GRI Database may have high latency (international servers, heavy HTML)
- Ticker lookup adds round-trip for retry path

**Mitigation**:
- Set per-provider timeout at 5 seconds (fail fast)
- Use asyncio for parallel queries within same tier
- Implement caching to reduce repeat queries (30-90 day retention)

**Validation**: Phase 2 test will measure P95 response time. If >5s, increase threshold to 10s or optimize slow providers.

---

### A8: No Authentication Required for GRI Database
**Assumption**: GRI Database allows unauthenticated access for search and report metadata retrieval.

**Basis**:
- GRI mission is public transparency
- Web interface accessible without login
- Data_sources.json lists "authentication: none_required"

**Risk**: Medium
- GRI may require registration for API access (email, organization)
- Download links may require login

**Mitigation**:
- If registration required, create free account for testing
- If downloads require auth, implement session management
- If auth blocks automation, defer to Task 008 (web scraping with auth)

**Validation**: Phase 1 test will attempt unauthenticated GRI query. If auth required, document limitation and revise implementation.

---

## Scope Assumptions

### A9: Phase 2 Test Uses English-Language Companies Only
**Assumption**: 30-company Phase 2 test set consists of companies that publish English-language ESG reports.

**Basis**:
- Task 006 test set used English-language companies (Apple, Walmart, etc.)
- Non-English reports require OCR/translation (out of scope for Task 007)
- Hypothesis.md excludes non-English reports

**Risk**: Low (explicit scope decision)

**Mitigation**:
- Phase 2 company selection criteria: "English-language companies only"
- If non-English report encountered, mark as "not available" (no penalty)

**Validation**: Phase 2 test documentation will list company selection criteria including language constraint.

---

### A10: Historical Data Limited to 2021-2023
**Assumption**: Phase 2 test searches for reports from 2021-2023 only, not older historical data.

**Basis**:
- Hypothesis.md exclusion: "Historical data (>1 year old) - Phase 2 test uses 2023 data only"
- Prospecting engine use case focuses on current ESG posture, not trends

**Risk**: Low (explicit scope decision)

**Mitigation**:
- Accept ±1 year tolerance (2022 or 2023 if 2023 not available)
- If only 2020 or older available, mark as "insufficient data"

**Validation**: Phase 2 results will report distribution of report years found.

---

## Exclusions (Explicit Non-Assumptions)

The following are **NOT** assumed (i.e., explicitly excluded from Task 007 scope):

1. **Paid API Access**: Bloomberg, MSCI, Refinitiv, Sustainalytics, corporate CDP
2. **Web Scraping**: Company IR pages, sustainability portals (deferred to Task 008)
3. **PDF Parsing Quality**: Extraction quality handled by Task 005
4. **Non-English Reports**: OCR/translation out of scope
5. **Real-Time Data**: Sustainability reports have 3-12 month lag (acceptable)
6. **100% Availability**: Target 90-95%, not 100% (some companies don't report)

---

## Assumption Validation Summary

| ID | Assumption | Risk Level | Validation Method |
|----|------------|------------|-------------------|
| A1 | GRI accessibility | High | Phase 1 unit test |
| A2 | SASB company-specific guidance | Medium | Phase 1 unit test |
| A3 | Free ticker APIs available | Medium | Phase 1 + Phase 2 tests |
| A4 | 2023 reports published | Low | Phase 2 report year distribution |
| A5 | SEC daily updates | Low | Phase 1 timestamp check |
| A6 | Company name consistency | Medium | Phase 2 match success rate |
| A7 | Response time <5s | Medium | Phase 2 P95 measurement |
| A8 | GRI no auth | Medium | Phase 1 query test |
| A9 | English-language only | Low | Test set selection criteria |
| A10 | Data 2021-2023 only | Low | Phase 2 report year distribution |

---

**Status**: Context phase in progress
**Next**: Create `cp_paths.json` to complete Context Gate
