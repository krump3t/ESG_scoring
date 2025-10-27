"""DuckDB analytics module for offline verification and prefiltering."""

from libs.analytics.duck import (
    get_conn,
    register_parquet,
    compute_stats,
    verify_parity,
    materialize,
    get_company_theme_stats,
)
from libs.analytics.prefilter import prefilter_ids

__all__ = [
    "get_conn",
    "register_parquet",
    "compute_stats",
    "verify_parity",
    "materialize",
    "get_company_theme_stats",
    "prefilter_ids",
]
