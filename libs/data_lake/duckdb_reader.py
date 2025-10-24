"""
DuckDBReader - Phase 4 Data Lake Integration

Queries ESG metrics from Parquet files using DuckDB SQL engine.
Critical Path implementation per SCA v13.8.

Design: libs/data_lake/duckdb_reader.py:80 lines
Tests: tests/data_lake/test_duckdb_reader_phase4.py:15 tests
"""

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
        file_path = self.base_path / filename

        sql = f"""
        SELECT *
        FROM '{file_path}'
        WHERE company_name = '{company_name}'
        ORDER BY fiscal_year DESC
        LIMIT 1
        """

        results = self.query(sql, filename)

        if not results:
            return None

        # Convert dict to ESGMetrics using Phase 3 deserialization
        return ESGMetrics.from_parquet_dict(results[0])

    def get_companies_summary(
        self,
        filename: str = "esg_metrics.parquet"
    ) -> List[Dict[str, Any]]:
        """Get summary of all companies in data lake.

        Returns:
            List of dicts with company_name, fiscal_year count, latest_year
        """
        file_path = self.base_path / filename

        sql = f"""
        SELECT
            company_name,
            COUNT(*) as record_count,
            MIN(fiscal_year) as earliest_year,
            MAX(fiscal_year) as latest_year
        FROM '{file_path}'
        GROUP BY company_name
        ORDER BY company_name
        """

        return self.query(sql, filename)

    def close(self):
        """Close DuckDB connection."""
        if self.conn:
            self.conn.close()
            self.conn = None
