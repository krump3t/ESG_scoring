"""
Bronze Evidence Writer for Parquet Storage

Writes Evidence objects to Parquet files with Hive partitioning.
Implements approved data model design (Parquet + DuckDB views).

Part of Task 008 - ESG Data Extraction vertical slice (Option 1).
"""

from typing import List
from pathlib import Path
from datetime import datetime, UTC
import pyarrow as pa
import pyarrow.parquet as pq
from dataclasses import asdict

from agents.parser.models import Evidence


# Parquet schema matching ESG Rubric v3.0 requirements (lines 116-122)
EVIDENCE_SCHEMA = pa.schema([
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
    ('ingestion_id', pa.string())
])


def generate_s3_uri(org_id: str, year: int, doc_id: str) -> str:
    """
    Generate S3 URI for document manifest.

    Args:
        org_id: Organization identifier (CIK or ticker)
        year: Fiscal year
        doc_id: Document identifier (e.g., SEC accession number)

    Returns:
        S3 URI string (e.g., s3://esg-reports/MSFT/2023/0000891020-23-000077.pdf)
    """
    return f"s3://esg-reports/{org_id}/{year}/{doc_id}.pdf"


def validate_evidence_constraints(evidence: Evidence) -> None:
    """
    Validate evidence against data model constraints.

    Raises:
        ValueError: If any constraint is violated

    Constraints (from data_model.md):
    - theme IN {TSP, OSP, DM, GHG, RD, EI, RMM}
    - stage_indicator BETWEEN 0 AND 4
    - confidence BETWEEN 0.0 AND 1.0
    - year BETWEEN 1900 AND 2100
    - span_end > span_start
    - page_no >= 1
    """
    VALID_THEMES = {'TSP', 'OSP', 'DM', 'GHG', 'RD', 'EI', 'RMM'}

    # Theme validation
    if evidence.theme not in VALID_THEMES:
        raise ValueError(
            f"Invalid theme: {evidence.theme}. "
            f"Must be one of {VALID_THEMES}"
        )

    # Stage validation
    if not (0 <= evidence.stage_indicator <= 4):
        raise ValueError(
            f"Stage must be 0-4, got {evidence.stage_indicator}"
        )

    # Confidence validation
    if not (0.0 <= evidence.confidence <= 1.0):
        raise ValueError(
            f"Confidence must be 0.0-1.0, got {evidence.confidence}"
        )

    # Year validation
    if not (1900 <= evidence.year <= 2100):
        raise ValueError(
            f"Year out of range: {evidence.year}"
        )

    # Span validation
    if evidence.span_end <= evidence.span_start:
        raise ValueError(
            f"span_end must be > span_start, got "
            f"start={evidence.span_start}, end={evidence.span_end}"
        )

    # Page number validation
    if evidence.page_no < 1:
        raise ValueError(
            f"page_no must be >= 1, got {evidence.page_no}"
        )


class BronzeEvidenceWriter:
    """
    Write Evidence objects to Parquet files with Hive partitioning.

    Storage structure:
    bronze/
      org_id=MSFT/
        year=2023/
          theme=GHG/
            part-001.parquet
            part-002.parquet

    Features:
    - Hive-style partitioning for partition pruning
    - Append mode (preserves existing data)
    - Automatic timestamp and ingestion_id injection
    - Schema validation before write
    """

    def __init__(self, base_path: Path):
        """
        Initialize bronze writer.

        Args:
            base_path: Root directory for bronze layer (e.g., data/bronze)
        """
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

    def write_evidence_batch(
        self,
        evidence_list: List[Evidence],
        ingestion_id: str
    ) -> None:
        """
        Write batch of evidence to Parquet with Hive partitioning.

        Args:
            evidence_list: List of Evidence objects to write
            ingestion_id: Unique identifier for this ingestion batch

        Raises:
            ValueError: If any evidence violates constraints
        """
        if not evidence_list:
            return  # Nothing to write

        # Validate all evidence before writing
        for evidence in evidence_list:
            validate_evidence_constraints(evidence)

        # Group evidence by partition (org_id, year, theme)
        partitions = {}
        for evidence in evidence_list:
            partition_key = (evidence.org_id, evidence.year, evidence.theme)
            if partition_key not in partitions:
                partitions[partition_key] = []
            partitions[partition_key].append(evidence)

        # Write each partition separately
        current_time = datetime.now(UTC)
        for (org_id, year, theme), partition_evidence in partitions.items():
            self._write_partition(
                evidence_list=partition_evidence,
                org_id=org_id,
                year=year,
                theme=theme,
                ingestion_id=ingestion_id,
                current_time=current_time
            )

    def _write_partition(
        self,
        evidence_list: List[Evidence],
        org_id: str,
        year: int,
        theme: str,
        ingestion_id: str,
        current_time: datetime
    ) -> None:
        """
        Write evidence to a specific partition.

        Args:
            evidence_list: Evidence for this partition
            org_id: Organization ID (partition key)
            year: Year (partition key)
            theme: Theme (partition key)
            ingestion_id: Batch identifier
            current_time: Timestamp for created_at
        """
        # Create partition directory: org_id=X/year=Y/theme=Z/
        partition_path = (
            self.base_path /
            f"org_id={org_id}" /
            f"year={year}" /
            f"theme={theme}"
        )
        partition_path.mkdir(parents=True, exist_ok=True)

        # Convert Evidence objects to records
        records = []
        for evidence in evidence_list:
            # Generate S3 URI for doc_manifest_uri
            doc_manifest_uri = generate_s3_uri(org_id, year, evidence.doc_id)

            record = {
                'evidence_id': evidence.evidence_id,
                'org_id': evidence.org_id,
                'year': evidence.year,
                'theme': evidence.theme,
                'stage_indicator': evidence.stage_indicator,
                'doc_id': evidence.doc_id,
                'page_no': evidence.page_no,
                'span_start': evidence.span_start,
                'span_end': evidence.span_end,
                'extract_30w': evidence.extract_30w,
                'hash_sha256': evidence.hash_sha256,
                'snapshot_id': evidence.snapshot_id,
                'confidence': evidence.confidence,
                'evidence_type': evidence.evidence_type,
                'extraction_timestamp': current_time,
                'doc_manifest_uri': doc_manifest_uri,
                'filing_url': '',  # TODO: Add from ExtractionResult metadata
                'schema_version': 1,
                'created_at': current_time,
                'ingestion_id': ingestion_id
            }
            records.append(record)

        # Convert to PyArrow table
        table = pa.Table.from_pylist(records, schema=EVIDENCE_SCHEMA)

        # Generate unique filename for this batch
        # Use timestamp + ingestion_id to ensure uniqueness
        timestamp_str = current_time.strftime("%Y%m%d_%H%M%S")
        filename = f"part-{timestamp_str}-{ingestion_id}.parquet"
        file_path = partition_path / filename

        # Write Parquet file (append mode: don't overwrite)
        # Note: use_dictionary=False to prevent schema mismatch when merging files
        pq.write_table(
            table,
            file_path,
            compression='snappy',
            use_dictionary=False,
            write_statistics=True
        )
