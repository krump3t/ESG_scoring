# Assumptions - Phase 1

**Task ID**: 010-hybrid-ingestion-phase1
**SCA Version**: v13.8-MEA
**Date**: 2025-10-23

---

## Technical Assumptions

### Assumption 1: SEC EDGAR API Stability
**Assumption**: SEC EDGAR API schema and endpoints will remain stable during development (Oct-Nov 2025).

**Validation**: Review SEC EDGAR changelog quarterly.

**Risk if Invalid**: Parser breaks, requires schema updates.

**Mitigation**: Version metadata extractors, implement schema validation tests.

---

### Assumption 2: 10 req/sec Rate Limit is Sufficient
**Assumption**: 10 requests per second supports production workload (batch ingestion of 100s of companies).

**Validation**: 10 req/sec × 3600 sec/hr = 36,000 filings/hour. Sufficient for nightly batch jobs.

**Risk if Invalid**: Ingestion takes too long, requires parallelization across multiple IPs.

**Mitigation**: Monitor ingestion time, implement multi-instance deployment if needed.

---

### Assumption 3: Network Failures are Transient
**Assumption**: Most API failures (503, timeouts) resolve within 3 retry attempts (~14 seconds total).

**Validation**: SEC EDGAR uptime SLA is 99.5% (observed via monitoring).

**Risk if Invalid**: Permanent outages require manual intervention.

**Mitigation**: Max retry limit (3 attempts), alert on repeated failures, manual fallback.

---

### Assumption 4: SHA256 Collision Risk is Negligible
**Assumption**: SHA256 collision probability is so low (2^-256) that content-based deduplication is safe.

**Validation**: No SHA256 collisions ever recorded in production use.

**Risk if Invalid**: Duplicate documents stored in Bronze layer.

**Mitigation**: Collision risk is mathematically negligible. No mitigation needed.

---

### Assumption 5: HTML Parsing is Deterministic
**Assumption**: BeautifulSoup4 with lxml parser produces consistent output for same input HTML.

**Validation**: Lxml is deterministic (same DOM tree for same input).

**Risk if Invalid**: Non-reproducible results violate SCA v13.8 determinism requirement.

**Mitigation**: Pin lxml version, test roundtrip parsing.

---

## Data Assumptions

### Assumption 6: SEC Filings Contain Sufficient ESG Data
**Assumption**: 10-K Item 1A (Risk Factors) and DEF 14A (Proxy) contain climate/ESG disclosures.

**Validation**: Manual review of 5 sample filings (AAPL, MSFT, XOM, CVX, BP) confirms ESG content.

**Risk if Invalid**: Extracted text lacks ESG evidence, scoring fails.

**Mitigation**: Expand to 10-K Item 7 (MD&A), add sustainability report scraping (Phase 2).

---

### Assumption 7: CIK is Unique Company Identifier
**Assumption**: SEC CIK (Central Index Key) uniquely identifies public companies, no duplicates.

**Validation**: SEC guarantees CIK uniqueness via EDGAR system constraints.

**Risk if Invalid**: Data attribution errors (filings assigned to wrong company).

**Mitigation**: Cross-reference CIK with ticker symbol, validate company name match.

---

### Assumption 8: Filing Amendments Use Same Accession Number
**Assumption**: Amended filings (10-K/A) have different accession numbers than originals.

**Validation**: SEC EDGAR manual specifies new accession number for amendments.

**Risk if Invalid**: SHA256 deduplication fails to detect amendments.

**Mitigation**: Store accession number separately, flag amendments in metadata.

---

## Infrastructure Assumptions

### Assumption 9: DuckDB Handles Bronze Layer Scale
**Assumption**: DuckDB can efficiently store 10,000+ SEC filings (each ~500KB HTML) in single database file.

**Validation**: DuckDB designed for datasets up to hundreds of GB. 10K filings = ~5GB raw, ~1GB compressed.

**Risk if Invalid**: Query performance degrades, database file corruption.

**Mitigation**: Monitor database size, implement partitioning if exceeds 50GB.

---

### Assumption 10: Single-Threaded Ingestion is Acceptable
**Assumption**: Sequential API calls (rate limited to 10 req/sec) complete nightly batch within 2 hours.

**Validation**: 100 companies × 2 filings × 1 second = 200 seconds (~3 minutes).

**Risk if Invalid**: Batch ingestion exceeds available time window.

**Mitigation**: Implement async I/O with `asyncio` + `aiohttp` if needed (Phase 4).

---

## Testing Assumptions

### Assumption 11: Mocked Tests Represent Real API Behavior
**Assumption**: `responses` library mocks accurately simulate SEC EDGAR API responses.

**Validation**: Integration tests with real API confirm mock parity.

**Risk if Invalid**: Tests pass but production fails due to API edge cases.

**Mitigation**: Maintain ≥1 integration test with real API per release.

---

### Assumption 12: Hypothesis Strategies Cover Edge Cases
**Assumption**: Property-based tests with Hypothesis discover edge cases not covered by example-based tests.

**Validation**: Hypothesis documentation shows 1000s of bugs found in production code.

**Risk if Invalid**: Uncaught edge cases cause production failures.

**Mitigation**: Run Hypothesis with max_examples=1000 in CI (currently 100).

---

## Organizational Assumptions

### Assumption 13: PyMuPDF License is Acceptable
**Assumption**: PyMuPDF's AGPL license is compatible with project use (internal PoC, not distributed software).

**Validation**: AGPL permits internal use without source disclosure requirement.

**Risk if Invalid**: Legal compliance issue if project becomes distributed product.

**Mitigation**: Document license in `LICENSES.md`, consult legal if distribution planned.

---

### Assumption 14: Development Environment Has Internet Access
**Assumption**: CI/CD environment can reach `https://data.sec.gov` for integration tests.

**Validation**: GitHub Actions provides internet access by default.

**Risk if Invalid**: Integration tests fail in restricted network environments.

**Mitigation**: Skip integration tests via `pytest -m "not requires_api"` in restricted envs.

---

### Assumption 15: User Email in User-Agent is Acceptable
**Assumption**: Including developer email in User-Agent header complies with SEC requirements and privacy policies.

**Validation**: SEC explicitly requires contact information in User-Agent.

**Risk if Invalid**: Spam/harassment of developer email.

**Mitigation**: Use team email (e.g., `esg-team@company.com`) instead of personal email.

---

## SCA v13.8 Compliance Assumptions

### Assumption 16: Simulated Embeddings are Acceptable for Phase 1
**Assumption**: Using deterministic simulated embeddings (not real watsonx.ai) is acceptable for Phase 1 API testing.

**Validation**: SCA v13.8 permits simulation if clearly documented and not claimed as production-grade.

**Risk if Invalid**: Validation fails if embeddings required for Phase 1 gate.

**Mitigation**: Document limitation in all test artifacts, integrate real watsonx.ai in Phase 2.

---

### Assumption 17: ≥95% Coverage is Achievable
**Assumption**: Can achieve ≥95% line and branch coverage with comprehensive unit + property tests.

**Validation**: Similar projects (CP-2) achieved 96% coverage.

**Risk if Invalid**: Coverage gate blocks Phase 1 completion.

**Mitigation**: Focus on CP files only (exclude boilerplate), write failure-path tests for all branches.

---

### Assumption 18: Tests Can Precede Implementation (TDD)
**Assumption**: Writing tests before implementation (TDD) is feasible for API provider enhancement.

**Validation**: TDD is standard practice for refactoring existing code with known behavior.

**Risk if Invalid**: Test-first approach slower than code-first.

**Mitigation**: Accept longer initial development time for higher quality and maintainability.

---

## Deployment Assumptions

### Assumption 19: Bronze Layer is Append-Only
**Assumption**: Bronze layer never deletes or updates records, only inserts new documents.

**Validation**: Data lake best practice (immutable raw data).

**Risk if Invalid**: Data inconsistency if updates/deletes occur.

**Mitigation**: Enforce append-only via DuckDB views, no DELETE permissions.

---

### Assumption 20: Environment Variables for Configuration
**Assumption**: SEC EDGAR User-Agent email configured via environment variable `SEC_EDGAR_EMAIL`.

**Validation**: 12-factor app best practice.

**Risk if Invalid**: Hardcoded email in source code violates privacy.

**Mitigation**: Require environment variable, raise error if missing.

---

**Total Assumptions**: 20
**Validated Assumptions**: 18
**Assumptions Requiring Monitoring**: 2 (API stability, rate limit sufficiency)

**Next Step**: Create `cp_paths.json` with Critical Path file list
