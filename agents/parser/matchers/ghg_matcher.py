"""
GHG (Greenhouse Gas Accounting) theme matcher.

Extracts evidence for GHG Accounting maturity including:
- Scope 1/2/3 emissions disclosure
- GHG Protocol methodology references
- Assurance level (limited vs. reasonable)
- Assurance provider identification
- Base year and recalculation policy
"""

from typing import List
from ..models import Match
from .base_matcher import BaseMatcher


class GHGMatcher(BaseMatcher):
    """
    Matcher for GHG (Greenhouse Gas Accounting) theme.

    Stage indicators (aligned with ESG Maturity Rubric v3.0):
    - Stage 0: No emissions accounting
    - Stage 1: Partial Scope 1/2 estimates without methodology
    - Stage 2: Scope 1/2 complete + partial Scope 3
    - Stage 3: Comprehensive Scope 1/2/3 + limited assurance
    - Stage 4: Reasonable assurance + GHG Protocol compliance
    """

    def __init__(self) -> None:
        """Initialize GHG matcher with theme-specific patterns."""
        super().__init__(theme="GHG")

        # Define regex patterns for GHG evidence
        patterns = {
            # Scope 1/2/3 emissions
            "scope_1": r"\bScope\s+1\s+(emissions?|GHG)",
            "scope_2": r"\bScope\s+2\s+(emissions?|GHG)",
            "scope_3": r"\bScope\s+3\s+(emissions?|GHG|value\s+chain)",

            # Emissions values with units
            "emissions_value_mtco2e": r"([\d,]+)\s*mtCO2e",
            "emissions_value_tco2e": r"([\d,]+)\s*tCO2e",
            "emissions_value_metric_tons": r"([\d,]+)\s*metric\s+tons?\s+(CO2|carbon|GHG)",

            # GHG Protocol references
            "ghg_protocol": r"\bGHG\s+Protocol\b",
            "ghg_protocol_corporate": r"\bGHG\s+Protocol\s+Corporate\s+(Standard|Accounting)",
            "iso_14064": r"\bISO\s+14064\b",

            # Assurance level (matches in either order: assurance...GHG or GHG...assurance)
            "limited_assurance": r"(?:\blimited\s+assurance\b.{0,100}(?:emissions?|GHG|inventory|carbon))|(?:(?:emissions?|GHG|inventory|carbon).{0,100}\blimited\s+assurance\b)",
            "reasonable_assurance": r"(?:\breasonable\s+assurance\b.{0,100}(?:emissions?|GHG|inventory|carbon))|(?:(?:emissions?|GHG|inventory|carbon).{0,100}\breasonable\s+assurance\b)",

            # Assurance providers (Big 4 + common providers) - matches provider + assurance/verification + GHG context
            "assurance_provider_deloitte": r"(?:\bDeloitte\b.{0,100}(?:assurance|verification|verified|audited?).{0,100}(?:emissions?|GHG|greenhouse\s+gas|inventory))|(?:(?:emissions?|GHG|greenhouse\s+gas|inventory).{0,100}(?:assurance|verification|verified|audited?).{0,100}\bDeloitte\b)",
            "assurance_provider_ey": r"(?:\b(?:EY|Ernst\s+&\s+Young)\b.{0,100}(?:assurance|verification|verified|audited?).{0,100}(?:emissions?|GHG|greenhouse\s+gas|inventory))|(?:(?:emissions?|GHG|greenhouse\s+gas|inventory).{0,100}(?:assurance|verification|verified|audited?).{0,100}\b(?:EY|Ernst\s+&\s+Young)\b)",
            "assurance_provider_kpmg": r"(?:\bKPMG\b.{0,100}(?:assurance|verification|verified|audited?).{0,100}(?:emissions?|GHG|greenhouse\s+gas|inventory))|(?:(?:emissions?|GHG|greenhouse\s+gas|inventory).{0,100}(?:assurance|verification|verified|audited?).{0,100}\bKPMG\b)",
            "assurance_provider_pwc": r"(?:\b(?:PwC|PricewaterhouseCoopers)\b.{0,100}(?:assurance|verification|verified|audited?).{0,100}(?:emissions?|GHG|greenhouse\s+gas|inventory))|(?:(?:emissions?|GHG|greenhouse\s+gas|inventory).{0,100}(?:assurance|verification|verified|audited?).{0,100}\b(?:PwC|PricewaterhouseCoopers)\b)",

            # Base year and recalculation
            "base_year": r"\bbase\s+year\s+(\d{4})",
            "baseline_year": r"\bbaseline\s+year\s+(\d{4})",
            "recalculation_policy": r"\brecalculation\s+(policy|approach|methodology)",

            # Comprehensive disclosure indicators
            "scope_123_comprehensive": r"\bScope\s+1,\s*2,?\s*(and|&)?\s*3\s+(emissions?|disclosure)",
            "value_chain_emissions": r"\bvalue\s+chain\s+emissions?\b",
            "supplier_emissions": r"\bsupplier\s+(emissions?|carbon|GHG)",

            # Uncertainty and materiality
            "uncertainty": r"\buncertainty\b.{0,30}(emissions?|GHG|inventory)",
            "materiality_threshold": r"\bmateriality\s+threshold\b.{0,30}(emissions?|GHG)"
        }

        self.compile_patterns(patterns)

    def match(self, text: str, page_offsets: dict[int, int]) -> List[Match]:
        """
        Find all GHG-related evidence in text.

        Args:
            text: Full text of SEC filing
            page_offsets: Dictionary mapping page numbers to character offsets

        Returns:
            List of Match objects for GHG evidence
        """
        matches = []

        for pattern_name, pattern in self.patterns.items():
            for regex_match in pattern.finditer(text):
                # Extract context window
                context_before, context_after = self.extract_context_window(
                    text, regex_match.start(), regex_match.end()
                )

                # Estimate page number
                page_no = self.estimate_page_number(regex_match.start(), page_offsets)

                # Create Match object
                match = Match(
                    pattern_name=pattern_name,
                    match_text=regex_match.group(0),
                    span_start=regex_match.start(),
                    span_end=regex_match.end(),
                    context_before=context_before,
                    context_after=context_after,
                    page_no=page_no,
                    metadata={}
                )

                # Check for negation (reduces false positives)
                if not self.check_negation(match.match_text, context_before):
                    matches.append(match)

        return matches

    def classify_evidence_type(self, match: Match) -> str:
        """
        Classify GHG evidence type based on pattern name.

        Args:
            match: Match object from match() method

        Returns:
            Evidence type string (e.g., "scope_1_disclosure", "limited_assurance")
        """
        pattern_name = match.pattern_name.lower()

        # Assurance evidence types (highest priority for stage classification)
        if "reasonable_assurance" in pattern_name:
            return "reasonable_assurance"
        if "limited_assurance" in pattern_name:
            return "limited_assurance"

        # Scope disclosure patterns
        if "scope_123_comprehensive" in pattern_name:
            return "scope_1_2_3_comprehensive"
        if "scope_1" in pattern_name:
            return "scope_1_disclosure"
        if "scope_2" in pattern_name:
            return "scope_2_disclosure"
        if "scope_3" in pattern_name or "value_chain" in pattern_name:
            return "scope_3_disclosure"

        # Methodology evidence
        if "ghg_protocol" in pattern_name:
            return "ghg_protocol_compliance"
        if "iso_14064" in pattern_name:
            return "iso_14064_compliance"

        # Assurance providers
        if "assurance_provider" in pattern_name:
            return "assurance_provider_big4"

        # Base year and recalculation
        if "base_year" in pattern_name or "baseline_year" in pattern_name:
            return "base_year_disclosure"
        if "recalculation" in pattern_name:
            return "recalculation_policy"

        # Emissions values
        if "emissions_value" in pattern_name:
            return "emissions_quantification"

        # Supplier engagement
        if "supplier" in pattern_name:
            return "supplier_engagement_scope3"

        # Default
        return "ghg_general_disclosure"

    def get_stage_indicator(self, evidence_type: str) -> int:
        """
        Map GHG evidence type to maturity stage (0-4).

        Mapping aligned with ESG Maturity Rubric v3.0:
        - Stage 0: No emissions accounting
        - Stage 1: Partial Scope 1/2 estimates without methodology (1 evidence type)
        - Stage 2: Scope 1/2 complete + partial Scope 3 + methodology (scope_1_2_complete)
        - Stage 3: Comprehensive Scope 1/2/3 + limited assurance (limited_assurance)
        - Stage 4: Reasonable assurance + GHG Protocol compliance (reasonable_assurance)

        Args:
            evidence_type: Evidence type from classify_evidence_type()

        Returns:
            Stage indicator (0-4)

        Raises:
            ValueError: If evidence_type is not recognized
        """
        # Stage 4 indicators (Leading)
        if evidence_type == "reasonable_assurance":
            return 4

        # Stage 3 indicators (Advanced)
        if evidence_type in [
            "limited_assurance",
            "scope_1_2_3_comprehensive",
            "assurance_provider_big4"
        ]:
            return 3

        # Stage 2 indicators (Intermediate)
        if evidence_type in [
            "scope_1_2_complete",
            "ghg_protocol_compliance",
            "iso_14064_compliance",
            "scope_3_disclosure",
            "base_year_disclosure",
            "recalculation_policy",
            "supplier_engagement_scope3"
        ]:
            return 2

        # Stage 1 indicators (Basic)
        if evidence_type in [
            "scope_1_disclosure",
            "scope_2_disclosure",
            "scope_1_partial",
            "emissions_quantification",
            "ghg_general_disclosure"
        ]:
            return 1

        # Unknown evidence type
        raise ValueError(
            f"Unknown evidence type: {evidence_type}. "
            f"Cannot map to stage indicator."
        )
