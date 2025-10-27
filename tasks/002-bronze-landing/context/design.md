# Design: Bronze Layer Data Ingestion

## Data Strategy

### Bronze Layer Schema
```python
bronze_schema = {
    "org_id": "string",           # Company identifier
    "year": "int32",              # Reporting year
    "doc_id": "string",           # UUID for document
    "source_url": "string",       # Original document URL
    "doc_type": "string",         # pdf|html|pptx
    "extraction_timestamp": "timestamp[us]",
    "sha256": "string",           # Document hash for dedup
    "page_count": "int32",
    "raw_text": "large_string",   # Full extracted text
    "tables": "list<struct>",     # Extracted tables as JSON
    "figures": "list<struct>",    # Figure metadata and captions
    "metadata": "map<string,string>"  # Additional metadata
}
```

### Directory Structure
```
s3://esg-lake/bronze/
├── microsoft/
│   ├── 2023/
│   │   └── a1b2c3d4-e5f6-7890-abcd-ef1234567890/
│   │       ├── raw.parquet
│   │       └── _manifest.json
│   └── 2024/
│       └── b2c3d4e5-f6g7-8901-bcde-f12345678901/
│           ├── raw.parquet
│           └── _manifest.json
└── shell/
    └── 2024/
        └── c3d4e5f6-g7h8-9012-cdef-123456789012/
            ├── raw.parquet
            └── _manifest.json
```

### Extraction Pipeline
```
Fetch URL → Parse Document → Extract Content → Transform → Write Parquet
     ↓            ↓               ↓              ↓           ↓
  Validate    Detect Type    Text/Tables    Schema Map   Atomic Write
```

## Data Extraction Details

### PDF Extraction (PyMuPDF + pdfminer)
```python
def extract_pdf(path: str) -> dict:
    with fitz.open(path) as doc:
        # Extract text with layout preservation
        text = "\n\n".join(page.get_text("text") for page in doc)

        # Extract tables using pdfplumber
        tables = []
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                tables.extend(page.extract_tables())

        # Extract figures/images
        figures = []
        for page_num, page in enumerate(doc):
            for img in page.get_images():
                figures.append({
                    "page": page_num,
                    "bbox": img[0:4],
                    "caption": extract_caption_near(page, img)
                })

        return {
            "text": text,
            "tables": tables,
            "figures": figures,
            "page_count": len(doc)
        }
```

### HTML Extraction (BeautifulSoup + trafilatura)
```python
def extract_html(content: bytes) -> dict:
    # Use trafilatura for main content extraction
    text = trafilatura.extract(
        content,
        include_tables=True,
        include_comments=False
    )

    # Parse with BeautifulSoup for structured data
    soup = BeautifulSoup(content, 'lxml')

    tables = []
    for table in soup.find_all('table'):
        tables.append(parse_html_table(table))

    return {
        "text": text,
        "tables": tables,
        "figures": extract_figures(soup)
    }
```

## Normalization Strategy

### Deduplication
- Hash-based: SHA256 of document content
- Check manifest before extraction
- Skip if sha256 already exists for org_id/year

### Schema Validation
- PyArrow schema enforcement on write
- Type coercion with error logging
- Reject invalid records to dead letter queue

### Parquet Optimization
```python
parquet_settings = {
    "compression": "zstd",
    "compression_level": 3,
    "row_group_size": 100,
    "data_page_size": 1024 * 1024,  # 1MB
    "dictionary_encoding": True
}
```

## Verification Plan

### Functional Tests
```python
@pytest.mark.cp
def test_fetch_real_sustainability_report():
    """Test fetching actual Microsoft 2024 sustainability report"""
    result = crawler.fetch("microsoft", 2024)
    assert result["success"]
    assert result["doc_type"] == "pdf"
    assert result["page_count"] > 50

@pytest.mark.cp
@given(st.sampled_from(["microsoft", "shell", "exxonmobil"]))
def test_extraction_idempotency(company: str):
    """Property: Re-extracting same doc produces same sha256"""
    result1 = crawler.extract(company, 2024)
    result2 = crawler.extract(company, 2024)
    assert result1["sha256"] == result2["sha256"]

@pytest.mark.cp
def test_parquet_write_atomic():
    """Test atomic writes with rollback on failure"""
    with pytest.raises(ExtractionError):
        writer.write(invalid_data)
    # Verify no partial file created
    assert not minio_client.object_exists("bronze/test/corrupt.parquet")
```

### Performance Tests
```python
def test_throughput_100_documents():
    """Benchmark: Process 100 docs in < 10 minutes"""
    start = time.time()
    results = crawler.batch_process(companies[:100])
    elapsed = time.time() - start

    assert elapsed < 600  # 10 minutes
    assert sum(r["success"] for r in results) >= 95  # 95% success rate
```

### Differential Tests
```python
def test_vs_legacy_extraction():
    """Compare extraction quality with legacy system"""
    legacy = legacy_extractor.extract("microsoft_2024.pdf")
    new = crawler.extract("microsoft", 2024)

    # Text length should be similar
    assert abs(len(new["text"]) - len(legacy["text"])) < 1000

    # Should detect same number of tables
    assert len(new["tables"]) == len(legacy["tables"])
```

## Success Thresholds
- **Extraction Success**: ≥ 95% of documents
- **Throughput**: ≥ 10 docs/min
- **Accuracy**: ≥ 90% text extraction quality
- **Deduplication**: 100% duplicate detection
- **Coverage**: ≥ 95% line/branch on CP
- **Type Safety**: 0 mypy errors on CP