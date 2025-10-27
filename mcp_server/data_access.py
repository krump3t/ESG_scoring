"""
Data Access Layer for MCP Server
Critical Path: Real queries to MinIO/Parquet bronze/silver/gold layers
NO MOCKS - All data from actual storage
"""
from typing import List, Dict, Any, Optional
import logging
from io import BytesIO
import pyarrow.parquet as pq  # type: ignore
from minio import Minio

logger = logging.getLogger(__name__)


class DataAccessLayer:
    """
    Data access layer for querying real Parquet data from MinIO

    NO synthetic data - all queries hit actual MinIO storage
    """

    def __init__(self, minio_endpoint: str = 'localhost:9000',
                 access_key: str = 'minioadmin',
                 secret_key: str = 'minioadmin',
                 bucket: str = 'esg-lake'):
        """Initialize MinIO client for real data access"""
        self.minio_endpoint = minio_endpoint
        self.bucket = bucket

        self.client = Minio(
            minio_endpoint,
            access_key=access_key,
            secret_key=secret_key,
            secure=False
        )

        logger.info(f"Initialized DataAccessLayer for bucket: {bucket}")

    def query_bronze_documents(self, org_id: str, year: int) -> List[Dict[str, Any]]:
        """
        Query bronze layer for raw documents

        Returns actual Parquet data from MinIO, no mocks
        """
        prefix = f"bronze/{org_id}/{year}/"

        logger.info(f"Querying bronze layer: {prefix}")

        documents = []

        try:
            objects = self.client.list_objects(self.bucket, prefix=prefix, recursive=True)

            for obj in objects:
                if obj.object_name.endswith('.parquet'):
                    # Read actual Parquet file
                    doc_data = self._read_parquet_object(obj.object_name)
                    if doc_data:
                        documents.append(doc_data)

            logger.info(f"Found {len(documents)} bronze documents for {org_id}/{year}")

        except Exception as e:
            logger.error(f"Error querying bronze layer: {e}")

        return documents

    def query_silver_findings(self, org_id: str, year: int,
                             theme: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Query silver layer for normalized findings

        Returns actual findings from silver Parquet files
        """
        # Silver layer would be partitioned: silver/org_id={org}/year={year}/theme={theme}/
        # For now, check if silver data exists
        prefix = f"silver/org_id={org_id}/year={year}/"

        logger.info(f"Querying silver layer: {prefix}")

        findings = []

        try:
            objects = self.client.list_objects(self.bucket, prefix=prefix, recursive=True)

            for obj in objects:
                if obj.object_name.endswith('.parquet'):
                    # Read actual Parquet file
                    finding_data = self._read_parquet_object(obj.object_name)
                    if finding_data:
                        # Filter by theme if specified
                        if theme is None or finding_data.get('theme') == theme:
                            findings.append(finding_data)

            logger.info(f"Found {len(findings)} silver findings")

        except Exception as e:
            logger.error(f"Error querying silver layer: {e}")

        return findings

    def query_gold_scores(self, org_id: str, year: int,
                         theme: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Query gold layer for maturity scores

        Returns actual scores from gold Parquet files
        """
        # Gold layer: gold/org_id={org}/year={year}/theme={theme}/
        prefix = f"gold/org_id={org_id}/year={year}/"

        logger.info(f"Querying gold layer: {prefix}")

        scores = []

        try:
            objects = self.client.list_objects(self.bucket, prefix=prefix, recursive=True)

            for obj in objects:
                if obj.object_name.endswith('.parquet'):
                    # Read actual Parquet file
                    score_data = self._read_parquet_object(obj.object_name)
                    if score_data:
                        # Filter by theme if specified
                        if theme is None or score_data.get('theme') == theme:
                            scores.append(score_data)

            logger.info(f"Found {len(scores)} gold scores")

        except Exception as e:
            logger.error(f"Error querying gold layer: {e}")

        return scores

    def _read_parquet_object(self, object_name: str) -> Optional[Dict[str, Any]]:
        """
        Read Parquet file from MinIO and return as dictionary

        Reads actual file bytes, no mocks
        """
        try:
            # Get object from MinIO
            response = self.client.get_object(self.bucket, object_name)

            # Read bytes
            parquet_bytes = response.read()
            response.close()
            response.release_conn()

            # Parse Parquet
            parquet_file = pq.read_table(BytesIO(parquet_bytes))

            # Convert to dict (first row if table has rows)
            if parquet_file.num_rows > 0:
                # Convert to pandas then to dict for first row
                df = parquet_file.to_pandas()
                return df.iloc[0].to_dict()

            return None

        except Exception as e:
            logger.error(f"Error reading Parquet object {object_name}: {e}")
            return None

    def write_gold_scores(self, org_id: str, year: int, theme: str,
                         scores: List[Dict[str, Any]]) -> bool:
        """
        Write scores to gold layer

        Writes actual Parquet files to MinIO
        """
        if not scores:
            logger.warning("No scores to write")
            return False

        try:
            from iceberg.tables.gold_schema import GoldSchema
            import pyarrow as pa  # type: ignore

            # Prepare scores
            prepared_scores = GoldSchema.prepare_score_data(scores)

            # Convert to PyArrow table
            table = pa.Table.from_pydict(
                {key: [score[key] for score in prepared_scores] for key in prepared_scores[0].keys()},
                schema=GoldSchema.SCHEMA
            )

            # Write to Parquet bytes
            buffer = BytesIO()
            pq.write_table(
                table,
                buffer,
                compression='zstd',
                compression_level=3
            )

            # Generate path
            object_name = f"gold/org_id={org_id}/year={year}/theme={theme}/scores.parquet"

            # Write to MinIO
            buffer.seek(0)
            self.client.put_object(
                self.bucket,
                object_name,
                buffer,
                length=len(buffer.getvalue()),
                content_type='application/octet-stream'
            )

            logger.info(f"Wrote {len(scores)} scores to {object_name}")
            return True

        except Exception as e:
            logger.error(f"Error writing gold scores: {e}")
            return False

    def write_silver_findings(self, org_id: str, year: int, theme: str,
                             findings: List[Dict[str, Any]]) -> bool:
        """
        Write findings to silver layer

        Writes actual Parquet files to MinIO
        """
        if not findings:
            logger.warning("No findings to write")
            return False

        try:
            from iceberg.tables.silver_schema import SilverSchema
            import pyarrow as pa  # type: ignore

            # Prepare findings
            prepared_findings = SilverSchema.prepare_merge_data(findings)

            # Convert to PyArrow table
            table = pa.Table.from_pydict(
                {key: [finding[key] for finding in prepared_findings] for key in prepared_findings[0].keys()},
                schema=SilverSchema.SCHEMA
            )

            # Write to Parquet bytes
            buffer = BytesIO()
            pq.write_table(
                table,
                buffer,
                compression='zstd',
                compression_level=3
            )

            # Generate path
            object_name = f"silver/org_id={org_id}/year={year}/theme={theme}/findings.parquet"

            # Write to MinIO
            buffer.seek(0)
            self.client.put_object(
                self.bucket,
                object_name,
                buffer,
                length=len(buffer.getvalue()),
                content_type='application/octet-stream'
            )

            logger.info(f"Wrote {len(findings)} findings to {object_name}")
            return True

        except Exception as e:
            logger.error(f"Error writing silver findings: {e}")
            return False
