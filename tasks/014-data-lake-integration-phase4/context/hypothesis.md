# Hypothesis - Phase 4: Data Lake Integration

**Task ID**: 014-data-lake-integration-phase4
**Phase**: 4 (Data Storage & Query Layer)
**Date**: 2025-10-24
**SCA Protocol**: v13.8-MEA

---

## Research Question

Can we persist extracted ESG metrics to Parquet files with 100% round-trip integrity and enable SQL queries via DuckDB using REAL Phase 3 metrics?

---

## Success Criteria (Testable)

### SC1: Parquet Write Integrity
- **Metric**: Round-trip data integrity (write → read → compare)
- **Target**: 100% field preservation for all ESGMetrics fields
- **Data**: Real Apple Inc. metrics from Phase 3 ($352.6B assets, $99.8B net income)
- **Method**: Write metrics to Parquet, read back, assert equality

### SC2: Schema Parity
- **Metric**: PyArrow schema matches ESGMetrics Pydantic model
- **Target**: All 20+ fields with correct types (float64, int64, string, timestamp)
- **Method**: Compare Parquet schema with ESGMetrics.model_fields

### SC3: DuckDB Query Correctness
- **Metric**: SQL query results match written data
- **Target**: 100% accuracy on SELECT, WHERE, GROUP BY, aggregate queries
- **Data**: 3+ real company metrics (Apple, Microsoft, Tesla from Phase 3)
- **Method**: Write metrics, query with DuckDB, assert results

### SC4: Null Handling
- **Metric**: Optional ESGMetrics fields (null values) preserved
- **Target**: Null values written and read correctly (not converted to 0 or "")
- **Method**: Write metrics with nulls, read back, assert nulls preserved

### SC5: Datetime Serialization
- **Metric**: datetime fields (extraction_timestamp, report_date) round-trip
- **Target**: Timestamps preserved with microsecond precision
- **Method**: Write with timestamp, read, assert datetime equality

### SC6: ParquetWriter Implementation
- **Metric**: Critical path file with domain logic
- **Target**: ParquetWriter class with write_metrics(), append_metrics()
- **Exclusions**: No placeholders, no hardcoded test data in production code

### SC7: DuckDBReader Implementation
- **Metric**: Critical path file with SQL query capabilities
- **Target**: DuckDBReader class with query(), get_latest_metrics()
- **Method**: Real SQL queries on Parquet files

### SC8: TDD Compliance
- **Metric**: Tests written BEFORE implementation
- **Target**: ≥20 tests, all with @pytest.mark.cp, git timestamps prove TDD
- **Method**: Git log verification

### SC9: Test Coverage
- **Metric**: Line and branch coverage on CP files
- **Target**: ≥95% line coverage, ≥95% branch coverage
- **Files**: `parquet_writer.py`, `duckdb_reader.py`

### SC10: End-to-End Pipeline
- **Metric**: Full pipeline with REAL data
- **Target**: Phase 3 extract → Phase 4 write → Phase 4 query → validate
- **Data**: Real Apple metrics
- **Method**: Integration test with all phases

---

## Critical Path (CP) Files

1. **`libs/data_lake/parquet_writer.py`** (~100 lines)
   - ParquetWriter class
   - write_metrics() - write single/batch metrics to Parquet
   - append_metrics() - append to existing Parquet file
   - Schema validation

2. **`libs/data_lake/duckdb_reader.py`** (~80 lines)
   - DuckDBReader class
   - query() - execute SQL on Parquet files
   - get_latest_metrics() - get most recent metrics per company
   - Connection pooling

---

## Exclusions (Out of Scope)

- ❌ Cloud storage (S3, GCS, Azure) - use local filesystem only
- ❌ Partitioning strategies (by year, company) - single file for Phase 4
- ❌ Delta Lake / Iceberg format - pure Parquet only
- ❌ Data versioning - append-only, no updates/deletes
- ❌ Compression optimization - use default Parquet compression

---

## Data Strategy (Authentic)

### Real Data Sources

1. **Phase 3 Structured Extraction**:
   - Apple Inc. FY2024: $352.6B assets, $99.8B net income
   - Source: test_data/sec_edgar/CIK0000320193.json
   - Already extracted and validated

2. **Phase 3 Ground Truth**:
   - Manually verified against SEC 10-K filing
   - Ground truth file: test_data/ground_truth/apple_2024_ground_truth.json

### Test Data Flow

```
Phase 3 Extraction (REAL)
  ↓
ESGMetrics (Pydantic model)
  ↓
Phase 4 ParquetWriter
  ↓
data_lake/esg_metrics.parquet (REAL file on disk)
  ↓
Phase 4 DuckDBReader
  ↓
SQL Query Results (REAL data)
  ↓
Assert: Results match original metrics
```

---

## Assumptions & Risks

### A1: Parquet File Location
- **Assumption**: data_lake/ directory in project root for Parquet files
- **Risk**: Path issues on different OS
- **Mitigation**: Use pathlib.Path for cross-platform compatibility

### A2: PyArrow Schema
- **Assumption**: ESGMetrics Pydantic model maps cleanly to PyArrow types
- **Risk**: Type mismatches (datetime, Optional fields)
- **Mitigation**: Use ESGMetrics.to_parquet_dict() method from Phase 3

### A3: DuckDB Performance
- **Assumption**: DuckDB can query 1000+ row Parquet files in <100ms
- **Risk**: Slow queries on large files
- **Mitigation**: Phase 4 tests use small datasets (3-10 companies)

### A4: Append Operations
- **Assumption**: Parquet append requires reading existing file
- **Risk**: Not truly append-only (read + write)
- **Mitigation**: Document as "append via merge" pattern

### A5: Concurrent Writes
- **Assumption**: Single-process writes (no concurrency in Phase 4)
- **Risk**: Race conditions if multiple processes write
- **Mitigation**: Out of scope, document as future work

---

## Expected Outcomes

### Primary Outcome
✅ **Complete end-to-end pipeline with REAL data**:
- Phase 1: Download (SEC EDGAR) ✅
- Phase 2: Prioritize (Multi-source) ✅
- Phase 3: Extract (Structured + LLM) ✅
- Phase 4: Store + Query (Parquet + DuckDB) ← **THIS PHASE**

### Secondary Outcomes
✅ **Data lake foundation** for future phases:
- Phase 5: Quality scoring can query stored metrics
- Phase 6: Analytics can aggregate across companies
- Phase 7: API can serve metrics from Parquet

✅ **Authentic validation**:
- Real Apple metrics persisted to disk
- SQL queries on real data
- 100% round-trip integrity

---

## Validation Plan

### Round-Trip Testing
```python
# Write
metrics = ESGMetrics(company_name="Apple", assets=352600000000, ...)
writer.write_metrics([metrics], "data_lake/test.parquet")

# Read
reader = DuckDBReader()
results = reader.query("SELECT * FROM 'data_lake/test.parquet'")

# Validate
assert results[0]["assets"] == 352600000000
assert results[0]["company_name"] == "Apple"
```

### SQL Query Testing
```sql
-- Aggregate query
SELECT company_name, AVG(assets) as avg_assets
FROM 'data_lake/esg_metrics.parquet'
GROUP BY company_name;

-- Filter query
SELECT * FROM 'data_lake/esg_metrics.parquet'
WHERE renewable_energy_pct >= 90.0;

-- Latest metrics per company
SELECT company_name, fiscal_year, assets
FROM 'data_lake/esg_metrics.parquet'
WHERE (company_name, fiscal_year) IN (
  SELECT company_name, MAX(fiscal_year)
  FROM 'data_lake/esg_metrics.parquet'
  GROUP BY company_name
);
```

---

**Prepared By**: Scientific Coding Agent v13.8-MEA
**Status**: Ready for Implementation
**Next**: Create design.md and evidence.json
