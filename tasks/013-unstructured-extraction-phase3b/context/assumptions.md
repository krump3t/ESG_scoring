# Assumptions - Phase 3B

## Technical Assumptions

1. **A1**: IBM watsonx.ai credentials available in .env file (WATSONX_PROJECT_ID, WATSONX_API_KEY)
2. **A2**: granite-13b-chat-v2 model accessible via watsonx.ai API
3. **A3**: PyMuPDF can extract ≥95% of text from born-digital PDFs
4. **A4**: Apple Sustainability Report 2024 is publicly downloadable as PDF
5. **A5**: LLM responses with greedy decoding (temperature=0) are deterministic
6. **A6**: Cached LLM responses remain valid across test runs
7. **A7**: PDF text can be truncated to ~12,000 chars (~3,000 tokens) without losing critical metrics
8. **A8**: JSON schema in prompt reduces LLM hallucinations

## Business Assumptions

9. **A9**: LLM extraction accuracy ≥85% is achievable with granite-13b-chat-v2
10. **A10**: ±10% tolerance acceptable for numeric ESG metrics (accounts for rounding, units)
11. **A11**: Sustainability PDFs contain ESG metrics in extractable text (not images/charts only)
12. **A12**: Prompt engineering can guide LLM to return valid JSON consistently

## Data Assumptions

13. **A13**: Apple Sustainability Report 2024 contains 5-10 ESG metrics (emissions, energy, water, waste)
14. **A14**: Ground truth from manual PDF review is accurate
15. **A15**: ESG metrics in PDFs are for fiscal year matching report year
16. **A16**: Units are consistent (tCO2e for emissions, % for percentages, m³ for water)

## Integration Assumptions

17. **A17**: Phase 3 ExtractionRouter can route PDF content_type to LLMExtractor
18. **A18**: Phase 3 ESGMetrics model accommodates environmental/social metrics
19. **A19**: Phase 4 data lake can ingest LLM-extracted metrics (same Parquet schema)
20. **A20**: LLM extraction latency (<10 seconds per PDF) is acceptable for batch processing

## Testing & Coverage Assumptions

21. **A21**: Cached LLM responses enable ≥95% coverage without live API calls in CI
22. **A22**: One integration test with real API (marked @pytest.mark.requires_api) validates end-to-end flow
23. **A23**: Failure path tests (malformed PDF, API error, invalid JSON) achieve branch coverage without mocking
