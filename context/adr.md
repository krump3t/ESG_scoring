# Architecture Decision Records (ADR)

## ADR-001: Hybrid Vector-Graph Retrieval Strategy
**Date**: 2024-10-21
**Status**: Accepted
**Context**: Need to retrieve relevant evidence from ESG reports for classification
**Decision**: Implement hybrid retrieval combining vector similarity search with graph traversal
**Rationale**:
- Pure vector search misses structural relationships between entities
- Graph-only search lacks semantic understanding
- Research shows 15% improvement with hybrid approach (Li et al., 2023)
**Consequences**:
- (+) Better recall of relevant evidence
- (+) Explainable retrieval paths
- (-) Increased system complexity
- (-) Higher latency than single method
**Alternatives Considered**:
- Pure vector search (rejected: insufficient recall)
- Pure graph traversal (rejected: lacks semantic matching)
- Keyword search (rejected: poor semantic understanding)

## ADR-002: watsonx.ai for LLM Services
**Date**: 2024-10-21
**Status**: Accepted
**Context**: Need LLM for embeddings, evidence extraction, and classification
**Decision**: Use IBM watsonx.ai as primary LLM provider
**Rationale**:
- Enterprise-grade reliability and support
- Integrated with IBM cloud ecosystem
- Cost-effective for our volume
- Strong performance on ESG domain tasks
**Consequences**:
- (+) Single vendor for all LLM needs
- (+) Simplified billing and support
- (-) Vendor lock-in risk
- (-) Limited model selection
**Alternatives Considered**:
- OpenAI API (rejected: cost and data privacy concerns)
- Self-hosted models (rejected: infrastructure overhead)
- Multiple providers (rejected: complexity)

## ADR-003: AstraDB for Vector and Graph Storage
**Date**: 2024-10-21
**Status**: Accepted
**Context**: Need scalable storage for embeddings and graph relationships
**Decision**: Use DataStax AstraDB for both vector and graph storage
**Rationale**:
- Native vector search with HNSW indexing
- Graph capabilities in same database
- Serverless scaling
- Managed service reduces operational burden
**Consequences**:
- (+) Single database for both needs
- (+) Automatic scaling
- (+) Built-in high availability
- (-) Vendor lock-in
- (-) Potential latency for complex graph queries
**Alternatives Considered**:
- Pinecone + Neo4j (rejected: two systems to manage)
- Elasticsearch (rejected: weaker vector capabilities)
- PostgreSQL + pgvector (rejected: limited scale)

## ADR-004: FastAPI for API Framework
**Date**: 2024-10-21
**Status**: Accepted
**Context**: Need REST API for ESG scoring service
**Decision**: Use FastAPI as web framework
**Rationale**:
- Native async support for I/O operations
- Automatic OpenAPI documentation
- Pydantic integration for validation
- High performance Python framework
**Consequences**:
- (+) Developer productivity
- (+) Type safety with Pydantic
- (+) Auto-generated docs
- (-) Python GIL limitations
- (-) Less mature than Flask/Django
**Alternatives Considered**:
- Flask (rejected: lacks async, manual validation)
- Django REST (rejected: heavyweight for our needs)
- Node.js (rejected: team Python expertise)

## ADR-005: PyArrow for Data Processing
**Date**: 2024-10-21
**Status**: Accepted
**Context**: Need efficient processing of large document datasets
**Decision**: Use PyArrow for data schemas and Parquet storage
**Rationale**:
- Columnar storage efficient for analytics
- Strong typing with Arrow schemas
- Interoperability with data tools
- Memory-efficient processing
**Consequences**:
- (+) Fast data processing
- (+) Schema enforcement
- (+) Parquet compression
- (-) Learning curve for team
- (-) Overkill for small datasets
**Alternatives Considered**:
- Pandas only (rejected: memory inefficient)
- Raw JSON (rejected: no schema, slow)
- SQLite (rejected: not suited for documents)

## ADR-006: Evidence-First Classification Approach
**Date**: 2024-10-21
**Status**: Accepted
**Context**: Need explainable ESG maturity classifications
**Decision**: Require evidence extraction before classification
**Rationale**:
- Explainability critical for user trust
- Reduces hallucination risk
- Enables audit trail
- Improves accuracy through grounding
**Consequences**:
- (+) Explainable decisions
- (+) Higher user trust
- (+) Audit capability
- (-) Higher latency
- (-) More LLM calls required
**Alternatives Considered**:
- Direct classification (rejected: black box)
- Rule-based (rejected: insufficient flexibility)
- Hybrid rules+ML (rejected: complexity)

## ADR-007: Rubric-Driven Evaluation
**Date**: 2024-10-21
**Status**: Accepted
**Context**: Need consistent evaluation criteria across themes
**Decision**: Use structured rubric with 5 stages (0-4) per theme
**Rationale**:
- Industry standard maturity model
- Clear progression criteria
- Version control for rubric evolution
- Enables comparative analysis
**Consequences**:
- (+) Consistent evaluations
- (+) Clear expectations
- (+) Version tracking
- (-) Rubric maintenance overhead
- (-) May not fit all industries perfectly
**Alternatives Considered**:
- Continuous scoring (rejected: less interpretable)
- Binary classification (rejected: insufficient granularity)
- Custom per industry (rejected: maintenance burden)

## ADR-008: Airflow for Orchestration (Future)
**Date**: 2024-10-21
**Status**: Proposed
**Context**: Need orchestration for batch processing pipelines
**Decision**: Use Apache Airflow for workflow orchestration
**Rationale**:
- Industry standard for data pipelines
- Rich monitoring and alerting
- Supports complex dependencies
- Python-native
**Consequences**:
- (+) Robust orchestration
- (+) Built-in monitoring
- (+) Failure handling
- (-) Infrastructure overhead
- (-) Learning curve
**Alternatives Considered**:
- Celery (rejected: less suited for DAGs)
- Kubernetes Jobs (rejected: less workflow features)
- AWS Step Functions (rejected: vendor lock-in)

## ADR-009: MCP Server for Agent Integration
**Date**: 2024-10-21
**Status**: Accepted
**Context**: Need to expose functionality to AI agents
**Decision**: Implement Model Context Protocol (MCP) server
**Rationale**:
- Standardized protocol for AI agents
- JSON-RPC based communication
- Supports multiple agent platforms
- Future-proof for agent ecosystem
**Consequences**:
- (+) Agent interoperability
- (+) Standardized interface
- (+) Ecosystem compatibility
- (-) Additional API surface
- (-) Protocol may evolve
**Alternatives Considered**:
- Custom protocol (rejected: no ecosystem)
- GraphQL (rejected: not agent-focused)
- gRPC (rejected: complexity)

## ADR-010: Prometheus for Metrics
**Date**: 2024-10-21
**Status**: Accepted
**Context**: Need observability for production system
**Decision**: Use Prometheus for metrics collection
**Rationale**:
- Industry standard for metrics
- Rich ecosystem of exporters
- Powerful query language
- Grafana integration
**Consequences**:
- (+) Comprehensive metrics
- (+) Alerting capabilities
- (+) Visualization options
- (-) Time-series only
- (-) Requires Grafana for dashboards
**Alternatives Considered**:
- CloudWatch (rejected: AWS lock-in)
- DataDog (rejected: cost)
- Custom metrics (rejected: reinventing wheel)

## ADR-011: Chunking Strategy with Overlap
**Date**: 2024-10-21
**Status**: Accepted
**Context**: Need to chunk documents for processing
**Decision**: Use 512-token chunks with 20% overlap
**Rationale**:
- Fits within LLM context windows
- Overlap ensures context preservation
- Semantic boundaries when possible
- Balance between context and granularity
**Consequences**:
- (+) Preserves context
- (+) Good retrieval granularity
- (-) Storage overhead from overlap
- (-) Deduplication needed
**Alternatives Considered**:
- No overlap (rejected: loses context)
- Sentence-level (rejected: too granular)
- Full documents (rejected: too large)

## ADR-012: Caching Strategy
**Date**: 2024-10-21
**Status**: Accepted
**Context**: Need to optimize performance and reduce costs
**Decision**: Implement multi-level caching (embedding, retrieval, classification)
**Rationale**:
- Embeddings expensive to compute
- Many repeated queries expected
- Classification results stable for 24h
- Reduces API costs significantly
**Consequences**:
- (+) Lower latency
- (+) Reduced costs
- (+) Better scalability
- (-) Cache invalidation complexity
- (-) Storage requirements
**Alternatives Considered**:
- No caching (rejected: expensive)
- Single level (rejected: suboptimal)
- CDN only (rejected: not suitable for API)

## ADR-013: Property-Based Testing
**Date**: 2024-10-21
**Status**: Accepted
**Context**: Need robust testing for complex domain logic
**Decision**: Use Hypothesis for property-based testing
**Rationale**:
- Finds edge cases automatically
- Ensures invariants hold
- Required by SCA protocol
- Particularly suited for data pipelines
**Consequences**:
- (+) Better test coverage
- (+) Finds subtle bugs
- (+) Documents invariants
- (-) Learning curve
- (-) Slower test execution
**Alternatives Considered**:
- Unit tests only (rejected: miss edge cases)
- Integration tests only (rejected: insufficient coverage)
- Fuzzing (rejected: less structured)

## ADR-014: Git for Version Control
**Date**: 2024-10-21
**Status**: Accepted
**Context**: Need version control for code and rubrics
**Decision**: Use Git with semantic versioning
**Rationale**:
- Industry standard VCS
- Supports branching strategies
- Integrates with CI/CD
- Enables rubric versioning
**Consequences**:
- (+) Full history tracking
- (+) Collaboration support
- (+) CI/CD integration
- (-) Learning curve for non-developers
- (-) Binary file limitations
**Alternatives Considered**:
- SVN (rejected: outdated)
- Mercurial (rejected: less ecosystem)
- No VCS (rejected: unacceptable risk)

## ADR-015: Error Recovery Strategy
**Date**: 2024-10-21
**Status**: Accepted
**Context**: Need resilience to failures
**Decision**: Implement circuit breakers with fallback mechanisms
**Rationale**:
- Prevents cascade failures
- Graceful degradation
- Automatic recovery
- Better user experience
**Consequences**:
- (+) System resilience
- (+) Automatic recovery
- (+) Prevents overload
- (-) Complexity
- (-) Fallback quality may be lower
**Alternatives Considered**:
- Simple retry (rejected: can worsen failures)
- Fail fast (rejected: poor UX)
- Manual intervention (rejected: not scalable)

## Review Schedule
- Quarterly ADR review with technical team
- Update status as decisions implemented
- Document lessons learned
- Propose new ADRs as needed
- Archive superseded decisions