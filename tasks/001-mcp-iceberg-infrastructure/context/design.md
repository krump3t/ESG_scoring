# Design: Infrastructure Architecture for MCP + Iceberg

## Data Strategy

### Storage Layers
```
MinIO (S3-compatible)
├── esg-lake/
│   ├── bronze/          # Raw Parquet files (append-only)
│   │   └── {org_id}/{year}/{doc_id}/raw.parquet
│   ├── silver/          # Normalized Iceberg tables
│   │   └── org_id={}/year={}/theme={}/normalized.parquet
│   └── gold/            # Scored Iceberg tables
│       ├── scores/      # ESG scores with confidence
│       └── evidence/    # Supporting evidence with page refs
```

### Table Design (Iceberg)
```sql
-- Silver Layer
CREATE TABLE silver.esg_normalized (
    org_id STRING,
    year INT,
    theme STRING,
    finding TEXT,
    evidence_strength DOUBLE,
    source_doc STRING,
    page_num INT,
    extraction_timestamp TIMESTAMP
) USING iceberg
PARTITIONED BY (hidden(org_id), hidden(year), hidden(theme));

-- Gold Layer
CREATE TABLE gold.esg_scores (
    org_id STRING,
    year INT,
    theme STRING,
    stage INT,
    confidence DOUBLE,
    evidence_quality STRING,
    astradb_manifest STRING,
    iceberg_snapshot_id BIGINT,
    score_timestamp TIMESTAMP
) USING iceberg
PARTITIONED BY (hidden(org_id), hidden(year));
```

### Normalization Strategy
- **Deduplication**: Hash-based on (org_id, finding_text, source_doc)
- **Schema Evolution**: Iceberg automatic schema evolution enabled
- **Time Travel**: Maintain 90 days of snapshots for audit
- **Compaction**: Daily compaction of small files < 128MB

## Verification Plan

### Connectivity Tests
```python
def test_infrastructure():
    assert minio_client.bucket_exists("esg-lake")
    assert iceberg_catalog.list_namespaces() == ["bronze", "silver", "gold"]
    assert trino_client.execute("SHOW CATALOGS").contains("iceberg")
    assert mcp_server.list_tools().count() >= 4
    assert watsonx_client.test_connection()["connected"]
    assert astradb_client.collections().count() >= 2
```

### Performance Benchmarks
- MinIO write: 1000 files in < 10 seconds
- Iceberg query: Full table scan < 2 seconds
- MCP tool call: Round-trip < 100ms
- Trino query: Aggregate query < 500ms

### Differential Testing
- Compare legacy scores with new Iceberg-based scores
- Validate evidence linkage between systems
- Cross-check confidence calculations

### Sensitivity Analysis
- Vary batch sizes (1, 10, 100, 1000 records)
- Test with different file formats (Parquet, JSON, CSV)
- Stress test with concurrent agent operations

## Infrastructure Components

### Docker Services
```yaml
services:
  minio:
    image: minio/minio:RELEASE.2024-10-13
    ports: ["9000:9000", "9001:9001"]
    environment:
      MINIO_ROOT_USER: minioadmin
      MINIO_ROOT_PASSWORD: minioadmin
    command: server /data --console-address ":9001"

  iceberg-rest:
    image: tabulario/iceberg-rest:1.5.0
    ports: ["8181:8181"]
    environment:
      AWS_ACCESS_KEY_ID: minioadmin
      AWS_SECRET_ACCESS_KEY: minioadmin
      CATALOG_WAREHOUSE: s3://esg-lake/
      CATALOG_S3_ENDPOINT: http://minio:9000

  trino:
    image: trinodb/trino:438
    ports: ["8080:8080"]
    volumes:
      - ./trino/catalog:/etc/trino/catalog

  mcp-server:
    build: ./mcp_server
    ports: ["8000:8000"]
    environment:
      WATSONX_API_KEY: ${WATSONX_API_KEY}
      ASTRADB_TOKEN: ${ASTRADB_TOKEN}
```

## Security Considerations
- All credentials in .env files (never committed)
- Network isolation between services
- Read-only mounts for configuration
- No external access to MinIO console in production
- API key rotation every 90 days

## Leakage Prevention
- Separate environments for dev/test/prod
- No cross-environment data sharing
- Audit logs for all data access
- Immutable snapshots for compliance

## Success Thresholds
- **Gate Pass Rate**: 14/14 gates passing
- **Service Uptime**: > 99% during development
- **Query Performance**: P95 < 1 second
- **Storage Efficiency**: < 20% overhead vs raw files
- **Memory Usage**: < 4GB total for all services