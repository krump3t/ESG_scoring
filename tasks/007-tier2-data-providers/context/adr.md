# Architecture Decision Records (ADR)

**Task**: 007-tier2-data-providers
**Date**: 2025-10-22
**Protocol**: SCA v13.8-MEA

---

## ADR-001: Use GRI Database as Primary Tier 2 ESG Report Source

**Status**: Accepted
**Date**: 2025-10-22

### Context
Task 006 achieved 83.3% data availability using SEC EDGAR alone, but CDP corporate data requires paid access. Need alternative source for:
- International companies (non-SEC filers)
- Voluntary ESG reporters (private companies, non-profits)
- Companies with robust sustainability programs outside regulatory filings

### Decision
Implement GRI (Global Reporting Initiative) Database as primary Tier 2 provider for sustainability reports.

### Rationale
- **Coverage**: 13,000+ organizations in 100+ countries
- **Quality**: GRI Standards are most widely adopted ESG framework globally
- **Access**: Free public database with search and download
- **Reliability**: Reports reviewed by GRI, standardized format
- **Complementarity**: Fills SEC EDGAR gaps (non-US, non-public, voluntary reporters)

### Alternatives Considered
1. **MSCI ESG Research**: Rejected (requires $10K+ subscription)
2. **Bloomberg ESG**: Rejected (requires Bloomberg Terminal $24K/year)
3. **Company IR Pages**: Rejected (inconsistent structure, robots.txt issues, deferred to Task 008)
4. **CSRHub**: Rejected (aggregated ratings, not primary reports)

### Consequences
- Positive: Increases availability 5-10 percentage points (hypothesis)
- Positive: Access to non-US and voluntary reporters
- Negative: May require HTML parsing if no API available
- Negative: Reports in PDF format may vary in structure

### Validation
Phase 2 integration test will measure GRI contribution to overall availability.

---

## ADR-002: Add SASB Navigator as Material Issue Metadata Source

**Status**: Accepted
**Date**: 2025-10-22

### Context
SEC 10-K/20-F filings contain ESG disclosures, but they're scattered across 100+ page documents. SASB (Sustainability Accounting Standards Board) provides industry-specific material issue guidance.

### Decision
Implement SASB Navigator as Tier 2 metadata provider to:
1. Identify material ESG issues by industry
2. Link to sections within SEC filings where issues are disclosed
3. Enrich report metadata with materiality indicators

### Rationale
- **Investor Focus**: SASB designed for investor decision-making (aligns with prospecting use case)
- **Standardization**: 77 industries, 26 ESG categories, consistent framework
- **SEC Integration**: Many companies reference SASB in 10-K filings
- **Free Access**: SASB Standards Navigator publicly available

### Alternatives Considered
1. **TCFD (Task Force on Climate-related Financial Disclosures)**: Rejected (narrower scope, climate-only)
2. **UN SDGs (Sustainable Development Goals)**: Rejected (too broad, less actionable for investors)
3. **Proprietary Frameworks**: Rejected (not standardized)

### Consequences
- Positive: Adds 3-5 percentage points to availability (hypothesis)
- Positive: Provides industry-specific context for ESG evaluation
- Neutral: SASB provides guidance, not actual reports (complements SEC/GRI)
- Negative: Requires mapping company → industry → material issues

### Validation
Phase 2 test will measure SASB's contribution to successfully locating ESG disclosures within SEC filings.

---

## ADR-003: Implement Ticker Symbol Lookup for Company Name Disambiguation

**Status**: Accepted
**Date**: 2025-10-22

### Context
Task 006 identified edge case: JPMorgan Chase has valid CIK but 0 2023 filings. Root cause may be:
- Company name variations ("JPMorgan Chase" vs "JP Morgan" vs "JPMorgan Chase & Co")
- Parent/subsidiary entity confusion
- Fuzzy matching insufficient for complex corporate structures

### Decision
Implement Ticker Lookup provider using:
1. **Primary**: Yahoo Finance Symbol Search (free, no auth)
2. **Fallback**: AlphaVantage Symbol Search (free with API key, 5 req/min)

Lookup chain: `Company Name → Ticker Symbol → SEC CIK → Retry SEC EDGAR Search`

### Rationale
- **Precision**: Ticker symbols are unambiguous identifiers
- **Coverage**: Yahoo Finance covers all public companies globally
- **Validation**: SEC provides official ticker → CIK mapping (company_tickers.json)
- **Resilience**: Two providers reduce single point of failure

### Alternatives Considered
1. **Direct CIK Fuzzy Matching**: Already implemented, insufficient for edge cases
2. **OpenFIGI API**: Rejected (requires registration, rate limits)
3. **Polygon.io**: Rejected (requires paid subscription for full access)

### Consequences
- Positive: Resolves company name ambiguities (+2-5 percentage points hypothesis)
- Positive: Two-tier fallback improves reliability
- Negative: Adds network round-trip (ticker lookup + SEC retry)
- Negative: AlphaVantage rate limit (5 req/min) may slow bulk processing

### Validation
Phase 2 test will measure ticker lookup success rate and impact on edge cases like JPMorgan Chase.

---

## ADR-004: Use Intelligent Multi-Tier Orchestration (Tier 1 First, Tier 2 Fallback)

**Status**: Accepted
**Date**: 2025-10-22

### Context
Adding 3 new Tier 2 providers increases total to 5 providers (SEC, CDP, GRI, SASB, Ticker Lookup). Need orchestration strategy to:
- Minimize latency (don't query all providers for every company)
- Maximize success rate (ensure fallback works)
- Maintain P95 response time <5s

### Decision
Implement tiered orchestration with intelligent prioritization:

**Tier 1 (Public Regulatory APIs)**: Try first, high success rate for public companies
- SEC EDGAR (US companies)
- CDP (if corporate access available in future)

**Tier 2 (Sustainability Databases)**: Try if Tier 1 fails or returns insufficient data
- GRI Database (global sustainability reports)
- SASB Navigator (material issue metadata)
- Ticker Lookup → SEC EDGAR retry

**Activation Logic**:
```
IF company is US-based AND public:
    Query SEC EDGAR first
    IF success: return
    ELSE: try Ticker Lookup → SEC retry
    IF still fails: try GRI Database

IF company is non-US OR private:
    Query GRI Database first
    IF success: return
    ELSE: try Ticker Lookup (if public) → SEC retry
```

### Rationale
- **Efficiency**: Tier 1 sources fastest and most authoritative for public companies
- **Coverage**: Tier 2 sources fill gaps (non-US, non-public, edge cases)
- **Latency**: Sequential queries with early exit prevent unnecessary API calls
- **Resilience**: Multiple fallback paths increase overall success rate

### Alternatives Considered
1. **Parallel Query All Providers**: Rejected (wastes API quota, increases latency)
2. **User-Selected Provider**: Rejected (requires manual configuration, reduces automation)
3. **Round-Robin Load Balancing**: Rejected (ignores provider strengths)

### Consequences
- Positive: Optimizes for common case (US public companies via SEC)
- Positive: Maintains response time <5s by avoiding unnecessary queries
- Negative: Complex orchestration logic requires careful testing
- Negative: Provider priority must be configurable for different use cases

### Validation
Phase 2 integration test will measure:
- Average number of providers queried per company
- Tier 1 vs Tier 2 contribution to success rate
- P95 response time with multi-tier orchestration

---

## ADR-005: Implement Rate Limiting and Caching for Free-Tier APIs

**Status**: Accepted
**Date**: 2025-10-22

### Context
Free-tier APIs have rate limits:
- Yahoo Finance: No documented limit (conservative estimate: 10 req/sec)
- AlphaVantage: 5 req/min, 500 req/day (free tier)
- GRI Database: Unknown (assume 1 req/sec conservative)
- SEC EDGAR: 10 req/sec (documented)

Bulk processing (30+ companies in Phase 2 test) may hit rate limits.

### Decision
Implement two-layer defense:

**1. Rate Limiting (Per-Provider)**:
```python
class BaseDataProvider:
    def __init__(self, rate_limit: float = 1.0):
        self.rate_limiter = RateLimiter(calls_per_second=rate_limit)
```

**2. Caching (Short-Term)**:
- Ticker lookups: 30 days (tickers rarely change)
- Company CIK mappings: 7 days (SEC updates daily)
- GRI report metadata: 90 days (reports published annually)

### Rationale
- **Compliance**: Respects provider terms of service
- **Reliability**: Prevents 429 Too Many Requests errors
- **Performance**: Caching reduces redundant API calls
- **Cost**: Maximizes free-tier usage, defers need for paid APIs

### Alternatives Considered
1. **No Rate Limiting**: Rejected (risks API bans)
2. **Global Rate Limiter**: Rejected (too coarse, doesn't account for per-provider limits)
3. **Long-Term Caching (1 year+)**: Rejected (violates data freshness requirements)

### Consequences
- Positive: Ensures stable API access during bulk processing
- Positive: Reduces network traffic and latency
- Negative: Requires cache invalidation logic
- Negative: Cached data may be stale (mitigated by short retention periods)

### Validation
Phase 2 test will run 30 companies and verify:
- 0 rate limit errors (429 responses)
- Cache hit rate ≥50% for repeated lookups
- Data freshness (no stale CIKs or tickers)

---

## Summary

| ADR | Decision | Impact on Availability | Impact on Latency |
|-----|----------|------------------------|-------------------|
| ADR-001 | GRI Database | +5-10 pp | +0.5-1.0s |
| ADR-002 | SASB Navigator | +3-5 pp | +0.2-0.5s |
| ADR-003 | Ticker Lookup | +2-5 pp | +0.5-1.0s (retry path) |
| ADR-004 | Multi-Tier Orchestration | Multiplicative | -1.0s (early exit) |
| ADR-005 | Rate Limiting + Caching | No direct impact | -0.5s (cache hits) |

**Expected Net Effect**: +10-15 pp availability, +0.5-1.5s latency (P95 <5s maintained)

---

**Status**: Context phase in progress
**Next**: Create `assumptions.md` and `cp_paths.json`
