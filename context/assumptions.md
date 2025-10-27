# Assumptions

## Domain Assumptions

### ESG Reporting Standards
1. **Reporting Consistency**: Companies follow established frameworks (GRI, SASB, TCFD) with sufficient consistency to enable automated analysis
2. **Language Quality**: Sustainability reports contain substantive content beyond boilerplate text (>70% unique content)
3. **Temporal Stability**: ESG reporting standards remain relatively stable within a 2-year window
4. **Data Availability**: At least 80% of public companies publish sustainability reports or ESG sections in annual reports
5. **Maturity Progression**: Companies generally progress monotonically through maturity stages (rare regressions)

### ESG Maturity Model
1. **Stage Distinctiveness**: The 5 maturity stages (0-4) represent meaningfully different levels of ESG sophistication
2. **Theme Independence**: While correlated, the 7 ESG themes can be assessed independently
3. **Evidence Sufficiency**: 3-10 evidence quotes per theme provide sufficient basis for stage assignment
4. **Cross-Industry Applicability**: The rubric applies across different industry sectors with minor variations
5. **Expert Consensus**: ESG experts have ≥70% inter-rater agreement on stage assignments

## Technical Assumptions

### Data Processing
1. **PDF Quality**: 95% of PDFs can be parsed with standard tools (pdfplumber/unstructured)
2. **Text Extraction**: OCR accuracy ≥95% for scanned documents
3. **Chunk Coherence**: 512-token chunks preserve semantic meaning in 90% of cases
4. **Metadata Preservation**: Page numbers and section headers can be reliably extracted
5. **Table Parsing**: Structured data in tables can be extracted with 80% accuracy

### Machine Learning
1. **Embedding Stability**: watsonx.ai embeddings remain consistent across API calls for identical text
2. **Semantic Similarity**: Cosine similarity effectively measures relevance for ESG content
3. **LLM Reliability**: watsonx.ai maintains consistent performance (no significant degradation)
4. **Context Window**: 8K tokens sufficient for evidence extraction and classification
5. **Few-Shot Learning**: 3-5 examples enable effective in-context learning for classification

### Infrastructure
1. **API Availability**: watsonx.ai maintains 99% uptime during business hours
2. **Rate Limits**: 100 requests/minute sufficient for production workload
3. **Storage Capacity**: 10GB vector storage accommodates 1000+ company reports
4. **Network Latency**: <100ms RTT to watsonx.ai and AstraDB endpoints
5. **Compute Resources**: 8GB RAM and 4 CPU cores handle concurrent processing

## Operational Assumptions

### Usage Patterns
1. **Batch Processing**: Users primarily submit batch requests (5-10 companies)
2. **Report Freshness**: Annual report updates sufficient (no real-time requirements)
3. **Query Volume**: <1000 scoring requests per day
4. **User Patience**: 30-second response time acceptable for comprehensive analysis
5. **Result Caching**: 24-hour cache validity for scoring results

### Data Sources
1. **Public Availability**: Sustainability reports remain publicly accessible
2. **URL Stability**: Report URLs remain valid for 1+ year
3. **Format Consistency**: 90% of reports published as PDF (not dynamic web pages)
4. **Update Frequency**: Companies publish reports annually (some bi-annually)
5. **Historical Access**: 3-5 years of historical reports available

## Quality Assumptions

### Validation
1. **Ground Truth**: Expert-labeled dataset of 200+ companies available for validation
2. **Feedback Loop**: Users provide feedback on 10% of classifications
3. **Error Tolerance**: Users accept 15% error rate for initial deployment
4. **Explainability**: Evidence-based explanations satisfy user requirements
5. **Audit Trail**: Complete traceability from evidence to decision required

### Performance
1. **Scalability**: Linear scaling up to 100 concurrent requests
2. **Degradation**: Graceful degradation when external services unavailable
3. **Recovery**: Automatic recovery from transient failures
4. **Monitoring**: Prometheus metrics sufficient for operational visibility
5. **Debugging**: Structured logs enable root cause analysis

## Risk Assumptions

### Business Risks
1. **Adoption Rate**: 50% of target users adopt system within 6 months
2. **Competitive Landscape**: No major competitor launches similar free service
3. **Regulatory Stability**: ESG regulations don't dramatically change in next 2 years
4. **Budget Continuity**: Funding for watsonx.ai and AstraDB continues
5. **Team Stability**: Core development team remains for 12+ months

### Technical Risks
1. **Model Drift**: Retraining required every 6-12 months maximum
2. **Data Drift**: Report formats remain parseable with minor adjustments
3. **Security**: No PII in sustainability reports (low privacy risk)
4. **Compliance**: GDPR/CCPA don't apply to public corporate reports
5. **Intellectual Property**: Fair use doctrine covers report analysis

## Constraints Acknowledged

### Known Limitations
1. **Language Support**: English-only in initial version
2. **Geographic Coverage**: Focus on North American and European companies
3. **Sector Coverage**: May underperform for highly specialized sectors
4. **Report Types**: Optimized for comprehensive sustainability reports
5. **Temporal Analysis**: Limited to year-over-year comparisons

### Future Considerations
1. **Multilingual Support**: Requires separate embeddings per language
2. **Real-time Analysis**: Would require streaming architecture redesign
3. **Regulatory Compliance**: May need audit features for SOC2/ISO27001
4. **Scale**: 10,000+ companies would require infrastructure upgrade
5. **Integration**: API-first design enables future platform integrations

## Assumption Validation Plan

### Continuous Monitoring
- Track assumption validity through metrics and logs
- Quarterly review of assumptions with stakeholders
- A/B testing to validate ML assumptions
- User surveys to validate operational assumptions
- Regular benchmarking against competitor solutions

### Assumption Violations
- Document when assumptions prove incorrect
- Assess impact on system performance
- Develop mitigation strategies
- Update assumptions based on empirical evidence
- Communicate changes to stakeholders

## Dependencies on Assumptions

### Critical Assumptions (System Fails if False)
1. watsonx.ai API availability and performance
2. PDF parsing capability for majority of reports
3. Expert consensus on maturity stages exists
4. Sustainability reports contain substantive content
5. 85% accuracy achievable with current approach

### Important Assumptions (Degraded Performance if False)
1. Graph augmentation improves retrieval
2. Caching reduces latency meaningfully
3. Users accept evidence-based explanations
4. Report formats remain stable
5. Batch processing is primary use case

### Minor Assumptions (Minimal Impact if False)
1. Temporal monotonicity of progressions
2. Industry sector variations are minor
3. 24-hour cache validity acceptable
4. Prometheus metrics sufficient
5. Linear scaling characteristics