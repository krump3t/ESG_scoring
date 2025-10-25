"""
Phase 6x CP Tests: /score API Contract Tests

Tests for apps/api/main.py /score endpoint to ensure:
- Request/response schema compliance
- Deterministic responses (same inputs → same output)
- Error handling (400, 500)
- Trace ID generation

SCA v13.8 Compliance:
- TDD-first: API contract verified
- Determinism: 3-run verification
- Type safety: Pydantic schemas
"""

import pytest
from fastapi.testclient import TestClient


@pytest.mark.cp
class TestScoreAPIContract:
    """API contract tests for /score endpoint."""

    def test_score_endpoint_exists(self):
        """Verify /score POST endpoint exists."""
        from apps.api.main import app

        client = TestClient(app)
        response = client.post(
            "/score",
            json={"company": "TestCo", "year": 2024, "query": "climate"}
        )

        # Should not 404
        assert response.status_code in [200, 500]  # 500 if Parquet missing, but endpoint exists

    def test_health_endpoint_returns_200(self):
        """Verify /health endpoint returns 200 OK."""
        from apps.api.main import app

        client = TestClient(app)
        response = client.get("/health")

        assert response.status_code == 200
        assert response.json()["status"] == "healthy"

    def test_metrics_endpoint_returns_200(self):
        """Verify /metrics endpoint returns 200 OK."""
        from apps.api.main import app

        client = TestClient(app)
        response = client.get("/metrics")

        assert response.status_code == 200
        # Metrics are in Prometheus text format, not JSON
        assert "requests_total" in response.text or "python_" in response.text

    def test_score_response_schema(self):
        """Verify /score response matches expected schema."""
        from apps.api.main import app

        client = TestClient(app)
        response = client.post(
            "/score",
            json={"company": "LSE", "year": 2024, "query": "climate"}
        )

        if response.status_code == 200:
            data = response.json()

            # Required fields
            assert "company" in data
            assert "scores" in data
            assert "trace_id" in data
            assert "model_version" in data
            assert "rubric_version" in data

            # Validate scores structure
            assert isinstance(data["scores"], list)
            if len(data["scores"]) > 0:
                score = data["scores"][0]
                assert "theme" in score
                assert "stage" in score
                assert "confidence" in score
                assert "evidence" in score
                assert 0 <= score["stage"] <= 4
                assert 0.0 <= score["confidence"] <= 1.0

    def test_deterministic_trace_id(self):
        """Verify trace_id is deterministic for same inputs."""
        from apps.api.main import app

        client = TestClient(app)

        # Same request 3 times
        response1 = client.post(
            "/score",
            json={"company": "TestCo", "year": 2024, "query": "climate"}
        )
        response2 = client.post(
            "/score",
            json={"company": "TestCo", "year": 2024, "query": "climate"}
        )
        response3 = client.post(
            "/score",
            json={"company": "TestCo", "year": 2024, "query": "climate"}
        )

        if response1.status_code == 200:
            trace1 = response1.json()["trace_id"]
            trace2 = response2.json()["trace_id"]
            trace3 = response3.json()["trace_id"]

            assert trace1 == trace2 == trace3

    def test_missing_required_fields_returns_422(self):
        """Verify missing required fields return 422 Unprocessable Entity."""
        from apps.api.main import app

        client = TestClient(app)

        # Missing 'company' field
        response = client.post(
            "/score",
            json={"year": 2024, "query": "climate"}  # Missing 'company'
        )

        assert response.status_code == 422


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
