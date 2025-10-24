# Hypothesis: Phase 1 - API Core Enhancement

**Task ID**: 010-hybrid-ingestion-phase1
**Phase**: API Core Enhancement (SEC EDGAR)
**SCA Version**: v13.8-MEA
**Date**: 2025-10-23

---

## Research Question

**Can we enhance the existing SEC EDGAR API provider with production-grade reliability features (rate limiting, retry logic, comprehensive error handling) while maintaining ≥95% test coverage and SCA v13.8 authenticity standards?**

---

## Metrics and Thresholds

### Primary Metrics

| Metric | Target | Measurement Method | Success Threshold |
|--------|--------|-------------------|-------------------|
| **Test Coverage (Line)** | ≥95% | `pytest --cov` on CP files | ≥95% |
| **Test Coverage (Branch)** | ≥95% | `pytest --cov` with branch | ≥95% |
| **API Success Rate** | ≥99% | Integration tests with SEC EDGAR | ≥99% (excluding valid 404s) |
| **Rate Limit Compliance** | 100% | Mock timer verification | 100% adherence to 10 req/sec |
| **Retry Success Rate** | ≥90% | Simulated 503 recovery tests | ≥90% on transient failures |
| **Type Safety** | 100% | `mypy --strict` on CP files | 0 errors |

### Secondary Metrics

| Metric | Target | Measurement Method |
|--------|--------|-------------------|
| **Cyclomatic Complexity** | ≤10 | Lizard CCN per function |
| **Cognitive Complexity** | ≤15 | Lizard cognitive complexity |
| **Docstring Coverage** | ≥95% | `interrogate` |
| **Security Scan** | 0 findings | `bandit` on CP files |

---

## Critical Path (CP) Files

### New/Modified CP Files

1. **`agents/crawler/data_providers/sec_edgar_provider.py`** (MODIFY)
   - Add `@sleep_and_retry` and `@limits` decorators
   - Add `@retry` with exponential backoff
   - Enhanced error handling with logging
   - Comprehensive metadata extraction

2. **`libs/models/document.py`** (CREATE - Phase 3 dependency, documented here)
   - Pydantic `UnifiedDocument` schema
   - Validators for SHA256, dates, URLs
   - Factory methods (`from_pdf`, `from_api`)

### Test Files (TDD - Must Precede Implementation)

1. **`tests/crawler/test_sec_edgar_provider_enhanced.py`** (CREATE)
   - ≥1 test marked `@pytest.mark.cp`
   - ≥1 Hypothesis property test
   - ≥1 failure-path test (404, 503, rate limit exceeded)

---

## Exclusions

### Out of Scope for Phase 1

- ❌ Web scraping with Playwright (deferred to Phase 2)
- ❌ Dagster orchestration (deferred to Phase 4)
- ❌ PowerPoint/HTML extraction (deferred to Phase 2)
- ❌ Real watsonx.ai embeddings (covered in CP-2, using simulated for testing)

### Deliberate Simplifications

- **Mock SEC EDGAR in Unit Tests**: Use `responses` library to mock HTTP calls
  - *Rationale*: Avoid rate limiting during test execution
  - *Authenticity Safeguard*: Maintain separate integration test with real API calls

- **Fixed Company List**: Test with 3 companies (AAPL, MSFT, XOM)
  - *Rationale*: Reproducible test data
  - *Production Path*: Configuration-driven company list from `config/companies.json`

---

## Power Analysis and Confidence Intervals

### Statistical Assumptions

- **Population**: All SEC EDGAR 10-K/DEF 14A filings (2000-2025)
- **Sample Size**: 3 companies × 3 years = 9 filings for integration test
- **Expected Effect Size**: 99% success rate (1% failure on valid 404s)

### Confidence Intervals

| Test Type | Sample Size | Expected Success Rate | 95% CI |
|-----------|-------------|----------------------|---------|
| Unit Tests (Mocked) | 20 test cases | 100% | [98.3%, 100%] |
| Integration (Real API) | 9 API calls | 99% | [85%, 100%] |
| Retry Logic | 10 simulated failures | 90% | [73%, 97%] |

### Power Calculation

For detecting 5% degradation in API success rate:
- **α (Type I Error)**: 0.05
- **β (Type II Error)**: 0.20 (80% power)
- **Required Sample Size**: ≥8 API calls

*Conclusion*: 9 integration test calls provide adequate power.

---

## Risk Assessment

### High Risks

#### Risk 1: SEC EDGAR Rate Limiting (10 req/sec)
**Likelihood**: HIGH
**Impact**: HIGH (blocks data ingestion)
**Mitigation**:
- Implement `ratelimit` decorator with sleep
- Add integration test verifying rate limit compliance
- Log all rate limit violations to `qa/run_log.txt`

#### Risk 2: Transient API Failures (503 Service Unavailable)
**Likelihood**: MEDIUM
**Impact**: MEDIUM (temporary ingestion failure)
**Mitigation**:
- Implement `tenacity` retry with exponential backoff
- Max 3 retries with 2-4-8 second delays
- Test failure recovery with mocked 503 responses

### Medium Risks

#### Risk 3: Invalid Company Identifiers
**Likelihood**: MEDIUM
**Impact**: LOW (graceful failure, log error)
**Mitigation**:
- Validate CIK format (10-digit zero-padded string)
- Return clear error message for invalid identifiers
- Test with malformed CIK inputs

### Low Risks

- **SEC EDGAR API Deprecation**: LOW (stable API, active maintenance)
- **Schema Changes**: LOW (SEC EDGAR schema is versioned)

---

## Validation Plan

### Leakage Guards

**Not Applicable** - Phase 1 is data ingestion only (no ML training/validation split)

### Differential Testing

**Approach**: Compare enhanced provider output with original provider

```python
def test_differential_parity():
    """Ensure enhanced provider returns same data as original."""
    original = SECEdgarProviderV1()
    enhanced = SECEdgarProvider()  # v2 with retry/rate-limit

    doc_original = original.fetch_10k("AAPL", 2023)
    doc_enhanced = enhanced.fetch_10k("AAPL", 2023)

    assert doc_original["cik"] == doc_enhanced["cik"]
    assert doc_original["text"][:1000] == doc_enhanced["text"][:1000]
```

### Sensitivity Testing

**Approach**: Verify retry logic behavior under network failures

```python
@pytest.mark.parametrize("failure_count", [1, 2, 3, 4])
def test_retry_sensitivity(failure_count):
    """Test retry behavior with varying failure counts."""
    provider = SECEdgarProvider()

    with mock_http_failures(count=failure_count):
        if failure_count <= 3:
            result = provider.fetch_10k("AAPL", 2023)
            assert result is not None  # Should recover
        else:
            with pytest.raises(MaxRetriesExceeded):
                provider.fetch_10k("AAPL", 2023)  # Should fail
```

---

## Success Criteria

### Phase 1 Complete When:

1. ✅ **Test Coverage**: ≥95% line + branch on `sec_edgar_provider.py`
2. ✅ **Type Safety**: `mypy --strict` passes with 0 errors
3. ✅ **Complexity**: All functions ≤10 CCN, ≤15 cognitive
4. ✅ **Security**: `bandit` scan returns 0 findings
5. ✅ **TDD**: Tests written BEFORE implementation (checked via git timestamps)
6. ✅ **Failure Paths**: ≥1 test for 404, 503, rate limit, invalid CIK
7. ✅ **Integration**: Real SEC EDGAR API call succeeds in CI
8. ✅ **Documentation**: Docstring coverage ≥95% via `interrogate`
9. ✅ **Artifacts**: `qa/run_log.txt`, `artifacts/run_manifest.json` generated
10. ✅ **MEA Validation**: `validate-only.ps1` returns `status: "ok"`

### Acceptance Criteria

**User Validation**: Phase 1 snapshot includes:
- Enhanced `sec_edgar_provider.py` with retry/rate-limit
- ≥20 unit tests + ≥1 integration test
- Coverage report showing ≥95%
- Execution log proving real API calls succeeded
- `artifacts/state.json` updated with Phase 1 completion

---

## Reproducibility Requirements

### Environment Pinning

```toml
# pyproject.toml dependencies for Phase 1
[tool.poetry.dependencies]
requests = "^2.31.0"
ratelimit = "^2.2.1"
tenacity = "^8.2.3"
pydantic = "^2.5.0"

[tool.poetry.group.dev.dependencies]
pytest = "^7.4.0"
pytest-cov = "^4.1.0"
pytest-mock = "^3.12.0"
responses = "^0.24.0"  # HTTP mocking
mypy = "^1.7.0"
bandit = "^1.7.5"
interrogate = "^1.5.0"
lizard = "^1.17.10"
```

### Random Seed Policy

**Not Applicable** - Phase 1 is deterministic API calls (no randomness)

### Artifact Manifest

All executions must generate:
- `qa/run_log.txt` - Timestamped execution trace
- `artifacts/run_context.json` - Environment metadata (Python version, package versions)
- `artifacts/run_manifest.json` - List of all API calls made (CIK, filing type, timestamp)
- `artifacts/run_events.jsonl` - Event stream (API call start/end, retry attempts)

---

**Hypothesis Approved By**: SCA v13.8-MEA
**Next Step**: Create `design.md` with technical implementation details
