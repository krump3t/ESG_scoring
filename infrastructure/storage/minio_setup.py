"""
MinIO S3-compatible storage setup and management
Critical Path: This module handles bucket creation and S3 client initialization
"""
from typing import Dict, List, Optional
from minio import Minio
from minio.error import S3Error
import logging

logger = logging.getLogger(__name__)


class MinIOSetup:
    """Manages MinIO bucket setup and S3 client initialization"""

    def __init__(self, endpoint: str, access_key: str, secret_key: str, secure: bool = False):
        """
        Initialize MinIO client.

        Args:
            endpoint: MinIO endpoint (e.g., 'localhost:9000')
            access_key: MinIO access key
            secret_key: MinIO secret key
            secure: Whether to use HTTPS (default: False for local)
        """
        # Remove http:// or https:// prefix if present
        if endpoint.startswith('http://'):
            endpoint = endpoint[7:]
            secure = False
        elif endpoint.startswith('https://'):
            endpoint = endpoint[8:]
            secure = True

        self.client = Minio(
            endpoint,
            access_key=access_key,
            secret_key=secret_key,
            secure=secure
        )
        self.endpoint = endpoint

    def create_bucket(self, bucket_name: str) -> bool:
        """
        Create a bucket if it doesn't exist.

        Args:
            bucket_name: Name of bucket to create

        Returns:
            True if bucket created or already exists, False on error
        """
        try:
            if not self.client.bucket_exists(bucket_name):
                self.client.make_bucket(bucket_name)
                logger.info(f"Created bucket: {bucket_name}")
            else:
                logger.info(f"Bucket already exists: {bucket_name}")
            return True
        except S3Error as e:
            logger.error(f"Error creating bucket {bucket_name}: {e}")
            return False

    def create_buckets(self, bucket_names: List[str]) -> Dict[str, bool]:
        """
        Create multiple buckets.

        Args:
            bucket_names: List of bucket names to create

        Returns:
            Dict mapping bucket name to success status
        """
        results = {}
        for bucket_name in bucket_names:
            results[bucket_name] = self.create_bucket(bucket_name)
        return results

    def list_buckets(self) -> List[str]:
        """
        List all buckets.

        Returns:
            List of bucket names
        """
        try:
            buckets = self.client.list_buckets()
            return [bucket.name for bucket in buckets]
        except S3Error as e:
            logger.error(f"Error listing buckets: {e}")
            return []

    def bucket_exists(self, bucket_name: str) -> bool:
        """
        Check if a bucket exists.

        Args:
            bucket_name: Name of bucket to check

        Returns:
            True if bucket exists, False otherwise
        """
        try:
            return self.client.bucket_exists(bucket_name)
        except S3Error as e:
            logger.error(f"Error checking bucket {bucket_name}: {e}")
            return False

    def setup_esg_buckets(self) -> bool:
        """
        Set up standard ESG lake house buckets.

        Creates:
        - esg-lake (root bucket)

        Returns:
            True if all buckets created successfully
        """
        buckets = ['esg-lake']
        results = self.create_buckets(buckets)
        success = all(results.values())

        if success:
            logger.info("ESG buckets setup complete")
        else:
            failed = [name for name, status in results.items() if not status]
            logger.error(f"Failed to create buckets: {failed}")

        return success


def get_minio_client(endpoint: str, access_key: str, secret_key: str, secure: bool = False) -> Minio:
    """
    Factory function to get MinIO client.

    Args:
        endpoint: MinIO endpoint
        access_key: MinIO access key
        secret_key: MinIO secret key
        secure: Whether to use HTTPS

    Returns:
        Configured Minio client
    """
    # Remove http:// or https:// prefix
    if endpoint.startswith('http://'):
        endpoint = endpoint[7:]
        secure = False
    elif endpoint.startswith('https://'):
        endpoint = endpoint[8:]
        secure = True

    return Minio(endpoint, access_key=access_key, secret_key=secret_key, secure=secure)
