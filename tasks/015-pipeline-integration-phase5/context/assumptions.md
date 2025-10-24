# Assumptions - Phase 5: End-to-End Pipeline Integration

**Task ID**: 015-pipeline-integration-phase5
**Phase**: 5
**Date**: 2025-10-24
**SCA Protocol**: v13.8-MEA

---

## Technical Assumptions

### A1: Phase 2 Crawler Output Format
**Assumption**: Phase 2 MultiSourceCrawlerV2 returns CompanyReport with fields: company_name, cik, fiscal_year, local_path, content, sha256, source, timestamp.

**Justification**: Phase 2 is complete with validated implementation.

**Risk**: Low - Phase 2 has 98% coverage, implementation is stable
**Mitigation**: Review Phase 2 code before implementing Phase 5 orchestrator

**Validation**: Integration test: Feed Phase 2 output directly to Phase 3 input

---

### A2: Phase 3 Extractor Input Compatibility
**Assumption**: Phase 3 ExtractionRouter accepts CompanyReport from Phase 2 without modification.

**Justification**: Phase 3 design expects CompanyReport input; Phases 2-3 interface is proven.

**Risk**: Medium - Interface compatibility depends on exact field names/types
**Mitigation**: Validate Phase 2 → 3 handoff FIRST before full pipeline

**Validation**: Unit test: Pass Phase 2 output to Phase 3 extractor

---

### A3: ESGMetrics Pydantic Model Stability
**Assumption**: ESGMetrics model from Phase 3 will not change during Phase 5 implementation.

**Justification**: Phase 3 is complete; model is frozen.

**Risk**: Low - Phase 3 already finalized
**Mitigation**: No changes to ESGMetrics; if needed, Phase 6 addresses model evolution

**Validation**: Phase 5 tests use same ESGMetrics model as Phase 3

---

### A4: Parquet Schema from Phase 3 is Compatible
**Assumption**: Phase 4's ESG_METRICS_PARQUET_SCHEMA exactly matches ESGMetrics fields from Phase 3.

**Justification**: Phase 4 is complete with proven Parquet round-trip (100% coverage).

**Risk**: Low - Phase 4 validated schema compatibility
**Mitigation**: Reuse Phase 4's schema validation logic

**Validation**: Phase 5 write→query test confirms schema compatibility

---

### A5: DuckDB Query Execution is Deterministic
**Assumption**: DuckDB queries on same Parquet file return identical results.

**Justification**: DuckDB is deterministic (no randomness in SQL execution).

**Risk**: Low - Standard property of SQL databases
**Mitigation**: No mitigation needed; inherent to DuckDB

**Validation**: Run same query twice, compare results

---

## Data Assumptions

### A6: Microsoft SEC 10-K Data Available via API
**Assumption**: SEC EDGAR API returns Microsoft (CIK 0000789019) FY2024 10-K filing in JSON format.

**Justification**: Microsoft is large-cap company; 10-K filings are mandatory.

**Risk**: Medium - API could be down, rate limits could apply
**Mitigation**: Implement retry logic (exponential backoff), cache fallback

**Validation**: Test Phase 2 crawler independently on Microsoft CIK

---

### A7: Tesla SEC 10-K Data Available via API
**Assumption**: SEC EDGAR API returns Tesla (CIK 0001318605) FY2024 10-K filing.

**Justification**: Tesla is large-cap company; 10-K filings are mandatory.

**Risk**: Medium - API could be down, rate limits could apply
**Mitigation**: Implement retry logic, cache fallback

**Validation**: Test Phase 2 crawler independently on Tesla CIK

---

### A8: Ground Truth Metrics Are Accurately Extracted
**Assumption**: Manually extracted Microsoft & Tesla ground truth values are correct (±0.1% accuracy).

**Justification**: Manual extraction from official SEC EDGAR database.

**Risk**: Low - Human verification reduces error risk
**Mitigation**: Double-check ground truth values against official SEC filings

**Validation**: Ground truth used for SC4 (±1% tolerance validation)

---

### A9: SEC EDGAR API Respects Rate Limiting
**Assumption**: SEC EDGAR API enforces rate limiting at ~10 RPS, returns 429 on excess requests.

**Justification**: SEC documentation specifies rate limits; Phase 2 already implements throttling.

**Risk**: Low - Phase 2 proven with SEC data
**Mitigation**: Use Phase 2's existing throttle (1-2s per request)

**Validation**: Monitor API response codes, implement retry logic

---

## Integration Assumptions

### A10: Phase 2-3-4 Components are Thread-Safe
**Assumption**: Crawler, Extractor, Writer components can be called sequentially without state conflicts.

**Justification**: Each phase is stateless (no shared mutable state).

**Risk**: Low - Each phase designed for independence
**Mitigation**: No mitigation needed; phases are independent

**Validation**: Run multiple companies sequentially, confirm no cross-contamination

---

### A11: Parquet Files are Readable After Write
**Assumption**: Parquet file written by Phase 4 can be read immediately by Phase 4 DuckDB reader.

**Justification**: Phase 4 write→query test validates this (100% coverage).

**Risk**: Low - Phase 4 proven
**Mitigation**: No mitigation needed

**Validation**: Phase 5 end-to-end test confirms write→read works

---

### A12: No Network Connectivity Required (Except SEC API)
**Assumption**: All components (crawler, extractor, writer, reader, validator) run locally after SEC API call.

**Justification**: Phases 3-4 are local; only Phase 2 requires network.

**Risk**: Low - Phases 3-4 are offline
**Mitigation**: Cache Phase 2 output if network unavailable

**Validation**: Run Phase 5 in offline mode (using cached data)

---

## Testing Assumptions

### A13: Hypothesis Property Tests are Feasible
**Assumption**: Can generate random valid company CIKs and fiscal years for property-based testing.

**Justification**: Hypothesis supports integer strategies; CIK is integer, fiscal_year is integer.

**Risk**: Low - Hypothesis is flexible
**Mitigation**: Use realistic ranges (CIK > 0, fiscal_year 2000-2030)

**Validation**: Property test: any valid CIK/year → pipeline completes or fails gracefully

---

### A14: Real Data Tests Won't Exceed Timeout
**Assumption**: Full pipeline (crawl → query) completes in <60s (test timeout).

**Justification**: SC5 target is <60s; Phase 2 throttling controls API access.

**Risk**: Medium - Actual latency depends on SEC API performance
**Mitigation**: Measure baseline, increase timeout if needed, use cached data

**Validation**: Benchmark pipeline latency for Microsoft & Tesla

---

### A15: Test Fixtures Can Capture SEC API Responses
**Assumption**: Can save SEC API responses to `data/raw/sec_edgar/*/` for replay in tests.

**Justification**: Phase 2 already implements this pattern; Phase 3B also uses fixtures.

**Risk**: Low - Proven pattern from earlier phases
**Mitigation**: Reuse Phase 2's caching logic

**Validation**: Save Microsoft & Tesla responses, use in offline tests

---

## Performance Assumptions

### A16: ±1% Tolerance is Appropriate for Numeric Metrics
**Assumption**: Financial metrics can vary by ±1% due to rounding, unit conversions, date variations.

**Justification**: SEC filings round to millions/billions; variation is legitimate.

**Risk**: Low - 1% is standard tolerance in financial analysis
**Mitigation**: If tolerance too loose, tighten to 0.5%; if too tight, loosen to 2%

**Validation**: Compare extracted vs ground truth, observe actual variation distribution

---

### A17: <60 Second Latency is Acceptable for PoC
**Assumption**: 60-second end-to-end latency is satisfactory for proof-of-concept.

**Justification**: Dominated by SEC API throttling (20-40s); extracting, writing, querying are <10s each.

**Risk**: Low - Target is realistic for PoC
**Mitigation**: If latency exceeds 60s, document bottleneck and propose Phase 6 optimization

**Validation**: Measure actual latencies in Phase 5 tests

---

### A18: ≥95% Field Completeness is Achievable
**Assumption**: Most companies will have ≥95% of expected ESG fields populated after extraction.

**Justification**: Financial metrics (assets, liabilities, income) are always in SEC 10-K.

**Risk**: Medium - ESG metrics may be missing for some companies
**Mitigation**: Accept 80-95% for companies with limited ESG disclosures; adjust SC3 if needed

**Validation**: Measure actual completeness % for Microsoft & Tesla

---

## Scope Assumptions

### A19: Single-Company Processing (No Multi-Company Queuing)
**Assumption**: Phase 5 processes one company at a time (sequential, not concurrent).

**Justification**: PoC scope, parallelization deferred to Phase 6.

**Risk**: Low - Clearly scoped
**Mitigation**: Document as Phase 5 limitation

**Validation**: Implementation processes one company from start to finish

---

### A20: Local Filesystem Only (No Cloud Storage)
**Assumption**: Parquet files stored on local filesystem (`data_lake/`); no S3/GCS.

**Justification**: PoC scope, cloud storage deferred to Phase 6.

**Risk**: Low - Clearly scoped
**Mitigation**: Document as Phase 5 limitation

**Validation**: Verify Parquet files stored locally

---

### A21: No Schema Evolution (Frozen ESGMetrics)
**Assumption**: ESGMetrics model will not change during Phase 5 implementation.

**Justification**: Phase 3 is complete; model is stable.

**Risk**: Low - Phase 3 frozen
**Mitigation**: No changes needed; any future changes defer to Phase 6

**Validation**: Phase 5 tests use Phase 3's ESGMetrics model as-is

---

### A22: Fail-Closed on Critical Errors (No Silent Failures)
**Assumption**: If any critical error occurs (crawler fail, extraction fail, write fail), pipeline stops with clear error.

**Justification**: Authentic computation mandate; no silent failures or fabricated data.

**Risk**: Low - Fail-closed is safer than fail-open
**Mitigation**: Implement comprehensive error handling

**Validation**: Error handling tests verify fail-closed behavior

---

### A23: No External Dependencies Beyond Phases 2-4
**Assumption**: Phase 5 orchestrator only depends on existing Phase 2-4 code; no new external libraries.

**Justification**: Minimize dependencies, maximize stability.

**Risk**: Low - Phase 2-4 are complete with all dependencies
**Mitigation**: Only import from Phase 2-4 modules

**Validation**: Phase 5 imports are minimal (only Phase 2-4 + standard lib)

---

**Prepared By**: Scientific Coding Agent v13.8-MEA
**Status**: 23 Assumptions Documented
**Next**: Create cp_paths.json
