"""
Silver Layer Schema - Iceberg Table for Normalized ESG Findings
Critical Path: Deduplication, normalization, and MERGE upserts
"""
from typing import Dict, Any, List, Optional
import logging
import pyarrow as pa  # type: ignore
from datetime import datetime
import hashlib

logger = logging.getLogger(__name__)


class SilverSchema:
    """
    Silver layer Iceberg table schema for normalized ESG findings

    Features:
    - Deduplication via finding_hash
    - Hidden partitioning on (org_id, year, theme)
    - Schema evolution support
    - ACID guarantees via Iceberg MERGE operations
    """

    # Silver layer schema - esg_normalized table
    SCHEMA = pa.schema([
        # Primary identifiers
        ('finding_id', pa.string()),  # UUID for finding
        ('finding_hash', pa.string()),  # SHA256 hash for deduplication

        # Source tracking
        ('org_id', pa.string()),  # Organization identifier
        ('year', pa.int32()),  # Reporting year
        ('source_doc_id', pa.string()),  # Reference to bronze layer doc
        ('page_number', pa.int32()),  # Page in source document

        # Content
        ('finding_text', pa.large_string()),  # Extracted finding text
        ('context', pa.large_string()),  # Surrounding context

        # Classification
        ('theme', pa.string()),  # ESG theme (E/S/G/Climate/etc)
        ('framework', pa.string()),  # Detected framework (SBTi/TCFD/GHG/etc)
        ('metric_type', pa.string()),  # Type of metric (target/actual/policy)

        # Extraction metadata
        ('extraction_method', pa.string()),  # chunking|table|full_text
        ('extraction_confidence', pa.float64()),  # 0.0-1.0
        ('extraction_timestamp', pa.timestamp('us')),

        # Normalization metadata
        ('normalized_timestamp', pa.timestamp('us')),
        ('dedup_cluster_id', pa.string()),  # For near-duplicate grouping

        # Iceberg metadata
        ('_inserted_at', pa.timestamp('us')),
        ('_updated_at', pa.timestamp('us')),
    ])

    @staticmethod
    def calculate_finding_hash(org_id: str, finding_text: str,
                               source_doc_id: str) -> str:
        """
        Calculate SHA256 hash for finding deduplication

        Args:
            org_id: Organization identifier
            finding_text: Finding text content
            source_doc_id: Source document ID

        Returns:
            SHA256 hash (hex) for deduplication
        """
        content = f"{org_id}|{finding_text}|{source_doc_id}"
        return hashlib.sha256(content.encode('utf-8')).hexdigest()

    @staticmethod
    def validate_finding(finding: Dict[str, Any]) -> bool:
        """
        Validate finding conforms to silver schema

        Args:
            finding: Finding data dictionary

        Returns:
            True if valid, False otherwise
        """
        required_fields = [
            'finding_id', 'finding_hash', 'org_id', 'year',
            'source_doc_id', 'finding_text', 'theme'
        ]

        for field in required_fields:
            if field not in finding:
                logger.error(f"Missing required field: {field}")
                return False

        # Type validation
        try:
            assert isinstance(finding['org_id'], str)
            assert isinstance(finding['year'], int)
            assert isinstance(finding['finding_hash'], str)
            assert len(finding['finding_hash']) == 64  # SHA256 hex length
            assert isinstance(finding['finding_text'], str)
            assert len(finding['finding_text']) > 0

            return True
        except (AssertionError, TypeError) as e:
            logger.error(f"Schema validation failed: {e}")
            return False

    @staticmethod
    def generate_partition_spec() -> Dict[str, str]:
        """
        Generate Iceberg partition specification

        Returns:
            Partition spec for hidden partitioning
        """
        return {
            'org_id': 'identity',  # Partition by organization
            'year': 'identity',  # Partition by year
            'theme': 'identity'  # Partition by ESG theme
        }

    @staticmethod
    def prepare_merge_data(findings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Prepare findings for MERGE upsert operation

        Args:
            findings: List of finding dictionaries

        Returns:
            Prepared findings with timestamps and validation
        """
        now = datetime.utcnow()
        prepared = []

        for finding in findings:
            # Validate
            if not SilverSchema.validate_finding(finding):
                logger.warning(f"Skipping invalid finding: {finding.get('finding_id', 'unknown')}")
                continue

            # Add Iceberg metadata
            finding['_inserted_at'] = now
            finding['_updated_at'] = now

            # Ensure normalized_timestamp
            if 'normalized_timestamp' not in finding:
                finding['normalized_timestamp'] = now

            prepared.append(finding)

        logger.info(f"Prepared {len(prepared)}/{len(findings)} findings for MERGE")
        return prepared

    @staticmethod
    def get_merge_condition() -> str:
        """
        Get MERGE condition for upsert operation

        Returns:
            SQL condition for matching records
        """
        return "target.finding_hash = source.finding_hash"

    @staticmethod
    def get_table_properties() -> Dict[str, str]:
        """
        Get Iceberg table properties for silver layer

        Returns:
            Table properties dict
        """
        return {
            'format-version': '2',
            'write.parquet.compression-codec': 'zstd',
            'write.parquet.compression-level': '3',
            'write.metadata.compression-codec': 'gzip',
            'commit.manifest.min-count-to-merge': '3',
            'commit.manifest-merge.enabled': 'true',
            'history.expire.max-snapshot-age-ms': str(30 * 24 * 60 * 60 * 1000),  # 30 days
        }
