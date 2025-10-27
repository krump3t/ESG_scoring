# Architecture Decision Records - Phase 4: Data Lake Integration

**Task ID**: 014-data-lake-integration-phase4
**Phase**: 4
**Date**: 2025-10-24
**SCA Protocol**: v13.8-MEA

---

## ADR-001: Use Apache Parquet for Columnar Storage

**Status**: Accepted
**Date**: 2025-10-24
**Deciders**: SCA v13.8-MEA

### Context
Phase 4 requires persistent storage for extracted ESG metrics with schema validation, efficient compression, and compatibility with analytical tools.

### Decision
Use Apache Parquet as the storage format for ESG metrics.

### Rationale
1. **Columnar Efficiency**: Parquet's columnar layout optimizes for analytical queries (aggregates, filters)
2. **Compression**: Snappy compression achieves 3-5x size reduction vs JSON
3. **Schema Enforcement**: PyArrow schema validates data types at write time
4. **Industry Standard**: Used by Snowflake, Databricks, BigQuery, Spark
5. **Zero-Copy Reads**: DuckDB can query Parquet without loading into memory
6. **Nested Data Support**: Handles optional fields (nulls) cleanly

### Alternatives Considered
- **CSV**: No schema enforcement, poor compression, inefficient for analytics
- **JSON**: No compression, no columnar layout, large file sizes
- **SQLite**: Row-oriented (inefficient for column scans), requires server process
- **Delta Lake**: Overkill for Phase 4 (ACID transactions not needed yet)

### Consequences
- **Positive**: Fast writes, efficient storage, schema validation, DuckDB integration
- **Negative**: Binary format (not human-readable), append requires read-modify-write
- **Mitigation**: Use Parquet tools for inspection (parquet-tools, DuckDB)

---

## ADR-002: Use DuckDB for SQL Query Engine

**Status**: Accepted
**Date**: 2025-10-24
**Deciders**: SCA v13.8-MEA

### Context
Phase 4 requires SQL query capabilities on Parquet files without a separate database server.

### Decision
Use DuckDB as the in-memory analytical SQL engine.

### Rationale
1. **Zero Setup**: No database server required (in-memory connection)
2. **Parquet Native**: Direct queries on Parquet files (`SELECT * FROM 'file.parquet'`)
3. **Performance**: 10-100x faster than pandas for analytical queries
4. **Full SQL Support**: Aggregates, joins, window functions, CTEs
5. **Zero-Copy Integration**: Works directly with PyArrow buffers
6. **Python Native**: Simple Python API with no additional dependencies

### Alternatives Considered
- **pandas**: Slower for large datasets, must load entire file into memory
- **PySpark**: Overkill for Phase 4 (distributed compute not needed), heavy setup
- **SQLite**: Row-oriented (inefficient for analytics), poor Parquet integration
- **PostgreSQL**: Requires server setup, no native Parquet support

### Consequences
- **Positive**: Fast analytical queries, simple API, no server management
- **Negative**: In-memory only (no persistent database), single-node only
- **Mitigation**: Phase 4 scope is single-node analytics (distributed compute deferred to Phase 6)

---

## ADR-003: Append Strategy via Read-Modify-Write

**Status**: Accepted
**Date**: 2025-10-24
**Deciders**: SCA v13.8-MEA

### Context
ParquetWriter needs append functionality to add new metrics to existing files.

### Decision
Implement append via read-modify-write pattern:
1. Read existing Parquet file into memory
2. Append new records to in-memory list
3. Write combined list back to file

### Rationale
1. **Simplicity**: Single-file operations, no partitioning logic needed for Phase 4
2. **Schema Consistency**: Ensures all rows have same schema
3. **PyArrow Native**: Uses standard PyArrow read/write APIs
4. **Atomic Writes**: File replaced atomically (no partial writes)

### Alternatives Considered
- **Parquet Row Groups**: Append as new row group (requires lower-level API)
- **Partitioned Files**: Write separate files per company/year (deferred to Phase 6)
- **Delta Lake**: ACID append transactions (overkill for Phase 4)

### Consequences
- **Positive**: Simple implementation, atomic updates, schema validation
- **Negative**: Full file rewrite on append (not scalable for large files)
- **Mitigation**: Phase 4 limited to 10-100 companies (acceptable performance)

### Future Work
Phase 6 will implement partitioned Parquet files (by company, year) for scalable appends.

---

## ADR-004: Leverage Phase 3 Parquet Serialization Methods

**Status**: Accepted
**Date**: 2025-10-24
**Deciders**: SCA v13.8-MEA

### Context
ESGMetrics model from Phase 3 already has `to_parquet_dict()` and `from_parquet_dict()` methods.

### Decision
Use existing Phase 3 serialization methods instead of reimplementing Parquet logic.

### Rationale
1. **DRY Principle**: Reuse validated code from Phase 3
2. **Schema Parity**: Guaranteed consistency with Phase 3 extraction
3. **Field Mapping**: Handles datetime, Optional fields, type conversions
4. **Tested**: Phase 3 has 96.7% coverage including serialization methods

### Consequences
- **Positive**: No duplicate logic, schema consistency, faster implementation
- **Negative**: Phase 4 coupled to Phase 3 model changes
- **Mitigation**: ESGMetrics is stable (20+ fields defined in Phase 3)

---

## ADR-005: Store Parquet Files in Local data_lake/ Directory

**Status**: Accepted
**Date**: 2025-10-24
**Deciders**: SCA v13.8-MEA

### Context
Phase 4 needs a filesystem location for Parquet files.

### Decision
Store Parquet files in `data_lake/` directory at project root.

### Rationale
1. **Simple Path Management**: Relative to project root
2. **Cross-Platform**: pathlib.Path handles Windows/Linux differences
3. **Gitignore**: Easy to exclude from version control
4. **Test Isolation**: Tests use pytest tmpdir fixture (separate from production)

### Alternatives Considered
- **Cloud Storage (S3, GCS)**: Deferred to Phase 7 (cloud integration)
- **Database**: Would require separate server (contradicts ADR-002)
- **tasks/014-*/data_lake/**: Tight coupling to task directory

### Consequences
- **Positive**: Simple, cross-platform, easy cleanup
- **Negative**: Local filesystem only (no cloud sync yet)
- **Mitigation**: Phase 7 will add S3/GCS support

---

## ADR-006: Accept Branch Coverage Gap for API Failures

**Status**: Accepted
**Date**: 2025-10-24
**Deciders**: SCA v13.8-MEA

### Context
Testing all DuckDB/PyArrow error paths may be difficult without mocking.

### Decision
Accept branch coverage gap (down to 90%) for defensive error handlers that are hard to trigger.

### Rationale
1. **Authenticity**: SCA v13.8 prohibits mocking (would violate authentic computation)
2. **Precedent**: Phase 3 accepted 91.0% branch coverage for similar reasons
3. **Diminishing Returns**: Triggering low-level PyArrow errors requires corrupting files
4. **Documented**: Explicitly document untested branches with justification

### Consequences
- **Positive**: Maintains authentic computation principle
- **Negative**: Some error paths untested
- **Mitigation**: Document exact untested branches in coverage report

### Coverage Tradeoff
- **Line Coverage Target**: ≥95% (achievable)
- **Branch Coverage Target**: ≥90% (realistic with authenticity)
- **Untested Branches**: PyArrow schema validation failures, DuckDB connection errors

---

## ADR-007: Use Snappy Compression for Parquet Files

**Status**: Accepted
**Date**: 2025-10-24
**Deciders**: SCA v13.8-MEA

### Context
Parquet supports multiple compression codecs (snappy, gzip, zstd, lz4).

### Decision
Use Snappy compression for all Parquet writes.

### Rationale
1. **Balance**: Good compression ratio (3-4x) with fast write/read speeds
2. **Default**: PyArrow default compression (widely supported)
3. **Compatibility**: Works with all Parquet readers (Spark, DuckDB, pandas)
4. **Phase 4 Scope**: Optimize later if needed (easy to change compression codec)

### Alternatives Considered
- **gzip**: Higher compression (5-6x) but 2-3x slower writes
- **zstd**: Better than snappy but newer (compatibility concerns)
- **lz4**: Faster than snappy but lower compression
- **None**: No compression (large files)

### Consequences
- **Positive**: Fast writes, good compression, universal compatibility
- **Negative**: Not optimal for extreme compression or extreme speed
- **Mitigation**: Phase 7 can tune compression per use case

---

## ADR-008: In-Memory DuckDB Connection (No Persistent DB)

**Status**: Accepted
**Date**: 2025-10-24
**Deciders**: SCA v13.8-MEA

### Context
DuckDB supports both in-memory (`:memory:`) and persistent database files.

### Decision
Use in-memory DuckDB connection for all queries.

### Rationale
1. **Simplicity**: No database file management
2. **Stateless**: Each query starts fresh (no stale data)
3. **Parquet as Source of Truth**: Data persisted in Parquet, not DuckDB
4. **Fast Startup**: No database file loading time

### Alternatives Considered
- **Persistent DuckDB File**: Would require file cleanup, version management
- **Hybrid**: Persistent for production, in-memory for tests (adds complexity)

### Consequences
- **Positive**: Simple, stateless, fast, no cleanup needed
- **Negative**: No query result caching (must re-read Parquet each time)
- **Mitigation**: DuckDB's zero-copy Parquet reads are fast enough for Phase 4

---

**Prepared By**: Scientific Coding Agent v13.8-MEA
**Status**: Phase 4 Architecture Decisions Complete
**Next**: Create assumptions.md
