# Architecture Decision Records (ADR) - Phase 1

**Task ID**: 010-hybrid-ingestion-phase1
**SCA Version**: v13.8-MEA
**Date**: 2025-10-23

---

## ADR-001: Use `ratelimit` Library Over Custom Token Bucket

**Status**: ACCEPTED

**Context**:
SEC EDGAR enforces 10 requests per second rate limit. We need thread-safe rate limiting for concurrent API calls.

**Decision**:
Use `ratelimit` library with `@sleep_and_retry` and `@limits` decorators instead of implementing custom token bucket algorithm.

**Rationale**:
- ✅ **Battle-tested**: Used in production by thousands of projects
- ✅ **Simple API**: Single decorator covers 90% of use cases
- ✅ **Thread-safe**: Built-in locking for concurrent requests
- ✅ **Zero overhead**: Sleep-based approach (no busy-waiting)
- ❌ **Alternative rejected**: Custom implementation would require extensive testing for race conditions

**Consequences**:
- Positive: Reduces implementation time by ~4 hours
- Positive: Eliminates potential concurrency bugs
- Negative: Adds external dependency (acceptable risk)

**Implementation**:
```python
from ratelimit import limits, sleep_and_retry

@sleep_and_retry
@limits(calls=10, period=1)
def _make_request(url: str) -> requests.Response:
    return requests.get(url)
```

---

## ADR-002: Use `tenacity` for Retry Logic Over `backoff`

**Status**: ACCEPTED

**Context**:
Need exponential backoff retry for transient API failures (503, network timeouts).

**Decision**:
Use `tenacity` library instead of `backoff` or custom retry logic.

**Rationale**:
- ✅ **Configurability**: Supports complex retry policies (exception filtering, custom wait strategies)
- ✅ **Observability**: Built-in logging for retry attempts
- ✅ **Type hints**: Full mypy support
- ✅ **Active maintenance**: Last release 2023-12 (vs `backoff` 2022-06)
- ❌ **Alternative rejected**: `backoff` has simpler API but less flexible

**Consequences**:
- Positive: Fine-grained control over retry behavior
- Positive: Better debugging via structured logs
- Negative: Slightly more verbose decorator syntax (acceptable)

**Implementation**:
```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10)
)
def _fetch_with_retry(url: str) -> requests.Response:
    response = requests.get(url)
    response.raise_for_status()
    return response
```

---

## ADR-003: Mock HTTP with `responses` Over `requests-mock`

**Status**: ACCEPTED

**Context**:
Unit tests must mock SEC EDGAR API calls for deterministic, fast execution.

**Decision**:
Use `responses` library for HTTP mocking in tests.

**Rationale**:
- ✅ **Simplicity**: Decorator-based API matches pytest conventions
- ✅ **Comprehensive**: Supports status codes, headers, JSON, binary bodies
- ✅ **Maintained**: Active development, 12k+ GitHub stars
- ✅ **Pytest integration**: Works seamlessly with fixtures
- ❌ **Alternative rejected**: `requests-mock` requires context manager (more verbose)

**Consequences**:
- Positive: Tests are readable and maintainable
- Positive: Fast test execution (~100ms for 20 tests)
- Negative: Only works with `requests` library (acceptable - we use requests)

**Implementation**:
```python
import responses

@responses.activate
def test_fetch_10k():
    responses.add(
        responses.GET,
        "https://data.sec.gov/cgi-bin/browse-edgar",
        json={"filings": [...]},
        status=200
    )
    provider = SECEdgarProvider()
    doc = provider.fetch_10k("0000320193", 2023)
    assert doc["cik"] == "0000320193"
```

---

## ADR-004: Extract Metadata with BeautifulSoup4 Over Regex

**Status**: ACCEPTED

**Context**:
SEC filings are HTML documents requiring metadata extraction (company name, filing date, sections).

**Decision**:
Use BeautifulSoup4 with lxml parser for HTML parsing, not regex.

**Rationale**:
- ✅ **Robustness**: Handles malformed HTML gracefully
- ✅ **Maintainability**: CSS selectors more readable than regex
- ✅ **Performance**: lxml parser is C-based (fast)
- ✅ **Standard practice**: Industry standard for HTML parsing
- ❌ **Alternative rejected**: Regex is brittle and error-prone for HTML

**Consequences**:
- Positive: Graceful degradation on malformed HTML
- Positive: Easy to debug with `.prettify()`
- Negative: Additional dependency (lxml) - acceptable

**Implementation**:
```python
from bs4 import BeautifulSoup

def extract_metadata(html: str) -> dict:
    soup = BeautifulSoup(html, 'lxml')
    company_name = soup.find('title').text.strip()
    return {"company_name": company_name}
```

---

## ADR-005: Store Raw HTML + Extracted Text in Bronze Layer

**Status**: ACCEPTED

**Context**:
Need to decide what to persist in Bronze layer: only text, only HTML, or both.

**Decision**:
Store both `raw_html` (original) and `raw_text` (extracted) in Bronze layer.

**Rationale**:
- ✅ **Auditability**: Can re-extract text if parser improves
- ✅ **Debugging**: Original HTML useful for investigating parse errors
- ✅ **Compliance**: Regulatory requirement to preserve original source
- ✅ **Storage cost**: Minimal (DuckDB compression ~5:1 on HTML)
- ❌ **Alternative rejected**: Text-only loses fidelity, HTML-only requires re-parsing

**Consequences**:
- Positive: Full traceability from raw source to final output
- Positive: Enables differential testing (re-run parser on old data)
- Negative: ~20% larger Bronze layer (acceptable)

**Schema**:
```sql
CREATE TABLE bronze.sec_filings (
    raw_html TEXT,        -- Original SEC HTML
    raw_text TEXT,        -- BeautifulSoup extracted text
    content_sha256 TEXT   -- Hash of raw_text for deduplication
);
```

---

## ADR-006: Deduplicate via SHA256 Hash Over CIK+FiscalYear

**Status**: ACCEPTED

**Context**:
Need to prevent duplicate ingestion if pipeline re-runs.

**Decision**:
Use SHA256 hash of `raw_text` as deduplication key, not `(CIK, fiscal_year, filing_type)`.

**Rationale**:
- ✅ **Content-based**: Detects if filing content changes (e.g., amendment)
- ✅ **Simple**: Single column index, no composite key
- ✅ **Portable**: Works across all document types (not SEC-specific)
- ❌ **Alternative rejected**: CIK+year key misses amendments and corrected filings

**Consequences**:
- Positive: Catches duplicate ingestion from different sources
- Positive: Detects amended filings automatically
- Negative: Small collision risk (SHA256: 2^-256, negligible)

**Implementation**:
```python
import hashlib

def compute_hash(text: str) -> str:
    return hashlib.sha256(text.encode('utf-8')).hexdigest()

# Before insert
existing = db.execute(
    "SELECT 1 FROM bronze.sec_filings WHERE content_sha256 = ?",
    (hash,)
).fetchone()
if existing:
    logger.info(f"Skipping duplicate document: {hash[:8]}...")
    return
```

---

## ADR-007: Log Retry Attempts to JSONL Event Stream

**Status**: ACCEPTED

**Context**:
Need observability into retry behavior for debugging production issues.

**Decision**:
Log all retry attempts to `artifacts/run_events.jsonl` in structured format.

**Rationale**:
- ✅ **Queryable**: JSONL can be analyzed with `jq`, `duckdb`, or pandas
- ✅ **Complete**: Captures timestamp, URL, attempt number, exception
- ✅ **SCA v13.8**: Satisfies "Honest Status Reporting" requirement
- ❌ **Alternative rejected**: Plain text logs harder to analyze

**Consequences**:
- Positive: Production debugging via event analysis
- Positive: Metrics (retry rate, failure patterns)
- Negative: Additional I/O overhead (~10ms per retry) - acceptable

**Event Schema**:
```json
{
  "timestamp": "2025-10-23T17:45:12.123Z",
  "event_type": "retry_attempt",
  "url": "https://data.sec.gov/...",
  "attempt": 2,
  "max_attempts": 3,
  "exception": "HTTPError 503",
  "wait_seconds": 4.0
}
```

---

## ADR-008: Fail Fast on Invalid CIK Format

**Status**: ACCEPTED

**Context**:
CIK must be 10-digit zero-padded string. Invalid formats cause confusing API errors.

**Decision**:
Validate CIK format and raise `ValueError` immediately, before making API call.

**Rationale**:
- ✅ **Fail fast**: Clear error message at call site, not after retry attempts
- ✅ **Testability**: Easy to write failure-path test
- ✅ **User experience**: Better error message than SEC API's generic 404
- ❌ **Alternative rejected**: Passing invalid CIK to API wastes retry attempts

**Consequences**:
- Positive: Clearer error messages for users
- Positive: Reduces unnecessary API calls
- Negative: Additional validation logic (~5 lines) - acceptable

**Implementation**:
```python
def validate_cik(cik: str) -> None:
    if not re.match(r'^\d{10}$', cik):
        raise ValueError(
            f"Invalid CIK format: {cik}. Must be 10-digit zero-padded string."
        )

def fetch_10k(cik: str, fiscal_year: int) -> dict:
    validate_cik(cik)  # Fail fast
    ...
```

---

## ADR-009: Use Pydantic for Future Schema (Phase 3 Dependency)

**Status**: ACCEPTED

**Context**:
Phase 3 will introduce unified document schema. Need to decide between dataclasses and Pydantic.

**Decision**:
Use Pydantic v2 `BaseModel` for `UnifiedDocument` schema (Phase 3).

**Rationale**:
- ✅ **Validation**: Automatic type checking + custom validators
- ✅ **Serialization**: Built-in JSON serialization with `.model_dump()`
- ✅ **Documentation**: Auto-generates JSON schema for API docs
- ✅ **Performance**: Pydantic v2 uses Rust core (10x faster than v1)
- ❌ **Alternative rejected**: Dataclasses require manual validation

**Consequences**:
- Positive (Phase 3): Type-safe document ingestion
- Positive (Phase 3): Easy schema versioning
- Negative: Dependency on Pydantic (acceptable - widely used)

**Future Implementation** (Phase 3):
```python
from pydantic import BaseModel, Field

class UnifiedDocument(BaseModel):
    document_id: str
    cik: str = Field(pattern=r'^\d{10}$')
    raw_text: str = Field(min_length=100)
    content_sha256: str = Field(pattern=r'^[a-f0-9]{64}$')
```

---

## ADR-010: Defer Dagster Integration to Phase 4

**Status**: ACCEPTED

**Context**:
Could implement Dagster orchestration now or defer to Phase 4.

**Decision**:
Defer Dagster to Phase 4. Phase 1 uses standalone scripts callable from Dagster later.

**Rationale**:
- ✅ **Incremental delivery**: Phase 1 delivers value immediately
- ✅ **Testability**: Easier to test standalone functions than Dagster assets
- ✅ **Flexibility**: Can switch to Prefect if Dagster proves unsuitable
- ✅ **Scope control**: Reduces Phase 1 complexity
- ❌ **Alternative rejected**: Implementing Dagster now adds 16-24 hours to Phase 1

**Consequences**:
- Positive: Faster Phase 1 delivery (5-6 days → 3-4 days)
- Positive: Can validate core logic before adding orchestration
- Negative: Requires refactor in Phase 4 (acceptable - planned work)

**Migration Path** (Phase 4):
```python
# Phase 1: Standalone function
def ingest_sec_filing(cik: str, year: int) -> dict:
    provider = SECEdgarProvider()
    return provider.fetch_10k(cik, year)

# Phase 4: Dagster asset (minimal change)
@asset
def bronze_sec_10k(cik: str, year: int) -> dict:
    return ingest_sec_filing(cik, year)  # Reuse Phase 1 logic
```

---

**ADR Summary**: 10 decisions documented
**Next Step**: Create `assumptions.md` and `cp_paths.json`
