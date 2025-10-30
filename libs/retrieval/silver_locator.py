"""Silver Directory Locator - Backend-Aware Path Resolution (Task 026)

This module provides dynamic path resolution for silver-tier parquet files
based on the active PDF parser backend.

SCA v13.8-MEA Compliance:
- Type hints: 100%
- Docstrings: Complete
- Thread-safe: Read-only environment variable access
- Deterministic: Same inputs → same output
- No mutable global state
"""
import os
import pathlib
from typing import Literal

BackendType = Literal["default", "docling"]


def locate_chunks_parquet(doc_id: str, org_id: str, year: int) -> str:
    """Locate chunks parquet file for given document.

    Strategy:
    1. Check PARSER_BACKEND environment variable
    2. If "docling", try silver_docling/ directory first
    3. Fall back to silver/ directory (default location)
    4. Return path if file exists, empty string otherwise

    Args:
        doc_id: Document identifier (e.g., "LSE_HEAD_2025")
        org_id: Organization ID (e.g., "LSE_HEAD")
        year: Report year (e.g., 2025)

    Returns:
        Path to parquet file (relative or absolute) or empty string if not found

    Example:
        >>> os.environ["PARSER_BACKEND"] = "docling"
        >>> path = locate_chunks_parquet("LSE_HEAD_2025", "LSE_HEAD", 2025)
        >>> # Returns: "data/silver_docling/org_id=LSE_HEAD/year=2025/LSE_HEAD_2025_chunks.parquet"

        >>> os.environ["PARSER_BACKEND"] = "default"
        >>> path = locate_chunks_parquet("LSE_HEAD_2025", "LSE_HEAD", 2025)
        >>> # Returns: "data/silver/org_id=LSE_HEAD/year=2025/LSE_HEAD_2025_chunks.parquet"

    Notes:
        - Thread-safe (read-only environment variable access)
        - No caching (stateless function)
        - Falls back gracefully if preferred backend file not found
    """
    root = pathlib.Path(".")
    prefer_docling = (get_active_backend() == "docling")

    # Try Docling silver first if preferred
    if prefer_docling:
        docling_path = root / f"data/silver_docling/org_id={org_id}/year={year}/{doc_id}_chunks.parquet"
        if docling_path.exists():
            return str(docling_path)

    # Fall back to default silver
    default_path = root / f"data/silver/org_id={org_id}/year={year}/{doc_id}_chunks.parquet"
    if default_path.exists():
        return str(default_path)

    # Not found
    return ""


def get_active_backend() -> BackendType:
    """Get currently active parser backend from environment.

    Returns:
        "docling" if PARSER_BACKEND environment variable is set to "docling"
        (case-insensitive), otherwise "default"

    Example:
        >>> os.environ["PARSER_BACKEND"] = "docling"
        >>> get_active_backend()
        'docling'

        >>> os.environ["PARSER_BACKEND"] = "DEFAULT"
        >>> get_active_backend()
        'default'

        >>> # Unset or unknown value
        >>> os.environ.pop("PARSER_BACKEND", None)
        >>> get_active_backend()
        'default'

    Notes:
        - Case-insensitive comparison
        - Defaults to "default" if unset or unrecognized value
        - Thread-safe (read-only environment variable access)
    """
    backend = os.getenv("PARSER_BACKEND", "default").lower()
    if backend == "docling":
        return "docling"
    return "default"
