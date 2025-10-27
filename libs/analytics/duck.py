"""
DuckDB analytics and parity verification over Parquet files.

Real in-process SQL analytics: No mocks, no synthetic data.
Deterministic verification with explicit error handling.

SCA v13.8 Compliance:
- Real DuckDB: Offline analytics, no external dependencies
- Deterministic: Fixed ORDER BY, stable aggregation
- Type hints: 100% annotated
- Failure paths: Explicit exception handling, STRICT mode enforcement
"""

import logging
import json
from pathlib import Path
from typing import Dict, Any, Optional, List

# Configure logging
logger = logging.getLogger(__name__)


def get_conn(db_path: Optional[str] = None) -> Any:
    """Get or create DuckDB connection.

    Args:
        db_path: Optional path to persistent database file (default: in-memory)

    Returns:
        duckdb.DuckDBPyConnection instance

    Raises:
        RuntimeError: If DuckDB import fails
    """
    try:
        import duckdb
    except ImportError as e:
        raise RuntimeError(
            "duckdb SDK not installed. Install with: pip install duckdb"
        ) from e

    if db_path:
        conn = duckdb.connect(str(db_path))
        logger.info(f"Connected to DuckDB at {db_path}")
    else:
        conn = duckdb.connect(":memory:")
        logger.info("Connected to in-memory DuckDB")

    return conn


def register_parquet(conn: Any, name: str, path: str) -> None:
    """Register Parquet file as DuckDB view.

    Args:
        conn: DuckDB connection
        name: View name (e.g., 'v_docs')
        path: Path to Parquet file

    Raises:
        FileNotFoundError: If Parquet file not found
        RuntimeError: If registration fails
    """
    parquet_path = Path(path)

    if not parquet_path.exists():
        raise FileNotFoundError(f"Parquet file not found: {path}")

    try:
        # Register as view (lazy, memory-efficient)
        conn.execute(
            f"CREATE OR REPLACE VIEW {name} AS SELECT * FROM read_parquet('{path}')"
        )
        logger.info(f"Registered Parquet view: {name} ({path})")
    except Exception as e:
        raise RuntimeError(f"Failed to register Parquet: {e}") from e


def compute_stats(conn: Any) -> Dict[str, Any]:
    """Compute statistics over registered views.

    Assumes views v_docs and v_emb are already registered.

    Args:
        conn: DuckDB connection

    Returns:
        Dictionary with counts, quantiles, and metadata

    Raises:
        RuntimeError: If query execution fails
    """
    try:
        # Count documents and embeddings
        doc_count = conn.execute("SELECT COUNT(*) FROM v_docs").fetchall()[0][0]
        emb_count = conn.execute("SELECT COUNT(*) FROM v_emb").fetchall()[0][0]

        logger.info(f"Document count: {doc_count}, Embedding count: {emb_count}")

        # Compute text length statistics
        stats_query = """
        WITH s AS (
            SELECT
                COUNT(*) AS n_docs,
                MIN(text_len) AS min_text_len,
                approx_quantile(text_len, 0.5) AS p50_text_len,
                MAX(text_len) AS max_text_len,
                MAX(published_at) AS latest_published_at
            FROM v_docs
        )
        SELECT * FROM s
        """

        stats_row = conn.execute(stats_query).fetchall()[0]

        stats = {
            "document_count": doc_count,
            "embedding_count": emb_count,
            "text_statistics": {
                "min_length": int(stats_row[1]) if stats_row[1] is not None else 0,
                "median_length": int(stats_row[2]) if stats_row[2] is not None else 0,
                "max_length": int(stats_row[3]) if stats_row[3] is not None else 0,
            },
            "latest_published_at": str(stats_row[4]) if stats_row[4] is not None else "",
        }

        logger.info(f"Statistics computed: {json.dumps(stats, indent=2)}")
        return stats

    except Exception as e:
        raise RuntimeError(f"Statistics computation failed: {e}") from e


def verify_parity(conn: Any) -> None:
    """Verify parity between documents and embeddings.

    Checks:
    1. Same count
    2. No orphan documents (left anti join)
    3. No orphan embeddings (right anti join)

    Args:
        conn: DuckDB connection

    Raises:
        RuntimeError: If any parity check fails (STRICT)
    """
    try:
        # Check counts match
        doc_count = conn.execute("SELECT COUNT(*) FROM v_docs").fetchall()[0][0]
        emb_count = conn.execute("SELECT COUNT(*) FROM v_emb").fetchall()[0][0]

        if doc_count != emb_count:
            raise RuntimeError(
                f"Document/embedding count mismatch: docs={doc_count}, emb={emb_count}"
            )

        # Check no orphan documents
        orphan_docs = conn.execute(
            "SELECT COUNT(*) FROM v_docs d LEFT ANTI JOIN v_emb e ON d.id = e.id"
        ).fetchall()[0][0]

        if orphan_docs > 0:
            raise RuntimeError(f"Found {orphan_docs} documents with no embedding")

        # Check no orphan embeddings
        orphan_emb = conn.execute(
            "SELECT COUNT(*) FROM v_emb e LEFT ANTI JOIN v_docs d ON e.id = d.id"
        ).fetchall()[0][0]

        if orphan_emb > 0:
            raise RuntimeError(f"Found {orphan_emb} embeddings with no document")

        logger.info(
            f"Parity verification PASSED: {doc_count} docs == {emb_count} emb, "
            f"0 orphans both directions"
        )

    except RuntimeError:
        raise
    except Exception as e:
        raise RuntimeError(f"Parity verification failed: {e}") from e


def materialize(conn: Any, sql: str, out_path: str) -> None:
    """Materialize deterministic Parquet from SQL query.

    Args:
        conn: DuckDB connection
        sql: SQL query (must include ORDER BY for determinism)
        out_path: Output Parquet file path

    Raises:
        RuntimeError: If materialization fails
    """
    out_file = Path(out_path)

    try:
        out_file.parent.mkdir(parents=True, exist_ok=True)

        # COPY TO with stable format
        copy_sql = f"COPY ({sql}) TO '{out_path}' (FORMAT PARQUET)"
        conn.execute(copy_sql)

        logger.info(f"Materialized {out_path}")

    except Exception as e:
        raise RuntimeError(f"Materialization failed: {e}") from e


def get_company_theme_stats(conn: Any) -> Dict[str, Any]:
    """Get distribution of companies and themes.

    Args:
        conn: DuckDB connection

    Returns:
        Dictionary with company and theme distributions

    Raises:
        RuntimeError: If query fails
    """
    try:
        # Company distribution
        company_query = (
            "SELECT company, COUNT(*) as count FROM v_docs GROUP BY company ORDER BY count DESC"
        )
        company_rows = conn.execute(company_query).fetchall()
        company_dist = {row[0]: row[1] for row in company_rows}

        # Theme distribution
        theme_query = (
            "SELECT theme, COUNT(*) as count FROM v_docs GROUP BY theme ORDER BY count DESC"
        )
        theme_rows = conn.execute(theme_query).fetchall()
        theme_dist = {row[0]: row[1] for row in theme_rows}

        stats = {"company_distribution": company_dist, "theme_distribution": theme_dist}

        logger.info(f"Company/theme stats: {json.dumps(stats, indent=2)}")
        return stats

    except Exception as e:
        raise RuntimeError(f"Company/theme stats failed: {e}") from e
