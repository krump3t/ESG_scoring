"""
DuckDB Manager for Evidence Query Layer

Creates DuckDB views over Parquet files (bronze/silver layers).
Provides query interface for evidence retrieval and aggregation.

Implements approved data model design (Parquet + DuckDB views).
Part of Task 008 - ESG Data Extraction vertical slice (Option 1).
"""

import logging
from typing import List, Dict, Any, Optional
from pathlib import Path
from contextlib import contextmanager
import duckdb

logger = logging.getLogger(__name__)


class DuckDBManager:
    """
    Manage DuckDB connection and views over Parquet files.

    Provides SQL query layer on top of bronze/silver Parquet storage.
    Uses persistent connection for performance (single db file).
    """

    def __init__(self, db_path: Path, bronze_path: Optional[Path] = None, silver_path: Optional[Path] = None):
        """
        Initialize DuckDB manager.

        Args:
            db_path: Path to DuckDB database file
            bronze_path: Path to bronze Parquet directory (optional)
            silver_path: Path to silver Parquet directory (optional)
        """
        self.db_path = Path(db_path)
        self.bronze_path = Path(bronze_path) if bronze_path else None
        self.silver_path = Path(silver_path) if silver_path else None
        self._connection: Optional[duckdb.DuckDBPyConnection] = None

    @contextmanager
    def get_connection(self):
        """
        Get DuckDB connection (context manager).

        Creates persistent connection on first call.
        Yields connection for query execution.

        Yields:
            DuckDB connection object
        """
        if self._connection is None:
            self._connection = duckdb.connect(str(self.db_path))

        try:
            yield self._connection
        except Exception:
            raise

    def close(self) -> None:
        """Close DuckDB connection."""
        if self._connection:
            try:
                self._connection.close()
            except Exception as e:
                logger.debug(f"DuckDB connection already closed: {e}")

    def __del__(self):
        """Cleanup: Close connection on deletion."""
        try:
            self.close()
        except Exception as e:
            logger.debug(f"Error during DuckDB cleanup on deletion: {e}")


def create_bronze_view(con: duckdb.DuckDBPyConnection, bronze_path: Path) -> None:
    """
    Create bronze_evidence view over bronze Parquet files.

    Args:
        con: DuckDB connection
        bronze_path: Path to bronze Parquet directory

    Creates view:
        bronze_evidence → bronze/**/*.parquet with Hive partitioning

    If no Parquet files exist, creates empty view with expected schema.
    """
    # Use glob pattern to read all Parquet files in bronze directory
    parquet_path = bronze_path / "**" / "*.parquet"

    try:
        con.execute(f"""
            CREATE OR REPLACE VIEW bronze_evidence AS
            SELECT * FROM read_parquet(
                '{parquet_path}',
                hive_partitioning = true,
                union_by_name = true
            )
        """)
    except Exception as e:
        # If no files found, create empty view with expected schema
        if "No files found" in str(e):
            con.execute("""
                CREATE OR REPLACE VIEW bronze_evidence AS
                SELECT
                    CAST(NULL AS VARCHAR) AS evidence_id,
                    CAST(NULL AS VARCHAR) AS org_id,
                    CAST(NULL AS INTEGER) AS year,
                    CAST(NULL AS VARCHAR) AS theme,
                    CAST(NULL AS INTEGER) AS stage_indicator,
                    CAST(NULL AS VARCHAR) AS doc_id,
                    CAST(NULL AS INTEGER) AS page_no,
                    CAST(NULL AS INTEGER) AS span_start,
                    CAST(NULL AS INTEGER) AS span_end,
                    CAST(NULL AS VARCHAR) AS extract_30w,
                    CAST(NULL AS VARCHAR) AS hash_sha256,
                    CAST(NULL AS VARCHAR) AS snapshot_id,
                    CAST(NULL AS DOUBLE) AS confidence,
                    CAST(NULL AS VARCHAR) AS evidence_type,
                    CAST(NULL AS TIMESTAMP) AS extraction_timestamp,
                    CAST(NULL AS VARCHAR) AS doc_manifest_uri,
                    CAST(NULL AS VARCHAR) AS filing_url,
                    CAST(NULL AS INTEGER) AS schema_version,
                    CAST(NULL AS TIMESTAMP) AS created_at,
                    CAST(NULL AS VARCHAR) AS ingestion_id
                WHERE FALSE
            """)
        else:
            raise


def query_evidence_by_org_theme(
    con: duckdb.DuckDBPyConnection,
    org_id: str,
    year: int,
    theme: str
) -> List[Dict[str, Any]]:
    """
    Query evidence by org_id, year, and theme (Q1 from data model).

    Args:
        con: DuckDB connection
        org_id: Organization identifier
        year: Fiscal year
        theme: ESG theme (TSP|OSP|DM|GHG|RD|EI|RMM)

    Returns:
        List of evidence records as dicts
    """
    df = con.execute("""
        SELECT *
        FROM bronze_evidence
        WHERE org_id = ?
          AND year = ?
          AND theme = ?
        ORDER BY page_no, span_start
    """, [org_id, year, theme]).fetchdf()

    # Convert DataFrame to list of dicts
    return df.to_dict('records')
