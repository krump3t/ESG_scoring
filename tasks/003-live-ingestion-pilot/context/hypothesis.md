# Hypothesis: Live SEC EDGAR Ingestion Pilot

The wired MultiSourceCrawler + SECEdgarProvider can successfully download the 2024 Apple Inc. 10-K filing from SEC EDGAR to the local filesystem at `data/raw/sec_edgar`.

## Success Criteria

### Primary Metrics
- **Download Success:** File successfully retrieved from SEC API
- **File Integrity:** SHA256 hash calculated and non-empty
- **File Size:** Downloaded file > 100 KB (typical 10-K size)
- **File Location:** File saved to `data/raw/sec_edgar/AAPL_2024_10K.htm`

### Secondary Metrics
- **API Compliance:** No rate limit violations (HTTP 429 errors)
- **User-Agent Validation:** SEC accepts configured User-Agent
- **Error Handling:** Graceful failure if network unavailable

## Test Company

**Company:** Apple Inc.
**Ticker:** AAPL
**CIK:** 0000320193
**Report Type:** 10-K (Annual Report)
**Fiscal Year:** 2024 (most recent available)

**Rationale:**
- Apple is a well-known, high-volume SEC filer
- Guaranteed to have 10-K filings available
- Large, stable company with consistent reporting

## Critical Path

- `agents/crawler/multi_source_crawler.py` - Orchestrator initialization
- `agents/crawler/data_providers/sec_edgar_provider.py` - SEC API integration
- `data/raw/sec_edgar/` - Download destination

## Exclusions

- Not testing multi-document batch ingestion
- Not testing error recovery/retry logic
- Not testing all report types (only 10-K)
- Not testing all companies (only AAPL)

## Risks

### Risk 1: Network Connectivity
- **Impact:** High - pilot cannot proceed without internet
- **Mitigation:** Script catches connection errors gracefully
- **Fallback:** Document network requirements in HANDOFF

### Risk 2: SEC API Availability
- **Impact:** Medium - SEC may be down for maintenance
- **Mitigation:** Check SEC EDGAR status before execution
- **Fallback:** Retry logic or manual retry

### Risk 3: Rate Limiting
- **Impact:** Low - single download unlikely to trigger
- **Mitigation:** Built-in rate limiter (0.1s delay)

### Risk 4: Filing Not Yet Available
- **Impact:** Low - Apple files consistently
- **Mitigation:** Script can fall back to 2023 filing
- **Validation:** Check SEC EDGAR for latest Apple 10-K

## Acceptance

This hypothesis is **accepted** if:
1. Script executes without exceptions
2. File downloaded to `data/raw/sec_edgar/AAPL_2024_10K.htm`
3. File size > 100 KB
4. SHA256 hash calculated successfully
5. Pilot manifest generated with metadata

This hypothesis is **rejected** if:
1. Network/API errors occur (document in HANDOFF)
2. File not downloaded or empty
3. Exceptions raised (document error)
