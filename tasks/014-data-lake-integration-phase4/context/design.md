# Design - Phase 4: Data Lake Integration

**Task ID**: 014-data-lake-integration-phase4
**Phase**: 4
**Date**: 2025-10-24
**SCA Protocol**: v13.8-MEA

---

## Architecture Overview

Phase 4 implements the data lake layer that persists extracted ESG metrics to Parquet files and enables SQL queries via DuckDB.

```
┌────────────────────────────────────────────────────────┐
│              Phase 3: Extraction Layer                  │
│  ┌─────────────────┐  ┌──────────────────┐            │
│  │ StructuredExtractor│  │  LLMExtractor    │            │
│  └────────┬──────────┘  └────────┬─────────┘            │
│           └──────────────┬───────┘                      │
│                          ▼                               │
│                   ┌──────────────┐                      │
│                   │  ESGMetrics  │                      │
│                   └──────┬───────┘                      │
└──────────────────────────┼───────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────┐
│              Phase 4: Data Lake Layer (NEW)            │
│                                                         │
│  ┌──────────────────────────────────────────────────┐ │
│  │           ParquetWriter                           │ │
│  │  - write_metrics(metrics, path)                  │ │
│  │  - append_metrics(metrics, path)                 │ │
│  │  - _validate_schema(metrics)                     │ │
│  └────────────────────┬─────────────────────────────┘ │
│                       │                                 │
│                       ▼                                 │
│            ┌─────────────────────┐                     │
│            │  esg_metrics.parquet │ (on disk)          │
│            └─────────┬───────────┘                     │
│                      │                                  │
│                      ▼                                  │
│  ┌──────────────────────────────────────────────────┐ │
│  │           DuckDBReader                            │ │
│  │  - query(sql) → List[Dict]                       │ │
│  │  - get_latest_metrics(company) → ESGMetrics     │ │
│  │  - _connect() → duckdb.DuckDBPyConnection       │ │
│  └──────────────────────────────────────────────────┘ │
└────────────────────────────────────────────────────────┘
```

---

## Component Design

### 1. ParquetWriter (Critical Path)

**Purpose**: Write ESGMetrics to Parquet files with schema validation

**Interface**:
```python
from typing import List, Union
from pathlib import Path
import pyarrow as pa
import pyarrow.parquet as pq
from libs.models.esg_metrics import ESGMetrics, ESG_METRICS_PARQUET_SCHEMA


class ParquetWriter:
    """Writes ESGMetrics to Parquet files for data lake storage."""

    def __init__(self, base_path: str = "data_lake"):
        """Initialize Parquet writer.

        Args:
            base_path: Base directory for Parquet files
        """
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

    def write_metrics(
        self,
        metrics: Union[ESGMetrics, List[ESGMetrics]],
        filename: str = "esg_metrics.parquet"
    ) -> Path:
        """Write metrics to Parquet file (overwrites existing).

        Args:
            metrics: Single ESGMetrics or list of metrics
            filename: Output filename (within base_path)

        Returns:
            Path to written Parquet file

        Raises:
            ValueError: If metrics list is empty
        """
        if not isinstance(metrics, list):
            metrics = [metrics]

        if not metrics:
            raise ValueError("Cannot write empty metrics list")

        # Convert to Parquet dicts
        records = [m.to_parquet_dict() for m in metrics]

        # Create PyArrow Table
        table = pa.Table.from_pylist(records, schema=ESG_METRICS_PARQUET_SCHEMA)

        # Write to Parquet
        output_path = self.base_path / filename
        pq.write_table(table, output_path, compression="snappy")

        return output_path

    def append_metrics(
        self,
        metrics: Union[ESGMetrics, List[ESGMetrics]],
        filename: str = "esg_metrics.parquet"
    ) -> Path:
        """Append metrics to existing Parquet file.

        If file doesn't exist, creates new file.

        Args:
            metrics: Single ESGMetrics or list of metrics
            filename: Target filename (within base_path)

        Returns:
            Path to updated Parquet file
        """
        if not isinstance(metrics, list):
            metrics = [metrics]

        if not metrics:
            raise ValueError("Cannot append empty metrics list")

        file_path = self.base_path / filename

        # If file doesn't exist, write new
        if not file_path.exists():
            return self.write_metrics(metrics, filename)

        # Read existing data
        existing_table = pq.read_table(file_path)
        existing_records = existing_table.to_pylist()

        # Append new metrics
        new_records = [m.to_parquet_dict() for m in metrics]
        all_records = existing_records + new_records

        # Write combined data
        combined_table = pa.Table.from_pylist(
            all_records,
            schema=ESG_METRICS_PARQUET_SCHEMA
        )
        pq.write_table(combined_table, file_path, compression="snappy")

        return file_path

    def get_row_count(self, filename: str = "esg_metrics.parquet") -> int:
        """Get number of rows in Parquet file.

        Args:
            filename: Parquet filename

        Returns:
            Number of rows

        Raises:
            FileNotFoundError: If file doesn't exist
        """
        file_path = self.base_path / filename
        if not file_path.exists():
            raise FileNotFoundError(f"Parquet file not found: {file_path}")

        table = pq.read_table(file_path)
        return table.num_rows
```

**Design Rationale**:
- Uses PyArrow for efficient Parquet I/O
- Leverages ESGMetrics.to_parquet_dict() from Phase 3
- Snappy compression (fast, good compression ratio)
- Append via read-modify-write (simple, safe for Phase 4 scope)

---

### 2. DuckDBReader (Critical Path)

**Purpose**: Query Parquet files using SQL via DuckDB

**Interface**:
```python
from typing import List, Dict, Any, Optional
from pathlib import Path
import duckdb
from libs.models.esg_metrics import ESGMetrics


class DuckDBReader:
    """Queries ESG metrics from Parquet files using DuckDB SQL engine."""

    def __init__(self, base_path: str = "data_lake"):
        """Initialize DuckDB reader.

        Args:
            base_path: Base directory for Parquet files
        """
        self.base_path = Path(base_path)
        self.conn = None

    def _connect(self) -> duckdb.DuckDBPyConnection:
        """Create DuckDB connection (in-memory).

        Returns:
            DuckDB connection
        """
        if self.conn is None:
            self.conn = duckdb.connect(":memory:")
        return self.conn

    def query(
        self,
        sql: str,
        filename: str = "esg_metrics.parquet"
    ) -> List[Dict[str, Any]]:
        """Execute SQL query on Parquet file.

        Args:
            sql: SQL query (use table name or 'parquet_path' in FROM clause)
            filename: Parquet filename to query

        Returns:
            List of result rows as dicts

        Raises:
            FileNotFoundError: If Parquet file doesn't exist
        """
        file_path = self.base_path / filename
        if not file_path.exists():
            raise FileNotFoundError(f"Parquet file not found: {file_path}")

        conn = self._connect()

        # Replace placeholder with actual file path
        sql = sql.replace("${parquet_file}", f"'{file_path}'")

        # Execute query
        result = conn.execute(sql).fetchall()

        # Get column names
        columns = [desc[0] for desc in conn.description]

        # Convert to list of dicts
        return [dict(zip(columns, row)) for row in result]

    def get_latest_metrics(
        self,
        company_name: str,
        filename: str = "esg_metrics.parquet"
    ) -> Optional[ESGMetrics]:
        """Get latest metrics for a company (most recent fiscal year).

        Args:
            company_name: Company name
            filename: Parquet filename

        Returns:
            ESGMetrics for latest year, or None if not found
        """
        sql = f"""
        SELECT *
        FROM '{self.base_path / filename}'
        WHERE company_name = '{company_name}'
        ORDER BY fiscal_year DESC
        LIMIT 1
        """

        results = self.query(sql, filename)

        if not results:
            return None

        # Convert dict to ESGMetrics
        return ESGMetrics.from_parquet_dict(results[0])

    def get_companies_summary(
        self,
        filename: str = "esg_metrics.parquet"
    ) -> List[Dict[str, Any]]:
        """Get summary of all companies in data lake.

        Returns:
            List of dicts with company_name, fiscal_year count, latest_year
        """
        sql = f"""
        SELECT
            company_name,
            COUNT(*) as record_count,
            MIN(fiscal_year) as earliest_year,
            MAX(fiscal_year) as latest_year
        FROM '{self.base_path / filename}'
        GROUP BY company_name
        ORDER BY company_name
        """

        return self.query(sql, filename)

    def close(self):
        """Close DuckDB connection."""
        if self.conn:
            self.conn.close()
            self.conn = None
```

**Design Rationale**:
- DuckDB: Fast analytical queries on Parquet (faster than pandas)
- In-memory connection (no persistent DB file needed)
- SQL interface familiar to data analysts
- Direct Parquet file queries (no data loading required)

---

## Data Flow (End-to-End)

### Write Path
```python
# 1. Extract metrics (Phase 3)
from agents.extraction.structured_extractor import StructuredExtractor

extractor = StructuredExtractor()
result = extractor.extract(apple_report)
metrics = result.metrics  # ESGMetrics instance

# 2. Write to data lake (Phase 4)
from libs.data_lake.parquet_writer import ParquetWriter

writer = ParquetWriter(base_path="data_lake")
parquet_path = writer.write_metrics(metrics, "esg_metrics.parquet")

print(f"Metrics written to: {parquet_path}")
# Output: data_lake/esg_metrics.parquet
```

### Read Path
```python
# 3. Query metrics (Phase 4)
from libs.data_lake.duckdb_reader import DuckDBReader

reader = DuckDBReader(base_path="data_lake")

# SQL query
results = reader.query("""
    SELECT company_name, fiscal_year, assets, net_income
    FROM ${parquet_file}
    WHERE assets > 300000000000
""", "esg_metrics.parquet")

print(results)
# [{'company_name': 'Apple Inc.', 'fiscal_year': 2024, 'assets': 352583000000.0, ...}]

# Convenience method
latest = reader.get_latest_metrics("Apple Inc.")
print(f"Latest Apple assets: ${latest.assets:,.0f}")
# Latest Apple assets: $352,583,000,000
```

---

## Schema Design

Phase 4 uses the **ESGMetrics Pydantic model and PyArrow schema from Phase 3**:

```python
# From libs/models/esg_metrics.py (Phase 3)
ESG_METRICS_PARQUET_SCHEMA = pa.schema([
    ("company_name", pa.string()),
    ("cik", pa.string()),
    ("fiscal_year", pa.int64()),
    ("fiscal_period", pa.string()),
    ("report_date", pa.timestamp("us")),
    # Financial
    ("assets", pa.float64()),
    ("liabilities", pa.float64()),
    ("net_income", pa.float64()),
    # Environmental
    ("scope1_emissions", pa.float64()),
    ("scope2_emissions", pa.float64()),
    ("renewable_energy_pct", pa.float64()),
    # Metadata
    ("extraction_method", pa.string()),
    ("extraction_timestamp", pa.timestamp("us")),
    ("data_source", pa.string()),
])
```

**Key Design Decisions**:
1. ✅ All numeric fields as float64 (handles large values like $352B)
2. ✅ Timestamps as microsecond precision
3. ✅ Nullability: All Optional fields support null
4. ✅ String fields for identifiers (cik, company_name)

---

## Integration with Previous Phases

### Phase 3 → Phase 4
- ESGMetrics model (unchanged)
- to_parquet_dict() / from_parquet_dict() methods (Phase 3)
- Parquet schema (Phase 3)

Phase 4 is **pure storage + query layer** - no changes to extraction logic.

---

## Success Thresholds

- **Round-trip integrity**: 100% (all fields preserved)
- **Query correctness**: 100% (SQL results match written data)
- **Coverage**: ≥95% line & branch on both CP files
- **Tests**: ≥20 tests, all with real Apple metrics

---

**Prepared By**: Scientific Coding Agent v13.8-MEA
**Status**: Ready for Implementation
**Next**: Create evidence.json and remaining context files
