# Assumptions: Task 011 Service Activation

**Task:** 011-service-activation
**Protocol:** SCA v13.8-MEA
**Date:** 2025-11-19

---

## Infrastructure Assumptions

### A1: Docker Environment Availability
**Assumption:** Docker and docker-compose are installed and functional on deployment environment.

**Validation:**
```bash
docker --version
docker-compose --version
```

**Risk if False:** Cannot deploy containerized service.
**Mitigation:** Document minimum versions in README (Docker ≥20.10, docker-compose ≥1.29).

---

### A2: Network Connectivity for Live Mode
**Assumption:** When `ALLOW_NETWORK=true`, deployment environment has outbound HTTPS access to:
- `https://www.sec.gov/` (SEC EDGAR API)
- `https://data.sec.gov/` (SEC data feeds)

**Validation:**
```bash
curl -I https://www.sec.gov/
# Expected: HTTP 200
```

**Risk if False:** Live mode will fail with network timeout errors.
**Mitigation:**
- Auto-detection falls back to offline mode (graceful degradation)
- Document network requirements in deployment guide

---

### A3: Sufficient Disk Space
**Assumption:** Deployment environment has ≥5 GB free disk space for:
- Docker images (~2 GB)
- PDF cache directory (`data/pdf_cache`, up to 2 GB)
- Artifacts/logs (~1 GB)

**Validation:**
```bash
df -h
```

**Risk if False:** Crawler cannot cache downloaded PDFs, degraded performance.
**Mitigation:** Implement cache size limits and automatic cleanup of old files.

---

## Data Assumptions

### A4: Data Source Registry Validity
**Assumption:** `configs/data_source_registry.json` exists and contains valid provider configurations for:
- SEC EDGAR (base_url, rate_limits)
- Ticker lookup mappings

**Validation:**
- File exists: `assert Path("configs/data_source_registry.json").exists()`
- Valid JSON: `json.load(open("configs/data_source_registry.json"))`

**Risk if False:** MultiSourceCrawler initialization fails.
**Mitigation:** Task 011 validates registry in unit tests before deployment.

---

### A5: CIK Lookup Coverage
**Assumption:** Ticker Lookup Provider has CIK mappings for ≥90% of S&P 500 companies.

**Validation:**
```python
# Test against known CIKs
test_ciks = ["0000320193", "0000789019", "0001018724"]  # AAPL, MSFT, AMZN
for cik in test_ciks:
    company_name = provider.lookup_by_cik(cik)
    assert company_name is not None
```

**Risk if False:** Adapter returns empty results for unknown CIKs.
**Mitigation:**
- Log warning for unknown CIKs
- Return HTTP 404 with clear error message
- Document supported companies in API docs

---

### A6: Demo Flow Manifest Integrity
**Assumption:** `artifacts/demo/companies.json` exists and contains valid cached data for offline mode testing.

**Validation:**
- File exists
- Valid JSON
- Contains at least 1 company entry

**Risk if False:** Offline mode fails, CI/CD breaks.
**Mitigation:** Task 011 does not modify demo manifest. Relies on Tasks 003-009 artifacts.

---

## API Assumptions

### A7: PipelineOrchestrator Output Schema Compatibility
**Assumption:** Output from `PipelineOrchestrator.run_pipeline()` matches output from `demo_flow.run_score()` schema.

**Expected Schema:**
```json
{
  "company": "AAPL",
  "year": 2024,
  "maturity_score": 1.71,
  "confidence": 0.67,
  "dimensions": {...}
}
```

**Validation:** Integration test compares outputs from both paths.

**Risk if False:** API response format differs based on mode (breaks clients).
**Mitigation:** Standardize output via response model in FastAPI. Test both paths.

---

### A8: ALLOW_NETWORK Environment Variable Availability
**Assumption:** `ALLOW_NETWORK` environment variable is set in all deployment environments (Docker, Kubernetes, local dev).

**Validation:**
```python
import os
allow_network = os.getenv("ALLOW_NETWORK")
assert allow_network in ["true", "false"], "ALLOW_NETWORK must be set"
```

**Risk if False:** Defaults to "false" (offline mode), live service unavailable.
**Mitigation:**
- Docker configs default to "true"
- Document env var in deployment guide
- Log warning if env var missing

---

## Performance Assumptions

### A9: SEC EDGAR API Response Time
**Assumption:** SEC EDGAR API responds within 10 seconds for 10-K filing fetch (95th percentile).

**Validation:** Smoke test with timer:
```python
import time
start = time.time()
response = requests.get("https://www.sec.gov/...")
latency = time.time() - start
assert latency < 10.0, f"Latency too high: {latency}s"
```

**Risk if False:** API timeout, poor user experience.
**Mitigation:**
- Implement 30-second timeout
- Return HTTP 504 Gateway Timeout with retry suggestion

---

### A10: In-Memory Vector Store Performance
**Assumption:** In-memory vector store (30-dimensional TF vectors) handles single-company queries in <1 second.

**Validation:** Benchmark test:
```python
# Index 1000 chunks
# Query with TF vector
# Assert latency < 1.0s
```

**Risk if False:** Slow response times.
**Mitigation:** Task 011 does NOT address vector store scaling (deferred to future task). Document limitation.

---

## Security Assumptions

### A11: No PII in Downloaded SEC Filings
**Assumption:** SEC EDGAR 10-K filings do not contain personally identifiable information (PII).

**Validation:** SEC filings are public documents, no PII by regulation.

**Risk if False:** Privacy compliance issues.
**Mitigation:** Run `detect-secrets` on downloaded PDFs (already in SCA protocol).

---

### A12: HTTPS for SEC Communication
**Assumption:** All SEC EDGAR API calls use HTTPS (not HTTP).

**Validation:**
```python
assert "https://" in SEC_BASE_URL
```

**Risk if False:** Man-in-the-middle attacks, data tampering.
**Mitigation:** Hardcode `https://` in provider URLs. Reject HTTP redirects.

---

## Testing Assumptions

### A13: Offline Mode Determinism
**Assumption:** Running demo_flow with same input 3 times produces identical SHA256 hash.

**Validation:** Determinism test (Phase 6):
```bash
for i in {1..3}; do
    ALLOW_NETWORK=false curl .../score > run_$i.json
done
sha256sum run_*.json  # All hashes must match
```

**Risk if False:** Non-deterministic behavior breaks reproducibility.
**Mitigation:** Task 009 already validated demo_flow determinism. Task 011 preserves this.

---

### A14: Live Mode Network Tolerance
**Assumption:** Live mode (ALLOW_NETWORK=true) may fail ≤20% of time due to network flakiness, SEC maintenance, rate limits.

**Validation:** Smoke test with 5 attempts, expect ≥4 successes (80%).

**Risk if False:** Unreliable service.
**Mitigation:**
- Implement retry logic (3 attempts with exponential backoff)
- Fall back to cached data if available
- Return HTTP 503 Service Unavailable with Retry-After header

---

## Deployment Assumptions

### A15: Single-Tenant Deployment
**Assumption:** Task 011 targets single-tenant deployment (one service instance per organization).

**Out of Scope:**
- Multi-tenancy (shared instance across orgs)
- User authentication/authorization
- Rate limiting per customer

**Risk if False:** Security/scaling issues in multi-tenant scenario.
**Mitigation:** Document as single-tenant. Multi-tenancy is future enhancement.

---

### A16: Python 3.11+ Runtime
**Assumption:** Deployment environment uses Python 3.11 or newer.

**Validation:**
```python
import sys
assert sys.version_info >= (3, 11), "Python 3.11+ required"
```

**Risk if False:** Type hint errors, missing library features.
**Mitigation:** Dockerfile specifies `FROM python:3.11-slim`.

---

## Exclusions (Explicit Non-Assumptions)

**Task 011 does NOT assume:**
- ❌ PDF extraction works (Task 010 documented this gap)
- ❌ Vector store scales to millions of chunks (deferred to future task)
- ❌ UI exists (API-only for now)
- ❌ Background job processing (synchronous /score endpoint)
- ❌ Multi-company batch processing

---

**Assumptions Status:** Documented
**Validation Plan:** Unit tests (A4, A5, A6), Integration tests (A7, A9), Smoke tests (A13, A14)
**Review Date:** 2025-11-19
