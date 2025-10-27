# Task 007: Tier 2 Data Providers - Design

**Task ID**: 007-tier2-data-providers
**Date**: 2025-10-22
**Protocol**: SCA v13.8-MEA

---

## Architecture Overview

### Multi-Tier Provider Hierarchy

```
┌─────────────────────────────────────────────────────────────┐
│                  MultiSourceCrawler                         │
│  (Orchestrates providers with intelligent fallback)        │
└─────────────────────────────────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
   ┌────▼────┐         ┌────▼────┐         ┌───▼────┐
   │ TIER 1  │         │ TIER 2  │         │ TIER 3 │
   │ (Task 6)│         │(Task 7) │         │(Future)│
   └────┬────┘         └────┬────┘         └────────┘
        │                   │
  ┌─────┴─────┐      ┌──────┴──────┐
  │           │      │      │      │
SEC EDGAR   CDP**  GRI   SASB   Ticker
(10-K/20-F)        DB    Nav    Lookup
  83%        0%*

* CDP requires paid access (Task 006 finding)
** Disabled for corporate data

NEW in Task 007: GRI, SASB, Ticker Lookup
```

### Tier 2 Strategy

**Tier 2 activates when**:
1. Tier 1 returns 0 results, OR
2. Tier 1 report older than target year by >2 years

**Tier 2 priority order**:
1. **GRI Database** (comprehensive sustainability reports, global coverage)
2. **SASB Navigator** (material ESG issues, industry-specific)
3. **Ticker Lookup + SEC retry** (resolve name ambiguities)

---

## Provider Designs

### 1. GRI Database Provider

**Purpose**: Access publicly disclosed sustainability reports following GRI Standards

**Data Source**:
- GRI Sustainability Disclosure Database: https://database.globalreporting.org/
- Alternative: GRI Reports List API (if available)

**API Approach**:
```python
class GRIDatabaseProvider(BaseDataProvider):
    """
    GRI Database provider for sustainability reports

    GRI Standards are the most widely used sustainability reporting framework.
    13,000+ organizations in 100+ countries report using GRI.
    """

    def __init__(self, rate_limit: float = 0.5):
        super().__init__(source_id="gri_database", rate_limit=rate_limit)
        self.base_url = "https://database.globalreporting.org"
        # Or use API if available: https://api.globalreporting.org/v1

    def search_company(
        self,
        company_name: str,
        year: Optional[int] = None
    ) -> List[CompanyReport]:
        """
        Search GRI database for company sustainability reports

        Returns:
            List of GRI-compliant sustainability reports
        """
        # Implementation approaches:
        # Option A: Use GRI API (if exists)
        # Option B: Query GRI search endpoint
        # Option C: Download GRI dataset CSV and search locally
```

**Implementation Strategy**:
1. **First**: Check if GRI provides REST API (likely requires registration)
2. **Fallback**: Use GRI search page with requests (parse HTML/JSON response)
3. **Last Resort**: Download GRI reports list CSV, search locally

**Expected Data Quality**:
- **Coverage**: Global (13,000+ organizations)
- **Frequency**: Annual reports
- **Format**: PDF, HTML (downloadable)
- **Metadata**: Company name, year, GRI Standards version, report URL

**Challenges**:
- May require GRI account registration (free)
- Search may be web-based (HTML parsing required)
- Report URLs may be external (company websites, not GRI-hosted)

---

### 2. SASB Navigator Provider

**Purpose**: Identify material ESG issues by industry, complement SEC disclosures

**Data Source**:
- SASB Standards Navigator: https://www.sasb.org/standards/
- SASB Materiality Map: https://materiality.sasb.org/

**API Approach**:
```python
class SASBNavigatorProvider(BaseDataProvider):
    """
    SASB Navigator provider for material ESG issues

    SASB provides industry-specific materiality guidance used in
    SEC filings and investor communications.
    """

    def __init__(self, rate_limit: float = 0.5):
        super().__init__(source_id="sasb_navigator", rate_limit=rate_limit)
        self.base_url = "https://www.sasb.org"
        self.materiality_map_url = "https://materiality.sasb.org"

    def search_company(
        self,
        company_name: str,
        industry: Optional[str] = None,
        year: Optional[int] = None
    ) -> List[CompanyReport]:
        """
        Search SASB for company ESG disclosures

        Returns:
            List of SASB-aligned reports or material issue summaries
        """
        # Implementation:
        # 1. Determine company industry (SICS classification)
        # 2. Fetch SASB material issues for industry
        # 3. Search for company disclosures on SASB topics
```

**Implementation Strategy**:
1. **Industry Mapping**: Use SICS (Sustainable Industry Classification System) to map company → industry
2. **Material Issues**: Fetch SASB material issues for industry (26 general issue categories)
3. **Disclosure Search**: Look for company disclosures on SASB topics (may link to IR pages or SEC filings)

**Expected Data Quality**:
- **Coverage**: 77 industries covered by SASB Standards
- **Frequency**: Standards updated periodically, company disclosures annual
- **Format**: JSON (metadata), links to external reports
- **Metadata**: Industry, material issues, disclosure topics

**Challenges**:
- SASB may not host reports directly (links to company IR or SEC)
- Industry classification required (may need manual mapping or API)
- Not all companies follow SASB (voluntary framework)

---

### 3. Ticker Symbol Lookup Provider

**Purpose**: Resolve company name ambiguities by finding ticker symbol, then retry SEC with ticker

**Data Source**:
- Yahoo Finance API (free, no auth): `https://query1.finance.yahoo.com/v1/finance/search?q={query}`
- AlphaVantage API (free, requires key): `https://www.alphavantage.co/query?function=SYMBOL_SEARCH&keywords={query}`
- Financial Modeling Prep API (free tier): `https://financialmodelingprep.com/api/v3/search?query={query}`

**API Approach**:
```python
class TickerLookupProvider(BaseDataProvider):
    """
    Ticker symbol lookup to resolve company name → ticker → CIK

    Handles edge cases like:
    - "JPMorgan Chase" → "JPM" → retry SEC with ticker
    - "Exxon" → "XOM" → CIK 0000034088
    """

    def __init__(self, api_key: Optional[str] = None, rate_limit: float = 1.0):
        super().__init__(source_id="ticker_lookup", rate_limit=rate_limit)
        self.api_key = api_key  # For AlphaVantage (optional)
        self.yahoo_url = "https://query1.finance.yahoo.com/v1/finance/search"
        self.alpha_url = "https://www.alphavantage.co/query"

    def search_company(
        self,
        company_name: str,
        year: Optional[int] = None
    ) -> List[CompanyReport]:
        """
        Lookup ticker, then delegate to SEC EDGAR provider

        Returns:
            List of reports from SEC (via ticker → CIK)
        """
        # 1. Query Yahoo Finance for ticker
        # 2. Extract ticker symbol (e.g., "JPM")
        # 3. Call SEC provider with ticker instead of company name
        # 4. Return SEC results
```

**Implementation Strategy**:
1. **Primary**: Use Yahoo Finance (no auth required, fast)
2. **Fallback**: Use AlphaVantage if Yahoo fails (requires free API key)
3. **Chain to SEC**: Once ticker found, use SEC provider's ticker search (already implemented)

**Expected Data Quality**:
- **Coverage**: All publicly traded companies (US + international)
- **Frequency**: Real-time (ticker changes are rare)
- **Format**: JSON
- **Metadata**: Ticker symbol, company name, exchange

**Challenges**:
- Free APIs have rate limits (Yahoo: none, AlphaVantage: 5 req/min)
- Non-public companies won't have tickers (fallback to fuzzy name matching)
- International tickers may not map to SEC CIK (use exchange filter)

---

## Data Flow

### Happy Path (All Tiers Work)

```
User Request: "Apple 2023"
    │
    ▼
MultiSourceCrawler.search_company_reports()
    │
    ├─► Tier 1: SEC EDGAR
    │   └─► Found: 10-K ✓
    │
    └─► Tier 2: (skipped - Tier 1 succeeded)

Result: Apple 2023 10-K from SEC EDGAR
```

### Tier 2 Activation (Tier 1 Fails)

```
User Request: "Unilever 2023" (pre-Task 006 fix)
    │
    ▼
MultiSourceCrawler.search_company_reports()
    │
    ├─► Tier 1: SEC EDGAR
    │   └─► Found: 0 results (no 10-K for Unilever)
    │
    └─► Tier 2: GRI Database
        ├─► Search: "Unilever"
        └─► Found: "Unilever Sustainability Report 2023" ✓

Result: Unilever 2023 GRI Report
```

### Ticker Lookup Fallback (Name Ambiguity)

```
User Request: "JPMorgan Chase 2023"
    │
    ▼
MultiSourceCrawler.search_company_reports()
    │
    ├─► Tier 1: SEC EDGAR
    │   ├─► Fuzzy Match: "JPMORGAN CHASE & CO" → CIK 0000019617
    │   └─► Found: 0 10-K/20-F for 2023 (edge case)
    │
    └─► Tier 2: Ticker Lookup
        ├─► Yahoo: "JPMorgan Chase" → Ticker "JPM"
        ├─► SEC Retry: Ticker "JPM" → CIK 0000019617
        ├─► Check subsidiaries: JPMorgan Chase Bank, N.A. (CIK 0001665650)
        └─► Found: 10-K under parent entity ✓

Result: JPMorgan Chase 2023 10-K (via ticker→CIK chain)
```

---

## Multi-Source Crawler Updates

### Enhanced Priority Logic

```python
class MultiSourceCrawler:
    def __init__(self, registry_path: str):
        # Tier 1 providers
        self.tier1_providers = [
            SECEdgarProvider(),
            # CDPClimateProvider() - disabled (corporate data requires paid access)
        ]

        # NEW: Tier 2 providers
        self.tier2_providers = [
            GRIDatabaseProvider(),
            SASBNavigatorProvider(),
            TickerLookupProvider()
        ]

    def search_company_reports(
        self,
        company_name: str,
        year: Optional[int] = None,
        us_company: bool = True
    ) -> List[CompanyReport]:
        """Search with Tier 1 → Tier 2 fallback"""

        all_reports = []

        # Try Tier 1 first
        for provider in self.tier1_providers:
            reports = provider.search_company(company_name, year=year)
            if reports:
                all_reports.extend(reports)

        # If Tier 1 found recent reports, skip Tier 2
        recent_reports = [r for r in all_reports if r.year == year]
        if recent_reports:
            return all_reports

        # Activate Tier 2 fallback
        logger.info(f"Tier 1 found 0 reports for {company_name} {year}, trying Tier 2...")

        for provider in self.tier2_providers:
            reports = provider.search_company(company_name, year=year)
            if reports:
                all_reports.extend(reports)

        return all_reports
```

### Tier-Aware Reporting

```python
def download_best_report(
    self,
    company_name: str,
    year: int,
    ...
) -> Optional[str]:
    """Download best report with tier tracking"""

    reports = self.search_company_reports(company_name, year)

    # Prioritize by tier, then by source quality
    tier1_reports = [r for r in reports if r.source in ['sec_edgar']]
    tier2_reports = [r for r in reports if r.source in ['gri_database', 'sasb_navigator', 'ticker_lookup']]

    # Try Tier 1 first
    for report in tier1_reports:
        if self._download_report(report, output_path):
            logger.info(f"✓ Downloaded from Tier 1 ({report.source})")
            return output_path

    # Fallback to Tier 2
    for report in tier2_reports:
        if self._download_report(report, output_path):
            logger.info(f"✓ Downloaded from Tier 2 ({report.source})")
            return output_path

    return None
```

---

## Testing Strategy

### Unit Tests (Per Provider)

```python
# tests/crawler/data_providers/test_gri_provider.py
@pytest.mark.cp
def test_gri_search_company_found():
    """Test GRI search returns reports for known GRI reporter"""
    provider = GRIDatabaseProvider()
    reports = provider.search_company("Unilever", year=2023)
    assert len(reports) > 0
    assert reports[0].source == "gri_database"

@pytest.mark.cp
@given(company_name=st.sampled_from(["Microsoft", "Shell", "Unilever"]))
def test_gri_search_property_test(company_name: str):
    """Property test: GRI search handles various company names"""
    provider = GRIDatabaseProvider()
    reports = provider.search_company(company_name, year=2023)
    # Should not crash, may return 0 or more reports
    assert isinstance(reports, list)

@pytest.mark.cp
def test_gri_search_company_not_found():
    """Failure path: GRI search handles unknown company gracefully"""
    provider = GRIDatabaseProvider()
    reports = provider.search_company("NonexistentCompanyXYZ", year=2023)
    assert reports == []
```

### Integration Test (Phase 2)

```python
# tasks/007-tier2-data-providers/qa/phase2_integration_test.py
PHASE2_COMPANIES = [
    # Task 006 companies (baseline)
    {"name": "Apple", "year": 2023, "us": True},
    {"name": "Unilever", "year": 2023, "us": False},
    {"name": "ExxonMobil", "year": 2023, "us": True},
    {"name": "Walmart", "year": 2023, "us": True},
    {"name": "JPMorgan Chase", "year": 2023, "us": True},
    {"name": "Tesla", "year": 2023, "us": True},

    # New companies (diverse geography/industry)
    {"name": "Microsoft", "year": 2023, "us": True},
    {"name": "Shell", "year": 2023, "us": False},
    {"name": "HSBC", "year": 2023, "us": False},
    {"name": "Toyota", "year": 2023, "us": False},
    # ... 20 more companies
]

def test_phase2_availability():
    """Test multi-tier architecture achieves ≥90% availability"""
    crawler = MultiSourceCrawler("data/registry.json")

    results = []
    for company in PHASE2_COMPANIES:
        file_path = crawler.download_best_report(
            company["name"], company["year"], us_company=company["us"]
        )
        results.append({"company": company["name"], "success": file_path is not None})

    success_count = sum(1 for r in results if r["success"])
    availability = success_count / len(PHASE2_COMPANIES)

    assert availability >= 0.90, f"Availability {availability:.1%} < 90% threshold"
```

---

## Verification Plan

### Differential Testing

**Not applicable** - No existing Tier 2 implementation

### Sensitivity Testing

1. **Timeout Sensitivity**: Test with 5s, 10s, 30s provider timeouts
2. **Company Name Variations**: Test "JPMorgan" vs "JPMorgan Chase" vs "JP Morgan"
3. **Year Sensitivity**: Test 2023 vs 2022 vs 2021 data availability

### Cross-Validation

1. **GRI vs SEC Overlap**: Verify companies in both datasets have matching years
2. **Ticker→CIK Accuracy**: Validate ticker lookups against SEC official CIK list
3. **Report URL Validity**: Check downloaded reports are non-empty, valid format

---

## Success Thresholds

| Gate | Threshold | Target | Measurement |
|------|-----------|--------|-------------|
| **Data Availability** | ≥90% (27/30) | ≥95% (28-29/30) | Phase 2 integration test |
| **Tier 2 Contribution** | ≥7% (2/30) | ≥10% (3/30) | Companies unique to Tier 2 |
| **Response Time P95** | <10s | <5s | Phase 2 timing |
| **Test Coverage** | ≥90% | ≥95% | pytest --cov |
| **Type Safety** | 0 errors | 0 errors | mypy --strict |
| **Complexity** | CCN ≤15 | CCN ≤10 | lizard |

---

## Implementation Phases

### Phase 1: Context (30 min) ✓
- [x] hypothesis.md
- [x] design.md
- [ ] evidence.json
- [ ] data_sources.json
- [ ] adr.md
- [ ] assumptions.md
- [ ] cp_paths.json

### Phase 2: TDD Setup (30 min)
- [ ] Create test files with failure-path tests
- [ ] Write property tests for each provider
- [ ] Verify tests fail (no implementation yet)

### Phase 3: Implementation (2-3 hours)
- [ ] Implement GRI Database provider
- [ ] Implement SASB Navigator provider
- [ ] Implement Ticker Lookup provider
- [ ] Update MultiSourceCrawler with Tier 2 logic
- [ ] Run tests until 100% pass

### Phase 4: Integration Testing (30 min)
- [ ] Create Phase 2 integration test with 30 companies
- [ ] Run test, measure availability and response time
- [ ] Adjust provider priority if needed

### Phase 5: MEA Validation (30 min)
- [ ] Run pytest --cov (target ≥95%)
- [ ] Run mypy --strict (target 0 errors)
- [ ] Run lizard (target CCN ≤10)
- [ ] Generate artifacts and snapshot

---

**Status**: Design complete
**Next**: Create `evidence.json` with provider API documentation
