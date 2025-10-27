# [HYP] ESG Maturity Classification Hypothesis

## Core Hypothesis
We can accurately assign ESG maturity stages (0-4) per theme using evidence extraction from company sustainability reports, achieving **≥85% agreement** with expert human assessments through a hybrid vector-graph retrieval and LLM classification pipeline.

## Success Metrics

### Primary Metrics
- **Classification Accuracy**: ≥85% agreement with expert ESG analysts on stage assignment
- **Evidence Precision**: ≥90% of extracted evidence quotes directly support assigned stage
- **Theme Coverage**: Successfully classify all 7 ESG themes for ≥95% of evaluated companies
- **Processing Latency**: <30 seconds per company report (avg 50-200 pages)

### Secondary Metrics
- **Retrieval Recall**: ≥80% of relevant evidence chunks retrieved (top-k=20)
- **Confidence Calibration**: Predicted confidence correlates with accuracy (Spearman ρ > 0.7)
- **Inter-theme Consistency**: Adjacent themes differ by ≤1 stage in 90% of cases
- **Temporal Progression**: Year-over-year stage changes are monotonic in 85% of cases

## Input/Output Thresholds

### Inputs
- **Report Size**: 10-500 pages PDF (sustainability/annual reports)
- **Text Quality**: OCR confidence ≥95% for scanned documents
- **Language**: English (expandable to multilingual in future)
- **Report Years**: 2020-2024 (recent reporting standards)

### Outputs
- **Stage Range**: Integer 0-4 per theme (5 distinct stages)
- **Confidence Range**: Float 0.0-1.0 (0.7+ considered high confidence)
- **Evidence Count**: 3-10 supporting quotes per theme
- **Response Time**: <30s P95, <10s P50

## Critical Path Components

### Core Algorithms
1. **PDF Parsing** (`apps/ingestion/parser.py`): Extract structured text chunks with boundaries
2. **Embedding Generation** (`apps/scoring/wx_client.py`): Convert text to semantic vectors
3. **Hybrid Retrieval** (`apps/index/retriever.py`): KNN + graph traversal for evidence
4. **LLM Classification** (`apps/scoring/grade.py`): Stage assignment with watsonx.ai
5. **API Serving** (`apps/api/main.py`): FastAPI endpoints for scoring requests

### Data Structures
- **Vector Store** (`apps/index/vector_store.py`): High-dimensional embedding index
- **Graph Store** (`apps/index/graph_store.py`): Entity relationships (Company→Report→Chunk)
- **Rubric Compiler** (`rubrics/compile_rubric.py`): MD→JSON maturity criteria

## Exclusions & Constraints

### Out of Scope
- Real-time streaming analysis (batch processing only)
- Non-English reports (future enhancement)
- Financial performance correlation (ESG focus only)
- Regulatory compliance checking (maturity assessment only)
- Historical reports pre-2020 (outdated standards)

### Technical Constraints
- watsonx.ai API rate limits: 100 requests/minute
- AstraDB storage: 10GB vector embeddings
- Memory footprint: <8GB RAM per scoring session
- Concurrent requests: Max 10 parallel scorings

## Statistical Power Analysis

### Sample Size Calculation
- **Effect Size**: Cohen's d = 0.5 (medium effect for stage differences)
- **Power**: 0.80 (80% chance to detect true differences)
- **Alpha**: 0.05 (5% false positive rate)
- **Required N**: 64 company-year pairs minimum
- **Target N**: 100 companies × 2 years = 200 evaluations

### Confidence Intervals
- **Stage Assignment**: 95% CI = ±0.3 stages
- **Overall Accuracy**: 95% CI = ±5% (based on N=200)
- **Evidence Relevance**: 95% CI = ±3% (human validation subset)

## Risk Analysis

### Technical Risks
1. **LLM Hallucination** (High Impact, Medium Probability)
   - Mitigation: Require direct quote extraction with page numbers
   - Counter: Track evidence-to-conclusion traceability

2. **Embedding Drift** (Medium Impact, Low Probability)
   - Mitigation: Version embeddings, periodic retraining
   - Counter: A/B test new embeddings before deployment

3. **Graph Sparsity** (Medium Impact, Medium Probability)
   - Mitigation: Fallback to pure vector search
   - Counter: Enrich graph with external data sources

### Domain Risks
1. **Greenwashing Detection** (High Impact, High Probability)
   - Mitigation: Cross-reference claims with quantitative data
   - Counter: Flag inconsistencies for manual review

2. **Standard Evolution** (Medium Impact, Medium Probability)
   - Mitigation: Versioned rubrics, regular updates
   - Counter: Track GRI/SASB/TCFD standard changes

## Validation Strategy

### Unit Validation
- Property-based testing for all CP components
- Differential testing between rubric versions
- Sensitivity analysis on confidence thresholds

### Integration Validation
- End-to-end scoring on benchmark dataset
- A/B testing against human analysts
- Cross-validation with public ESG ratings

### Production Validation
- Shadow mode comparison for 2 weeks
- Gradual rollout with monitoring
- Feedback loop with domain experts

## Dependencies
- watsonx.ai API access (embeddings + LLM)
- AstraDB instance (vector/graph storage)
- PDF parsing libraries (pdfplumber/unstructured)
- Sustainability report sources (public websites)

## Success Criteria Summary
✓ 85% classification accuracy vs human experts
✓ 90% evidence precision (relevant quotes)
✓ <30s processing latency (P95)
✓ 7/7 themes classified for 95% of companies
✓ High confidence calibration (ρ > 0.7)
✓ 200+ company evaluations completed