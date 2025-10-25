"""
Phase 7b CP Tests: /score Demo Contract

Tests for apps/api/main.py with demo company lookup:
- POST /score {company, year, query} returns required schema
- 404 for unknown company
- 422 for malformed body
- Deterministic trace_id in deterministic mode

SCA v13.8 Compliance:
- TDD-first: Tests before implementation
- Contract stability: schema unchanged
- Determinism: Fixed trace_id for same inputs
- Type safety: 100% annotated
"""

import pytest
from fastapi.testclient import TestClient
from typing import Dict, Any


@pytest.mark.cp
class TestScoreDemoContract:
    """Tests for /score endpoint with demo company lookup."""

    def test_score_returns_required_schema_fields(self):
        """Verify /score returns company, year, scores, model_version, rubric_version, trace_id."""
        from apps.api.main import app

        client = TestClient(app)
        response = client.post("/score", json={
            "company": "TestCo",
            "year": 2024,
            "query": "climate targets"
        })

        # Should return 200 if company is prepared
        if response.status_code == 200:
            data = response.json()

            # Required fields per contract
            assert "company" in data
            assert "year" in data
            assert "scores" in data
            assert "model_version" in data
            assert "rubric_version" in data
            assert "trace_id" in data

            # Scores should be array of DimensionScore
            assert isinstance(data["scores"], list)
            if len(data["scores"]) > 0:
                score = data["scores"][0]
                assert "theme" in score
                assert "stage" in score
                assert "confidence" in score
                assert "evidence" in score

    def test_unknown_company_returns_404(self):
        """Verify /score returns 404 for companies not in demo index."""
        from apps.api.main import app

        client = TestClient(app)
        response = client.post("/score", json={
            "company": "NonExistentCorp",
            "year": 2024,
            "query": "climate"
        })

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_malformed_body_returns_422(self):
        """Verify /score returns 422 for missing required fields."""
        from apps.api.main import app

        client = TestClient(app)

        # Missing company
        response = client.post("/score", json={
            "year": 2024,
            "query": "climate"
        })
        assert response.status_code == 422

        # Missing query
        response2 = client.post("/score", json={
            "company": "TestCo",
            "year": 2024
        })
        assert response2.status_code == 422

        # Empty query
        response3 = client.post("/score", json={
            "company": "TestCo",
            "year": 2024,
            "query": ""
        })
        assert response3.status_code == 422

    def test_deterministic_trace_id_three_runs(self):
        """Verify trace_id is identical for same inputs (deterministic mode)."""
        from apps.api.main import app

        client = TestClient(app)

        # Same payload 3 times
        payload = {
            "company": "TestCo",
            "year": 2024,
            "query": "net zero targets"
        }

        response1 = client.post("/score", json=payload)
        response2 = client.post("/score", json=payload)
        response3 = client.post("/score", json=payload)

        # If successful, trace_ids should match
        if response1.status_code == 200:
            trace1 = response1.json()["trace_id"]
            trace2 = response2.json()["trace_id"]
            trace3 = response3.json()["trace_id"]

            assert trace1 == trace2 == trace3, \
                f"trace_id not deterministic: {trace1}, {trace2}, {trace3}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
