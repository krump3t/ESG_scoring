# Design: Production Hardening

## Optimization Strategies

### 1. Iceberg Compaction
```python
# Configure compaction policies
table.updateProperties()
    .set("write.metadata.delete-after-commit.enabled", "true")
    .set("write.metadata.previous-versions-max", "100")
    .set("write.target-file-size-bytes", "134217728")  # 128MB
    .commit()

# Run compaction
spark.sql("""
    CALL catalog.system.rewrite_data_files(
        table => 'gold.esg_scores',
        strategy => 'binpack',
        options => map('min-input-files', '5')
    )
""")
```

### 2. Compression Tuning
- ZSTD level 3-5 for balanced compression/speed
- Dictionary encoding for low-cardinality columns
- Run-length encoding for repeated values

### 3. Bloom Filters
```python
# Add bloom filters to hot columns
table.updateProperties()
    .set("write.bloom-filter.enabled", "true")
    .set("write.bloom-filter.columns", "org_id,framework_code,doc_id")
    .set("write.bloom-filter.fpp", "0.01")  # 1% false positive rate
    .commit()
```

### 4. Snapshot Retention
- Keep last 90 days of daily snapshots
- Keep monthly snapshots for 1 year
- Expire old snapshots automatically

## Performance Benchmarks
- Query latency: P50, P95, P99
- Compaction time vs data volume
- Storage overhead after optimization

## Success Criteria
- **Query P95**: < 1 second
- **Compaction Overhead**: < 10%
- **Storage Efficiency**: > 80%
- **All Gates**: 14/14 passing
