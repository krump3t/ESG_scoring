# Assumptions - Phase 4: Data Lake Integration

**Task ID**: 014-data-lake-integration-phase4
**Phase**: 4
**Date**: 2025-10-24
**SCA Protocol**: v13.8-MEA

---

## Technical Assumptions

### A1: PyArrow Schema Compatibility
**Assumption**: ESGMetrics Pydantic model maps cleanly to PyArrow schema without type mismatches.

**Justification**: Phase 3 already defines `ESG_METRICS_PARQUET_SCHEMA` and validates it with real Apple metrics.

**Risk**: Medium - datetime and Optional field handling could fail
**Mitigation**: Use Phase 3's `to_parquet_dict()` method (already handles type conversions)

**Validation**: Round-trip test - write ESGMetrics → read back → assert equality

---

### A2: DuckDB Parquet Integration
**Assumption**: DuckDB can query Parquet files without loading them into memory (zero-copy reads).

**Justification**: DuckDB documentation confirms native Parquet support with PyArrow integration.

**Risk**: Low - well-documented feature
**Mitigation**: Test with real Parquet file in Phase 4 tests

**Validation**: Query 100-row Parquet file and verify results match written data

---

### A3: Filesystem Path Compatibility
**Assumption**: `pathlib.Path` handles Windows and Linux path differences correctly.

**Justification**: Python standard library guarantees cross-platform path handling.

**Risk**: Low - proven standard library functionality
**Mitigation**: Use `Path.resolve()` for absolute paths in tests

**Validation**: Run tests on Windows (current) and Linux (CI if available)

---

### A4: Parquet Append Performance
**Assumption**: Read-modify-write append pattern is acceptable for Phase 4 scale (10-100 companies).

**Justification**: 100 ESGMetrics rows ≈ 50 KB Parquet file (with snappy). Reading 50 KB into memory is < 10ms.

**Risk**: Medium - not scalable to 10,000+ companies
**Mitigation**: Document as Phase 4 limitation, defer partitioned writes to Phase 6

**Validation**: Benchmark append_metrics() with 100 existing rows (target: < 100ms)

---

### A5: Snappy Compression Availability
**Assumption**: PyArrow installation includes Snappy compression codec.

**Justification**: Snappy is PyArrow's default compression and included in binary distributions.

**Risk**: Low - standard PyArrow feature
**Mitigation**: Test suite will fail immediately if Snappy not available

**Validation**: Test writes Parquet with compression='snappy'

---

### A6: DuckDB SQL Dialect
**Assumption**: DuckDB SQL syntax is standard enough for basic queries (SELECT, WHERE, GROUP BY, ORDER BY).

**Justification**: DuckDB aims for PostgreSQL compatibility.

**Risk**: Low - Phase 4 only uses basic SQL
**Mitigation**: Test suite covers all SQL patterns used in production

**Validation**: Execute 10 different SQL queries in tests (filters, aggregates, joins)

---

### A7: In-Memory DuckDB Performance
**Assumption**: In-memory DuckDB connection can query 100-row Parquet file in < 50ms.

**Justification**: DuckDB is optimized for analytical queries on columnar data.

**Risk**: Low - small data size for Phase 4
**Mitigation**: No mitigation needed (50ms is acceptable for Phase 4)

**Validation**: Benchmark query() with complex SQL (aggregates + filters)

---

## Data Assumptions

### A8: Phase 3 Metrics Availability
**Assumption**: Real Apple Inc. metrics from Phase 3 SEC EDGAR extraction are available for Phase 4 tests.

**Justification**: Phase 3 completed with 96.7% coverage, $352.6B assets validated.

**Risk**: Low - Phase 3 complete
**Mitigation**: Use fixtures from `test_data/ground_truth/apple_2024_ground_truth.json`

**Validation**: Phase 4 tests import Phase 3 fixtures

---

### A9: ESGMetrics Field Stability
**Assumption**: ESGMetrics model schema will not change during Phase 4 implementation.

**Justification**: Phase 3 finalized schema with 20+ fields (financial, environmental, social, governance).

**Risk**: Low - schema frozen after Phase 3
**Mitigation**: Phase 4 uses Phase 3's schema, no modifications

**Validation**: Tests assert exact field list matches Phase 3

---

### A10: Null Value Handling
**Assumption**: Parquet correctly preserves null values for Optional ESGMetrics fields.

**Justification**: PyArrow schema marks Optional fields as nullable.

**Risk**: Medium - nulls could be converted to 0 or ""
**Mitigation**: Explicit test for null preservation (write metrics with nulls → read → assert nulls)

**Validation**: Test with ESGMetrics where scope1_emissions=None

---

### A11: Datetime Microsecond Precision
**Assumption**: Parquet timestamps preserve microsecond precision for `extraction_timestamp` and `report_date`.

**Justification**: PyArrow `pa.timestamp('us')` schema supports microsecond precision.

**Risk**: Low - well-documented feature
**Mitigation**: Test datetime round-trip with microsecond precision

**Validation**: Write metrics with specific microsecond timestamp → read → assert exact match

---

## Integration Assumptions

### A12: No External Dependencies
**Assumption**: Phase 4 only depends on PyArrow, DuckDB, and Phase 3 models (no new external services).

**Justification**: All libraries installable via pip, no API keys required.

**Risk**: Low - pure Python libraries
**Mitigation**: Update requirements.txt with pyarrow, duckdb

**Validation**: Clean virtual environment install + pytest run

---

### A13: Test Data Isolation
**Assumption**: Pytest tmpdir fixture provides isolated filesystem for each test.

**Justification**: Pytest standard fixture, creates unique temp directory per test.

**Risk**: Low - proven pytest functionality
**Mitigation**: Use tmpdir for all Parquet file writes in tests

**Validation**: Parallel test execution (pytest -n auto) shows no conflicts

---

### A14: No Concurrent Writes
**Assumption**: Phase 4 has single-process writes only (no concurrent ParquetWriter instances).

**Justification**: Phase 4 scope is sequential extraction → write → query.

**Risk**: Medium - would break in multi-process scenario
**Mitigation**: Document as Phase 4 limitation, defer locking to Phase 7

**Validation**: Document in design.md (no test needed for Phase 4)

---

## Testing Assumptions

### A15: TDD with Real Data
**Assumption**: Tests can be written before implementation using Phase 3 metrics as fixtures.

**Justification**: Phase 3 ground truth available in `test_data/ground_truth/`.

**Risk**: Low - fixtures already created
**Mitigation**: Create comprehensive fixtures in conftest.py

**Validation**: Run tests before implementing ParquetWriter/DuckDBReader (should fail)

---

### A16: Coverage Target Achievable
**Assumption**: ≥95% line coverage and ≥90% branch coverage achievable with authentic tests (no mocking).

**Justification**: Phase 3 achieved 96.7% line / 91.0% branch with similar constraints.

**Risk**: Medium - some error paths hard to trigger
**Mitigation**: Accept coverage gap per ADR-006 (follows Phase 3 precedent)

**Validation**: Coverage report with explicit justification for untested branches

---

### A17: Hypothesis Property Tests Feasible
**Assumption**: Hypothesis can generate valid ESGMetrics instances for property-based testing.

**Justification**: Hypothesis supports Pydantic models via `from_type()`.

**Risk**: Low - standard Hypothesis feature
**Mitigation**: Use `@st.from_type(ESGMetrics)` strategy

**Validation**: Property test: write/read any valid ESGMetrics → assert equality

---

### A18: Failure Tests Without Corruption
**Assumption**: Failure tests can be written without corrupting Parquet files (file not found, empty metrics list, invalid SQL).

**Justification**: Most error paths triggered by invalid inputs, not corrupted data.

**Risk**: Low - Phase 4 has clear error conditions
**Mitigation**: Test error handlers with invalid inputs (missing files, empty lists)

**Validation**: ≥3 failure tests per CP file (as per TDD guard)

---

## Business Assumptions

### A19: Single-Node Performance Sufficient
**Assumption**: Phase 4 does not require distributed compute (Spark, Dask).

**Justification**: Phase 4 scope is 10-100 companies (< 10 MB data).

**Risk**: Low - well-scoped phase
**Mitigation**: Phase 6 will introduce distributed analytics if needed

**Validation**: Query 100-row Parquet file completes in < 100ms

---

### A20: No Data Versioning Required
**Assumption**: Phase 4 does not need versioning (immutable writes only, no updates/deletes).

**Justification**: Phase 4 is append-only data lake.

**Risk**: Low - Phase 4 scope
**Mitigation**: Phase 7 can add versioning (Delta Lake, Iceberg)

**Validation**: Design.md documents append-only constraint

---

### A21: Coverage Exception Precedent
**Assumption**: SCA v13.8 permits branch coverage < 95% if justified with authentic computation rationale.

**Justification**: Phase 3 snapshot explicitly states: "Coverage tradeoff: authenticity > metrics. We accept 4% line gap and 9% branch gap to honor authentic computation (no mocking PyArrow/DuckDB errors)."

**Risk**: Low - explicit precedent from Phase 3
**Mitigation**: Document exact untested branches in Phase 4 snapshot

**Validation**: Phase 3 snapshot.md shows SCA accepted 91.0% branch coverage

---

### A22: Local Filesystem Only (Phase 4)
**Assumption**: Phase 4 stores Parquet files on local filesystem (not S3, GCS, Azure).

**Justification**: Phase 4 focuses on core write/query functionality, cloud storage deferred.

**Risk**: Low - clear phase boundary
**Mitigation**: ADR-005 documents local storage decision

**Validation**: ParquetWriter base_path parameter uses local Path

---

### A23: No Schema Evolution (Phase 4)
**Assumption**: ESGMetrics schema is frozen for Phase 4 (no new fields added mid-phase).

**Justification**: Schema finalized in Phase 3, Phase 4 is storage layer only.

**Risk**: Low - no business requirement for schema changes
**Mitigation**: Phase 6 can handle schema evolution if needed

**Validation**: Tests assert exact 20+ field schema from Phase 3

---

### A24: Deterministic Test Execution
**Assumption**: Tests execute deterministically (same input → same output) without random seeds.

**Justification**: Parquet writes are deterministic, DuckDB queries are deterministic.

**Risk**: Low - no randomness in Phase 4
**Mitigation**: No seeds needed (unlike ML models)

**Validation**: Run tests 10 times, assert identical results

---

**Prepared By**: Scientific Coding Agent v13.8-MEA
**Status**: 24 Assumptions Documented
**Next**: Begin Phase 4 TDD test implementation
