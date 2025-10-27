"""
Base matcher interface for theme-specific evidence extraction.

All theme matchers (TSP, OSP, DM, GHG, RD, EI, RMM) inherit from BaseMatcher
and implement theme-specific pattern matching logic.
"""

from abc import ABC, abstractmethod
from typing import List, Pattern
import re

from ..models import Match


class BaseMatcher(ABC):
    """
    Abstract base class for theme-specific evidence matchers.

    Each theme matcher implements:
    1. Regex patterns for evidence keywords
    2. match() method to find evidence in text
    3. Theme-specific evidence type classification
    4. Stage indicator mapping (evidence type → stage 0-4)

    Attributes:
        theme: Theme code (TSP|OSP|DM|GHG|RD|EI|RMM)
        patterns: Dictionary mapping pattern names to compiled regex patterns
    """

    def __init__(self, theme: str):
        """
        Initialize base matcher.

        Args:
            theme: Theme code (must be validated by subclass)

        Raises:
            ValueError: If theme is not valid
        """
        valid_themes = {"TSP", "OSP", "DM", "GHG", "RD", "EI", "RMM"}
        if theme not in valid_themes:
            raise ValueError(
                f"Invalid theme '{theme}'. Must be one of {valid_themes}"
            )
        self.theme = theme
        self.patterns: dict[str, Pattern[str]] = {}

    def compile_patterns(self, pattern_dict: dict[str, str]) -> None:
        """
        Compile regex patterns for matching.

        Args:
            pattern_dict: Dictionary mapping pattern names to regex strings

        Raises:
            re.error: If pattern compilation fails
        """
        self.patterns = {
            name: re.compile(pattern, re.IGNORECASE | re.MULTILINE)
            for name, pattern in pattern_dict.items()
        }

    @abstractmethod
    def match(self, text: str, page_offsets: dict[int, int]) -> List[Match]:
        """
        Find all evidence matches in text.

        Args:
            text: Full text of SEC filing (HTML stripped)
            page_offsets: Dictionary mapping page numbers to character offsets

        Returns:
            List of Match objects (may be empty if no matches found)

        Note:
            Implementations should:
            1. Apply regex patterns to text
            2. Extract match text and surrounding context
            3. Estimate page number from span position
            4. Return Match objects (not Evidence - confidence scoring happens later)
        """
        pass

    @abstractmethod
    def classify_evidence_type(self, match: Match) -> str:
        """
        Classify evidence type based on match pattern and content.

        Args:
            match: Match object from match() method

        Returns:
            Evidence type string (e.g., "SBTi_validated", "limited_assurance")

        Note:
            Evidence types map to stage indicators in get_stage_indicator()
        """
        pass

    @abstractmethod
    def get_stage_indicator(self, evidence_type: str) -> int:
        """
        Map evidence type to stage indicator (0-4).

        Args:
            evidence_type: Evidence type from classify_evidence_type()

        Returns:
            Stage indicator (0-4)

        Raises:
            ValueError: If evidence_type is not recognized

        Note:
            Mapping should align with ESG Maturity Rubric v3.0 stage descriptors
        """
        pass

    def extract_context_window(
        self,
        text: str,
        span_start: int,
        span_end: int,
        window_words: int = 15
    ) -> tuple[str, str]:
        """
        Extract context window around match (15 words before, 15 words after).

        Args:
            text: Full text
            span_start: Match start position
            span_end: Match end position
            window_words: Number of words to extract before/after (default 15)

        Returns:
            Tuple of (context_before, context_after)

        Note:
            ADR-002 specifies 30-word windows (15 before + 15 after)
        """
        # Extract text before match
        before_text = text[:span_start]
        before_words = before_text.split()[-window_words:]
        context_before = " ".join(before_words)

        # Extract text after match
        after_text = text[span_end:]
        after_words = after_text.split()[:window_words]
        context_after = " ".join(after_words)

        return context_before, context_after

    def estimate_page_number(
        self,
        span_start: int,
        page_offsets: dict[int, int]
    ) -> int:
        """
        Estimate page number from character offset.

        Args:
            span_start: Character offset of match
            page_offsets: Dictionary mapping page numbers to character offsets
                         (e.g., {1: 0, 2: 3000, 3: 6000, ...})

        Returns:
            Estimated page number (1-indexed)

        Note:
            Page numbers are approximate for HTML filings (Assumption A9).
            If page_offsets is empty, uses heuristic (3000 chars/page).
        """
        if not page_offsets:
            # Fallback heuristic: assume ~3000 characters per page
            return max(1, span_start // 3000 + 1)

        # Find the page whose offset is closest to (but not greater than) span_start
        page_no = 1
        for page, offset in sorted(page_offsets.items()):
            if offset <= span_start:
                page_no = page
            else:
                break

        return page_no

    def check_negation(self, match_text: str, context_before: str) -> bool:
        """
        Check if match is negated by surrounding context.

        Args:
            match_text: The matched text
            context_before: Text before the match

        Returns:
            True if negation detected, False otherwise

        Note:
            Negation detection reduces false positives from phrases like
            "we do not have SBTi targets" or "no Scope 3 disclosure"
        """
        negation_patterns = [
            r'\b(no|not|never|without|lack|lacking)\b',
            r'\b(absence\s+of)\b',
            r'\b(do\s+not|does\s+not|did\s+not|will\s+not|cannot|have\s+no)\b',
        ]

        # Check last 100 characters of context_before
        context_check = context_before[-100:].lower()

        for pattern in negation_patterns:
            if re.search(pattern, context_check, re.IGNORECASE):
                return True

        return False

    def __repr__(self) -> str:
        """String representation of matcher."""
        return f"{self.__class__.__name__}(theme='{self.theme}', patterns={len(self.patterns)})"
