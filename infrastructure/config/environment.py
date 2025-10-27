"""
Environment configuration and validation for ESG infrastructure
Critical Path: This module validates all required environment variables
"""
import os
from typing import Dict, List, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass


@dataclass
class InfrastructureConfig:
    """Configuration for infrastructure services"""

    # MinIO (S3-compatible storage)
    minio_endpoint: str
    minio_access_key: str
    minio_secret_key: str
    minio_bucket: str

    # Iceberg Catalog
    iceberg_catalog_uri: str
    iceberg_warehouse: str

    # Trino Query Engine
    trino_host: str
    trino_port: int
    trino_catalog: str

    # Cloud Services (existing)
    watsonx_api_key: Optional[str]
    watsonx_project_id: Optional[str]
    watsonx_url: str
    astradb_token: Optional[str]
    astradb_endpoint: Optional[str]


def get_infrastructure_config() -> InfrastructureConfig:
    """
    Get infrastructure configuration from environment variables.

    Returns:
        InfrastructureConfig with all required settings

    Raises:
        ValueError: If required environment variables are missing
    """
    # Local infrastructure (required)
    minio_endpoint = os.getenv('MINIO_ENDPOINT', 'http://localhost:9000')
    minio_access_key = os.getenv('MINIO_ACCESS_KEY', 'minioadmin')
    minio_secret_key = os.getenv('MINIO_SECRET_KEY', 'minioadmin')
    minio_bucket = os.getenv('MINIO_BUCKET', 'esg-lake')

    iceberg_catalog_uri = os.getenv('ICEBERG_CATALOG_URI', 'http://localhost:8181')
    iceberg_warehouse = os.getenv('ICEBERG_WAREHOUSE', 's3://esg-lake/')

    trino_host = os.getenv('TRINO_HOST', 'localhost')
    trino_port = int(os.getenv('TRINO_PORT', '8080'))
    trino_catalog = os.getenv('TRINO_CATALOG', 'iceberg')

    # Cloud services (optional - can be None for local-only testing)
    watsonx_api_key = os.getenv('WATSONX_API_KEY')
    watsonx_project_id = os.getenv('WATSONX_PROJECT_ID')
    watsonx_url = os.getenv('WATSONX_URL', 'https://us-south.ml.cloud.ibm.com')

    astradb_token = os.getenv('ASTRADB_TOKEN')
    astradb_endpoint = os.getenv('ASTRADB_ENDPOINT')

    return InfrastructureConfig(
        minio_endpoint=minio_endpoint,
        minio_access_key=minio_access_key,
        minio_secret_key=minio_secret_key,
        minio_bucket=minio_bucket,
        iceberg_catalog_uri=iceberg_catalog_uri,
        iceberg_warehouse=iceberg_warehouse,
        trino_host=trino_host,
        trino_port=trino_port,
        trino_catalog=trino_catalog,
        watsonx_api_key=watsonx_api_key,
        watsonx_project_id=watsonx_project_id,
        watsonx_url=watsonx_url,
        astradb_token=astradb_token,
        astradb_endpoint=astradb_endpoint
    )


def validate_environment() -> Tuple[bool, List[str]]:
    """
    Validate that all required environment variables are set.

    Returns:
        Tuple of (is_valid, list_of_issues)
    """
    issues = []

    try:
        config = get_infrastructure_config()

        # Validate MinIO configuration
        if not config.minio_endpoint:
            issues.append("MINIO_ENDPOINT is not set")
        if not config.minio_access_key:
            issues.append("MINIO_ACCESS_KEY is not set")
        if not config.minio_secret_key:
            issues.append("MINIO_SECRET_KEY is not set")

        # Validate Iceberg configuration
        if not config.iceberg_catalog_uri:
            issues.append("ICEBERG_CATALOG_URI is not set")
        if not config.iceberg_warehouse:
            issues.append("ICEBERG_WAREHOUSE is not set")

        # Validate Trino configuration
        if not config.trino_host:
            issues.append("TRINO_HOST is not set")
        if config.trino_port <= 0 or config.trino_port > 65535:
            issues.append(f"TRINO_PORT invalid: {config.trino_port}")

    except Exception as e:
        issues.append(f"Configuration error: {str(e)}")

    return len(issues) == 0, issues


def create_env_template(output_path: Optional[Path] = None) -> str:
    """
    Create a .env.template file with all required variables.

    Args:
        output_path: Optional path to write template file

    Returns:
        Template content as string
    """
    template = """# ESG Infrastructure Environment Variables

# MinIO (S3-compatible local storage)
MINIO_ENDPOINT=http://localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET=esg-lake

# Iceberg Catalog
ICEBERG_CATALOG_URI=http://localhost:8181
ICEBERG_WAREHOUSE=s3://esg-lake/

# Trino Query Engine
TRINO_HOST=localhost
TRINO_PORT=8080
TRINO_CATALOG=iceberg

# watsonx.ai (Cloud Service - REQUIRED for scoring)
WATSONX_API_KEY=your_api_key_here
WATSONX_PROJECT_ID=your_project_id_here
WATSONX_URL=https://us-south.ml.cloud.ibm.com

# AstraDB (Cloud Service - REQUIRED for vector/graph)
ASTRADB_TOKEN=your_token_here
ASTRADB_ENDPOINT=your_endpoint_here
"""

    if output_path:
        output_path.write_text(template)

    return template
