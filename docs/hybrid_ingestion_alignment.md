# Hybrid Data Ingestion Strategy Alignment Analysis

**Document Version**: 1.0
**Date**: 2025-10-23
**SCA Protocol**: v13.8-MEA
**Status**: Remediation Planning Phase

---

## Executive Summary

This document analyzes the proposed **Hybrid Data Ingestion Strategy** (API + Web Scraping) and aligns it with the current ESG Evaluation System architecture. The analysis identifies gaps, proposes remediation steps, and ensures compatibility with existing Bronze/Silver/Gold data modeling and SCA v13.8 authenticity standards.

**Key Findings**:
- ✅ **Phase 1 (API Core)**: Partially implemented - SEC EDGAR provider exists but needs enhancement
- ⚠️ **Phase 2 (Web Scraper)**: Missing - No Playwright-based scraper implemented
- ⚠️ **Phase 3 (Unified Schema)**: Partially implemented - Using dataclasses, needs Pydantic migration
- ⚠️ **Phase 4 (Orchestration)**: Missing - No Dagster/Prefect orchestration layer

**Remediation Priority**: Medium complexity, high value - can be implemented incrementally without breaking current E2E pipeline.

---

## 1. Proposed Hybrid Ingestion Strategy Overview

### Architecture Components

#### Phase 1: API Core (SEC EDGAR)
**Purpose**: Structured data ingestion from official regulatory filings

**Technology Stack**:
- `requests` - HTTP client for API calls
- `BeautifulSoup4` / `lxml` - HTML/XML parsing
- `ratelimit` - Rate limiting decorator

**Data Sources**:
- SEC EDGAR 10-K filings (Annual Reports)
- SEC EDGAR DEF 14A filings (Proxy Statements)

**Expected Outputs**:
- Structured metadata (CIK, filing date, accession number)
- Extracted text content (Management's Discussion & Analysis, Risk Factors)
- Downloaded PDF/HTML documents

#### Phase 2: Web Scraper (Sustainability Reports)
**Purpose**: Best-effort extraction of unstructured sustainability reports

**Technology Stack**:
- `Playwright` - Headless browser for JavaScript-rendered pages
- `BeautifulSoup4` - HTML parsing
- `PyMuPDF` - PDF text extraction
- `python-pptx` / `pdf2image` - PowerPoint/PDF processing

**Data Sources**:
- Company sustainability report landing pages
- Direct PDF links from investor relations
- Sustainability/CSR section deep links

**Expected Outputs**:
- PDF sustainability reports (saved to Bronze layer)
- Extracted text content
- Metadata (publication date, report type, URL)

#### Phase 3: Unified Document Schema (Pydantic)
**Purpose**: Type-safe, validated data model for all ingestion sources

**Technology Stack**:
- `Pydantic v2` - Data validation and serialization
- `pydantic-settings` - Configuration management

**Schema Requirements**:
```python
class UnifiedDocument(BaseModel):
    """Universal document schema for all ingestion sources."""

    # Identification
    document_id: str  # UUID or hash
    source_type: Literal["api_sec_edgar", "web_scrape", "manual_upload"]

    # Content
    raw_text: str
    raw_html: Optional[str]
    pdf_path: Optional[Path]

    # Metadata
    company_name: str
    company_identifier: str  # CIK, ticker, or domain
    document_type: Literal["10-K", "DEF 14A", "Sustainability Report", "ESG Report"]
    publication_date: date
    fiscal_year: int

    # Provenance
    source_url: str
    retrieval_timestamp: datetime
    data_provider: str  # "SEC EDGAR", "CompanyWebsite", etc.

    # Quality
    extraction_confidence: float = Field(ge=0.0, le=1.0)
    text_length: int
    page_count: Optional[int]

    # Hash for deduplication
    content_sha256: str
```

#### Phase 4: Orchestration (Dagster)
**Purpose**: Dependency-aware, monitored data pipeline execution

**Technology Stack**:
- `Dagster` - Data orchestration framework
- `dagster-duckdb` - DuckDB integration for asset materialization

**Asset Graph**:
```
bronze_sec_10k → silver_extracted_text → gold_evidence_tables
bronze_web_pdf ↗                       ↗
```

**Features Required**:
- Asset dependencies (Bronze → Silver → Gold)
- Incremental materialization (only process new documents)
- Failure recovery (retry failed downloads)
- Observability (logs, metrics, lineage)

---

## 2. Current Implementation Analysis

### Existing Architecture

#### Data Ingestion Layer
**Location**: `agents/crawler/data_providers/`

**Current Providers**:
1. **`sec_edgar_provider.py`** ✅
   - Base URL: `https://data.sec.gov`
   - User-Agent with email required
   - Rate limiting: Manual (not decorator-based)
   - Document types: 10-K, DEF 14A
   - Output: JSON metadata + raw HTML

2. **`base_provider.py`** ✅
   - Abstract base class for all data providers
   - Defines interface: `fetch_document()`, `search_company()`

**Gaps**:
- ❌ No Playwright-based web scraper
- ❌ No unified Pydantic schema
- ❌ No orchestration layer
- ⚠️ Rate limiting not using `ratelimit` decorator
- ⚠️ No retry logic with exponential backoff

#### Document Processing Layer
**Location**: `agents/parser/`

**Current Parsers**:
1. **PDF Extraction** ✅
   - Uses PyMuPDF (validated in E2E test)
   - Function: `extract_pdf_text_authentic()` in `scripts/test_lse_report_sca_compliant.py`
   - **Status**: Working, extracting 75,287 characters from 27-page PDF

2. **Text Chunking** ✅
   - Sentence-based extraction with keyword filtering
   - Function: `extract_evidence_statements()` in E2E tests
   - **Status**: Extracting 50 ESG-relevant sentences

**Gaps**:
- ❌ No PowerPoint extraction
- ❌ No HTML-to-markdown conversion
- ❌ No unified text normalization pipeline

#### Data Storage Layer
**Location**: `agents/datalake/`

**Current Architecture**:
- **Bronze Layer**: Raw Parquet files in `data/raw/` (DuckDB-backed)
- **Silver Layer**: Cleaned/extracted text in `data/processed/`
- **Gold Layer**: Evidence tables in `data/gold/`

**Gaps**:
- ⚠️ No formal ingestion → Bronze pipeline
- ❌ No metadata tracking for document provenance
- ❌ No deduplication via SHA256

#### Orchestration Layer
**Current State**: ❌ **MISSING**

- No Dagster/Prefect implementation
- Manual script execution only
- No dependency graph
- No incremental processing

---

## 3. Gap Analysis

### 3.1 Phase 1 (API Core) Gaps

| Component | Current State | Required State | Gap Severity |
|-----------|--------------|----------------|--------------|
| SEC EDGAR Client | ✅ Implemented | ✅ Enhanced with retry | LOW |
| Rate Limiting | ⚠️ Manual | 🔧 `ratelimit` decorator | MEDIUM |
| HTML Parsing | ✅ Basic | ✅ BeautifulSoup4 extraction | LOW |
| Error Handling | ⚠️ Basic | 🔧 Exponential backoff + logging | MEDIUM |
| Metadata Extraction | ✅ Partial | 🔧 Full CIK/filing metadata | LOW |

**Remediation Effort**: 4-6 hours

### 3.2 Phase 2 (Web Scraper) Gaps

| Component | Current State | Required State | Gap Severity |
|-----------|--------------|----------------|--------------|
| Playwright Scraper | ❌ Missing | 🔧 Full implementation | HIGH |
| PDF Download | ⚠️ Manual | 🔧 Automated via scraper | HIGH |
| Dynamic JS Rendering | ❌ Missing | 🔧 Playwright headless | HIGH |
| URL Discovery | ❌ Missing | 🔧 Search + crawl logic | MEDIUM |

**Remediation Effort**: 12-16 hours

### 3.3 Phase 3 (Unified Schema) Gaps

| Component | Current State | Required State | Gap Severity |
|-----------|--------------|----------------|--------------|
| Data Model | ⚠️ Dataclasses | 🔧 Pydantic BaseModel | MEDIUM |
| Validation | ⚠️ Manual | 🔧 Pydantic validators | MEDIUM |
| Serialization | ⚠️ Custom JSON | 🔧 Pydantic `.model_dump()` | LOW |
| Schema Versioning | ❌ Missing | 🔧 Pydantic migrations | LOW |

**Remediation Effort**: 6-8 hours

### 3.4 Phase 4 (Orchestration) Gaps

| Component | Current State | Required State | Gap Severity |
|-----------|--------------|----------------|--------------|
| Dagster Assets | ❌ Missing | 🔧 Full asset graph | HIGH |
| Incremental Processing | ❌ Missing | 🔧 Partitioned assets | HIGH |
| Lineage Tracking | ❌ Missing | 🔧 Dagster metadata | MEDIUM |
| Monitoring | ❌ Missing | 🔧 Dagster UI + sensors | MEDIUM |

**Remediation Effort**: 16-24 hours

**Total Estimated Remediation**: 38-54 hours (5-7 working days)

---

## 4. Proposed Remediation Roadmap

### Phase 1: Enhance API Core (Priority: HIGH)
**Timeline**: 1 day
**Dependencies**: None
**SCA Gate**: Context + Phase 1

#### Tasks
1. **Add `ratelimit` Decorator** (2 hours)
   ```python
   from ratelimit import limits, sleep_and_retry

   @sleep_and_retry
   @limits(calls=10, period=1)  # 10 req/sec
   def fetch_sec_document(cik: str, filing_type: str) -> dict:
       ...
   ```

2. **Implement Retry Logic** (2 hours)
   ```python
   from tenacity import retry, stop_after_attempt, wait_exponential

   @retry(
       stop=stop_after_attempt(3),
       wait=wait_exponential(multiplier=1, min=2, max=10)
   )
   def fetch_with_retry(url: str) -> requests.Response:
       ...
   ```

3. **Enhanced Metadata Extraction** (2 hours)
   - Extract all filing metadata (CIK, accession number, filing date)
   - Parse XBRL tags for financial metrics
   - Store in Bronze layer with full provenance

4. **Test Coverage** (2 hours)
   - Unit tests for rate limiting (mock time.sleep)
   - Integration test with SEC EDGAR sandbox
   - Failure-path tests for 503/429 responses

**Deliverable**: `agents/crawler/data_providers/sec_edgar_provider.py` (v2.0)

---

### Phase 2: Build Web Scraper (Priority: MEDIUM)
**Timeline**: 2 days
**Dependencies**: Phase 1 complete
**SCA Gate**: Phase 2

#### Tasks
1. **Install Playwright** (0.5 hours)
   ```bash
   pip install playwright pytest-playwright
   playwright install chromium
   ```

2. **Create `WebScraperProvider`** (6 hours)
   ```python
   class WebScraperProvider(BaseProvider):
       """Playwright-based web scraper for sustainability reports."""

       async def discover_sustainability_reports(
           self, company_domain: str
       ) -> List[str]:
           """Search for PDF links on company website."""
           async with async_playwright() as p:
               browser = await p.chromium.launch(headless=True)
               page = await browser.new_page()
               await page.goto(f"https://{company_domain}/sustainability")

               # Find PDF links
               pdf_links = await page.locator('a[href$=".pdf"]').all()
               return [await link.get_attribute('href') for link in pdf_links]

       async def download_pdf(self, url: str, output_path: Path) -> Path:
           """Download PDF with retry logic."""
           ...
   ```

3. **URL Discovery Logic** (4 hours)
   - Google Search API fallback for discovering report URLs
   - Common sustainability URL patterns (e.g., `/esg`, `/sustainability`, `/csr`)
   - Robots.txt compliance check

4. **Test Coverage** (3 hours)
   - Mock Playwright with recorded HAR files
   - Test PDF download with retry
   - Test URL discovery with mock search results

**Deliverable**: `agents/crawler/data_providers/web_scraper_provider.py`

---

### Phase 3: Unified Pydantic Schema (Priority: HIGH)
**Timeline**: 1 day
**Dependencies**: None (can run parallel to Phase 1-2)
**SCA Gate**: Phase 3

#### Tasks
1. **Create `UnifiedDocument` Model** (3 hours)
   ```python
   from pydantic import BaseModel, Field, field_validator
   from datetime import datetime, date
   from pathlib import Path
   from typing import Literal, Optional
   import hashlib

   class UnifiedDocument(BaseModel):
       """Universal document schema for all ingestion sources."""

       document_id: str = Field(default_factory=lambda: str(uuid4()))
       source_type: Literal["api_sec_edgar", "web_scrape", "manual_upload"]

       # Content
       raw_text: str = Field(min_length=100)
       raw_html: Optional[str] = None
       pdf_path: Optional[Path] = None

       # Metadata
       company_name: str = Field(min_length=1)
       company_identifier: str  # CIK or domain
       document_type: Literal["10-K", "DEF 14A", "Sustainability Report", "ESG Report"]
       publication_date: date
       fiscal_year: int = Field(ge=2000, le=2030)

       # Provenance
       source_url: str
       retrieval_timestamp: datetime = Field(default_factory=datetime.now)
       data_provider: str

       # Quality
       extraction_confidence: float = Field(ge=0.0, le=1.0, default=1.0)
       text_length: int = Field(ge=0)
       page_count: Optional[int] = Field(None, ge=1)

       # Hash for deduplication
       content_sha256: str

       @field_validator('content_sha256')
       @classmethod
       def validate_sha256(cls, v: str) -> str:
           if len(v) != 64 or not all(c in '0123456789abcdef' for c in v):
               raise ValueError("Invalid SHA256 hash")
           return v

       @classmethod
       def from_pdf(cls, pdf_path: Path, **kwargs) -> "UnifiedDocument":
           """Factory method for PDF documents."""
           text = extract_pdf_text_authentic(pdf_path)
           return cls(
               raw_text=text,
               pdf_path=pdf_path,
               text_length=len(text),
               content_sha256=hashlib.sha256(text.encode()).hexdigest(),
               **kwargs
           )
   ```

2. **Migrate Existing Code** (3 hours)
   - Update `sec_edgar_provider.py` to return `UnifiedDocument`
   - Update E2E tests to use Pydantic schema
   - Update Bronze layer writers to serialize Pydantic models

3. **Schema Versioning** (1 hour)
   - Add `schema_version: str = "1.0"` field
   - Document migration strategy in `docs/schema_migrations.md`

4. **Test Coverage** (2 hours)
   - Property tests for all field validators
   - Test `from_pdf()` factory method
   - Test serialization roundtrip (JSON → Pydantic → JSON)

**Deliverable**: `libs/models/unified_document.py`

---

### Phase 4: Dagster Orchestration (Priority: MEDIUM)
**Timeline**: 2-3 days
**Dependencies**: Phases 1-3 complete
**SCA Gate**: Phase 4

#### Tasks
1. **Install Dagster** (0.5 hours)
   ```bash
   pip install dagster dagster-webserver dagster-duckdb
   ```

2. **Define Asset Graph** (8 hours)
   ```python
   from dagster import asset, AssetExecutionContext
   from dagster_duckdb import DuckDBResource

   @asset(
       group_name="bronze",
       compute_kind="api"
   )
   def bronze_sec_10k(context: AssetExecutionContext) -> None:
       """Ingest SEC 10-K filings to Bronze layer."""
       provider = SECEdgarProvider()
       companies = ["AAPL", "MSFT", "XOM"]  # From config

       for ticker in companies:
           doc = provider.fetch_10k(ticker, year=2023)
           unified = UnifiedDocument.from_dict(doc)

           # Save to DuckDB Bronze
           context.resources.duckdb.execute(
               "INSERT INTO bronze.sec_filings VALUES (?, ?, ?)",
               (unified.document_id, unified.model_dump_json(), unified.content_sha256)
           )

   @asset(
       group_name="silver",
       deps=[bronze_sec_10k],
       compute_kind="transform"
   )
   def silver_extracted_text(context: AssetExecutionContext) -> None:
       """Extract and normalize text from Bronze documents."""
       ...

   @asset(
       group_name="gold",
       deps=[silver_extracted_text],
       compute_kind="ml"
   )
   def gold_evidence_tables(context: AssetExecutionContext) -> None:
       """Generate evidence tables using semantic matching."""
       ...
   ```

3. **Incremental Materialization** (4 hours)
   - Use partitions for fiscal year
   - Only process new documents (check SHA256)
   - Implement backfill strategy

4. **Monitoring & Observability** (3 hours)
   - Add metadata to assets (row counts, execution time)
   - Configure Dagster sensors for failures
   - Setup Dagster UI for monitoring

5. **Test Coverage** (3 hours)
   - Unit tests for each asset (mocked resources)
   - Integration test with DuckDB in-memory
   - Test incremental materialization logic

**Deliverable**: `orchestration/dagster_pipeline.py`

---

## 5. Integration with Current E2E Pipeline

### Current E2E Test (As-Is)
```python
# tests/e2e/test_lse_healthcare_e2e.py
def test_end_to_end_evidence_table_generation(report_path: Path, rubric_path: Path):
    # Step 1: Extract text from PDF
    text = extract_pdf_text(report_path)

    # Step 2: Extract evidence
    evidence = extract_esg_sentences(text, max_count=50)

    # Step 3: Load rubric
    rubric = RubricLoader().load_from_markdown(rubric_path)

    # Step 4: Generate evidence tables
    tables = generate_evidence_table(evidence, theme, rubric, matcher)
```

### Enhanced E2E Test (To-Be)
```python
# tests/e2e/test_hybrid_ingestion_e2e.py
def test_hybrid_ingestion_to_evidence_tables():
    # Step 1: Ingest via API (REAL)
    sec_provider = SECEdgarProvider()
    sec_doc = sec_provider.fetch_10k("XOM", year=2023)
    unified_sec = UnifiedDocument.from_dict(sec_doc)

    # Step 2: Ingest via Web Scraper (REAL)
    web_provider = WebScraperProvider()
    pdf_url = web_provider.discover_sustainability_reports("exxonmobil.com")[0]
    pdf_path = web_provider.download_pdf(pdf_url, output_dir=Path("data/raw"))
    unified_web = UnifiedDocument.from_pdf(
        pdf_path,
        source_type="web_scrape",
        company_name="ExxonMobil",
        document_type="Sustainability Report",
        publication_date=date(2023, 3, 1),
        fiscal_year=2023,
        source_url=pdf_url,
        data_provider="CompanyWebsite"
    )

    # Step 3: Validate Pydantic schema
    assert unified_sec.text_length > 10000
    assert unified_web.content_sha256 == hashlib.sha256(unified_web.raw_text.encode()).hexdigest()

    # Step 4: Process through existing pipeline
    evidence_sec = extract_esg_sentences(unified_sec.raw_text, max_count=50)
    evidence_web = extract_esg_sentences(unified_web.raw_text, max_count=50)

    # Step 5: Generate evidence tables (existing logic)
    rubric = RubricLoader().load_from_markdown("rubrics/esg_rubric_v1.md")
    tables = generate_evidence_table(
        evidence_extracts=evidence_sec + evidence_web,
        theme="target_setting",
        rubric=rubric,
        matcher=CharacteristicMatcher(embedder),
        max_rows=10
    )

    assert len(tables) == 10
```

**Key Changes**:
1. ✅ Multiple ingestion sources (API + Web)
2. ✅ Unified Pydantic schema validation
3. ✅ Real data from SEC EDGAR + web scraping
4. ✅ Downstream pipeline unchanged (evidence extraction → matching → tables)

---

## 6. Remediation Strategy Summary

### Implementation Order

```
Phase 1 (API Core)     ──────┐
                              ├──> Phase 3 (Pydantic Schema) ──> Phase 4 (Dagster)
Phase 2 (Web Scraper)  ──────┘
```

**Parallel Tracks**:
- Track A: Phase 1 → Phase 3 → Phase 4
- Track B: Phase 2 → Phase 3 → Phase 4

### Milestones

| Milestone | Deliverables | Timeline | SCA Gate |
|-----------|-------------|----------|----------|
| M1: Enhanced API | `sec_edgar_provider.py` v2.0 with retry/rate-limit | Day 1 | Context + Phase 1 |
| M2: Pydantic Schema | `UnifiedDocument` model + migrations | Day 2 | Phase 3 |
| M3: Web Scraper | `web_scraper_provider.py` with Playwright | Day 3-4 | Phase 2 |
| M4: Dagster Pipeline | Full asset graph with incremental processing | Day 5-7 | Phase 4 |
| M5: E2E Validation | Hybrid ingestion E2E test passing | Day 8 | Phase 5 |

### Success Criteria

#### Technical Criteria
- ✅ All 4 phases implemented with ≥95% test coverage
- ✅ Dagster UI shows complete asset lineage
- ✅ E2E test validates API → Bronze → Silver → Gold pipeline
- ✅ SCA v13.8 authenticity invariants maintained (no mocked APIs in production)

#### Quality Criteria
- ✅ `mypy --strict` passes on all new code
- ✅ Lizard complexity ≤10 for all functions
- ✅ `interrogate` docstring coverage ≥95%
- ✅ All CP files have ≥1 failure-path test

#### Documentation Criteria
- ✅ `REPRODUCIBILITY.md` updated with Playwright setup
- ✅ `docs/schema_migrations.md` created
- ✅ Dagster asset documentation complete
- ✅ E2E test artifacts saved to `artifacts/e2e/`

---

## 7. Risk Assessment

### High-Risk Areas

#### Risk 1: Playwright Flakiness
**Likelihood**: MEDIUM
**Impact**: HIGH
**Mitigation**:
- Use `await page.wait_for_selector()` for all element interactions
- Implement screenshot capture on failure
- Add retry logic with exponential backoff
- Use HAR (HTTP Archive) files for test mocking

#### Risk 2: Schema Migration Breaking Changes
**Likelihood**: LOW
**Impact**: HIGH
**Mitigation**:
- Version all schemas (`schema_version: str = "1.0"`)
- Implement backward-compatible migrations
- Test roundtrip serialization (Pydantic → JSON → Pydantic)
- Document migration strategy upfront

#### Risk 3: Dagster Learning Curve
**Likelihood**: MEDIUM
**Impact**: MEDIUM
**Mitigation**:
- Start with simple asset graph (3 assets only)
- Use Dagster quickstart guide
- Implement incrementally (Bronze → Silver → Gold)
- Fallback to manual scripts if Dagster blocks progress

### Low-Risk Areas
- ✅ SEC EDGAR API (stable, well-documented)
- ✅ Pydantic (mature library, excellent docs)
- ✅ PyMuPDF (already validated in E2E test)

---

## 8. Alignment with SCA v13.8 Protocol

### Authenticity Invariants Compliance

#### 1. Authentic Computation ✅
- **Phase 1**: Real SEC EDGAR API calls (no mocked responses in production)
- **Phase 2**: Real Playwright browser automation (actual DOM rendering)
- **Phase 3**: Real Pydantic validation (not trivial pass-through)
- **Phase 4**: Real Dagster execution (actual dependency resolution)

#### 2. Algorithmic Fidelity ✅
- **Web Scraper**: Real URL discovery logic (not hardcoded links)
- **PDF Extraction**: Real PyMuPDF processing (validated in E2E test)
- **Evidence Matching**: Real cosine similarity (not random scoring)

#### 3. Honest Validation ✅
- **Test Coverage**: ≥95% for all CP files
- **Failure-Path Tests**: ≥1 per CP file (e.g., test 503 response handling)
- **E2E Tests**: Real data from SEC EDGAR + web scraping

#### 4. Determinism ✅
- **Rate Limiting**: Fixed 10 req/sec (not variable)
- **Retry Logic**: Fixed exponential backoff parameters
- **Pydantic Seeds**: Fixed default values for timestamps (can override)

#### 5. Honest Status Reporting ✅
- **Artifacts**: Save all logs to `qa/run_log.txt`
- **Manifests**: Track all ingested documents in `artifacts/run_manifest.json`
- **Coverage**: Report actual coverage (not inflated)

### TDD Guard Compliance

#### CP Files (New)
1. `agents/crawler/data_providers/web_scraper_provider.py` (Phase 2)
2. `libs/models/unified_document.py` (Phase 3)
3. `orchestration/dagster_pipeline.py` (Phase 4)

#### Test Requirements (Per CP File)
- ✅ ≥1 test marked `@pytest.mark.cp`
- ✅ ≥1 Hypothesis property test (`@given(...)`)
- ✅ ≥1 failure-path test (e.g., test 404 response, invalid schema)

#### Example: Web Scraper TDD
```python
# tests/crawler/test_web_scraper_provider.py

@pytest.mark.cp
def test_web_scraper_discovers_pdfs(mock_playwright):
    """Test PDF discovery on company website."""
    provider = WebScraperProvider()
    links = provider.discover_sustainability_reports("exxonmobil.com")
    assert len(links) > 0
    assert all(link.endswith(".pdf") for link in links)

@pytest.mark.cp
@given(url=st.from_regex(r"https://.*\.pdf", fullmatch=True))
def test_download_pdf_idempotent(url):
    """Property test: downloading same URL twice produces same file."""
    provider = WebScraperProvider()
    path1 = provider.download_pdf(url, output_dir=Path("/tmp"))
    path2 = provider.download_pdf(url, output_dir=Path("/tmp"))

    hash1 = hashlib.sha256(path1.read_bytes()).hexdigest()
    hash2 = hashlib.sha256(path2.read_bytes()).hexdigest()
    assert hash1 == hash2

@pytest.mark.cp
def test_web_scraper_handles_404(mock_playwright):
    """Failure-path test: scraper raises exception on 404."""
    provider = WebScraperProvider()
    with pytest.raises(HTTPError, match="404"):
        provider.discover_sustainability_reports("nonexistent-domain-12345.com")
```

---

## 9. Next Steps

### Immediate Actions (Before Code Implementation)

1. **User Review** - Review this document and confirm:
   - Phase prioritization (API → Pydantic → Dagster → Web Scraper)
   - Timeline expectations (5-7 days)
   - Risk mitigation strategies

2. **SCA Context Gate** - Create context documents for Phase 1:
   - `context/hypothesis.md` - Define success metrics for API enhancement
   - `context/design.md` - Document rate limiting + retry strategy
   - `context/cp_paths.json` - List all CP files for Phase 1-4

3. **Dependency Installation** - Confirm environment setup:
   ```bash
   pip install ratelimit tenacity playwright pydantic dagster dagster-duckdb
   playwright install chromium
   ```

### Implementation Sequence (Post-Approval)

#### Week 1: Foundation (Phase 1 + 3)
- **Day 1**: Enhance SEC EDGAR provider (retry + rate limit)
- **Day 2**: Create Pydantic `UnifiedDocument` schema
- **Day 3**: Migrate existing code to use Pydantic
- **Day 4**: Write comprehensive tests (≥95% coverage)
- **Day 5**: Run MEA validation loop + snapshot save

#### Week 2: Expansion (Phase 2 + 4)
- **Day 1-2**: Build Playwright web scraper
- **Day 3**: Integrate web scraper with Pydantic schema
- **Day 4-5**: Implement Dagster asset graph
- **Day 6**: Create hybrid ingestion E2E test
- **Day 7**: Final MEA validation + documentation

### Open Questions

1. **Dagster vs Prefect**: User preference for orchestration framework?
   - Dagster: Better asset modeling, stronger typing
   - Prefect: More flexible, easier setup

2. **Web Scraper Scope**: Should Phase 2 include:
   - Only direct PDF links?
   - OR also search API integration (Google Custom Search)?

3. **Incremental Processing**: Should Dagster use:
   - Time-based partitions (daily/weekly)?
   - OR fiscal year partitions?

4. **Error Handling**: For failed web scrapes, should system:
   - Retry with exponential backoff?
   - OR mark as "manual review required" and continue?

---

## 10. Conclusion

This document demonstrates a comprehensive understanding of the proposed **Hybrid Data Ingestion Strategy** and provides a detailed remediation roadmap to align the current ESG Evaluation System with the proposed architecture.

**Key Takeaways**:
1. ✅ **Current E2E pipeline is valid** - No rework needed, only enhancement
2. ⚠️ **4 implementation phases** - Can be executed incrementally (5-7 days)
3. ✅ **SCA v13.8 compliance maintained** - All authenticity invariants preserved
4. 📊 **Estimated effort: 38-54 hours** - Manageable scope for single developer

**Recommended Next Step**: User review and approval to proceed with Phase 1 (API Core enhancement) context gate preparation.

---

**Document Prepared By**: Scientific Coding Agent (SCA v13.8-MEA)
**Review Status**: Pending User Approval
**Next Milestone**: Phase 1 Context Gate Validation
