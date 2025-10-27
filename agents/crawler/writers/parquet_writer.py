"""
Parquet Writer for Bronze Layer
Critical Path: Writes extracted data to MinIO in Parquet format
"""
from typing import Dict, Any, Optional
from datetime import datetime
import logging
import pyarrow as pa  # type: ignore
import pyarrow.parquet as pq  # type: ignore
from io import BytesIO
import uuid
from libs.utils.clock import get_clock
clock = get_clock()

logger = logging.getLogger(__name__)


class ParquetWriter:
    """
    Write extracted data to Parquet format in MinIO bronze layer

    Schema:
    - org_id: string
    - year: int32
    - doc_id: string
    - source_url: string
    - doc_type: string (pdf|html|pptx)
    - extraction_timestamp: timestamp[us]
    - sha256: string
    - page_count: int32
    - raw_text: large_string
    - tables: list<struct>
    - figures: list<struct>
    - metadata: map<string, string>
    """

    # Define bronze layer schema
    BRONZE_SCHEMA = pa.schema([
        ('org_id', pa.string()),
        ('year', pa.int32()),
        ('doc_id', pa.string()),
        ('source_url', pa.string()),
        ('doc_type', pa.string()),
        ('extraction_timestamp', pa.timestamp('us')),
        ('sha256', pa.string()),
        ('page_count', pa.int32()),
        ('raw_text', pa.large_string()),
        ('tables', pa.list_(pa.struct([
            ('page', pa.int32()),
            ('table_index', pa.int32()),
            ('data', pa.large_string()),
            ('row_count', pa.int32()),
            ('col_count', pa.int32())
        ]))),
        ('figures', pa.list_(pa.struct([
            ('page', pa.int32()),
            ('image_index', pa.int32()),
            ('xref', pa.int32()),
            ('width', pa.int32()),
            ('height', pa.int32())
        ]))),
        ('metadata', pa.map_(pa.string(), pa.string()))
    ])

    def __init__(self, minio_endpoint: str, access_key: str,
                 secret_key: str, bucket: str):
        """
        Initialize Parquet writer

        Args:
            minio_endpoint: MinIO endpoint (e.g., 'localhost:9000')
            access_key: MinIO access key
            secret_key: MinIO secret key
            bucket: S3 bucket name
        """
        self.minio_endpoint = minio_endpoint
        self.access_key = access_key
        self.secret_key = secret_key
        self.bucket = bucket

        # Initialize MinIO client
        self.client = self._init_minio_client()

        logger.info(f"Initialized Parquet Writer (bucket: {bucket})")

    def _init_minio_client(self) -> Any:
        """Initialize MinIO client"""
        try:
            from minio import Minio

            # Remove http:// prefix if present
            endpoint = self.minio_endpoint
            if endpoint.startswith('http://'):
                endpoint = endpoint[7:]
                secure = False
            elif endpoint.startswith('https://'):
                endpoint = endpoint[8:]
                secure = True
            else:
                secure = False

            client = Minio(
                endpoint,
                access_key=self.access_key,
                secret_key=self.secret_key,
                secure=secure
            )

            return client

        except ImportError:
            logger.error("minio package not installed")
            raise
        except Exception as e:
            logger.error(f"Error initializing MinIO client: {e}")
            raise

    def validate_schema(self, data: Dict[str, Any]) -> bool:
        """
        Validate data conforms to bronze schema

        Args:
            data: Data to validate

        Returns:
            True if valid, False otherwise
        """
        required_fields = [
            'org_id', 'year', 'doc_id', 'source_url', 'doc_type',
            'extraction_timestamp', 'sha256', 'page_count', 'raw_text'
        ]

        for field in required_fields:
            if field not in data:
                logger.error(f"Missing required field: {field}")
                return False

        # Type validation
        try:
            assert isinstance(data['org_id'], str)
            assert isinstance(data['year'], int)
            assert isinstance(data['doc_id'], str)
            assert isinstance(data['page_count'], int)
            assert isinstance(data['sha256'], str)
            assert len(data['sha256']) == 64  # SHA256 hex length

            return True
        except (AssertionError, TypeError) as e:
            logger.error(f"Schema validation failed: {e}")
            return False

    def generate_path(self, org_id: str, year: int, doc_id: str) -> str:
        """
        Generate S3 path for Parquet file

        Format: bronze/{org_id}/{year}/{doc_id}/raw.parquet

        Args:
            org_id: Organization identifier
            year: Reporting year
            doc_id: Document identifier

        Returns:
            S3 object key path
        """
        return f"bronze/{org_id}/{year}/{doc_id}/raw.parquet"

    def write(self, data: Dict[str, Any], atomic: bool = True) -> bool:
        """
        Write data to Parquet format in MinIO

        Args:
            data: Data conforming to bronze schema
            atomic: Perform atomic write with validation

        Returns:
            True if successful, False otherwise
        """
        try:
            # Validate schema
            if not self.validate_schema(data):
                logger.error("Schema validation failed")
                return False

            # Prepare data for PyArrow
            arrow_data = self._prepare_arrow_data(data)

            # Create PyArrow table
            table = pa.Table.from_pydict(arrow_data, schema=self.BRONZE_SCHEMA)

            # Write to Parquet in memory
            buffer = BytesIO()
            pq.write_table(
                table,
                buffer,
                compression='zstd',
                compression_level=3,
                use_dictionary=True
            )

            # Get Parquet bytes
            parquet_bytes = buffer.getvalue()
            buffer.close()

            # Generate S3 path
            s3_path = self.generate_path(
                data['org_id'],
                data['year'],
                data['doc_id']
            )

            # Write to MinIO
            self.client.put_object(
                self.bucket,
                s3_path,
                BytesIO(parquet_bytes),
                length=len(parquet_bytes),
                content_type='application/octet-stream'
            )

            logger.info(f"Successfully wrote Parquet to {s3_path}")
            return True

        except Exception as e:
            logger.error(f"Error writing Parquet: {e}")
            if atomic:
                # Atomic write failed, no partial data written
                return False
            raise

    def _prepare_arrow_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare data for PyArrow (convert to columnar format)"""
        # Convert tables to serialized format if needed
        tables_serialized = []
        for table in data.get('tables', []):
            # Convert table data to string for storage
            table_copy = table.copy()
            if 'data' in table_copy and not isinstance(table_copy['data'], str):
                import json
                table_copy['data'] = json.dumps(table_copy['data'])
            tables_serialized.append(table_copy)

        # Ensure extraction_timestamp is datetime
        extraction_ts = data.get('extraction_timestamp')
        if not isinstance(extraction_ts, datetime):
            extraction_ts = clock.now()

        # Convert metadata to dict if needed
        metadata = data.get('metadata', {})
        if not isinstance(metadata, dict):
            metadata = {}

        return {
            'org_id': [data['org_id']],
            'year': [data['year']],
            'doc_id': [data['doc_id']],
            'source_url': [data['source_url']],
            'doc_type': [data['doc_type']],
            'extraction_timestamp': [extraction_ts],
            'sha256': [data['sha256']],
            'page_count': [data['page_count']],
            'raw_text': [data['raw_text']],
            'tables': [tables_serialized],
            'figures': [data.get('figures', [])],
            'metadata': [list(metadata.items())]
        }
