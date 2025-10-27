# Task 007: Tier 2 Data Providers - Hypothesis

**Task ID**: 007-tier2-data-providers
**Date**: 2025-10-22
**Protocol**: SCA v13.8-MEA
**Dependencies**: Task 006 (Multi-Source Ingestion - 83.3% baseline)

---

## Primary Hypothesis

**Adding Tier 2 data providers (GRI Database, SASB Navigator, Ticker Symbol Lookup) will increase ESG report availability from 83.3% (SEC EDGAR only) to ≥90% through intelligent multi-tier fallback, while maintaining API response time P95 <5 seconds.**

### Sub-Hypotheses

1. **GRI Database Provider**: Publicly available sustainability reports from GRI Standards reporters will add 5-10 percentage points to availability
2. **SASB Navigator**: Material ESG issues by industry will complement SEC disclosures, adding 3-5 percentage points
3. **Ticker Symbol Lookup**: Resolving company name → ticker → CIK will recover edge cases like JPMorgan Chase, adding 2-5 percentage points
4. **Response Time**: Tier 2 providers will not degrade P95 response time below 5 second threshold (currently 4.37s with 56% margin)

---

## Success Metrics

### Primary Metrics

| Metric | Baseline (Task 006) | Target | Threshold | Measurement |
|--------|---------------------|--------|-----------|-------------|
| **Data Availability** | 83.3% (5/6) | ≥95% | ≥90% (27/30) | Phase 2 integration test (30 companies) |
| **API Response Time (P95)** | 4.37s | <5s | <10s | Phase 2 integration test timing |
| **Tier 2 Contribution** | 0% | 10-15% | ≥7% | Companies recovered by Tier 2 only |
| **Fallback Success Rate** | N/A | ≥80% | ≥60% | Tier 2 used when Tier 1 fails |

### Secondary Metrics

| Metric | Target | Threshold | Measurement |
|--------|--------|-----------|-------------|
| **Test Coverage (CP)** | ≥95% | ≥90% | pytest --cov on CP files |
| **Type Safety** | 0 errors | 0 errors | mypy --strict on CP files |
| **Complexity** | CCN ≤10 | CCN ≤15 | lizard on CP files |
| **Provider Reliability** | ≥95% uptime | ≥90% | Integration test success rate per provider |

---

## Critical Path

### CP Files (New Implementations)

1. `agents/crawler/data_providers/gri_provider.py` - GRI Database API integration
2. `agents/crawler/data_providers/sasb_provider.py` - SASB Navigator integration
3. `agents/crawler/data_providers/ticker_lookup.py` - Yahoo Finance/AlphaVantage ticker resolver
4. `agents/crawler/multi_source_crawler.py` - **Updated** with Tier 2 orchestration

### Exclusions

- Paid APIs (Bloomberg ESG, MSCI, Refinitiv) - out of scope (no budget)
- Web scraping (company IR pages) - deferred to Task 008 (robots.txt, rate limits)
- Historical data (>1 year old) - Phase 2 test uses 2023 data only
- Non-English reports - Phase 2 test uses English-language companies

---

## Experimental Design

### Phase 2 Integration Test

**Test Set**: 30 diverse companies (5x Task 006 size)

**Company Selection Criteria**:
- **Geography**: 50% US, 30% Europe, 20% Asia-Pacific (diverse filing requirements)
- **Industry**: Tech, Energy, Consumer Goods, Finance, Healthcare, Manufacturing (SASB coverage)
- **Size**: Mix of S&P 500, FTSE 100, and mid-cap (GRI reporting varies by size)
- **Known Edge Cases**: Include JPMorgan Chase, companies with name variations, non-SEC filers

**Test Procedure**:
1. Run multi-source crawler with all 5 providers (SEC, CDP, GRI, SASB, Ticker Lookup)
2. Measure per-company success rate, response time, source used
3. Calculate tier-specific contribution (Tier 1 only vs Tier 2 recovery)
4. Validate downloaded reports (non-empty, valid format)

**Success Criteria**:
- ≥90% availability (27/30 companies)
- P95 response time <5s
- ≥7% Tier 2 contribution (2+

 companies recovered by Tier 2 only)

---

## Data Validation Plan

### Differential Testing

**Not applicable** - No existing Tier 2 implementation to compare against

### Sensitivity Testing

1. **Provider Timeout Sensitivity**: Test with 5s, 10s, 30s timeouts (expect minimal impact on success rate)
2. **Company Name Variation**: Test "JPMorgan Chase" vs "JP Morgan" vs "JPMorgan Chase & Co" (expect ticker lookup to resolve)
3. **Year Sensitivity**: Test 2023, 2022, 2021 data (expect availability to degrade for older years)
4. **Tier Priority**: Swap Tier 1/Tier 2 priority (expect minimal change if both sources have data)

### Cross-Validation

1. **GRI Reports vs SEC 10-K**: Compare report years for overlap (expect 100% match on year)
2. **SASB Material Issues vs 10-K Disclosures**: Validate SASB issues mentioned in SEC filings (expect ≥80% alignment)
3. **Ticker Lookup Accuracy**: Validate ticker → CIK mapping against SEC official list (expect 100% accuracy)

---

## Statistical Power

### Sample Size

**Phase 2 Test**: 30 companies
- **Baseline**: 83.3% (25/30 expected successes)
- **Target**: 90% (27/30 expected successes)
- **Improvement**: +2 companies (+6.7 percentage points)

**Power Calculation**:
- α = 0.05 (significance level)
- β = 0.20 (power = 80%)
- Effect size: 6.7 percentage points
- **Conclusion**: 30 companies provides 80% power to detect 6.7pp improvement

### Confidence Intervals

**90% Availability** (27/30):
- 95% CI: [73.5%, 97.9%] (binomial exact)
- Margin of error: ±12.2 percentage points

**Conclusion**: With 30 companies, we can confidently detect if Tier 2 providers achieve ≥90% threshold.

---

## Risks & Mitigations

### Risk 1: GRI Database API Availability
- **Risk**: GRI may not have free public API (requires registration or scraping)
- **Mitigation**: Test GRI website first; if no API, use SASB + Ticker Lookup to reach 90%
- **Contingency**: Skip GRI, add CSRHub or Company IR scraper in Task 008

### Risk 2: SASB Data Insufficient
- **Risk**: SASB Navigator may only provide material issue *lists*, not actual reports
- **Mitigation**: Verify SASB API returns downloadable reports or ESG disclosure links
- **Contingency**: Use SASB for metadata only, rely on SEC/GRI for reports

### Risk 3: Ticker Lookup Rate Limits
- **Risk**: Free ticker APIs (Yahoo, AlphaVantage) may have strict rate limits (5 req/min)
- **Mitigation**: Implement caching, batch lookups, use multiple API keys
- **Contingency**: Fall back to SEC CIK-based fuzzy matching (already implemented in Task 006)

### Risk 4: Response Time Degradation
- **Risk**: Adding 3 new providers may increase P95 >5s
- **Mitigation**: Use asyncio for parallel provider queries, set 5s timeout per provider
- **Contingency**: Increase threshold to 10s if quality justifies latency

### Risk 5: False Positives
- **Risk**: Providers may return unrelated reports (wrong company, wrong year)
- **Mitigation**: Validate company name match (Levenshtein distance <3), year match exact
- **Contingency**: Add post-download validation step, reject mismatches

---

## Exclusions & Assumptions

### Exclusions
- Paid APIs (Bloomberg, MSCI, Refinitiv, Sustainalytics)
- Web scraping (IR pages, sustainability portals)
- PDF parsing quality (Task 005 handles extraction)
- Non-English language reports
- Historical data beyond 2021

### Assumptions
1. GRI Database has accessible API or downloadable dataset
2. SASB Navigator provides company-specific material issues or report links
3. Free ticker APIs (Yahoo Finance, AlphaVantage, FMP) remain available
4. 2023 sustainability reports are published by October 2025 (test date)
5. Companies maintain consistent naming across platforms
6. Response time includes network latency (no local caching for first test)

---

## Validation Gates

### Context Gate (Pass/Fail)
- [x] `hypothesis.md` - This file
- [ ] `design.md` - Technical architecture
- [ ] `evidence.json` - ≥3 primary sources
- [ ] `data_sources.json` - Provider APIs with provenance
- [ ] `adr.md` - Architecture decisions
- [ ] `assumptions.md` - Explicit assumptions
- [ ] `cp_paths.json` - Critical path file patterns

### TDD Guard (Pass/Fail)
- [ ] ≥1 test per CP file marked `@pytest.mark.cp`
- [ ] ≥1 Hypothesis `@given` property test per provider
- [ ] ≥1 failure-path test per provider
- [ ] Tests written BEFORE implementation

### Coverage Gate (Pass/Fail)
- [ ] ≥95% line coverage on new CP files
- [ ] ≥95% branch coverage on new CP files

### Type Safety Gate (Pass/Fail)
- [ ] `mypy --strict` = 0 errors on new CP files

### Complexity Gate (Pass/Fail)
- [ ] Lizard CCN ≤10 on all functions in new CP files

### Integration Gate (Pass/Fail)
- [ ] Phase 2 test: ≥90% availability (27/30 companies)
- [ ] Phase 2 test: P95 <5s response time
- [ ] ≥7% Tier 2 contribution

---

## Timeline Estimate

- **Context Phase**: 30 minutes (this document + design.md + evidence.json)
- **Implementation Phase**: 2-3 hours (3 providers + tests)
- **Integration Testing**: 30 minutes (30-company test run)
- **MEA Validation**: 30 minutes (coverage, type safety, complexity)
- **Total**: **4-5 hours**

---

**Status**: Context in progress
**Next**: Create `design.md` with provider architecture
