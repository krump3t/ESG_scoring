"""
Silver Evidence Normalizer (Deduplication + Freshness)

Normalizes bronze evidence to silver layer with:
- Deduplication (confidence-first, then recency)
- Graduated freshness penalties
- Adjusted confidence calculation
- is_most_recent flag tracking

Implements approved data model design (confidence-first deduplication).
Part of Task 008 - ESG Data Extraction vertical slice (Option 1).
"""

from typing import Optional
from pathlib import Path
from datetime import datetime, UTC
import duckdb
import pyarrow as pa
import pyarrow.parquet as pq


# Silver schema extends bronze with normalization fields
SILVER_SCHEMA = pa.schema([
    # Bronze fields
    ('evidence_id', pa.string()),
    ('org_id', pa.string()),
    ('year', pa.int32()),
    ('theme', pa.string()),
    ('stage_indicator', pa.int32()),
    ('doc_id', pa.string()),
    ('page_no', pa.int32()),
    ('span_start', pa.int32()),
    ('span_end', pa.int32()),
    ('extract_30w', pa.string()),
    ('hash_sha256', pa.string()),
    ('snapshot_id', pa.string()),
    ('confidence', pa.float64()),
    ('evidence_type', pa.string()),
    ('extraction_timestamp', pa.timestamp('us')),
    ('doc_manifest_uri', pa.string()),
    ('filing_url', pa.string()),
    ('schema_version', pa.int32()),
    ('created_at', pa.timestamp('us')),
    ('ingestion_id', pa.string()),

    # Silver-specific fields
    ('is_most_recent', pa.bool_()),
    ('freshness_penalty', pa.float64()),
    ('adjusted_confidence', pa.float64())
])


def calculate_freshness_penalty(extraction_timestamp: datetime, reference_time: datetime) -> float:
    """
    Calculate graduated freshness penalty based on evidence age.

    Penalty schedule (per approved data model):
    - 0-24 months: 0.0
    - 25-36 months: 0.1
    - 37-48 months: 0.2
    - >48 months: 0.3

    Args:
        extraction_timestamp: When evidence was extracted
        reference_time: Current time for age calculation

    Returns:
        Freshness penalty (0.0 - 0.3)
    """
    # Calculate age in months
    age_days = (reference_time - extraction_timestamp).days
    age_months = age_days / 30.0  # Approximate

    if age_months <= 24:
        return 0.0
    elif age_months <= 36:
        return 0.1
    elif age_months <= 48:
        return 0.2
    else:
        return 0.3


def deduplicate_evidence(bronze_df):
    """
    Deduplicate evidence DataFrame.

    Deduplication logic (per approved data model):
    - Group by: hash_sha256, org_id, year
    - Sort by: confidence DESC, extraction_timestamp DESC
    - Keep: First row (highest confidence, most recent if tied)

    Args:
        bronze_df: DuckDB DataFrame from bronze layer

    Returns:
        Deduplicated DataFrame
    """
    # This is a placeholder - actual implementation uses SQL in normalize method
    pass


class SilverNormalizer:
    """
    Normalize bronze evidence to silver layer.

    Responsibilities:
    - Deduplicate evidence (confidence-first, then recency)
    - Calculate freshness penalties
    - Calculate adjusted confidence
    - Mark most recent records
    - Write to silver Parquet with same partitioning
    """

    def __init__(self, db_path: Path, bronze_path: Path, silver_path: Path):
        """
        Initialize silver normalizer.

        Args:
            db_path: Path to DuckDB database
            bronze_path: Path to bronze Parquet directory
            silver_path: Path to silver Parquet directory
        """
        self.db_path = Path(db_path)
        self.bronze_path = Path(bronze_path)
        self.silver_path = Path(silver_path)
        self.silver_path.mkdir(parents=True, exist_ok=True)

    def normalize_bronze_to_silver(self) -> None:
        """
        Normalize all bronze evidence to silver layer.

        Process:
        1. Read bronze Parquet files
        2. Deduplicate (confidence DESC, extraction_timestamp DESC)
        3. Calculate freshness penalties
        4. Calculate adjusted confidence
        5. Add is_most_recent flag
        6. Write to silver Parquet with same partitioning
        """
        con = duckdb.connect(str(self.db_path))

        try:
            # Check if bronze has any data
            bronze_pattern = str(self.bronze_path / "**" / "*.parquet")

            try:
                # Read bronze data
                con.execute(f"""
                    CREATE OR REPLACE TEMP TABLE bronze_raw AS
                    SELECT * FROM read_parquet(
                        '{bronze_pattern}',
                        hive_partitioning = true,
                        union_by_name = true
                    )
                """)
            except Exception as e:
                if "No files found" in str(e):
                    # No bronze data to normalize
                    return
                raise

            # Deduplicate: Keep highest confidence, then most recent
            con.execute("""
                CREATE OR REPLACE TEMP TABLE deduplicated AS
                SELECT
                    *,
                    ROW_NUMBER() OVER (
                        PARTITION BY hash_sha256, org_id, year
                        ORDER BY confidence DESC, extraction_timestamp DESC
                    ) AS rn
                FROM bronze_raw
            """)

            con.execute("""
                CREATE OR REPLACE TEMP TABLE bronze_deduped AS
                SELECT * EXCLUDE (rn)
                FROM deduplicated
                WHERE rn = 1
            """)

            # Calculate freshness penalty and adjusted confidence
            now = datetime.now(UTC)
            con.execute(f"""
                CREATE OR REPLACE TEMP TABLE silver_normalized AS
                SELECT
                    *,
                    TRUE AS is_most_recent,
                    CASE
                        WHEN DATEDIFF('month', extraction_timestamp, TIMESTAMP '{now.isoformat()}') > 48 THEN 0.3
                        WHEN DATEDIFF('month', extraction_timestamp, TIMESTAMP '{now.isoformat()}') > 36 THEN 0.2
                        WHEN DATEDIFF('month', extraction_timestamp, TIMESTAMP '{now.isoformat()}') > 24 THEN 0.1
                        ELSE 0.0
                    END AS freshness_penalty
                FROM bronze_deduped
            """)

            con.execute("""
                CREATE OR REPLACE TEMP TABLE silver_final AS
                SELECT
                    *,
                    GREATEST(0.0, confidence - freshness_penalty) AS adjusted_confidence
                FROM silver_normalized
            """)

            # Get all unique partitions
            partitions = con.execute("""
                SELECT DISTINCT org_id, year, theme
                FROM silver_final
            """).fetchall()

            # Write each partition separately (Hive partitioning)
            for org_id, year, theme in partitions:
                partition_df = con.execute("""
                    SELECT * FROM silver_final
                    WHERE org_id = ? AND year = ? AND theme = ?
                """, [org_id, year, theme]).fetchdf()

                # Convert to PyArrow table
                table = pa.Table.from_pandas(
                    partition_df,
                    schema=SILVER_SCHEMA,
                    preserve_index=False
                )

                # Create partition directory
                partition_path = (
                    self.silver_path /
                    f"org_id={org_id}" /
                    f"year={year}" /
                    f"theme={theme}"
                )
                partition_path.mkdir(parents=True, exist_ok=True)

                # Write Parquet file
                # Use timestamp to avoid conflicts if run multiple times
                timestamp_str = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
                filename = f"part-{timestamp_str}.parquet"
                file_path = partition_path / filename

                pq.write_table(
                    table,
                    file_path,
                    compression='snappy',
                    use_dictionary=True,
                    write_statistics=True
                )

        finally:
            con.close()
