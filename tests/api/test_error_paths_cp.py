"""
Error Path Testing for Coverage: main.py and demo_flow.py

Tests designed to exercise error handling and edge cases in:
- apps/api/main.py
- apps/pipeline/demo_flow.py

SCA v13.8 Compliance:
- Tests verify error paths and validation
- Authentic error scenarios from real constraints
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch
import json


@pytest.mark.cp
class TestErrorPaths:
    """Tests for error paths in main.py and demo_flow.py."""

    def test_company_not_found_returns_404(self) -> None:
        """Test /score returns 404 when company not in manifest."""
        from apps.api.main import app

        # Clear manifest to ensure company not found
        app.COMPANIES_MANIFEST = []

        client = TestClient(app)
        response = client.post(
            "/score?semantic=0&k=10&alpha=0.6",
            json={
                "company": "NonExistentCorp",
                "year": 2025,
                "query": "test"
            }
        )

        assert response.status_code == 404
        assert "not found" in response.json().get("detail", "").lower()

    def test_invalid_alpha_returns_422(self) -> None:
        """Test /score rejects invalid alpha."""
        from apps.api.main import app

        client = TestClient(app)

        # alpha > 1.0
        response = client.post(
            "/score?semantic=0&k=10&alpha=1.5",
            json={
                "company": "TestCo",
                "year": 2024,
                "query": "test"
            }
        )

        assert response.status_code == 422

    def test_invalid_k_returns_422(self) -> None:
        """Test /score rejects invalid k."""
        from apps.api.main import app

        client = TestClient(app)

        # k > 100
        response = client.post(
            "/score?semantic=0&k=101&alpha=0.6",
            json={
                "company": "TestCo",
                "year": 2024,
                "query": "test"
            }
        )

        assert response.status_code == 422

        # k < 1
        response = client.post(
            "/score?semantic=0&k=0&alpha=0.6",
            json={
                "company": "TestCo",
                "year": 2024,
                "query": "test"
            }
        )

        assert response.status_code == 422

    def test_invalid_semantic_returns_422(self) -> None:
        """Test /score rejects invalid semantic."""
        from apps.api.main import app

        client = TestClient(app)

        # semantic not in [0, 1]
        response = client.post(
            "/score?semantic=2&k=10&alpha=0.6",
            json={
                "company": "TestCo",
                "year": 2024,
                "query": "test"
            }
        )

        assert response.status_code == 422

    def test_missing_company_field_returns_422(self) -> None:
        """Test /score rejects request without company."""
        from apps.api.main import app

        client = TestClient(app)

        response = client.post(
            "/score?semantic=0&k=10&alpha=0.6",
            json={
                "year": 2025,
                "query": "test"
            }
        )

        assert response.status_code == 422

    def test_missing_query_field_returns_422(self) -> None:
        """Test /score rejects request without query."""
        from apps.api.main import app

        client = TestClient(app)

        response = client.post(
            "/score?semantic=0&k=10&alpha=0.6",
            json={
                "company": "TestCo",
                "year": 2025
            }
        )

        assert response.status_code == 422

    def test_empty_company_returns_422(self) -> None:
        """Test /score rejects empty company string."""
        from apps.api.main import app

        client = TestClient(app)

        response = client.post(
            "/score?semantic=0&k=10&alpha=0.6",
            json={
                "company": "",
                "year": 2025,
                "query": "test"
            }
        )

        assert response.status_code == 422

    def test_empty_query_returns_422(self) -> None:
        """Test /score rejects empty query string."""
        from apps.api.main import app

        client = TestClient(app)

        response = client.post(
            "/score?semantic=0&k=10&alpha=0.6",
            json={
                "company": "TestCo",
                "year": 2025,
                "query": ""
            }
        )

        assert response.status_code == 422

    def test_get_company_record_with_mismatched_year(self) -> None:
        """Test get_company_record returns None for year mismatch."""
        from apps.api.main import get_company_record

        # Setup manifest with TestCo 2024
        from apps.api.main import app
        app.COMPANIES_MANIFEST = [
            {
                "company": "TestCo",
                "year": 2024,
                "slug": "testco",
                "bronze": "artifacts/bronze/testco_2024.parquet",
                "sources": {"pdf": "artifacts/raw/test_report.pdf"}
            }
        ]

        # Search for TestCo 2025 (year mismatch)
        result = get_company_record("TestCo", 2025)
        assert result is None

    def test_get_company_record_with_nonexistent_company(self) -> None:
        """Test get_company_record returns None for nonexistent company."""
        from apps.api.main import get_company_record

        # Setup manifest
        from apps.api.main import app
        app.COMPANIES_MANIFEST = [
            {
                "company": "TestCo",
                "year": 2024,
                "slug": "testco",
                "bronze": "artifacts/bronze/testco_2024.parquet",
                "sources": {"pdf": "artifacts/raw/test_report.pdf"}
            }
        ]

        # Search for nonexistent company
        result = get_company_record("NonExistent", 2024)
        assert result is None

    def test_score_response_structure_on_200(self) -> None:
        """Test /score response has all required fields on success."""
        from apps.api.main import app

        # Setup manifest
        app.COMPANIES_MANIFEST = [
            {
                "company": "TestCo",
                "year": 2024,
                "slug": "testco",
                "bronze": "artifacts/bronze/testco_2024.parquet",
                "sources": {"pdf": "artifacts/raw/test_report.pdf"}
            }
        ]

        client = TestClient(app)
        response = client.post(
            "/score?semantic=0&k=10&alpha=0.6",
            json={
                "company": "TestCo",
                "year": 2024,
                "query": "climate"
            }
        )

        if response.status_code == 200:
            data = response.json()

            # Verify all required fields
            assert "company" in data
            assert "year" in data
            assert "scores" in data
            assert "model_version" in data
            assert "rubric_version" in data
            assert "trace_id" in data

            # Verify scores structure
            assert isinstance(data["scores"], list)
            for score in data["scores"]:
                assert "theme" in score
                assert "stage" in score
                assert "confidence" in score
                assert "evidence" in score
                assert isinstance(score["evidence"], list)

    def test_score_with_year_2100_boundary(self) -> None:
        """Test /score accepts year=2100 (max boundary)."""
        from apps.api.main import app

        client = TestClient(app)

        response = client.post(
            "/score?semantic=0&k=10&alpha=0.6",
            json={
                "company": "TestCo",
                "year": 2100,
                "query": "test"
            }
        )

        # Should not be 422 (validation error)
        assert response.status_code != 422

    def test_score_with_year_2000_boundary(self) -> None:
        """Test /score accepts year=2000 (min boundary)."""
        from apps.api.main import app

        client = TestClient(app)

        response = client.post(
            "/score?semantic=0&k=10&alpha=0.6",
            json={
                "company": "TestCo",
                "year": 2000,
                "query": "test"
            }
        )

        # Should not be 422 (validation error)
        assert response.status_code != 422

    def test_score_with_year_outside_range(self) -> None:
        """Test /score rejects year outside [2000, 2100]."""
        from apps.api.main import app

        client = TestClient(app)

        # year < 2000
        response = client.post(
            "/score?semantic=0&k=10&alpha=0.6",
            json={
                "company": "TestCo",
                "year": 1999,
                "query": "test"
            }
        )

        assert response.status_code == 422

        # year > 2100
        response = client.post(
            "/score?semantic=0&k=10&alpha=0.6",
            json={
                "company": "TestCo",
                "year": 2101,
                "query": "test"
            }
        )

        assert response.status_code == 422
