"""
ESG Maturity Rubric v3.0 Loader
Loads and provides access to the updated 7-theme rubric with evidence-based scoring
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass


@dataclass
class StageDescriptor:
    """Descriptor for a single maturity stage"""
    label: str
    descriptor: str
    evidence_examples: List[str]


@dataclass
class ThemeRubric:
    """Rubric for a single ESG theme"""
    code: str
    name: str
    intent: str
    stages: Dict[int, StageDescriptor]


class RubricV3Loader:
    """
    Loader for ESG Maturity Rubric v3.0
    Supports 7 themes with evidence-based stage descriptors
    """

    def __init__(self, rubric_path: Optional[Path] = None):
        """
        Initialize rubric loader

        Args:
            rubric_path: Path to esg_rubric_schema_v3.json. If None, uses default location.
        """
        if rubric_path is None:
            base = Path(__file__).parent.parent.parent
            rubric_path = base / "rubrics" / "esg_rubric_schema_v3.json"

        self.rubric_path = rubric_path
        self.rubric_data = self._load_rubric()
        self.themes = self._parse_themes()

    def _load_rubric(self) -> Dict[str, Any]:
        """Load rubric JSON file"""
        with open(self.rubric_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def _parse_themes(self) -> Dict[str, ThemeRubric]:
        """Parse themes from rubric data"""
        themes = {}

        for theme_data in self.rubric_data.get("themes", []):
            code = theme_data["code"]
            name = theme_data["name"]
            intent = theme_data["intent"]

            stages = {}
            for stage_num, stage_data in theme_data["stages"].items():
                stages[int(stage_num)] = StageDescriptor(
                    label=stage_data["label"],
                    descriptor=stage_data["descriptor"],
                    evidence_examples=stage_data.get("evidence_examples", [])
                )

            themes[code] = ThemeRubric(
                code=code,
                name=name,
                intent=intent,
                stages=stages
            )

        return themes

    def get_theme_codes(self) -> List[str]:
        """Get all theme codes (TSP, OSP, DM, GHG, RD, EI, RMM)"""
        return list(self.themes.keys())

    def get_theme_names(self) -> List[str]:
        """Get all theme names (full names)"""
        return [theme.name for theme in self.themes.values()]

    def get_theme(self, code: str) -> Optional[ThemeRubric]:
        """Get theme rubric by code"""
        return self.themes.get(code)

    def get_theme_by_name(self, name: str) -> Optional[ThemeRubric]:
        """Get theme rubric by name"""
        for theme in self.themes.values():
            if theme.name.lower() == name.lower():
                return theme
        return None

    def get_stage_descriptor(self, theme_code: str, stage: int) -> Optional[StageDescriptor]:
        """Get stage descriptor for a specific theme and stage"""
        theme = self.get_theme(theme_code)
        if theme:
            return theme.stages.get(stage)
        return None

    def get_rubric_for_llm(self, theme_code: str) -> Dict[int, str]:
        """
        Get rubric formatted for LLM prompts
        Returns dict mapping stage number to full descriptor text
        """
        theme = self.get_theme(theme_code)
        if not theme:
            return {}

        return {
            stage_num: f"{stage.label}: {stage.descriptor}"
            for stage_num, stage in theme.stages.items()
        }

    def get_scoring_rules(self) -> Dict[str, Any]:
        """Get scoring rules from rubric"""
        return self.rubric_data.get("scoring_rules", {})

    def get_framework_signals(self) -> Dict[str, Any]:
        """Get framework signals (SBTi, ISSB, GHG Protocol, CSRD)"""
        rules = self.get_scoring_rules()
        return rules.get("framework_signals", {})

    def get_evidence_requirements(self) -> int:
        """Get minimum evidence per stage claim"""
        rules = self.get_scoring_rules()
        return rules.get("evidence_min_per_stage_claim", 2)

    def get_freshness_penalty(self) -> Dict[str, Any]:
        """Get freshness penalty rules"""
        rules = self.get_scoring_rules()
        return rules.get("freshness_months_penalty", {"months": 24, "confidence_delta": -0.1})

    def get_confidence_guidance(self, confidence: float) -> str:
        """Get confidence label for a confidence score"""
        rules = self.get_scoring_rules()
        guidance = rules.get("confidence_guidance", [])

        for item in guidance:
            min_conf, max_conf = item["range"]
            if min_conf <= confidence <= max_conf:
                return item["label"]

        return "unknown"

    def get_output_contract(self) -> Dict[str, Any]:
        """Get output contract schema"""
        return self.rubric_data.get("output_contract", {})

    def apply_framework_boost(
        self,
        theme_code: str,
        base_stage: int,
        detected_frameworks: List[str]
    ) -> int:
        """
        Apply framework-based stage boosts

        Args:
            theme_code: Theme code (TSP, OSP, etc.)
            base_stage: Base maturity stage
            detected_frameworks: List of detected frameworks (e.g., ["SBTi", "ISSB_TCFD"])

        Returns:
            Adjusted stage (may be increased based on frameworks)
        """
        framework_signals = self.get_framework_signals()
        adjusted_stage = base_stage

        for framework in detected_frameworks:
            if framework in framework_signals:
                rules = framework_signals[framework]

                # Check theme-specific boosts
                if theme_code == "TSP" and framework == "SBTi":
                    if "approved_sets_stage" in rules:
                        adjusted_stage = max(adjusted_stage, rules["approved_sets_stage"])

                elif theme_code == "RD" and framework == "ISSB_TCFD":
                    if "assured_and_tagged_sets_stage" in rules:
                        adjusted_stage = max(adjusted_stage, rules["assured_and_tagged_sets_stage"])

                elif theme_code == "GHG" and framework == "GHG_Protocol":
                    if "reasonable_assurance_sets_stage" in rules:
                        adjusted_stage = max(adjusted_stage, rules["reasonable_assurance_sets_stage"])

        return min(adjusted_stage, 4)  # Cap at stage 4

    def apply_freshness_penalty(self, confidence: float, evidence_age_months: int) -> float:
        """
        Apply freshness penalty to confidence score

        Args:
            confidence: Base confidence score
            evidence_age_months: Age of evidence in months

        Returns:
            Adjusted confidence score
        """
        penalty_rules = self.get_freshness_penalty()
        threshold_months = penalty_rules.get("months", 24)
        penalty = penalty_rules.get("confidence_delta", -0.1)

        if evidence_age_months > threshold_months:
            confidence += penalty

        return max(0.0, min(1.0, confidence))

    def validate_evidence_count(self, evidence_count: int) -> bool:
        """Check if evidence count meets minimum requirements"""
        min_required = self.get_evidence_requirements()
        return evidence_count >= min_required


def get_rubric_v3() -> RubricV3Loader:
    """Get singleton instance of rubric loader"""
    return RubricV3Loader()


if __name__ == "__main__":
    # Test the loader
    rubric = get_rubric_v3()

    print("ESG Maturity Rubric v3.0")
    print("=" * 60)
    print(f"\nVersion: {rubric.rubric_data.get('version')}")
    print(f"Updated: {rubric.rubric_data.get('updated_utc')}")

    print(f"\nThemes ({len(rubric.themes)}):")
    for code, theme in rubric.themes.items():
        print(f"  [{code}] {theme.name}")
        print(f"      Intent: {theme.intent}")
        print(f"      Stages: {len(theme.stages)}")

    print(f"\nScoring Rules:")
    rules = rubric.get_scoring_rules()
    print(f"  Min evidence per stage: {rules.get('evidence_min_per_stage_claim')}")
    print(f"  Freshness threshold: {rules.get('freshness_months_penalty', {}).get('months')} months")

    print(f"\nFramework Signals:")
    for framework, signals in rubric.get_framework_signals().items():
        print(f"  {framework}: {signals}")
