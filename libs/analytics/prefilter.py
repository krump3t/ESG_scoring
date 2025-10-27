"""
DuckDB Prefilter for Hybrid Retrieval

Deterministic SQL filtering over enriched Parquet to reduce semantic call volume.
No mocks, no synthetic data, STRICT authenticity mode.

SCA v13.8 Compliance:
- Real DuckDB: Offline SQL over materialized Parquet
- Deterministic: Fixed ORDER BY (published_at DESC, id)
- Type hints: 100% annotated
- Failure paths: Explicit exception handling, STRICT mode enforcement
"""

import os
from typing import Optional, List
from pathlib import Path

ENRICHED_PARQUET = "data/ingested/esg_docs_enriched.parquet"


def prefilter_ids(
    company: Optional[str] = None,
    theme: Optional[str] = None,
    limit: int = 50,
    strict: bool = False,
) -> List[str]:
    """Filter document IDs from enriched Parquet by (company, theme).

    Args:
        company: Optional company filter
        theme: Optional theme filter
        limit: Max number of IDs to return (default: 50)
        strict: If True, raise FileNotFoundError when parquet missing (default: False)

    Returns:
        List of document IDs in deterministic order (published_at DESC, id)

    Raises:
        FileNotFoundError: If enriched Parquet missing and strict=True
        RuntimeError: If DuckDB query fails
    """
    try:
        import duckdb
    except ImportError as e:
        raise RuntimeError(
            "duckdb not installed. Install with: pip install duckdb"
        ) from e

    # Check STRICT mode (parameter takes precedence over env var)
    strict_mode = strict or os.getenv("ESG_STRICT_AUTH", "0") == "1"

    # Verify enriched Parquet exists
    if not Path(ENRICHED_PARQUET).exists():
        if strict_mode:
            raise FileNotFoundError(
                f"STRICT mode: Enriched Parquet required but not found: {ENRICHED_PARQUET}"
            )
        return []

    try:
        con = duckdb.connect(":memory:")

        # Register enriched view
        con.execute(
            f"CREATE OR REPLACE VIEW v AS SELECT id, company, theme, published_at FROM read_parquet('{ENRICHED_PARQUET}')"
        )

        # Build WHERE clause
        where_parts: List[str] = []
        params: List[str] = []

        if company:
            where_parts.append("company = ?")
            params.append(company)

        if theme:
            where_parts.append("theme = ?")
            params.append(theme)

        # Build SQL
        sql = "SELECT id FROM v"
        if where_parts:
            sql += " WHERE " + " AND ".join(where_parts)
        sql += " ORDER BY published_at DESC NULLS LAST, id LIMIT ?"
        params.append(str(limit))

        # Execute
        results = con.execute(sql, params).fetchall()
        return [row[0] for row in results]

    except Exception as e:
        raise RuntimeError(f"Prefilter query failed: {e}") from e
