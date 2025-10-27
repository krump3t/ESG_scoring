"""
Iceberg catalog initialization and table management
Critical Path: This module handles Iceberg catalog connection and namespace creation
"""
from typing import Dict, List, Optional
from pyiceberg.catalog.rest import RestCatalog
from pyiceberg.exceptions import NamespaceAlreadyExistsError, NoSuchNamespaceError
import logging

logger = logging.getLogger(__name__)


class IcebergCatalogManager:
    """Manages Iceberg catalog operations"""

    def __init__(self, catalog_uri: str, warehouse: str, s3_endpoint: str,
                 access_key: str, secret_key: str):
        """
        Initialize Iceberg catalog manager.

        Args:
            catalog_uri: REST catalog URI (e.g., 'http://localhost:8181')
            warehouse: Warehouse location (e.g., 's3://esg-lake/')
            s3_endpoint: S3 endpoint for storage
            access_key: S3 access key
            secret_key: S3 secret key
        """
        self.catalog_uri = catalog_uri
        self.warehouse = warehouse

        # Initialize REST catalog
        self.catalog = RestCatalog(
            "esg",
            **{
                "uri": catalog_uri,
                "warehouse": warehouse,
                "s3.endpoint": s3_endpoint,
                "s3.access-key-id": access_key,
                "s3.secret-access-key": secret_key,
                "s3.path-style-access": "true"
            }
        )

    def create_namespace(self, namespace: str) -> bool:
        """
        Create a namespace (database) in the catalog.

        Args:
            namespace: Namespace name (e.g., 'bronze', 'silver', 'gold')

        Returns:
            True if created or already exists, False on error
        """
        try:
            self.catalog.create_namespace(namespace)
            logger.info(f"Created namespace: {namespace}")
            return True
        except NamespaceAlreadyExistsError:
            logger.info(f"Namespace already exists: {namespace}")
            return True
        except Exception as e:
            logger.error(f"Error creating namespace {namespace}: {e}")
            return False

    def list_namespaces(self) -> List[str]:
        """
        List all namespaces in the catalog.

        Returns:
            List of namespace names
        """
        try:
            namespaces = self.catalog.list_namespaces()
            return [str(ns) for ns in namespaces]
        except Exception as e:
            logger.error(f"Error listing namespaces: {e}")
            return []

    def namespace_exists(self, namespace: str) -> bool:
        """
        Check if a namespace exists.

        Args:
            namespace: Namespace name to check

        Returns:
            True if namespace exists, False otherwise
        """
        try:
            self.catalog.load_namespace_properties(namespace)
            return True
        except NoSuchNamespaceError:
            return False
        except Exception as e:
            logger.error(f"Error checking namespace {namespace}: {e}")
            return False

    def setup_esg_namespaces(self) -> bool:
        """
        Set up standard ESG namespaces: bronze, silver, gold.

        Returns:
            True if all namespaces created successfully
        """
        namespaces = ['bronze', 'silver', 'gold']
        results = {}

        for ns in namespaces:
            results[ns] = self.create_namespace(ns)

        success = all(results.values())

        if success:
            logger.info("ESG namespaces setup complete")
        else:
            failed = [ns for ns, status in results.items() if not status]
            logger.error(f"Failed to create namespaces: {failed}")

        return success

    def list_tables(self, namespace: str) -> List[str]:
        """
        List all tables in a namespace.

        Args:
            namespace: Namespace to list tables from

        Returns:
            List of table names
        """
        try:
            tables = self.catalog.list_tables(namespace)
            return [str(table) for table in tables]
        except Exception as e:
            logger.error(f"Error listing tables in {namespace}: {e}")
            return []


def get_catalog_manager(catalog_uri: str, warehouse: str, s3_endpoint: str,
                       access_key: str, secret_key: str) -> IcebergCatalogManager:
    """
    Factory function to get Iceberg catalog manager.

    Args:
        catalog_uri: REST catalog URI
        warehouse: Warehouse location
        s3_endpoint: S3 endpoint
        access_key: S3 access key
        secret_key: S3 secret key

    Returns:
        Configured IcebergCatalogManager
    """
    return IcebergCatalogManager(catalog_uri, warehouse, s3_endpoint, access_key, secret_key)
