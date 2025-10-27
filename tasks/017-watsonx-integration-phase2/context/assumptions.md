# Assumptions - Phase 2: watsonx.ai Integration

## Data & Sources

1. **Real Corporate ESG PDFs Available**
   - Assumption: Apple, ExxonMobil, JPMorgan Chase 2023 ESG reports are cached locally and accessible
   - Verification: SHA256 hashes match crawl_metadata.json
   - Risk: PDF files moved/deleted → Mitigation: Verify checksums before processing

2. **PDF Text Extraction Reliable**
   - Assumption: PyMuPDF (fitz) can extract text from modern corporate PDFs
   - Verification: 13/13 extraction tests PASSED on Apple 126-page PDF
   - Risk: PDF format incompatibility → Mitigation: Fallback OCR provider (future phase)

3. **ESG Metrics Discoverable in Text**
   - Assumption: Real ESG metrics (emissions, diversity, governance) are present in extracted text
   - Verification: Apple page 12 contains "14.5" mmt CO2e emissions data
   - Risk: Metrics not in expected format → Mitigation: LLM extraction as alternative

4. **Public Document Accessibility**
   - Assumption: Corporate ESG reports remain publicly available at source URLs
   - Verification: All 3 URLs verified live as of 2025-10-22
   - Risk: Corporate URLs change → Mitigation: Maintain local cache

## Cloud Services

5. **IBM watsonx.ai Available**
   - Assumption: IBM watsonx.ai service operational and accessible with provided credentials
   - Verification: Credentials in .env.production configured
   - Risk: Service outage or credential expiration → Mitigation: Error handling with rate limit backoff

6. **Slate 125m Embeddings Stable**
   - Assumption: Slate 125m model produces consistent 384-dimensional vectors
   - Verification: Model specification from IBM documentation
   - Risk: Model deprecated or changed → Mitigation: Version pinning in API calls

7. **Granite LLM Functional**
   - Assumption: Granite 3.0-8B-Instruct LLM operational and responsive
   - Verification: Model in watsonx.ai catalog
   - Risk: Model availability changes → Mitigation: Fallback to alternative LLM

8. **AstraDB Operational**
   - Assumption: AstraDB vector database operational with provided credentials
   - Verification: Token in .env.production configured
   - Risk: Database unavailable → Mitigation: Connection pooling and health checks

9. **Vector Dimension Compatibility**
   - Assumption: AstraDB supports 384-dimensional vectors (Slate output)
   - Verification: AstraDB supports up to 4096 dimensions
   - Risk: Dimension mismatch → Mitigation: Validate on first upsert

## Rate Limiting

10. **API Rate Limits Enforced**
    - Assumption: watsonx.ai enforces 100 requests/hour rate limit
    - Verification: Rate limit documented in evidence.json
    - Risk: Rate limit exceeded → Mitigation: Exponential backoff (2^n seconds, max 32s)

11. **Exponential Backoff Sufficient**
    - Assumption: Exponential backoff with jitter resolves rate limit hits
    - Verification: Standard pattern for API rate limiting
    - Risk: Persistent rate limiting → Mitigation: Queue failed requests for retry

## Performance

12. **Embedding Latency <5s per Document**
    - Assumption: Slate embeddings API responds in <5 seconds per batch
    - Verification: API specification states <5s latency
    - Risk: Slower API response → Mitigation: Increase timeout, reduce batch size

13. **Similarity Search Latency <500ms**
    - Assumption: AstraDB ANN search returns top-K results in <500ms
    - Verification: AstraDB documentation states <500ms for 1M vectors
    - Risk: Slower queries → Mitigation: Index tuning, query optimization

14. **RAG Pipeline Latency <20s End-to-End**
    - Assumption: Complete RAG workflow (embed → search → LLM) completes in <20s
    - Verification: Target SLA from design.md
    - Risk: Longer latency → Mitigation: Parallelize where possible, optimize prompt

## Data Quality

15. **Extracted Text Quality ≥80%**
    - Assumption: PDF text extraction preserves semantic content with ≥80% accuracy
    - Verification: Manual sampling and verification tests
    - Risk: Corrupted/missing text → Mitigation: OCR fallback for unsupported PDFs

16. **Embedding Semantic Coherence**
    - Assumption: 384-dimensional embeddings capture semantic meaning
    - Verification: Cosine similarity >0.7 for related documents
    - Risk: Poor embedding quality → Mitigation: Alternative embeddings model

17. **LLM Response Coherence**
    - Assumption: Granite LLM generates coherent ESG analysis without hallucination
    - Verification: Manual review of generated responses
    - Risk: Hallucinations in responses → Mitigation: Prompt engineering, output validation

## Infrastructure

18. **Docker Services Running**
    - Assumption: Required Docker services (postgres, redis, minio) operational
    - Verification: docker-compose ps shows healthy services
    - Risk: Service outage → Mitigation: Service health checks, restart policies

19. **Credentials Secure**
    - Assumption: API credentials in .env.production are secure and not exposed
    - Verification: .env.production in .gitignore, no credentials in logs
    - Risk: Credential exposure → Mitigation: Credential rotation, secret scanning

20. **Network Connectivity**
    - Assumption: Outbound HTTPS connectivity to IBM watsonx.ai and AstraDB
    - Verification: Successful API calls during tests
    - Risk: Network issues → Mitigation: Proxy configuration, network debugging

## Testing

21. **TDD Guard Compliance**
    - Assumption: All CP files will have ≥1 @pytest.mark.cp, ≥1 @given property test, ≥1 failure-path test
    - Verification: Test file structure reviewed
    - Risk: Incomplete test coverage → Mitigation: SCA validator gates enforcement

22. **Test Execution Reproducible**
    - Assumption: Tests produce consistent results across multiple runs
    - Verification: Fixed seeds, pinned dependencies, deterministic order
    - Risk: Flaky tests → Mitigation: Explicit test ordering, fixed randomization

23. **Coverage ≥95% for CP Files**
    - Assumption: Code coverage of CP files reaches ≥95% line and branch coverage
    - Verification: Coverage measurement via pytest-cov
    - Risk: Incomplete coverage → Mitigation: SCA coverage enforcer gate

## Compliance

24. **SCA v13.8 Context Gate Passes**
    - Assumption: All 7 required context files present and valid
    - Verification: hypothesis.md, design.md, evidence.json, data_sources.json, cp_paths.json, adr.md, assumptions.md
    - Risk: Missing file → Mitigation: Context gate validation before coding

25. **No Placeholders in CP Code**
    - Assumption: CP files contain zero TODO/FIXME/PLACEHOLDER markers
    - Verification: SCA placeholder scanner (placeholders_cp.py)
    - Risk: Placeholder detection → Mitigation: Remove all before commit

26. **Type Hints Complete (100%)**
    - Assumption: All CP function signatures have full type hints
    - Verification: mypy --strict validation
    - Risk: Missing type hints → Mitigation: SCA type safety gate

27. **Docstrings Complete (≥95%)**
    - Assumption: ≥95% of CP functions have docstrings
    - Verification: interrogate tool validation
    - Risk: Missing docstrings → Mitigation: SCA docs enforcer gate

28. **Zero Security Vulnerabilities**
    - Assumption: No hardcoded credentials, SQL injection risks, or security issues
    - Verification: bandit security scanner
    - Risk: Security findings → Mitigation: SCA security gate

## Success Criteria Validity

29. **SC6-SC10 Measurable**
    - Assumption: All Phase 2 success criteria (SC6-SC10) are measurable and testable
    - Verification: Explicit metrics in hypothesis.md
    - Risk: Vague criteria → Mitigation: Quantified thresholds in tests

30. **Real Data Authenticity**
    - Assumption: All test data originates from verified real ESG sources
    - Verification: SHA256 hashes, timestamps, URL provenance
    - Risk: Synthetic data used → Mitigation: SCA authenticity scanner

---

## Approval

**Phase 2 Assumptions Document**: ✅ COMPLETE

All 30 assumptions documented with verification method and mitigation strategy.

**Next Step**: Proceed with MEA validation and implementation.
