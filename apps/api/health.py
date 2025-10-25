"""Health check endpoints for production readiness and liveness probes.

Provides lightweight endpoints for orchestrators (Kubernetes, Docker Swarm)
to monitor application health without triggering business logic.

SCA v13.8-MEA Phase 9
"""

from datetime import datetime
from typing import Dict, Any

from fastapi import APIRouter, Response, status


def create_router() -> APIRouter:
    """
    Create health check router with readiness and liveness probes.

    Returns:
        Configured APIRouter with health endpoints
    """
    router = APIRouter(tags=["Health"])

    @router.get(
        "/health",
        status_code=status.HTTP_200_OK,
        summary="Basic health check",
        response_description="Service is operational"
    )
    async def health() -> Dict[str, Any]:
        """
        Basic health check endpoint.

        Returns service status and timestamp. Always returns 200 if the
        application is running.

        Returns:
            Health status dictionary
        """
        return {
            "status": "healthy",
            "service": "prospecting-engine",
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }

    @router.get(
        "/ready",
        status_code=status.HTTP_200_OK,
        summary="Readiness probe",
        response_description="Service is ready to accept traffic"
    )
    async def readiness() -> Dict[str, bool]:
        """
        Kubernetes-style readiness probe.

        Indicates whether the service is ready to accept traffic.
        Returns 200 if ready, 503 if not ready (future enhancement).

        Returns:
            Readiness status
        """
        # Future: Check database connections, cache availability, etc.
        return {"ready": True}

    @router.get(
        "/live",
        status_code=status.HTTP_200_OK,
        summary="Liveness probe",
        response_description="Service is alive and not deadlocked"
    )
    async def liveness() -> Dict[str, bool]:
        """
        Kubernetes-style liveness probe.

        Indicates whether the service is alive. Returns 200 if alive,
        otherwise the service should be restarted.

        Returns:
            Liveness status
        """
        # Future: Check for deadlocks, memory exhaustion, etc.
        return {"live": True}

    return router
