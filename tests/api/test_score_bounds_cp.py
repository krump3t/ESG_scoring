"""
Phase 9 CP Tests: Score API Parameter Bounds Validation

Tests for apps/api/main.py /score endpoint parameter validation:
- alpha<0, alpha>1 → 422
- k<=0, k>100 → 422
- semantic not in [0,1] → 422
- Invalid company → 404
- Missing required fields → 422

SCA v13.8 Compliance:
- TDD-first: Parameter bounds tested before impl
- Type safety: Pydantic validation
- Contract: /score request/response schema unchanged
"""

import pytest
from fastapi.testclient import TestClient


@pytest.mark.cp
class TestScoreParameterBounds:
    """Parameter validation tests for /score endpoint."""

    def test_alpha_below_zero_returns_422(self):
        """Verify alpha < 0 returns 422 validation error."""
        from apps.api.main import app

        client = TestClient(app)
        response = client.post(
            "/score?alpha=-0.1",
            json={"company": "TestCo", "year": 2024, "query": "climate"}
        )

        assert response.status_code == 422
        assert "detail" in response.json()

    def test_alpha_above_one_returns_422(self):
        """Verify alpha > 1.0 returns 422 validation error."""
        from apps.api.main import app

        client = TestClient(app)
        response = client.post(
            "/score?alpha=1.5",
            json={"company": "TestCo", "year": 2024, "query": "climate"}
        )

        assert response.status_code == 422
        assert "detail" in response.json()

    def test_k_zero_returns_422(self):
        """Verify k=0 returns 422 validation error."""
        from apps.api.main import app

        client = TestClient(app)
        response = client.post(
            "/score?k=0",
            json={"company": "TestCo", "year": 2024, "query": "climate"}
        )

        assert response.status_code == 422
        assert "detail" in response.json()

    def test_k_negative_returns_422(self):
        """Verify k<0 returns 422 validation error."""
        from apps.api.main import app

        client = TestClient(app)
        response = client.post(
            "/score?k=-5",
            json={"company": "TestCo", "year": 2024, "query": "climate"}
        )

        assert response.status_code == 422
        assert "detail" in response.json()

    def test_k_exceeds_max_returns_422(self):
        """Verify k>100 returns 422 validation error."""
        from apps.api.main import app

        client = TestClient(app)
        response = client.post(
            "/score?k=101",
            json={"company": "TestCo", "year": 2024, "query": "climate"}
        )

        assert response.status_code == 422
        assert "detail" in response.json()

    def test_semantic_invalid_returns_422(self):
        """Verify semantic not in [0,1] returns 422 validation error."""
        from apps.api.main import app

        client = TestClient(app)
        response = client.post(
            "/score?semantic=2",
            json={"company": "TestCo", "year": 2024, "query": "climate"}
        )

        assert response.status_code == 422
        assert "detail" in response.json()

    def test_missing_company_returns_422(self):
        """Verify missing company field returns 422."""
        from apps.api.main import app

        client = TestClient(app)
        response = client.post(
            "/score",
            json={"year": 2024, "query": "climate"}
        )

        assert response.status_code == 422

    def test_missing_query_returns_422(self):
        """Verify missing query field returns 422."""
        from apps.api.main import app

        client = TestClient(app)
        response = client.post(
            "/score",
            json={"company": "TestCo", "year": 2024}
        )

        assert response.status_code == 422

    def test_empty_company_returns_422(self):
        """Verify empty company string returns 422."""
        from apps.api.main import app

        client = TestClient(app)
        response = client.post(
            "/score",
            json={"company": "", "year": 2024, "query": "climate"}
        )

        assert response.status_code == 422

    def test_empty_query_returns_422(self):
        """Verify empty query string returns 422."""
        from apps.api.main import app

        client = TestClient(app)
        response = client.post(
            "/score",
            json={"company": "TestCo", "year": 2024, "query": ""}
        )

        assert response.status_code == 422

    def test_invalid_year_returns_422(self):
        """Verify year outside valid range returns 422."""
        from apps.api.main import app

        client = TestClient(app)
        # Too far in past
        response = client.post(
            "/score",
            json={"company": "TestCo", "year": 1900, "query": "climate"}
        )

        assert response.status_code == 422

    def test_year_too_far_future_returns_422(self):
        """Verify year too far in future returns 422."""
        from apps.api.main import app

        client = TestClient(app)
        response = client.post(
            "/score",
            json={"company": "TestCo", "year": 2200, "query": "climate"}
        )

        assert response.status_code == 422

    def test_valid_parameters_reach_endpoint(self):
        """Verify valid parameters don't trigger validation 422."""
        from apps.api.main import app

        client = TestClient(app)
        response = client.post(
            "/score?semantic=1&k=10&alpha=0.6",
            json={"company": "TestCo", "year": 2024, "query": "climate"}
        )

        # Should not be 422 (validation passed); may be 404 or 500 depending on data
        assert response.status_code in [200, 404, 500]


@pytest.mark.cp
class TestScoreUnknownCompany:
    """Tests for unknown company handling."""

    def test_unknown_company_returns_404(self):
        """Verify unknown company returns 404 Not Found."""
        from apps.api.main import app

        client = TestClient(app)
        response = client.post(
            "/score",
            json={"company": "NonExistentCorpXYZ", "year": 2024, "query": "climate"}
        )

        # Should be 404 since company not in manifest
        assert response.status_code == 404
        assert "not found" in response.json().get("detail", "").lower()
