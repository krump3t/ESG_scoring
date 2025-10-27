"""
Main infrastructure initialization script
Critical Path: This is the primary entry point for setting up all infrastructure
"""
import sys
import logging
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from infrastructure.config.environment import get_infrastructure_config, validate_environment
from infrastructure.storage.minio_setup import MinIOSetup
from infrastructure.iceberg.catalog_init import IcebergCatalogManager
from infrastructure.health.check_all import check_all_services, wait_for_services

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)


def initialize_infrastructure() -> bool:
    """
    Initialize all infrastructure components.

    Returns:
        True if initialization successful, False otherwise
    """
    logger.info("=" * 80)
    logger.info(" ESG INFRASTRUCTURE INITIALIZATION")
    logger.info("=" * 80)

    # Step 1: Validate environment
    logger.info("\n1. VALIDATING ENVIRONMENT")
    logger.info("-" * 80)

    is_valid, issues = validate_environment()
    if not is_valid:
        logger.error("Environment validation failed:")
        for issue in issues:
            logger.error(f"  - {issue}")
        return False

    logger.info("  [OK] Environment validation passed")

    # Step 2: Load configuration
    logger.info("\n2. LOADING CONFIGURATION")
    logger.info("-" * 80)

    try:
        config = get_infrastructure_config()
        logger.info(f"  MinIO endpoint: {config.minio_endpoint}")
        logger.info(f"  Iceberg catalog: {config.iceberg_catalog_uri}")
        logger.info(f"  Trino endpoint: {config.trino_host}:{config.trino_port}")
        logger.info("  [OK] Configuration loaded")
    except Exception as e:
        logger.error(f"  [FAIL] Configuration error: {e}")
        return False

    # Step 3: Wait for services
    logger.info("\n3. WAITING FOR SERVICES")
    logger.info("-" * 80)

    config_dict = {
        'minio_endpoint': config.minio_endpoint,
        'minio_access_key': config.minio_access_key,
        'minio_secret_key': config.minio_secret_key,
        'iceberg_catalog_uri': config.iceberg_catalog_uri,
        'trino_host': config.trino_host,
        'trino_port': config.trino_port,
        'watsonx_api_key': config.watsonx_api_key,
        'watsonx_project_id': config.watsonx_project_id,
        'watsonx_url': config.watsonx_url,
        'astradb_token': config.astradb_token,
        'astradb_endpoint': config.astradb_endpoint
    }

    if not wait_for_services(config_dict, timeout=120):
        logger.error("  [FAIL] Services did not become healthy in time")
        return False

    logger.info("  [OK] All services healthy")

    # Step 4: Initialize MinIO buckets
    logger.info("\n4. INITIALIZING MINIO BUCKETS")
    logger.info("-" * 80)

    try:
        minio = MinIOSetup(
            config.minio_endpoint,
            config.minio_access_key,
            config.minio_secret_key
        )

        if not minio.setup_esg_buckets():
            logger.error("  [FAIL] Failed to create MinIO buckets")
            return False

        buckets = minio.list_buckets()
        logger.info(f"  Buckets: {', '.join(buckets)}")
        logger.info("  [OK] MinIO buckets initialized")
    except Exception as e:
        logger.error(f"  [FAIL] MinIO setup error: {e}")
        return False

    # Step 5: Initialize Iceberg namespaces
    logger.info("\n5. INITIALIZING ICEBERG NAMESPACES")
    logger.info("-" * 80)

    try:
        iceberg = IcebergCatalogManager(
            config.iceberg_catalog_uri,
            config.iceberg_warehouse,
            config.minio_endpoint,
            config.minio_access_key,
            config.minio_secret_key
        )

        if not iceberg.setup_esg_namespaces():
            logger.error("  [FAIL] Failed to create Iceberg namespaces")
            return False

        namespaces = iceberg.list_namespaces()
        logger.info(f"  Namespaces: {', '.join(namespaces)}")
        logger.info("  [OK] Iceberg namespaces initialized")
    except Exception as e:
        logger.error(f"  [FAIL] Iceberg setup error: {e}")
        return False

    # Step 6: Final health check
    logger.info("\n6. FINAL HEALTH CHECK")
    logger.info("-" * 80)

    results = check_all_services(config_dict)
    failed = [svc for svc, (healthy, _) in results.items() if not healthy]

    if failed:
        logger.error(f"  [FAIL] Some services unhealthy: {', '.join(failed)}")
        return False

    logger.info("  [OK] All services healthy")

    # Success
    logger.info("\n" + "=" * 80)
    logger.info(" INFRASTRUCTURE INITIALIZATION COMPLETE")
    logger.info("=" * 80)
    logger.info("\nNext steps:")
    logger.info("  1. Verify buckets: http://localhost:9001 (MinIO console)")
    logger.info("  2. Verify Trino: http://localhost:8080 (Trino UI)")
    logger.info("  3. Test Iceberg catalog: Query namespaces via Trino")
    logger.info("\n" + "=" * 80)

    return True


if __name__ == "__main__":
    success = initialize_infrastructure()
    sys.exit(0 if success else 1)
