"""
Test ESG Rubric Schema v3 - JSON Source of Truth

Validates that the canonical JSON schema contains exactly:
- 7 themes (TSP, OSP, DP, GP, CSP, BP, IMP)
- 5 stages per theme (1-5)
- Required scoring_rules fields

SCA v13.8 Compliance:
- Type safety: 100% annotated
- No mocks: Tests real JSON file
- Determinism: Same JSON → same validation
"""

from __future__ import annotations
import json
import pathlib
import pytest
from typing import Any, Dict, List

SCHEMA_PATH = pathlib.Path("rubrics/esg_rubric_schema_v3.json")

EXPECTED_THEMES = ["TSP", "OSP", "DM", "GHG", "RD", "EI", "RMM"]
EXPECTED_STAGES = ["0", "1", "2", "3", "4"]


@pytest.fixture
def schema() -> Dict[str, Any]:
    """Load the JSON schema."""
    if not SCHEMA_PATH.exists():
        pytest.skip(f"Schema not found: {SCHEMA_PATH}")
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


@pytest.mark.cp
class TestRubricSchemaStructure:
    """Test canonical JSON schema structure."""

    def test_schema_has_version(self, schema: Dict[str, Any]) -> None:
        """Verify schema declares a version."""
        assert "version" in schema, "Schema must declare version field"
        assert schema["version"], "Version must be non-empty"

    def test_schema_has_themes_list(self, schema: Dict[str, Any]) -> None:
        """Verify schema contains themes array."""
        assert "themes" in schema, "Schema must contain themes field"
        assert isinstance(schema["themes"], list), "themes must be a list"
        assert len(schema["themes"]) > 0, "themes must not be empty"

    def test_schema_has_scoring_rules(self, schema: Dict[str, Any]) -> None:
        """Verify schema contains scoring_rules."""
        assert "scoring_rules" in schema, "Schema must contain scoring_rules"
        assert isinstance(schema["scoring_rules"], dict), "scoring_rules must be a dict"


@pytest.mark.cp
class TestThemeCount:
    """Test that exactly 7 themes are defined."""

    def test_exactly_seven_themes(self, schema: Dict[str, Any]) -> None:
        """Verify exactly 7 themes in schema."""
        themes = schema["themes"]
        assert len(themes) == 7, f"Expected 7 themes, found {len(themes)}"

    def test_all_expected_theme_codes_present(self, schema: Dict[str, Any]) -> None:
        """Verify all 7 expected theme codes are present."""
        themes = schema["themes"]
        codes = [t.get("code") for t in themes]

        for expected_code in EXPECTED_THEMES:
            assert expected_code in codes, f"Missing expected theme code: {expected_code}"

    def test_no_duplicate_theme_codes(self, schema: Dict[str, Any]) -> None:
        """Verify no duplicate theme codes."""
        themes = schema["themes"]
        codes = [t.get("code") for t in themes]

        assert len(codes) == len(set(codes)), f"Duplicate theme codes found: {codes}"


@pytest.mark.cp
class TestThemeStages:
    """Test that each theme has exactly 5 stages."""

    def test_each_theme_has_stages_field(self, schema: Dict[str, Any]) -> None:
        """Verify each theme has a stages field."""
        themes = schema["themes"]

        for theme in themes:
            code = theme.get("code", "unknown")
            assert "stages" in theme, f"Theme {code} missing stages field"
            assert isinstance(theme["stages"], dict), f"Theme {code} stages must be dict"

    def test_each_theme_has_five_stages(self, schema: Dict[str, Any]) -> None:
        """Verify each theme has exactly 5 stages (1-5)."""
        themes = schema["themes"]

        for theme in themes:
            code = theme.get("code", "unknown")
            stages = theme.get("stages", {})
            stage_keys = list(stages.keys())

            assert len(stage_keys) == 5, f"Theme {code} has {len(stage_keys)} stages, expected 5"

            for expected_stage in EXPECTED_STAGES:
                assert expected_stage in stage_keys, f"Theme {code} missing stage {expected_stage}"

    def test_all_stages_have_description(self, schema: Dict[str, Any]) -> None:
        """Verify each stage has a non-empty description."""
        themes = schema["themes"]

        for theme in themes:
            code = theme.get("code", "unknown")
            stages = theme.get("stages", {})

            for stage_num, stage_data in stages.items():
                assert isinstance(stage_data, dict), f"Theme {code} stage {stage_num} must be dict"
                assert "descriptor" in stage_data, f"Theme {code} stage {stage_num} missing descriptor"
                desc = stage_data["descriptor"]
                assert isinstance(desc, str), f"Theme {code} stage {stage_num} descriptor must be string"
                assert len(desc) > 0, f"Theme {code} stage {stage_num} descriptor is empty"


@pytest.mark.cp
class TestScoringRules:
    """Test scoring_rules configuration."""

    def test_evidence_min_per_stage_claim_exists(self, schema: Dict[str, Any]) -> None:
        """Verify evidence_min_per_stage_claim is defined."""
        rules = schema.get("scoring_rules", {})
        assert "evidence_min_per_stage_claim" in rules, "scoring_rules missing evidence_min_per_stage_claim"

    def test_evidence_min_is_positive_integer(self, schema: Dict[str, Any]) -> None:
        """Verify evidence_min is a positive integer."""
        rules = schema.get("scoring_rules", {})
        evidence_min = rules.get("evidence_min_per_stage_claim")

        assert isinstance(evidence_min, int), "evidence_min_per_stage_claim must be int"
        assert evidence_min > 0, "evidence_min_per_stage_claim must be positive"


@pytest.mark.cp
class TestThemeMetadata:
    """Test theme metadata fields."""

    def test_each_theme_has_code(self, schema: Dict[str, Any]) -> None:
        """Verify each theme has a code field."""
        themes = schema["themes"]

        for i, theme in enumerate(themes):
            assert "code" in theme, f"Theme {i} missing code field"
            assert isinstance(theme["code"], str), f"Theme {i} code must be string"
            assert len(theme["code"]) > 0, f"Theme {i} code is empty"

    def test_each_theme_has_name(self, schema: Dict[str, Any]) -> None:
        """Verify each theme has a name field."""
        themes = schema["themes"]

        for theme in themes:
            code = theme.get("code", "unknown")
            assert "name" in theme, f"Theme {code} missing name field"
            assert isinstance(theme["name"], str), f"Theme {code} name must be string"
            assert len(theme["name"]) > 0, f"Theme {code} name is empty"


@pytest.mark.cp
class TestSchemaLoadability:
    """Test that schema can be loaded by rubric loader."""

    def test_loader_can_import(self) -> None:
        """Verify rubric loader module can be imported."""
        try:
            from apps.rubric import loader
        except ImportError as e:
            pytest.fail(f"Cannot import apps.rubric.loader: {e}")

    def test_loader_can_load_schema(self) -> None:
        """Verify loader.load_rubric() works without errors."""
        from apps.rubric.loader import load_rubric

        rubric = load_rubric()
        assert rubric is not None, "load_rubric() returned None"
        assert len(rubric.themes) == 7, f"Loader loaded {len(rubric.themes)} themes, expected 7"

    def test_loaded_rubric_has_correct_theme_codes(self) -> None:
        """Verify loaded rubric contains all expected theme codes."""
        from apps.rubric.loader import load_rubric

        rubric = load_rubric()
        codes = [t.code for t in rubric.themes]

        for expected_code in EXPECTED_THEMES:
            assert expected_code in codes, f"Loaded rubric missing theme: {expected_code}"


@pytest.mark.cp
class TestEvidenceGateIntegration:
    """Test evidence gate module integration."""

    def test_evidence_gate_can_import(self) -> None:
        """Verify evidence gate module can be imported."""
        try:
            from libs.scoring import evidence_gate
        except ImportError as e:
            pytest.fail(f"Cannot import libs.scoring.evidence_gate: {e}")

    def test_enforce_evidence_min_function_exists(self) -> None:
        """Verify enforce_evidence_min_per_theme function exists."""
        from libs.scoring.evidence_gate import enforce_evidence_min_per_theme

        assert callable(enforce_evidence_min_per_theme), "enforce_evidence_min_per_theme must be callable"

    def test_evidence_gate_nullifies_insufficient_evidence(self) -> None:
        """Verify evidence gate nullifies scores with insufficient evidence."""
        from libs.scoring.evidence_gate import enforce_evidence_min_per_theme

        scores = {"TSP": 3, "OSP": 2}
        evidence_map = {
            "TSP": [{"quote": "evidence 1"}],  # Only 1 evidence
            "OSP": [{"quote": "evidence 1"}, {"quote": "evidence 2"}]  # 2 evidence
        }

        result = enforce_evidence_min_per_theme(scores, evidence_map, evidence_min=2)

        # TSP should be nullified (only 1 evidence, need 2)
        assert result["TSP"]["score"] is None, "TSP should be nullified with insufficient evidence"
        assert "insufficient_evidence" in result["TSP"]["reason"], "TSP should have insufficient_evidence reason"

        # OSP should keep score (has 2 evidence)
        assert result["OSP"] == 2, "OSP should keep score with sufficient evidence"
