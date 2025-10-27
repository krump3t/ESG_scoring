# Architecture Decision Records - Phase 3

## ADR-001: Use Content-Type Routing (Not File Extension)
**Decision**: Route extraction based on SourceRef.content_type field, not file extension
**Rationale**: Content-type is authoritative (from HTTP headers or provider metadata), file extensions unreliable
**Alternatives Considered**: File extension parsing, magic number detection
**Impact**: Requires Phase 2 SourceRef.content_type field (already implemented)

## ADR-002: Asymmetric Extraction Paths (Not Unified)
**Decision**: Separate StructuredExtractor and LLMExtractor, not single unified extractor
**Rationale**: Structured data (JSON) and unstructured (PDF) have fundamentally different processing logic and accuracy targets
**Alternatives Considered**: Single extractor with if/else branches, plugin architecture
**Impact**: Simpler code (CCN ≤5 for router), clear separation of concerns

## ADR-003: Pydantic for Schema Validation (Not JSON Schema)
**Decision**: Use Pydantic BaseModel for ESGMetrics, not raw JSON Schema
**Rationale**: Pydantic provides runtime validation, IDE autocomplete, mypy type checking
**Alternatives Considered**: JSON Schema + jsonschema library, dataclasses + marshmallow
**Impact**: Requires pydantic dependency, enables 1:1 Parquet schema parity

## ADR-004: PyMuPDF for PDF Text Extraction (Not pdfplumber)
**Decision**: Use PyMuPDF (fitz) for PDF text extraction
**Rationale**: Faster, better text ordering, actively maintained
**Alternatives Considered**: pdfplumber, PyPDF2, tika
**Impact**: Requires PyMuPDF dependency (already used in Phase 1)

## ADR-005: Use IBM watsonx.ai for LLM Extraction (Not OpenAI)
**Decision**: Use IBM watsonx.ai foundation models (granite-13b-chat-v2 or llama-2-70b-chat)
**Rationale**: Enterprise requirement for IBM Cloud infrastructure, IAM authentication, data residency
**Alternatives Considered**: OpenAI GPT-4, Anthropic Claude, local llama.cpp
**Impact**: Requires ibm-watsonx-ai SDK, IAM token management, IBM Cloud project setup

## ADR-006: Greedy Decoding for Determinism (Not Sampling)
**Decision**: Use greedy decoding (decoding_method="greedy", temperature=0) for all watsonx.ai calls
**Rationale**: Enables reproducible tests, reduces variance in extraction accuracy
**Alternatives Considered**: Sampling with low temperature, nucleus sampling
**Impact**: Deterministic outputs enable test reproducibility

## ADR-007: Cache watsonx.ai Responses in Tests
**Decision**: Cache watsonx.ai API responses for test reproducibility
**Rationale**: Avoids non-deterministic test failures, reduces API costs, enables offline testing
**Alternatives Considered**: Mock watsonx entirely, use local granite model
**Impact**: Requires test_data/watsonx_responses/ directory

## ADR-008: Parquet Datetime as ISO Strings (Not Native)
**Decision**: Store datetimes as ISO strings in Parquet, not Arrow timestamp type
**Rationale**: Simpler round-trip conversion, avoids timezone issues
**Alternatives Considered**: Arrow timestamp type with UTC timezone
**Impact**: to_parquet_dict() / from_parquet_dict() methods required

## ADR-009: ExtractionQuality Dataclass (Not Dict)
**Decision**: Use dataclass for quality metrics, not plain dict
**Rationale**: Type safety, autocomplete, clear interface
**Alternatives Considered**: Plain dict, Pydantic model
**Impact**: Requires @dataclass decorator, simple implementation

## ADR-010: Mock watsonx.ai in Unit Tests, Real API in Integration Tests
**Decision**: Unit tests mock watsonx.ai responses, integration tests use real IBM Cloud API
**Rationale**: Fast unit tests (no API calls), realistic integration tests validate end-to-end
**Alternatives Considered**: All tests use real watsonx, all tests use mocks
**Impact**: Requires @pytest.mark.integration for watsonx tests, IBM Cloud credentials for integration

## ADR-011: Property-Based Schema Tests (Hypothesis)
**Decision**: Use Hypothesis to generate random ESGMetrics for Parquet round-trip tests
**Rationale**: Catches edge cases (None values, extreme ranges) that manual tests miss
**Alternatives Considered**: Manual test cases only
**Impact**: Requires hypothesis dependency, ≥50 examples per test
