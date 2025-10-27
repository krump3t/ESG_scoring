"""
Cache Manager (Check Data Availability in Silver Layer)

Checks if evidence data already exists in silver layer for (company, year, theme).
Returns cache status to determine if ingestion is needed.

Uses DuckDB to query silver layer metadata.
Part of Task 008 - ESG Data Extraction vertical slice (Option 1).
"""

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional
from datetime import datetime
import duckdb


class CacheStatus(Enum):
    """Status of data in cache (silver layer)"""
    COMPLETE = "complete"      # Data exists and is sufficient
    PARTIAL = "partial"         # Data exists but may be incomplete
    MISSING = "missing"         # No data found


@dataclass
class CacheResult:
    """
    Result of cache check operation.

    Attributes:
        status: Cache status (COMPLETE, PARTIAL, MISSING)
        record_count: Number of evidence records found
        last_updated: Timestamp of most recent record (or None)
    """
    status: CacheStatus
    record_count: int
    last_updated: Optional[datetime]


class CacheManager:
    """
    Manage cache checks for evidence data in silver layer.

    Uses DuckDB to query silver Parquet files for data availability.
    """

    def __init__(self, db_path: Path, bronze_path: Path, silver_path: Path):
        """
        Initialize cache manager.

        Args:
            db_path: Path to DuckDB database
            bronze_path: Path to bronze Parquet directory (for reference)
            silver_path: Path to silver Parquet directory
        """
        self.db_path = Path(db_path)
        self.bronze_path = Path(bronze_path)
        self.silver_path = Path(silver_path)
        self.silver_path.mkdir(parents=True, exist_ok=True)

    def check_cache(
        self,
        company: str,
        year: int,
        theme: str
    ) -> CacheResult:
        """
        Check if data exists in silver layer for (company, year, theme).

        Args:
            company: Company ticker (e.g., "MSFT")
            year: Fiscal year (e.g., 2023)
            theme: ESG theme (e.g., "GHG")

        Returns:
            CacheResult with status, record count, and last updated timestamp
        """
        # Check if any silver files exist
        silver_pattern = str(self.silver_path / "**" / "*.parquet")

        con = duckdb.connect(str(self.db_path))

        try:
            # Try to read silver data
            try:
                con.execute(f"""
                    CREATE OR REPLACE TEMP VIEW silver_evidence AS
                    SELECT * FROM read_parquet(
                        '{silver_pattern}',
                        hive_partitioning = true,
                        union_by_name = true
                    )
                """)
            except Exception as e:
                if "No files found" in str(e):
                    # No silver data at all
                    return CacheResult(
                        status=CacheStatus.MISSING,
                        record_count=0,
                        last_updated=None
                    )
                raise

            # Query for specific (company, year, theme)
            result = con.execute("""
                SELECT
                    COUNT(*) as record_count,
                    MAX(created_at) as last_updated
                FROM silver_evidence
                WHERE org_id = ? AND year = ? AND theme = ?
            """, [company, year, theme]).fetchone()

            record_count = result[0]
            last_updated = result[1]

            # Determine cache status
            if record_count == 0:
                status = CacheStatus.MISSING
            else:
                # For now, any data is considered COMPLETE
                # Future: Could check confidence thresholds or minimum record count
                status = CacheStatus.COMPLETE

            return CacheResult(
                status=status,
                record_count=record_count,
                last_updated=last_updated
            )

        finally:
            con.close()
