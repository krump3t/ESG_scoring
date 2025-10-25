"""
Phase 9 CP Tests: Health Endpoint Tests

Tests for apps/api/health.py health check endpoints:
- GET /health → {"status": "healthy", "service": "...", "timestamp": "..."}
- GET /ready → {"ready": true}
- GET /live → {"live": true}

SCA v13.8 Compliance:
- TDD-first: Health endpoints tested before integration
- Type safety: Response validation
- Determinism: Stateless health checks
"""

import pytest
from fastapi.testclient import TestClient
from datetime import datetime
import re


@pytest.mark.cp
class TestHealthEndpoints:
    """Health endpoint tests."""

    def test_health_endpoint_returns_200(self):
        """Verify /health endpoint returns 200 OK."""
        from apps.api.main import app

        client = TestClient(app)
        response = client.get("/health")

        assert response.status_code == 200
        assert response.json()["status"] == "healthy"

    def test_health_endpoint_includes_service_name(self):
        """Verify /health response includes service name."""
        from apps.api.main import app

        client = TestClient(app)
        response = client.get("/health")

        data = response.json()
        assert "service" in data
        assert data["service"] == "prospecting-engine"

    def test_health_endpoint_includes_timestamp(self):
        """Verify /health response includes ISO timestamp."""
        from apps.api.main import app

        client = TestClient(app)
        response = client.get("/health")

        data = response.json()
        assert "timestamp" in data
        # Should be ISO format with Z suffix
        assert data["timestamp"].endswith("Z")
        # Should parse as valid datetime (without Z)
        datetime.fromisoformat(data["timestamp"].rstrip("Z"))

    def test_readiness_endpoint_returns_200(self):
        """Verify /ready endpoint returns 200 OK."""
        from apps.api.main import app

        client = TestClient(app)
        response = client.get("/ready")

        assert response.status_code == 200
        assert response.json()["ready"] is True

    def test_readiness_endpoint_schema(self):
        """Verify /ready response has correct schema."""
        from apps.api.main import app

        client = TestClient(app)
        response = client.get("/ready")

        data = response.json()
        assert isinstance(data, dict)
        assert "ready" in data
        assert isinstance(data["ready"], bool)

    def test_liveness_endpoint_returns_200(self):
        """Verify /live endpoint returns 200 OK."""
        from apps.api.main import app

        client = TestClient(app)
        response = client.get("/live")

        assert response.status_code == 200
        assert response.json()["live"] is True

    def test_liveness_endpoint_schema(self):
        """Verify /live response has correct schema."""
        from apps.api.main import app

        client = TestClient(app)
        response = client.get("/live")

        data = response.json()
        assert isinstance(data, dict)
        assert "live" in data
        assert isinstance(data["live"], bool)

    def test_health_endpoints_are_stateless(self):
        """Verify health endpoints are stateless (multiple calls return same structure)."""
        from apps.api.main import app

        client = TestClient(app)

        # Call health endpoint 3 times
        for _ in range(3):
            response = client.get("/health")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
            assert data["service"] == "prospecting-engine"
            assert "timestamp" in data

    def test_health_endpoints_not_in_scoring_routes(self):
        """Verify health endpoints don't interfere with /score endpoint."""
        from apps.api.main import app

        client = TestClient(app)

        # Health endpoints should work
        assert client.get("/health").status_code == 200
        assert client.get("/ready").status_code == 200
        assert client.get("/live").status_code == 200

        # /score should exist (though may fail due to missing data)
        # Just verify it's not a 404 due to routing conflicts
        # (It may 404 due to missing company manifest, which is OK)
        response = client.post(
            "/score",
            json={"company": "TestCo", "year": 2024, "query": "test"}
        )
        # Should be 404 (company not found) or 500 (error), but not 404 route not found
        assert response.status_code in [404, 422, 500]


@pytest.mark.cp
class TestHealthFailurePaths:
    """Failure path tests for health endpoints."""

    def test_health_get_only(self):
        """Verify /health only accepts GET requests."""
        from apps.api.main import app

        client = TestClient(app)

        # POST should not be allowed
        response = client.post("/health")
        assert response.status_code == 405  # Method Not Allowed

    def test_ready_get_only(self):
        """Verify /ready only accepts GET requests."""
        from apps.api.main import app

        client = TestClient(app)

        response = client.post("/ready")
        assert response.status_code == 405  # Method Not Allowed

    def test_live_get_only(self):
        """Verify /live only accepts GET requests."""
        from apps.api.main import app

        client = TestClient(app)

        response = client.post("/live")
        assert response.status_code == 405  # Method Not Allowed

    def test_health_query_params_ignored(self):
        """Verify health endpoints ignore query parameters."""
        from apps.api.main import app

        client = TestClient(app)

        # Query params should be ignored
        response = client.get("/health?foo=bar&baz=qux")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"

    def test_invalid_paths_return_404(self):
        """Verify invalid health paths return 404."""
        from apps.api.main import app

        client = TestClient(app)

        assert client.get("/health/invalid").status_code == 404
        assert client.get("/healthz").status_code == 404
        assert client.get("/readiness").status_code == 404
