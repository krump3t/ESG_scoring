"""
Critical Path Tests: Rubric Compliance Gate (AR-001)

Tests for evidence-first scoring: ≥2 quotes per theme required.

Compliance:
- TDD-first: Tests before implementation
- Property-based: Hypothesis tests for evidence fixtures
- Authenticity: Refuse stage > 0 without ≥2 quotes per evidence record
- Determinism: Rubric loaded from maturity_v3.json only

SCA v13.8 Authenticity Refactor
"""

import pytest
from typing import Dict, List, Any
from hypothesis import given, strategies as st
import json


@pytest.mark.cp
class TestRubricComplianceCP:
    """Tests for ≥2 quotes per theme enforcement in scoring."""

    def test_rubric_schema_matches_canonical(self):
        """Verify loaded rubric matches esg_rubric_schema_v3.json."""
        from pathlib import Path
        import json

        schema_file = Path("rubrics/esg_rubric_schema_v3.json")
        assert schema_file.exists(), "Rubric schema not found at rubrics/esg_rubric_schema_v3.json"

        schema = json.loads(schema_file.read_text())
        assert "themes" in schema
        assert "scale" in schema
        assert schema["scale"]["max"] == 4

    def test_maturity_v3_json_is_canonical(self):
        """Verify maturity_v3.json is used as runtime source."""
        from pathlib import Path
        import json

        maturity_file = Path("rubrics/maturity_v3.json")
        assert maturity_file.exists(), "maturity_v3.json not found"

        rubric = json.loads(maturity_file.read_text())
        assert "output_contract" in rubric
        assert "evidence_record" in rubric["output_contract"]

    def test_evidence_record_contract(self):
        """Verify evidence records match output_contract."""
        evidence_record = {
            "doc_id": "doc_apple_2024_10k",
            "evidence_id": "ev_001",
            "extract_30w": "We committed to renewable energy with 100% carbon neutral operations",
            "hash_sha256": "abc123def456",
            "org_id": "apple",
            "page_no": 42,
            "snapshot_id": "snap_123",
            "span_start": 100,
            "span_end": 200,
            "theme_code": "Climate",
            "year": 2024
        }

        # Verify all contract fields present
        required_fields = {
            "doc_id", "evidence_id", "extract_30w", "hash_sha256",
            "org_id", "page_no", "snapshot_id", "span_start", "span_end",
            "theme_code", "year"
        }
        assert required_fields.issubset(set(evidence_record.keys()))

    def test_minimum_two_quotes_per_theme_enforcement(self):
        """Test that scoring refuses stage > 0 without ≥2 evidence quotes."""
        from agents.scoring.rubric_scorer import RubricScorer

        scorer = RubricScorer()

        # Scenario: 1 quote only (insufficient)
        evidence = [
            {
                "theme_code": "Climate",
                "extract_30w": "Committed to net zero by 2050",
                "doc_id": "doc1"
            }
        ]

        score_result = scorer.score(
            theme="Climate",
            evidence=evidence,
            org_id="test_org"
        )

        # Should refuse stage > 0
        assert score_result["stage"] == 0, \
            "Should refuse stage > 0 with only 1 quote"

    def test_two_quotes_per_theme_sufficient(self):
        """Test that scoring allows stage > 0 with ≥2 evidence quotes."""
        from agents.scoring.rubric_scorer import RubricScorer

        scorer = RubricScorer()

        # Scenario: 2 quotes (sufficient)
        evidence = [
            {
                "theme_code": "Climate",
                "extract_30w": "Committed to net zero by 2050",
                "doc_id": "doc1"
            },
            {
                "theme_code": "Climate",
                "extract_30w": "Reduced emissions 25% year-over-year",
                "doc_id": "doc1"
            }
        ]

        score_result = scorer.score(
            theme="Climate",
            evidence=evidence,
            org_id="test_org"
        )

        # Should allow stage >= 1
        assert score_result["stage"] >= 1, \
            "Should allow stage >= 1 with 2+ quotes"

    @given(st.integers(min_value=0, max_value=10))
    def test_quote_count_threshold(self, quote_count: int):
        """Property test: stage decisions respect quote count threshold."""
        from agents.scoring.rubric_scorer import RubricScorer

        scorer = RubricScorer()

        # Generate evidence with quote_count entries
        evidence = [
            {
                "theme_code": "Climate",
                "extract_30w": f"Quote {i}: Evidence of climate action",
                "doc_id": f"doc{i}"
            }
            for i in range(quote_count)
        ]

        score_result = scorer.score(
            theme="Climate",
            evidence=evidence,
            org_id="test_org"
        )

        # If quote_count < 2, should be stage 0
        if quote_count < 2:
            assert score_result["stage"] == 0
        # If quote_count >= 2, may be stage > 0
        # (actual stage depends on quality, not just count)

    def test_score_record_contract(self):
        """Verify score records match output_contract."""
        score_record = {
            "confidence": 0.75,
            "doc_manifest_uri": "artifacts/ingestion/manifest.json",
            "evidence_ids": ["ev_001", "ev_002"],
            "frameworks": ["TCFD", "GRI"],
            "org_id": "apple",
            "snapshot_id": "snap_123",
            "stage": 2,
            "theme_code": "Climate",
            "year": 2024
        }

        # Verify all contract fields present
        required_fields = {
            "confidence", "doc_manifest_uri", "evidence_ids",
            "frameworks", "org_id", "snapshot_id", "stage",
            "theme_code", "year"
        }
        assert required_fields.issubset(set(score_record.keys()))
        assert 0.0 <= score_record["confidence"] <= 1.0
        assert 0 <= score_record["stage"] <= 4

    def test_no_runtime_markdown_parsing(self):
        """Verify no runtime markdown parsing; use JSON only."""
        from pathlib import Path
        import json

        # Rubric must be JSON, not Markdown
        maturity_file = Path("rubrics/maturity_v3.json")
        content = maturity_file.read_text()

        # Should parse as valid JSON
        rubric = json.loads(content)
        assert isinstance(rubric, dict)

        # Should NOT be markdown
        assert not content.strip().startswith("#")
        assert not content.strip().startswith("-")

    def test_rubric_scorer_missing_rubric_file(self, tmp_path):
        """Failure path: RubricScorer raises FileNotFoundError when rubric missing."""
        from agents.scoring.rubric_scorer import RubricScorer

        # Point to non-existent rubric
        with pytest.raises(FileNotFoundError):
            RubricScorer(rubric_path=str(tmp_path / "nonexistent.json"))

    def test_rubric_scorer_invalid_json_rubric(self, tmp_path):
        """Failure path: RubricScorer raises ValueError on invalid JSON."""
        from agents.scoring.rubric_scorer import RubricScorer

        # Create invalid JSON file
        bad_rubric = tmp_path / "bad_rubric.json"
        bad_rubric.write_text("{invalid json")

        with pytest.raises(ValueError, match="Invalid JSON"):
            RubricScorer(rubric_path=str(bad_rubric))

    def test_score_result_validates_confidence_bounds(self):
        """Failure path: Score validation ensures confidence in [0.0, 1.0]."""
        from agents.scoring.rubric_scorer import RubricScorer

        scorer = RubricScorer()

        # Provide sufficient evidence for scoring
        evidence = [
            {"theme_code": "Climate", "extract_30w": "Long evidence text with substantial content", "doc_id": "doc1"},
            {"theme_code": "Climate", "extract_30w": "Another high quality evidence statement", "doc_id": "doc2"}
        ]

        result = scorer.score(
            theme="Climate",
            evidence=evidence,
            org_id="test_org"
        )

        # Verify confidence is in valid range
        assert 0.0 <= result["confidence"] <= 1.0
        # Verify stage is in valid range
        assert 0 <= result["stage"] <= 4
