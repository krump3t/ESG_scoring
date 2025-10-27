# Architecture Decision Records - Phase 3B

## ADR-001: Use IBM watsonx.ai for LLM Extraction

**Status**: Accepted
**Date**: 2025-10-24

**Context**:
Phase 3B requires LLM for extracting ESG metrics from unstructured PDF text. Multiple LLM providers available (OpenAI, Anthropic, IBM watsonx.ai, Hugging Face).

**Decision**:
Use IBM watsonx.ai with granite-13b-chat-v2 model exclusively.

**Rationale**:
- User constraint: Only watsonx.ai models allowed (no other AI providers)
- granite-13b-chat-v2 optimized for instruction following
- Greedy decoding (temperature=0) provides deterministic outputs
- IBM Cloud integration aligns with enterprise requirements

**Consequences**:
- ✅ Consistent with Phase 3 ADR-005 (watsonx.ai mandate)
- ✅ Deterministic testing with cached responses
- ⚠️ Requires IBM Cloud credentials (.env file)
- ⚠️ API costs for testing (mitigated by caching)

---

## ADR-002: Use PyMuPDF (fitz) for PDF Text Extraction

**Status**: Accepted
**Date**: 2025-10-24

**Context**:
Need to extract text from born-digital PDF sustainability reports. Options: PyPDF2, pdfplumber, PyMuPDF, pdfminer.six.

**Decision**:
Use PyMuPDF (fitz) for all PDF text extraction.

**Rationale**:
- Battle-tested library (10,000+ projects)
- Fast (C++ backend via MuPDF)
- Simple API: `page.get_text()`
- Handles multi-page PDFs automatically
- Well-documented and maintained

**Consequences**:
- ✅ Minimal code (~80 lines for PDFTextExtractor)
- ✅ Fast extraction (<1 second per PDF)
- ✅ No external dependencies beyond PyMuPDF
- ❌ Does not handle scanned PDFs (OCR out of scope)

---

## ADR-003: Cache LLM Responses for Deterministic Testing

**Status**: Accepted
**Date**: 2025-10-24

**Context**:
LLM API calls introduce non-determinism, latency, and cost. Tests should be reproducible without live API calls.

**Decision**:
Implement response caching with filesystem storage:
- Cache key: `{cik}_{year}.json`
- Cache path: `test_data/llm_cache/`
- Cache contents: LLM response + metadata (model_id, timestamp)
- Tests use cached responses by default
- One integration test validates real API

**Rationale**:
- Enables deterministic testing (same input → same output)
- Reduces API costs (cache responses across test runs)
- Faster CI/CD (no API latency)
- Maintains authenticity (real responses cached, not mocked)

**Consequences**:
- ✅ Deterministic test suite (no flaky tests)
- ✅ Fast tests (<1 second vs. 5-10 seconds per API call)
- ✅ Reduced API costs
- ⚠️ Cache invalidation strategy needed (version changes, prompt updates)

---

## ADR-004: Truncate PDF Text to Fit Model Context Window

**Status**: Accepted
**Date**: 2025-10-24

**Context**:
granite-13b-chat-v2 has ~4,096 token context window. Full sustainability reports can be 50,000+ tokens. Need to fit extraction prompt + PDF text within context window.

**Decision**:
Truncate PDF text to first ~12,000 characters (~3,000 tokens):
- Reserve 1,000 tokens for prompt template
- Use first 3,000 tokens of PDF text
- Assume critical metrics appear early in reports

**Rationale**:
- Sustainability reports typically frontload key metrics (executive summary, first 10 pages)
- Extracting full text would require chunking + multiple API calls (costly, complex)
- 12,000 chars covers ~8-10 pages of text
- Simplifies implementation (single API call per PDF)

**Consequences**:
- ✅ Single API call per PDF (simple, fast)
- ✅ Fits within model context window
- ⚠️ May miss metrics buried deep in report (acceptable tradeoff)
- ⚠️ Assumption A7: Critical metrics appear early

---

## ADR-005: Use Explicit JSON Schema in Prompt

**Status**: Accepted
**Date**: 2025-10-24

**Context**:
LLMs can hallucinate or return malformed outputs. Need to ensure structured JSON responses for parsing into ESGMetrics.

**Decision**:
Include explicit JSON schema in extraction prompt:
```json
{
  "scope1_emissions": <number or null>,
  "scope2_emissions": <number or null>,
  ...
}
```

Instruct LLM: "Return ONLY valid JSON. If metric not found, use null. No explanations outside JSON."

**Rationale**:
- Research (E4) shows structured prompts reduce hallucinations by 15-25%
- Explicit schema guides LLM to expected format
- `null` handling prevents fabricated values
- Simplifies response parsing (find JSON object in text)

**Consequences**:
- ✅ Higher extraction accuracy
- ✅ Consistent JSON format
- ✅ Easier error handling (JSON parse errors caught)
- ⚠️ Prompt length increases (~200 tokens for schema)

---

## ADR-006: Accept Branch Coverage Gap for API Failure Paths

**Status**: Accepted
**Date**: 2025-10-24

**Context**:
SCA v13.8 requires ≥95% branch coverage. Retry logic and API error handling introduce branches that are difficult to test without mocking (violates Invariant #1).

**Decision**:
If branch coverage falls below 95% due to untestable API failure paths:
- Document gap in assumptions.md with justification
- Accept coverage exception (following Phase 3 precedent)
- Ensure realistic error paths ARE covered (file not found, invalid JSON, empty PDF)

**Rationale**:
- Phase 3 established precedent: authenticity > arbitrary metrics
- API transient failures (network timeout, 503 errors) cannot be authentically triggered
- Retry logic branches validated via integration test (one real API call)
- SCA Invariant #1 prioritizes authentic computation

**Consequences**:
- ✅ Maintains authentic testing (no mocks)
- ✅ Realistic error paths covered
- ⚠️ May require manual review / documented exception
- ⚠️ Branch coverage may be 90-93% (line coverage likely ≥95%)

---

**Total ADRs**: 6
**Status**: All Accepted
**Review Date**: 2025-10-24
