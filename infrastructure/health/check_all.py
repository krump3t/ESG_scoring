"""
Comprehensive health check for all infrastructure services
Critical Path: This module validates that all services are operational
"""
from typing import Dict, List, Tuple
import requests
from minio import Minio
from minio.error import S3Error
import time
import logging
from libs.utils.clock import get_clock
clock = get_clock()

logger = logging.getLogger(__name__)


def check_minio(endpoint: str, access_key: str, secret_key: str, timeout: int = 5) -> Tuple[bool, str]:
    """
    Check MinIO health.

    Args:
        endpoint: MinIO endpoint
        access_key: Access key
        secret_key: Secret key
        timeout: Timeout in seconds

    Returns:
        Tuple of (is_healthy, status_message)
    """
    try:
        # Remove http:// prefix if present
        clean_endpoint = endpoint.replace('http://', '').replace('https://', '')

        client = Minio(clean_endpoint, access_key=access_key, secret_key=secret_key, secure=False)

        # Try to list buckets as health check
        buckets = client.list_buckets()
        return True, f"MinIO healthy - {len(buckets)} buckets"
    except S3Error as e:
        return False, f"MinIO error: {e}"
    except Exception as e:
        return False, f"MinIO unreachable: {e}"


def check_iceberg_catalog(catalog_uri: str, timeout: int = 5) -> Tuple[bool, str]:
    """
    Check Iceberg REST catalog health.

    Args:
        catalog_uri: Catalog URI
        timeout: Timeout in seconds

    Returns:
        Tuple of (is_healthy, status_message)
    """
    try:
        # Try to reach the catalog health endpoint
        response = requests.get(f"{catalog_uri}/v1/config", timeout=timeout)

        if response.status_code == 200:
            return True, "Iceberg catalog healthy"
        else:
            return False, f"Iceberg catalog returned status {response.status_code}"
    except requests.exceptions.Timeout:
        return False, "Iceberg catalog timeout"
    except requests.exceptions.ConnectionError:
        return False, "Iceberg catalog unreachable"
    except Exception as e:
        return False, f"Iceberg catalog error: {e}"


def check_trino(host: str, port: int, timeout: int = 5) -> Tuple[bool, str]:
    """
    Check Trino query engine health.

    Args:
        host: Trino host
        port: Trino port
        timeout: Timeout in seconds

    Returns:
        Tuple of (is_healthy, status_message)
    """
    try:
        # Check Trino health endpoint
        response = requests.get(f"http://{host}:{port}/v1/info", timeout=timeout)

        if response.status_code == 200:
            info = response.json()
            version = info.get('nodeVersion', {}).get('version', 'unknown')
            return True, f"Trino healthy - version {version}"
        else:
            return False, f"Trino returned status {response.status_code}"
    except requests.exceptions.Timeout:
        return False, "Trino timeout"
    except requests.exceptions.ConnectionError:
        return False, "Trino unreachable"
    except Exception as e:
        return False, f"Trino error: {e}"


def check_watsonx(api_key: str, project_id: str, url: str, timeout: int = 10) -> Tuple[bool, str]:
    """
    Check watsonx.ai connectivity (optional cloud service).

    Args:
        api_key: Watson API key
        project_id: Watson project ID
        url: Watson URL
        timeout: Timeout in seconds

    Returns:
        Tuple of (is_healthy, status_message)
    """
    if not api_key or not project_id:
        return True, "watsonx.ai credentials not configured (optional)"

    try:
        # Simple connectivity test - just check if URL is reachable
        response = requests.get(url, timeout=timeout)
        return True, f"watsonx.ai reachable - status {response.status_code}"
    except requests.exceptions.Timeout:
        return False, "watsonx.ai timeout"
    except requests.exceptions.ConnectionError:
        return False, "watsonx.ai unreachable"
    except Exception as e:
        return False, f"watsonx.ai error: {e}"


def check_astradb(token: str, endpoint: str, timeout: int = 10) -> Tuple[bool, str]:
    """
    Check AstraDB connectivity (optional cloud service).

    Args:
        token: AstraDB token
        endpoint: AstraDB endpoint
        timeout: Timeout in seconds

    Returns:
        Tuple of (is_healthy, status_message)
    """
    if not token or not endpoint:
        return True, "AstraDB credentials not configured (optional)"

    try:
        # Simple connectivity test
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(endpoint, headers=headers, timeout=timeout)
        return True, f"AstraDB reachable - status {response.status_code}"
    except requests.exceptions.Timeout:
        return False, "AstraDB timeout"
    except requests.exceptions.ConnectionError:
        return False, "AstraDB unreachable"
    except Exception as e:
        return False, f"AstraDB error: {e}"


def check_all_services(config: Dict) -> Dict[str, Tuple[bool, str]]:
    """
    Check health of all infrastructure services.

    Args:
        config: Configuration dictionary with service endpoints

    Returns:
        Dict mapping service name to (is_healthy, status_message)
    """
    results = {}

    logger.info("Starting infrastructure health checks...")

    # Check MinIO
    results['minio'] = check_minio(
        config['minio_endpoint'],
        config['minio_access_key'],
        config['minio_secret_key']
    )

    # Check Iceberg catalog
    results['iceberg_catalog'] = check_iceberg_catalog(
        config['iceberg_catalog_uri']
    )

    # Check Trino
    results['trino'] = check_trino(
        config['trino_host'],
        config['trino_port']
    )

    # Check cloud services (optional)
    results['watsonx'] = check_watsonx(
        config.get('watsonx_api_key'),
        config.get('watsonx_project_id'),
        config.get('watsonx_url', 'https://us-south.ml.cloud.ibm.com')
    )

    results['astradb'] = check_astradb(
        config.get('astradb_token'),
        config.get('astradb_endpoint')
    )

    # Log results
    for service, (healthy, message) in results.items():
        status = "[OK]" if healthy else "[FAIL]"
        logger.info(f"  {status} {service}: {message}")

    return results


def wait_for_services(config: Dict, timeout: int = 60, interval: int = 5) -> bool:
    """
    Wait for all required services to become healthy.

    Args:
        config: Configuration dictionary
        timeout: Maximum wait time in seconds
        interval: Check interval in seconds

    Returns:
        True if all required services are healthy, False if timeout
    """
    required_services = ['minio', 'iceberg_catalog', 'trino']

    start_time = clock.time()
    while clock.time() - start_time < timeout:
        results = check_all_services(config)

        # Check if all required services are healthy
        all_healthy = all(results[svc][0] for svc in required_services if svc in results)

        if all_healthy:
            logger.info("All required services are healthy")
            return True

        logger.info(f"Waiting for services... ({int(clock.time() - start_time)}s elapsed)")
        time.sleep(interval)

    logger.error(f"Timeout waiting for services after {timeout}s")
    return False
