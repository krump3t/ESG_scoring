# [DES] ESG Maturity Classification System Design

## Core Architecture
Evidence-first pipeline: **chunk → embed → graph expand → classify** with hybrid vector-graph retrieval for maximum evidence recall and LLM-based stage classification.

## Data Strategy

### Data Sources
1. **Primary Sources**
   - Sustainability reports (PDF, 50-200 pages typical)
   - Annual reports with ESG sections
   - TCFD/CDP disclosures
   - GRI-indexed reports

2. **Data Collection**
   - Web crawling from SustainabilityReports.com
   - Rate-limited to 10 requests/minute
   - Retry logic with exponential backoff
   - Progress tracking and resumption capability

### Data Processing Pipeline

#### Stage 1: Document Ingestion
- **PDF Parsing**: Extract text with page boundaries preserved
- **Chunking Strategy**:
  - Semantic boundaries (paragraphs/sections)
  - Max 512 tokens per chunk (LLM context window)
  - 20% overlap between chunks
  - Preserve metadata (page, section, tables)

#### Stage 2: Embedding Generation
- **Model**: IBM watsonx.ai embeddings (768 dimensions)
- **Batch Processing**: 32 chunks per API call
- **Caching**: Store embeddings in AstraDB
- **Versioning**: Track embedding model version

#### Stage 3: Indexing
- **Vector Index**: HNSW index in AstraDB
  - M=16, ef_construction=200
  - Cosine similarity metric
- **Graph Construction**:
  - Nodes: Company, Report, Chunk, Theme
  - Edges: PUBLISHED, CONTAINS, MENTIONS
  - Properties: year, confidence, page_ref

#### Stage 4: Retrieval
- **Hybrid Strategy**:
  1. KNN search (k=20) for semantic similarity
  2. Graph expansion (1-hop) for context
  3. Re-ranking by relevance score
  4. Deduplication of overlapping chunks

#### Stage 5: Classification
- **Evidence Extraction**: watsonx.ai extracts quotes
- **Stage Assignment**: Map evidence to rubric stages
- **Confidence Scoring**: Based on evidence strength
- **Aggregation**: Weighted average across themes

## Data Splits & Validation

### Training/Validation Split
- **Training**: 60% (120 companies)
- **Validation**: 20% (40 companies)
- **Test**: 20% (40 companies)
- **Stratification**: By industry sector and company size
- **Temporal Split**: 2020-2022 train, 2023 validate, 2024 test

### Cross-Validation Strategy
- **K-Fold**: 5-fold CV on training set
- **Blocked by Company**: Prevent same company in train/test
- **Time-Series CV**: Walk-forward validation for temporal data

## Leakage Prevention

### Data Leakage Guards
1. **Company Isolation**: No company appears in multiple splits
2. **Temporal Ordering**: Test data strictly after training
3. **Feature Engineering**: No future information in features
4. **Embedding Versioning**: Separate embeddings per split
5. **Graph Isolation**: Subgraphs per data split

### Information Leakage Checks
- Mutual information analysis between splits
- Distribution shift detection (KS test)
- Feature importance stability across folds
- Prediction correlation analysis

## Normalization & Preprocessing

### Text Normalization
- Convert to UTF-8 encoding
- Remove special characters (keep punctuation)
- Normalize whitespace and line breaks
- Preserve acronyms (ESG, GHG, TCFD)
- Case preservation for proper nouns

### Numerical Normalization
- Standardize units (tCO2e, MWh, etc.)
- Extract and parse tables to structured format
- Normalize date formats (ISO 8601)
- Handle missing values explicitly

## Verification Plans

### Differential Testing
1. **Rubric Versions**: Compare v1.0 vs v1.1 classifications
2. **Model Versions**: A/B test watsonx.ai model updates
3. **Retrieval Methods**: Vector-only vs hybrid retrieval
4. **Chunk Sizes**: 256 vs 512 vs 1024 tokens
5. **Expected Δ**: <5% classification difference

### Sensitivity Analysis
1. **Confidence Thresholds**: Vary 0.5-0.9 in 0.1 increments
2. **K Parameter**: Test k=10, 20, 30, 50 for KNN
3. **Graph Hops**: Compare 1-hop vs 2-hop expansion
4. **Evidence Count**: Require 1-10 quotes per theme
5. **Impact Assessment**: ±10% change acceptable

### Domain-Specific Validation

#### ESG Expert Review
- 10% manual review by domain experts
- Inter-rater reliability (Cohen's κ > 0.7)
- Feedback incorporation loop
- Quarterly calibration sessions

#### Benchmark Comparison
- Compare with MSCI ESG ratings
- Correlate with Sustainalytics scores
- Validate against CDP grades
- Expected correlation: r > 0.6

## Success Thresholds

### Performance Metrics
- **Accuracy**: ≥85% stage agreement with experts
- **Precision**: ≥90% for high-confidence predictions
- **Recall**: ≥80% for material ESG issues
- **F1 Score**: ≥0.85 weighted average
- **AUC-ROC**: ≥0.90 for binary stage transitions

### Operational Metrics
- **Latency**: P50 < 10s, P95 < 30s, P99 < 60s
- **Throughput**: 100 reports/hour sustained
- **Availability**: 99.9% uptime SLA
- **Error Rate**: <1% processing failures
- **Cost**: <$0.50 per report scored

### Quality Metrics
- **Evidence Quality**: 90% quotes directly relevant
- **Confidence Calibration**: ECE < 0.1
- **Consistency**: 95% temporal monotonicity
- **Coverage**: 95% companies get all 7 themes
- **Explainability**: 100% decisions traceable to evidence

## Caching & Optimization

### Multi-Level Caching
1. **Embedding Cache**: 7-day TTL in AstraDB
2. **Retrieval Cache**: 1-hour TTL for common queries
3. **Classification Cache**: 24-hour TTL per company-year
4. **API Response Cache**: 5-minute TTL

### Performance Optimizations
- Batch processing for embeddings
- Async I/O for PDF parsing
- Connection pooling for databases
- Lazy loading of large models
- Prefetching for sequential processing

## Monitoring & Observability

### Key Metrics
- Request rate and latency (Prometheus)
- Token usage and costs (watsonx.ai)
- Cache hit rates (AstraDB)
- Error rates by component
- Data drift detection

### Logging Strategy
- Structured JSON logs
- Correlation IDs for request tracing
- Sensitive data masking
- Log aggregation in CloudWatch
- 30-day retention policy

## Security & Compliance

### Data Security
- Encryption at rest (AES-256)
- TLS 1.3 for data in transit
- API key rotation (monthly)
- Role-based access control
- Audit logging for all access

### Privacy Compliance
- No PII in sustainability reports
- Data retention: 1 year
- Right to deletion support
- GDPR compliance checklist
- Data lineage tracking

## Failure Modes & Recovery

### Graceful Degradation
1. If LLM unavailable → Use cached classifications
2. If vector store down → Fallback to keyword search
3. If graph store down → Use vector-only retrieval
4. If PDF parser fails → Try alternative parser
5. If all fail → Return status with explanation

### Error Handling
- Retry with exponential backoff
- Circuit breaker pattern
- Dead letter queues
- Manual review queue
- Automated alerts for failures

## Architecture Decisions Summary
✓ Hybrid retrieval for maximum recall
✓ Evidence-first approach for explainability
✓ Multi-level caching for performance
✓ Temporal validation for data integrity
✓ Differential testing for robustness
✓ Domain expert validation for accuracy