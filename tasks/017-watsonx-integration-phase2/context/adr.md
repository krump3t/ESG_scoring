# Architecture Decision Records (ADR) - Phase 2: watsonx.ai Integration

## ADR-1: Use Real Corporate ESG PDFs (Zero Fabrication)

**Status**: ACCEPTED

**Decision**: Use 3 real Fortune 500 corporate ESG reports (Apple, ExxonMobil, JPMorgan Chase) instead of synthetic test documents.

**Rationale**:
- SCA v13.8 mandate: Zero fabrication, no invented/mocked data
- Authentic computation requires real data from verified sources
- Corporate ESG reports are publicly available and contain realistic metrics
- SHA256 integrity verification ensures data authenticity

**Alternatives Considered**:
1. Synthetic ESG documents (rejected: violates zero-fabrication mandate)
2. Mock API responses (rejected: SCA v13.8 requires authentic computation)

**Consequences**:
- ✓ Maximum authenticity (real Fortune 500 documents)
- ✓ Verifiable via SHA256 hashes
- ✓ SCA v13.8 compliant
- ~ Requires real API credentials (IBM watsonx.ai, AstraDB)
- ~ API costs may apply (validate free tier limits)

---

## ADR-2: Slate 125m Embeddings (384-dimensional Vectors)

**Status**: ACCEPTED

**Decision**: Use IBM watsonx.ai Slate 125m embeddings model for generating 384-dimensional vectors from ESG document text.

**Rationale**:
- Slate 125m is specialized for semantic similarity in English text
- 384-dimensional output is optimal for ANN similarity search in AstraDB
- IBM-provided model aligned with watsonx.ai platform
- Batch processing capability (5-10 documents per request)

**Alternatives Considered**:
1. OpenAI embeddings (rejected: requires separate credentials, different model)
2. Open-source embeddings (rejected: less optimized for domain-specific text)

**Consequences**:
- ✓ Optimized for ESG document analysis
- ✓ Batch processing for efficiency
- ✓ 384-dimensional vectors compatible with AstraDB
- ~ Requires watsonx.ai authentication
- ~ Rate limit: 100 requests/hour

---

## ADR-3: AstraDB Vector Storage with SAI Indexing

**Status**: ACCEPTED

**Decision**: Use AstraDB (Cassandra-based) for vector storage with Storage-Attached Index (SAI) for ANN similarity search.

**Rationale**:
- Native vector search capability built on Cassandra
- SAI provides efficient approximate nearest neighbor search
- Supports 384-dimensional vectors (Slate output)
- <500ms query latency for 1M vectors
- Production-grade reliability

**Alternatives Considered**:
1. Pinecone (rejected: requires separate service, different vector format)
2. Milvus (rejected: requires additional deployment, operational overhead)
3. In-memory cache (rejected: insufficient for production scale)

**Consequences**:
- ✓ Reliable vector storage
- ✓ Fast similarity search (<500ms)
- ✓ Integration with existing AstraDB infrastructure
- ~ Requires AstraDB authentication and provisioning
- ~ Vector storage costs for 31.3 MB of documents

---

## ADR-4: Granite 3.0-8B-Instruct for Context-Aware Analysis

**Status**: ACCEPTED

**Decision**: Use IBM watsonx.ai Granite 3.0-8B-Instruct LLM for RAG-based ESG document analysis.

**Rationale**:
- Production-grade LLM optimized for text generation
- 4096-token context window sufficient for RAG augmentation
- ESG-focused prompt engineering for domain-specific analysis
- Rate limiting enforced to prevent API quota exhaustion

**Alternatives Considered**:
1. GPT-4 (rejected: separate credentials, higher cost)
2. LLaMA 2 (rejected: less optimized for ESG domain)

**Consequences**:
- ✓ Domain-specific ESG analysis capability
- ✓ Reliable inference from context
- ✓ Cost-effective for Phase 2 testing
- ~ Rate limit: 100 requests/hour
- ~ Inference latency: <10 seconds per query

---

## ADR-5: TDD-First Implementation (Tests Before Code)

**Status**: ACCEPTED

**Decision**: Write all tests BEFORE implementing CP files, following TDD guard requirements.

**Rationale**:
- SCA v13.8 TDD guard: Each CP file requires ≥1 @pytest.mark.cp test, ≥1 Hypothesis property test, ≥1 failure-path test
- Tests define contract before implementation
- Property-based tests validate invariants
- Failure-path tests ensure error handling

**Consequences**:
- ✓ Clear specification via tests
- ✓ SCA v13.8 compliance enforced
- ✓ High test coverage (95%+)
- ✓ Error handling validated upfront
- ~ Requires test writing before implementation

---

## ADR-6: Real Data Ingestion Pipeline

**Status**: ACCEPTED

**Decision**: Ingest real ESG documents through complete pipeline: crawl → extract → embed → store → retrieve → analyze.

**Rationale**:
- Authentic end-to-end workflow validation
- Tests real API integration (not mocked)
- Validates data quality at each stage
- Produces real artifacts for downstream phases

**Consequences**:
- ✓ Authentic data processing workflow
- ✓ Real API integration tested
- ✓ Full traceability from source PDF to LLM response
- ~ Longer test execution times (API latency)
- ~ Requires all cloud services operational

---

## ADR-7: Exponential Backoff for Rate Limiting

**Status**: ACCEPTED

**Decision**: Implement exponential backoff with jitter for rate limit handling (2^n seconds, max 32 seconds).

**Rationale**:
- IBM watsonx.ai rate limit: 100 requests/hour
- Exponential backoff prevents thundering herd
- Jitter ensures fair allocation across concurrent requests
- Max 3 retries before failure

**Consequences**:
- ✓ Reliable rate limit handling
- ✓ Fair API resource allocation
- ~ Slower execution on rate limit hits
- ✓ Transparent retry logging

---

## ADR-8: SHA256 Integrity Verification

**Status**: ACCEPTED

**Decision**: Verify SHA256 hashes of all PDF documents against crawl metadata.

**Rationale**:
- Ensures data authenticity (documents not modified)
- Validates source integrity
- Provides audit trail for compliance

**Consequences**:
- ✓ Verifiable data source integrity
- ✓ Audit trail for SCA v13.8
- ✓ Detection of data corruption
- Minimal performance impact

---

## ADR-9: Separate Test/Production Splits

**Status**: ACCEPTED

**Decision**: Maintain separate train/test document sets to prevent data leakage in validation.

**Rationale**:
- Prevents evaluation set contamination
- Ensures honest metric reporting
- SCA v13.8 authentic validation mandate

**Consequences**:
- ✓ Honest metric reporting
- ✓ Validation leakage guards
- ~ Requires larger corpus for both sets

---

## ADR-10: Audit Trail Logging

**Status**: ACCEPTED

**Decision**: Generate complete audit trail (qa/run_log.txt, artifacts/run_manifest.json, artifacts/run_events.jsonl) for all Phase 2 operations.

**Rationale**:
- SCA v13.8 traceability hard gate
- Complete record of data processing
- Reproducibility and debugging support

**Consequences**:
- ✓ Complete operational traceability
- ✓ SCA v13.8 compliance
- ✓ Reproducible execution
- ✓ Transparent logging
