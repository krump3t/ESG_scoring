# Hypothesis & Success Criteria - Phase 5: End-to-End Pipeline Integration

**Task ID**: 015-pipeline-integration-phase5
**Phase**: 5
**Date**: 2025-10-24
**SCA Protocol**: v13.8-MEA

---

## Primary Hypothesis

**The complete ESG data pipeline (Phase 2 crawler → Phase 3 asymmetric extractor → Phase 4 data lake) successfully processes multiple real companies with authentic data, validating end-to-end system integration, data integrity, and cross-phase compatibility.**

### Core Claims
1. Multi-phase orchestration works seamlessly without manual intervention
2. Data integrity is preserved across all phase boundaries (SHA256 validation)
3. Query results on stored data match ground truth from SEC filings (±1% tolerance)
4. Error handling prevents cascade failures (one phase error ≠ pipeline failure)
5. Total pipeline latency is acceptable for proof-of-concept (<60 seconds per company)

---

## Success Criteria (SC1-SC5)

### SC1: Multi-Company Pipeline Success
**Statement**: The pipeline successfully processes ≥2 real companies end-to-end

**Target Companies**:
- **Microsoft Corporation** (CIK 0000789019, FY2024)
  - Structured data (SEC 10-K financial statements)
  - Sustainability disclosures (renewable energy 100%)
- **Tesla, Inc.** (CIK 0001318605, FY2024)
  - Unstructured sustainability reports
  - Tests LLM-based extraction quality

**Success Metric**: Both companies complete: Crawl → Extract → Store → Query (zero failures)

**Measurement**:
```
result = pipeline.run_pipeline("0000789019", 2024)  # Microsoft
assert result.success == True
assert result.phase_completed == "query"

result = pipeline.run_pipeline("0001318605", 2024)  # Tesla
assert result.success == True
assert result.phase_completed == "query"
```

---

### SC2: Data Integrity (SHA256 Validation)
**Statement**: Data integrity is 100% verified at each phase boundary

**Validation Points**:
1. **Phase 2 → 3**: Crawler output matches extractor input (SHA256)
2. **Phase 3 → 4**: Extracted metrics match writer input (SHA256)
3. **Phase 4 → Query**: Parquet file integrity verified before querying

**Success Metric**: Zero SHA256 mismatches across all transitions

**Measurement**:
```
crawler_output_sha256 = "abc123..."
extractor_input_sha256 = calculate_sha256(extractor_input)
assert crawler_output_sha256 == extractor_input_sha256

extractor_metrics_sha256 = "def456..."
writer_input_sha256 = calculate_sha256(writer_input)
assert extractor_metrics_sha256 == writer_input_sha256
```

---

### SC3: Metric Field Completeness
**Statement**: ≥95% of expected ESGMetrics fields are populated (non-null)

**Expected Fields** (from Phase 3 ESGMetrics model):
- Financial: assets, liabilities, net_income, cik, fiscal_year
- Environmental: scope1_emissions, scope2_emissions, renewable_energy_pct, water_withdrawal
- Social: women_in_workforce_pct, employee_turnover_pct
- Governance: board_independence_pct
- Metadata: extraction_timestamp, data_source, confidence_score

**Success Metric**:
```
total_expected_fields = 14
null_fields_per_company = count_null_fields(metrics)
completion_pct = (total_expected_fields - null_fields_per_company) / total_expected_fields * 100
assert completion_pct >= 0.95  # 95% or higher
```

**Rationale**: Not all metrics available for all companies (e.g., Tesla may not disclose certain environmental metrics), but core financial metrics should always be present.

---

### SC4: Query Results Match Ground Truth
**Statement**: Query results on stored metrics match SEC filing ground truth (±1% tolerance)

**Ground Truth Definition**:
- Manually extracted from SEC 10-K filings (Microsoft & Tesla FY2024)
- Verified against official SEC EDGAR database
- Stored in `context/ground_truth/<cik>_<year>.json`

**Example Ground Truth** (Microsoft):
```json
{
  "cik": "0000789019",
  "fiscal_year": 2024,
  "assets": 512163000000.0,  // $512.163B
  "liabilities": 238515000000.0,  // $238.515B
  "net_income": 88136000000.0  // $88.136B
}
```

**Success Metric**:
```
query_result = query_latest_metrics("Microsoft Corporation")
ground_truth = load_ground_truth("0000789019", 2024)

tolerance = 0.01  # ±1%
assert abs(query_result.assets - ground_truth.assets) / ground_truth.assets <= tolerance
assert abs(query_result.net_income - ground_truth.net_income) / ground_truth.net_income <= tolerance
```

---

### SC5: Performance Baseline (<60 seconds total latency)
**Statement**: Complete pipeline execution (crawl → query) completes in <60 seconds per company

**Measurement Points**:
- t0: Pipeline start
- t1: Phase 2 (crawler) completes
- t2: Phase 3 (extractor) completes
- t3: Phase 4 (writer) completes
- t4: Phase 4 (query) completes

**Success Metric**:
```
total_latency = t4 - t0
assert total_latency < 60  # seconds

# Bonus: Breakdown per phase
assert (t1 - t0) < 20  # Crawl should be fast (API limited)
assert (t2 - t1) < 20  # Extract should be fast (no external calls)
assert (t3 - t2) < 10  # Write should be fast (local Parquet)
assert (t4 - t3) < 10  # Query should be fast (in-memory DuckDB)
```

**Rationale**: 60s target is acceptable for PoC; SEC EDGAR API throttling (~1-2 rps) is largest factor.

---

## Acceptance Criteria

**Phase 5 passes when ALL of the following are true**:

1. ✅ Microsoft pipeline: Success (SC1)
2. ✅ Tesla pipeline: Success (SC1)
3. ✅ SHA256 validation: 100% pass rate (SC2)
4. ✅ Field completeness: ≥95% for all companies (SC3)
5. ✅ Ground truth match: ±1% tolerance for all metrics (SC4)
6. ✅ Total latency: <60 seconds per company (SC5)
7. ✅ All tests passing: 15-20 @pytest.mark.e2e tests
8. ✅ Coverage: ≥95% line, ≥90% branch on CP files
9. ✅ MEA validation: status == "ok"

---

## Power Analysis & Sample Size

**Companies Tested**: 2 (Microsoft, Tesla)
- Rationale: Different industries, validates generalization
- Microsoft: Traditional tech (financial metrics reliable)
- Tesla: Sustainability-focused (ESG metrics rich)

**Metrics per Company**: 13 core fields
- Rationale: From Phase 3 ESGMetrics model

**Confidence Level**: 95% (standard for PoC validation)
- Rationale: Two successful companies reduces risk of single-company flukes

**Sample Size Justification**:
- 2 companies × 13 metrics = 26 data points
- Adequate for PoC (full pipeline coverage)
- Insufficient for production generalization (Phase 6 will test 10+ companies)

---

## Risks & Mitigation

### Risk 1: SEC EDGAR API Rate Limiting
**Risk**: API returns 429 (too many requests) → crawler fails

**Mitigation**:
- Implement exponential backoff (2s, 4s, 8s)
- Cache responses in `data/raw/sec_edgar/<cik>_<year>/` with manifest.json
- Use cached response if available (replay fixture)
- Set conservative throttle: 1 request per 2 seconds

---

### Risk 2: Phase 2-3 Interface Incompatibility
**Risk**: Crawler output format ≠ extractor input format → extraction fails

**Mitigation**:
- Review Phase 2 crawler output structure before implementing Phase 5
- Create adapter layer if formats differ
- Write integration test to validate Phase 2 → 3 handoff FIRST

---

### Risk 3: LLM Extraction Quality (Tesla)
**Risk**: PDF extraction returns mostly null values → completeness <95%

**Mitigation**:
- Set SC3 threshold at 95% (financial metrics), not 100%
- Accept some null ESG fields as expected
- Document which fields are typically null for which companies

---

### Risk 4: 60-Second Latency Target Too Aggressive
**Risk**: Real SEC EDGAR throttling causes pipeline >60s → fails SC5

**Mitigation**:
- Document assumption: Phase 2 accounts for 30-40s of latency (SEC API throttle)
- If actual latency >60s, propose SC5 revision to 90s for PoC phase
- Phase 6 will optimize (parallel crawling, caching)

---

## Exclusions & Out-of-Scope

- **Multi-tenancy**: Phase 5 is single-tenant (one pipeline execution at a time)
- **Parallel execution**: Phase 5 is sequential (Phase 2 → 3 → 4 → query)
- **Error recovery**: No automatic retry; failures are logged and reported
- **Performance optimization**: Baseline latency measured, not optimized
- **Production deployment**: Phase 5 is local execution only (no cloud)

---

**Prepared By**: Scientific Coding Agent v13.8-MEA
**Status**: Hypothesis & Success Criteria Complete
**Next**: Create design.md
