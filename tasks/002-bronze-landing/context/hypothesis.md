# Hypothesis: Bronze Layer - Raw Data Landing with MCP Crawler Agent

## Core Hypothesis
Implementing an MCP Crawler Agent that writes append-only Parquet files to MinIO bronze layer will create a reliable, traceable, and performant foundation for ESG document ingestion from real sustainability reports, eliminating the need for simulated demo data.

## Success Metrics
- **Extraction Success Rate**: > 95% of documents successfully extracted
- **Throughput**: Process > 10 documents per minute
- **Data Quality**: > 90% text extraction accuracy (verified by sampling)
- **Parquet Performance**: Write speed > 50 MB/s
- **Deduplication**: 100% detection of duplicate documents
- **Traceability**: All extractions logged with source URLs and timestamps

## Input/Output Specifications
**Inputs:**
- sustainabilityreports.com URLs or direct PDF/HTML/PPTX links
- Company identifiers (org_id)
- Year range for reports (2020-2024)

**Outputs:**
- Bronze Parquet files: `s3://esg-lake/bronze/{org_id}/{year}/{doc_id}/raw.parquet`
- Metadata manifest: company, year, doc_id, source_url, extraction_timestamp, sha256
- Extraction logs in `qa/extraction_log.txt`
- Quality metrics: text_length, page_count, tables_detected, figures_detected

## Critical Path Components
- `agents/crawler/mcp_crawler.py` - MCP Crawler Agent with tool registration
- `agents/crawler/fetchers/sustainability_fetcher.py` - Report fetching from sustainabilityreports.com
- `agents/crawler/extractors/pdf_extractor.py` - PDF text/table/image extraction
- `agents/crawler/extractors/html_extractor.py` - HTML parsing and cleaning
- `agents/crawler/writers/parquet_writer.py` - Append-only Parquet writes to MinIO
- `tests/test_crawler_agent.py` - Real API tests with actual reports

## Exclusions
- OCR for scanned PDFs (future enhancement)
- Image recognition for diagrams (future enhancement)
- Multi-language support (English only for POC)
- Real-time ingestion (batch processing only)

## Power Analysis & Confidence Intervals
- **Sample Size**: Test with 30 documents across 6 companies
- **Success Rate CI (95%)**: 95% ± 4%
- **Throughput CI (95%)**: 10 docs/min ± 2
- **Extraction Accuracy CI (95%)**: 90% ± 5%

## Risk Mitigators
1. **Website blocking**: Use respectful scraping (delays, user-agent), fallback to manual downloads
2. **PDF corruption**: Validate before processing, log failures, retry with alternative tools
3. **Storage failures**: Atomic writes with validation, rollback on error
4. **Memory exhaustion**: Stream processing for large files, chunk-based extraction
5. **Credential exposure**: All credentials in .env, never in code or logs

## Verification Strategy
- **Real Data Test**: Process actual Microsoft, Shell, ExxonMobil sustainability reports
- **Idempotency Test**: Re-run same document, verify no duplicates created
- **Format Test**: Validate all Parquet files readable by DuckDB and Trino
- **Completeness Test**: Verify all tables/figures detected in known documents
- **Performance Test**: Measure throughput with 100-document batch

## MCP Tool Definitions
```json
{
  "tools": [
    {
      "name": "sustainability.fetch",
      "description": "Fetch sustainability report from company website",
      "inputSchema": {
        "company": "string",
        "year": "integer",
        "force_refresh": "boolean"
      }
    },
    {
      "name": "pdf.extract",
      "description": "Extract text, tables, and metadata from PDF",
      "inputSchema": {
        "pdf_path": "string",
        "extract_tables": "boolean",
        "extract_images": "boolean"
      }
    },
    {
      "name": "parquet.land",
      "description": "Write extracted data to bronze Parquet",
      "inputSchema": {
        "org_id": "string",
        "year": "integer",
        "data": "object"
      }
    }
  ]
}
```