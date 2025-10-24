# Design: Phase 1 - API Core Enhancement

**Task ID**: 010-hybrid-ingestion-phase1
**Phase**: API Core Enhancement (SEC EDGAR)
**SCA Version**: v13.8-MEA
**Date**: 2025-10-23

---

## Overview

This design document specifies the technical implementation for enhancing the SEC EDGAR API provider with production-grade reliability: rate limiting (10 req/sec), exponential backoff retry logic, comprehensive error handling, and full observability.

---

## Data Strategy

### Input Data

#### SEC EDGAR API Endpoints

**Base URL**: `https://data.sec.gov`

**Endpoints Used**:
1. **Company Search**: `/cgi-bin/browse-edgar`
   - Query: `?action=getcompany&CIK={cik}&type={filing_type}&dateb=&owner=exclude&count=100`
   - Returns: JSON with filing metadata

2. **Document Retrieval**: `/Archives/edgar/data/{cik}/{accession}/{filename}`
   - Returns: HTML/TXT filing content

**Authentication**:
- No API key required
- User-Agent header MUST include contact email
- Format: `User-Agent: {company_name} {email}`

**Rate Limits**:
- 10 requests per second (enforced by SEC)
- Exceeding limit returns 503 Service Unavailable

### Output Data

#### Bronze Layer Schema (DuckDB)

```sql
CREATE TABLE IF NOT EXISTS bronze.sec_filings (
    document_id VARCHAR PRIMARY KEY,           -- UUID
    source_type VARCHAR DEFAULT 'api_sec_edgar',
    cik VARCHAR(10),                           -- Zero-padded CIK
    company_name VARCHAR,
    filing_type VARCHAR(20),                   -- '10-K', 'DEF 14A'
    filing_date DATE,
    fiscal_year INTEGER,
    accession_number VARCHAR(25),              -- e.g., '0000950170-23-027948'

    raw_text TEXT,                             -- Full filing text
    raw_html TEXT,                             -- Original HTML

    source_url VARCHAR,                        -- Full SEC EDGAR URL
    retrieval_timestamp TIMESTAMP,

    content_sha256 VARCHAR(64),                -- Deduplication hash
    text_length INTEGER,

    metadata JSON,                             -- Additional fields (sections, XBRL tags)

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_sec_filings_cik ON bronze.sec_filings(cik);
CREATE INDEX idx_sec_filings_fiscal_year ON bronze.sec_filings(fiscal_year);
CREATE INDEX idx_sec_filings_sha256 ON bronze.sec_filings(content_sha256);
```

### Data Normalization

**Text Cleaning Pipeline**:
1. **HTML Stripping**: BeautifulSoup4 to extract text from SEC HTML
2. **Whitespace Normalization**: Replace multiple spaces/newlines with single
3. **Encoding**: Ensure UTF-8 (SEC files sometimes use Latin-1)
4. **Section Extraction**: Parse 10-K sections (Item 1, Item 1A, Item 7, etc.)

**Example**:
```python
def normalize_sec_text(html: str) -> str:
    """Normalize SEC filing HTML to clean text."""
    soup = BeautifulSoup(html, 'lxml')

    # Remove script/style tags
    for element in soup(['script', 'style']):
        element.decompose()

    # Extract text
    text = soup.get_text()

    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'\n\s*\n', '\n\n', text)

    return text.strip()
```

### Leakage Guards

**Not Applicable** - Phase 1 is data ingestion only (no ML training).

---

## Verification Plan

### Test Strategy

#### 1. Unit Tests (Mocked HTTP)

**Library**: `responses` for HTTP mocking

**Test Cases**:
- ✅ Successful API call returns valid document
- ✅ Rate limiter enforces 10 req/sec (mock `time.sleep`)
- ✅ Retry logic recovers from single 503 error
- ✅ Retry logic recovers from two consecutive 503 errors
- ✅ Retry logic fails after 3 consecutive 503 errors
- ✅ Invalid CIK raises `ValueError`
- ✅ 404 (filing not found) raises `DocumentNotFoundError`
- ✅ Malformed HTML logs warning and returns partial text
- ✅ SHA256 hash computed correctly for deduplication

**Example**:
```python
import responses
from ratelimit import limits

@responses.activate
def test_fetch_10k_success():
    """Test successful 10-K retrieval."""
    responses.add(
        responses.GET,
        "https://data.sec.gov/cgi-bin/browse-edgar",
        json={"filings": [{"accessionNumber": "0000950170-23-027948"}]},
        status=200
    )
    responses.add(
        responses.GET,
        "https://data.sec.gov/Archives/edgar/data/320193/0000950170-23-027948/aapl-20230930.htm",
        body="<html>Apple Inc. 10-K Filing</html>",
        status=200
    )

    provider = SECEdgarProvider()
    doc = provider.fetch_10k(cik="0000320193", fiscal_year=2023)

    assert doc["cik"] == "0000320193"
    assert "Apple Inc." in doc["raw_text"]
    assert len(doc["content_sha256"]) == 64
```

#### 2. Integration Tests (Real API)

**Execution**: `pytest -m integration` (slower, requires network)

**Test Cases**:
- ✅ Fetch real 10-K from SEC EDGAR (AAPL 2023)
- ✅ Fetch real DEF 14A from SEC EDGAR (MSFT 2023)
- ✅ Verify rate limiting with 15 consecutive requests
- ✅ Verify retry recovery with real 503 (if SEC returns it)

**Example**:
```python
@pytest.mark.integration
@pytest.mark.slow
def test_fetch_real_sec_filing():
    """Integration test with real SEC EDGAR API."""
    provider = SECEdgarProvider()

    doc = provider.fetch_10k(cik="0000320193", fiscal_year=2023)  # Apple

    assert doc["company_name"] == "APPLE INC"
    assert doc["filing_type"] == "10-K"
    assert len(doc["raw_text"]) > 100000  # 10-Ks are long
    assert doc["source_url"].startswith("https://data.sec.gov")
```

#### 3. Property-Based Tests (Hypothesis)

**Test Cases**:
- ✅ Any valid CIK (10-digit string) does not crash
- ✅ Retry count never exceeds max_attempts
- ✅ SHA256 hash is deterministic (same text = same hash)

**Example**:
```python
from hypothesis import given, strategies as st

@given(cik=st.from_regex(r"\d{10}", fullmatch=True))
def test_valid_cik_no_crash(cik):
    """Property test: any valid CIK should not crash."""
    provider = SECEdgarProvider()

    try:
        doc = provider.fetch_10k(cik=cik, fiscal_year=2023)
        assert doc is not None or doc is None  # Should not crash
    except DocumentNotFoundError:
        pass  # Valid outcome for non-existent company
    except ValueError:
        pytest.fail("Should not raise ValueError for valid CIK format")
```

#### 4. Failure-Path Tests

**Required by SCA v13.8 TDD Guard**

**Test Cases**:
- ✅ 404 (filing not found) raises `DocumentNotFoundError`
- ✅ 503 (rate limit exceeded) triggers retry, fails after 3 attempts
- ✅ Invalid CIK format raises `ValueError`
- ✅ Network timeout raises `RequestTimeout`
- ✅ Malformed JSON response logs error and raises `InvalidResponseError`

**Example**:
```python
@pytest.mark.cp
@responses.activate
def test_rate_limit_exceeded_fails_after_retries():
    """Failure-path: 503 errors exceed retry limit."""
    # Mock 4 consecutive 503 responses
    for _ in range(4):
        responses.add(
            responses.GET,
            "https://data.sec.gov/cgi-bin/browse-edgar",
            json={"error": "Rate limit exceeded"},
            status=503
        )

    provider = SECEdgarProvider()

    with pytest.raises(MaxRetriesExceeded, match="503"):
        provider.fetch_10k(cik="0000320193", fiscal_year=2023)
```

### Differential Testing

**Approach**: Compare enhanced provider with original

```python
def test_differential_output_parity():
    """Ensure enhanced provider returns same data as v1."""
    original = SECEdgarProviderV1()  # Existing implementation
    enhanced = SECEdgarProvider()    # Enhanced version

    doc_v1 = original.fetch_10k("0000320193", 2023)
    doc_v2 = enhanced.fetch_10k("0000320193", 2023)

    # Core fields must match
    assert doc_v1["cik"] == doc_v2["cik"]
    assert doc_v1["company_name"] == doc_v2["company_name"]
    assert doc_v1["raw_text"][:5000] == doc_v2["raw_text"][:5000]  # First 5k chars
```

### Sensitivity Testing

**Approach**: Test retry behavior under varying failure rates

```python
@pytest.mark.parametrize("failure_rate", [0.1, 0.3, 0.5, 0.7])
def test_retry_under_varying_failure_rates(failure_rate):
    """Test retry resilience under different failure probabilities."""
    provider = SECEdgarProvider()

    with mock_random_failures(probability=failure_rate):
        success_count = 0
        for i in range(10):
            try:
                doc = provider.fetch_10k("0000320193", 2023)
                success_count += 1
            except MaxRetriesExceeded:
                pass

        # At 50% failure rate, expect ~80% final success (due to retries)
        if failure_rate <= 0.5:
            assert success_count >= 7  # Should recover most
```

---

## Implementation Details

### Rate Limiting

**Library**: `ratelimit`

**Configuration**:
```python
from ratelimit import limits, sleep_and_retry

# SEC EDGAR rate limit: 10 requests per second
RATE_LIMIT_CALLS = 10
RATE_LIMIT_PERIOD = 1  # seconds

@sleep_and_retry
@limits(calls=RATE_LIMIT_CALLS, period=RATE_LIMIT_PERIOD)
def _make_request(url: str, headers: dict) -> requests.Response:
    """Make HTTP request with rate limiting."""
    logger.debug(f"Making rate-limited request to {url}")
    return requests.get(url, headers=headers, timeout=30)
```

**How It Works**:
1. `@limits` tracks calls per second
2. If rate exceeded, `@sleep_and_retry` pauses thread until next second
3. Guarantees ≤10 req/sec compliance

### Retry Logic

**Library**: `tenacity`

**Configuration**:
```python
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log
)
import logging

logger = logging.getLogger(__name__)

@retry(
    retry=retry_if_exception_type((requests.HTTPError, requests.Timeout)),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True
)
def _fetch_with_retry(url: str, headers: dict) -> requests.Response:
    """Fetch URL with exponential backoff retry."""
    response = _make_request(url, headers)
    response.raise_for_status()  # Raise HTTPError for 4xx/5xx
    return response
```

**Retry Schedule**:
- Attempt 1: Immediate
- Attempt 2: Wait 2 seconds
- Attempt 3: Wait 4 seconds
- Attempt 4: Fail with `MaxRetriesExceeded`

**Logged Events**:
```
2025-10-23 17:45:12 WARNING - Retrying in 2.0 seconds (attempt 1 of 3): HTTPError 503
2025-10-23 17:45:14 WARNING - Retrying in 4.0 seconds (attempt 2 of 3): HTTPError 503
2025-10-23 17:45:18 ERROR - Max retries exceeded for https://data.sec.gov/...
```

### Error Handling

**Custom Exceptions**:
```python
class SECEdgarError(Exception):
    """Base exception for SEC EDGAR provider."""
    pass

class DocumentNotFoundError(SECEdgarError):
    """Requested filing does not exist (404)."""
    pass

class RateLimitExceededError(SECEdgarError):
    """API rate limit exceeded (503)."""
    pass

class InvalidCIKError(SECEdgarError):
    """Invalid CIK format."""
    pass

class MaxRetriesExceeded(SECEdgarError):
    """Retry attempts exhausted."""
    pass
```

**Error Mapping**:
```python
def _handle_http_error(response: requests.Response) -> None:
    """Map HTTP errors to custom exceptions."""
    if response.status_code == 404:
        raise DocumentNotFoundError(f"Filing not found: {response.url}")
    elif response.status_code == 503:
        raise RateLimitExceededError("SEC EDGAR rate limit exceeded")
    elif response.status_code >= 500:
        raise SECEdgarError(f"Server error {response.status_code}")
    else:
        response.raise_for_status()  # Default handling
```

### Logging and Observability

**Log Levels**:
- **DEBUG**: Individual API calls, rate limit sleeps
- **INFO**: Successful document retrieval, metadata
- **WARNING**: Retry attempts, partial failures
- **ERROR**: Max retries exceeded, invalid CIK, parsing errors

**Structured Logging**:
```python
import logging
import json
from datetime import datetime

logger = logging.getLogger(__name__)

def log_api_call(cik: str, filing_type: str, status: str, duration_ms: int):
    """Log structured API call event."""
    event = {
        "timestamp": datetime.now().isoformat(),
        "event_type": "sec_edgar_api_call",
        "cik": cik,
        "filing_type": filing_type,
        "status": status,
        "duration_ms": duration_ms
    }

    # Append to JSONL event stream
    with open("artifacts/run_events.jsonl", "a") as f:
        f.write(json.dumps(event) + "\n")

    logger.info(f"SEC EDGAR API call: {cik} {filing_type} - {status} ({duration_ms}ms)")
```

### Metadata Extraction

**Extract from SEC Filing**:
- **CIK**: Company identifier (10 digits, zero-padded)
- **Company Name**: Official business name
- **Filing Date**: Date filed with SEC
- **Fiscal Year**: Fiscal period covered
- **Accession Number**: Unique SEC filing ID
- **Document Sections**: Item 1, Item 1A, Item 7 (for 10-K)

**Implementation**:
```python
def extract_metadata(html: str, cik: str) -> dict:
    """Extract structured metadata from SEC filing HTML."""
    soup = BeautifulSoup(html, 'lxml')

    # Find company name (in <title> or first heading)
    company_name = soup.find('title').text.strip() if soup.find('title') else "Unknown"

    # Find filing date (usually in header table)
    filing_date = None
    for row in soup.find_all('tr'):
        if 'FILED AS OF DATE' in row.get_text():
            filing_date = row.find_all('td')[-1].text.strip()

    # Extract sections (10-K specific)
    sections = {}
    for heading in soup.find_all(['h2', 'h3']):
        if 'ITEM 1' in heading.get_text().upper():
            sections['item_1'] = heading.find_next('div').get_text()[:5000]

    return {
        "company_name": company_name,
        "filing_date": filing_date,
        "sections": sections,
        "cik": cik
    }
```

---

## Success Thresholds

### Code Quality Gates

| Gate | Tool | Threshold | Blocking |
|------|------|-----------|----------|
| **Line Coverage** | pytest-cov | ≥95% | ✅ YES |
| **Branch Coverage** | pytest-cov | ≥95% | ✅ YES |
| **Type Safety** | mypy --strict | 0 errors | ✅ YES |
| **Cyclomatic Complexity** | lizard | ≤10 per function | ✅ YES |
| **Cognitive Complexity** | lizard | ≤15 per function | ✅ YES |
| **Docstring Coverage** | interrogate | ≥95% | ✅ YES |
| **Security** | bandit | 0 HIGH/MEDIUM | ✅ YES |

### Functional Thresholds

| Metric | Threshold | Test Method |
|--------|-----------|-------------|
| **API Success Rate** | ≥99% | Integration test (9 calls) |
| **Retry Recovery Rate** | ≥90% | Mocked 503 tests (10 cases) |
| **Rate Limit Compliance** | 100% | Timer mock verification |
| **Deduplication Accuracy** | 100% | SHA256 collision test |

---

## Technical Risks

### Risk 1: SEC EDGAR Schema Changes
**Mitigation**: Version metadata extractors, log parsing failures

### Risk 2: Network Timeouts
**Mitigation**: 30-second timeout, retry logic

### Risk 3: HTML Parsing Fragility
**Mitigation**: Graceful degradation (return partial text on parse error)

---

## Dependencies

### Python Packages (Required)

```toml
[tool.poetry.dependencies]
requests = "^2.31.0"
beautifulsoup4 = "^4.12.0"
lxml = "^4.9.0"
ratelimit = "^2.2.1"
tenacity = "^8.2.3"
pydantic = "^2.5.0"  # For Phase 3 schema

[tool.poetry.group.dev.dependencies]
pytest = "^7.4.0"
pytest-cov = "^4.1.0"
pytest-mock = "^3.12.0"
responses = "^0.24.0"
hypothesis = "^6.92.0"
mypy = "^1.7.0"
bandit = "^1.7.5"
interrogate = "^1.5.0"
lizard = "^1.17.10"
```

### External Services

- **SEC EDGAR API**: `https://data.sec.gov` (public, no auth)
- **DuckDB**: Local database (no network dependency)

---

## File Structure

```
agents/crawler/data_providers/
├── __init__.py
├── base_provider.py                    # Existing abstract base
├── sec_edgar_provider.py               # MODIFIED (Phase 1)
└── exceptions.py                       # NEW (custom exceptions)

tests/crawler/
├── __init__.py
└── test_sec_edgar_provider_enhanced.py # NEW (Phase 1 tests)

artifacts/
├── run_log.txt                         # Execution trace
├── run_context.json                    # Environment metadata
├── run_manifest.json                   # API calls made
└── run_events.jsonl                    # Event stream

tasks/010-hybrid-ingestion-phase1/
├── context/
│   ├── hypothesis.md                   # This document's companion
│   ├── design.md                       # This document
│   ├── evidence.json                   # PRIMARY SOURCES (next)
│   ├── data_sources.json               # DATA PROVENANCE (next)
│   ├── adr.md                          # ARCHITECTURE DECISIONS (next)
│   ├── assumptions.md                  # ASSUMPTIONS (next)
│   └── cp_paths.json                   # CRITICAL PATH FILES (next)
```

---

**Design Approved By**: SCA v13.8-MEA
**Next Step**: Create `evidence.json` with ≥3 primary sources
