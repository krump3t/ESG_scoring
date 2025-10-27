# Task 006: Multi-Source Data Ingestion - Design

**Task ID**: 006-multi-source-ingestion
**Date**: 2025-10-22
**Protocol**: SCA v13.8-MEA

---

## Data Strategy

### Data Sources (4-Tier Fallback)

**Tier 1: Public APIs (Primary)**
- CDP Climate Change API (`https://data.cdp.net/api/odata/v4`)
  - Coverage: 13,000+ companies
  - Format: JSON (OData v4)
  - Auth: None required (public Open Data)
  - Rate: 10 requests/second

- SEC EDGAR API (`https://data.sec.gov/submissions/`)
  - Coverage: 10,000+ U.S. public companies
  - Format: JSON + HTML
  - Auth: User-Agent with contact email required
  - Rate: 10 requests/second (SEC policy)

**Tier 2: Comprehensive Databases (Secondary)**
- GRI Database (future)
- CSRHub API (future)

**Tier 3: Direct Company IR**
- Company investor relations websites
- Direct PDF downloads

**Tier 4: Aggregators (Fallback)**
- SustainabilityReports.com
- TCFD Hub

### Data Splits

**No train/test split required** — This is a data ingestion task, not ML training.

**Validation Approach:**
- Unit tests with mocked API responses
- Integration tests with real API endpoints (rate-limited)
- End-to-end tests with Phase 1 companies (6 companies)

### Normalization Strategy

**Unified Metadata Format**: `CompanyReport` dataclass
```python
@dataclass
class CompanyReport:
    company_name: str
    company_id: Optional[str]
    year: int
    report_type: str
    download_url: Optional[str]
    file_format: str
    source: str
    source_metadata: Dict[str, Any]
    date_published: Optional[str]
    date_retrieved: str
```

**Provider Interface**: All providers implement `BaseDataProvider` abstract class
- `search_company()` → List[CompanyReport]
- `download_report()` → bool
- `list_available_companies()` → List[Dict]

### Leakage Guards

**Data Isolation:**
- Each provider is stateless
- No caching of API responses (except rate limiting)
- No cross-company data sharing

**Rate Limiting:**
- Per-provider rate limits enforced
- Exponential backoff on failures
- Respects robots.txt for web sources

---

## Verification Plan

### Differential Testing

**CDP Data Validation:**
- Compare CDP GHG emissions against manual audit of company reports
- Target: ≥90% agreement for quantitative metrics

**SEC EDGAR Validation:**
- Compare extracted Item 1A Risk Factors against manual review
- Target: ≥85% text overlap (Jaccard similarity)

### Sensitivity Analysis

**API Failure Simulation:**
- Simulate Tier 1 failures → validate Tier 2 fallback
- Simulate network errors → validate retry logic
- Simulate rate limiting → validate backoff strategy

**Performance Testing:**
- Measure API response times (target: <5 seconds)
- Test with 6 Phase 1 companies
- Validate data availability ≥83% (5/6 companies)

---

## Success Thresholds

| Metric | Threshold | Measurement |
|--------|-----------|-------------|
| Data Availability | ≥90% | Phase 1: ≥5/6 companies |
| API Response Time | <10 seconds | 95th percentile |
| Fallback Success | ≥70% | Tier 2+ success rate when Tier 1 fails |
| Test Coverage (CP) | ≥95% | pytest-cov on CP files |
| Type Safety (CP) | 0 errors | mypy --strict |
| Complexity (CP) | CCN ≤10 | lizard analysis |

---

## Architecture

### Provider Pattern

```
BaseDataProvider (ABC)
    │
    ├── CDPClimateProvider
    │   - search_company()
    │   - download_report()
    │   - get_company_ghg_emissions()
    │
    ├── SECEdgarProvider
    │   - search_company()
    │   - download_report()
    │   - extract_risk_factors()
    │
    └── [Future Providers]
        - GRIProvider
        - CSRHubProvider
```

### Multi-Source Orchestrator

```
MultiSourceCrawler
    - providers: Dict[str, BaseDataProvider]
    - registry: data_source_registry.json

    Methods:
    - search_company_reports() → Dict[source_id, List[CompanyReport]]
    - download_best_report() → Optional[str]
    - bulk_download() → Dict[company, file_path]
```

### Fallback Logic

```
1. Determine provider priority (US company → SEC first, else CDP first)
2. Try Tier 1 providers (CDP, SEC)
3. If Tier 1 fails → Try Tier 2 (GRI, CSRHub)
4. If Tier 2 fails → Try Tier 3 (Direct IR)
5. If Tier 3 fails → Try Tier 4 (Aggregators)
6. Return first successful download or None
```

---

## Dependencies

**Python Packages:**
- `requests>=2.31.0` — HTTP requests
- `urllib3>=2.0.0` — URL parsing
- `pytest>=7.0` — Testing
- `pytest-cov>=4.0` — Coverage
- `mypy>=1.0` — Type checking

**External APIs:**
- CDP Open Data Portal (no API key)
- SEC EDGAR (User-Agent required)

---

## Risk Mitigation

**API Changes:**
- Version control API endpoints in registry
- Monitor for breaking changes
- Implement schema validation

**Rate Limiting:**
- Enforce rate limits per provider
- Exponential backoff on 429 responses
- Request queuing if needed

**Data Quality:**
- Validate response schemas
- Check file integrity (SHA256)
- Log all API errors for monitoring
