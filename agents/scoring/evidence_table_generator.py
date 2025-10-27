"""Evidence Table generation for ESG maturity scoring (CP-2).

This module generates Evidence Tables with up to 10 prioritized rows per theme,
ranking evidence extracts by relevance to rubric characteristics.
"""

from dataclasses import dataclass, field
from typing import List, Optional
import re

from agents.scoring.characteristic_matcher import CharacteristicMatcher, MatchResult
from agents.scoring.rubric_models import MaturityRubric


@dataclass
class EvidenceRow:
    """Single row in Evidence Table.

    Attributes:
        priority_score: Ranking score 1-10 (10 = highest priority)
        characteristic: Matched rubric characteristic description
        evidence_extract: Evidence text (max 30 words)
        maturity_stage: Matched maturity stage (0-4)
    """
    priority_score: int
    characteristic: str
    evidence_extract: str
    maturity_stage: int

    def __post_init__(self) -> None:
        """Validate and process evidence row fields."""
        # Validate priority score
        if not (1 <= self.priority_score <= 10):
            raise ValueError(
                f"Priority score must be between 1 and 10, "
                f"got {self.priority_score}"
            )

        # Validate maturity stage
        if not (0 <= self.maturity_stage <= 4):
            raise ValueError(
                f"Maturity stage must be between 0 and 4, "
                f"got {self.maturity_stage}"
            )

        # Truncate evidence extract to 30 words max
        self.evidence_extract = self._truncate_to_words(
            self.evidence_extract,
            max_words=30
        )

    def _truncate_to_words(self, text: str, max_words: int) -> str:
        """Truncate text to maximum number of words.

        Args:
            text: Input text
            max_words: Maximum word count

        Returns:
            Truncated text with ellipsis if shortened
        """
        words = text.split()
        if len(words) <= max_words:
            return text

        # Truncate and add ellipsis
        truncated = " ".join(words[:max_words])
        return f"{truncated}..."


class EvidenceTableGenerator:
    """Generator for Evidence Tables with prioritized evidence rows.

    Creates Evidence Tables with up to 10 rows per theme, ranking evidence
    by similarity to rubric characteristics for ESG maturity assessment.

    Attributes:
        matcher: Characteristic matcher for semantic similarity
        max_rows: Maximum rows in evidence table (default: 10)
    """

    def __init__(
        self,
        matcher: CharacteristicMatcher,
        max_rows: int = 10
    ) -> None:
        """Initialize evidence table generator.

        Args:
            matcher: Configured characteristic matcher
            max_rows: Maximum rows in output table

        Raises:
            ValueError: If max_rows is not positive
        """
        if max_rows <= 0:
            raise ValueError(f"max_rows must be positive, got {max_rows}")

        self.matcher = matcher
        self.max_rows = max_rows

    def generate_table(
        self,
        evidence_extracts: List[str],
        theme: str,
        rubric: MaturityRubric
    ) -> List[EvidenceRow]:
        """Generate Evidence Table for theme.

        Args:
            evidence_extracts: List of evidence texts from sustainability reports
            theme: Theme ID (e.g., "target_setting")
            rubric: Complete maturity rubric

        Returns:
            List of EvidenceRow objects, prioritized by similarity (max 10 rows)

        Raises:
            ValueError: If evidence_extracts is empty
        """
        if not evidence_extracts:
            raise ValueError("Evidence extracts list cannot be empty")

        # Match all evidence to characteristics
        match_results: List[MatchResult] = []
        for evidence in evidence_extracts:
            try:
                result = self.matcher.match_evidence_to_characteristic(
                    evidence_extract=evidence,
                    theme=theme,
                    rubric=rubric
                )
                match_results.append(result)
            except Exception as e:
                # Skip evidence that fails to match
                continue

        if not match_results:
            raise RuntimeError(
                f"No evidence could be matched for theme '{theme}'"
            )

        # Sort by similarity score (descending)
        match_results.sort(key=lambda r: r.similarity_score, reverse=True)

        # Take top N results
        top_matches = match_results[:self.max_rows]

        # Convert to Evidence Rows with priority scores
        evidence_table: List[EvidenceRow] = []
        for i, match in enumerate(top_matches):
            # Calculate priority score (10 for highest, down to 1)
            priority_score = self._calculate_priority_score(
                similarity=match.similarity_score,
                rank=i,
                total_matches=len(top_matches)
            )

            row = EvidenceRow(
                priority_score=priority_score,
                characteristic=match.characteristic.description,
                evidence_extract=match.evidence_extract,
                maturity_stage=match.characteristic.stage
            )
            evidence_table.append(row)

        return evidence_table

    def _calculate_priority_score(
        self,
        similarity: float,
        rank: int,
        total_matches: int
    ) -> int:
        """Calculate priority score (1-10) based on similarity and rank.

        Priority score combines similarity score and relative rank position.

        Args:
            similarity: Cosine similarity score (0-1)
            rank: Position in ranked list (0 = highest)
            total_matches: Total number of matches

        Returns:
            Priority score from 1 to 10
        """
        # High similarity (>0.85) → 9-10
        # Medium similarity (0.70-0.85) → 5-8
        # Lower similarity (<0.70) → 1-4

        if similarity >= 0.85:
            base_score = 9
        elif similarity >= 0.75:
            base_score = 7
        elif similarity >= 0.65:
            base_score = 5
        else:
            base_score = 3

        # Adjust by rank (top-ranked items get +1, bottom-ranked -1)
        rank_adjustment = 0
        if total_matches > 1:
            if rank == 0:  # Top ranked
                rank_adjustment = 1
            elif rank == total_matches - 1:  # Bottom ranked
                rank_adjustment = -1

        priority_score = base_score + rank_adjustment

        # Clamp to [1, 10] range
        return max(1, min(10, priority_score))


def generate_evidence_table(
    evidence_extracts: List[str],
    theme: str,
    rubric: MaturityRubric,
    matcher: CharacteristicMatcher,
    max_rows: int = 10
) -> List[EvidenceRow]:
    """Standalone function to generate Evidence Table.

    Convenience function that creates generator and produces table in one call.

    Args:
        evidence_extracts: List of evidence texts
        theme: Theme ID
        rubric: Maturity rubric
        matcher: Characteristic matcher
        max_rows: Maximum rows (default: 10)

    Returns:
        List of EvidenceRow objects
    """
    generator = EvidenceTableGenerator(matcher=matcher, max_rows=max_rows)
    return generator.generate_table(
        evidence_extracts=evidence_extracts,
        theme=theme,
        rubric=rubric
    )
