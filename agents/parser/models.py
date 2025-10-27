"""
Data models for ESG evidence extraction.

This module defines the core data structures used throughout the evidence
extraction pipeline, aligned with the ESG Maturity Rubric v3.0 schema.
"""

from dataclasses import dataclass, field
from typing import Optional, Any
from datetime import datetime
import hashlib
import uuid


@dataclass(frozen=True)
class Evidence:
    """
    Immutable evidence item extracted from SEC filings.

    Represents a single piece of evidence for ESG maturity assessment,
    aligned with ESG Maturity Rubric v3.0 (line 116-122).

    Attributes:
        evidence_id: Unique identifier (UUID v4)
        org_id: Organization identifier (CIK or company name)
        year: Fiscal year of the filing
        theme: ESG theme (TSP|OSP|DM|GHG|RD|EI|RMM)
        stage_indicator: Maturity stage indicator (0-4)
        doc_id: Document identifier (e.g., "10-K_2025_AAPL")
        page_no: Approximate page number in original filing
        span_start: Character offset of match start in document
        span_end: Character offset of match end in document
        extract_30w: 30-word context window (15 before + match + 15 after)
        hash_sha256: SHA256 hash of extract_30w for deduplication
        confidence: Confidence score (0.0-1.0)
        evidence_type: Evidence classification (e.g., "SBTi_validated")
        snapshot_id: Extraction run identifier
    """

    evidence_id: str
    org_id: str
    year: int
    theme: str
    stage_indicator: int
    doc_id: str
    page_no: int
    span_start: int
    span_end: int
    extract_30w: str
    hash_sha256: str
    confidence: float
    evidence_type: str
    snapshot_id: str

    def __post_init__(self) -> None:
        """Validate evidence fields after initialization."""
        # Validate theme
        valid_themes = {"TSP", "OSP", "DM", "GHG", "RD", "EI", "RMM"}
        if self.theme not in valid_themes:
            raise ValueError(
                f"Invalid theme '{self.theme}'. Must be one of {valid_themes}"
            )

        # Validate stage_indicator
        if not 0 <= self.stage_indicator <= 4:
            raise ValueError(
                f"Invalid stage_indicator {self.stage_indicator}. Must be 0-4"
            )

        # Validate confidence
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(
                f"Invalid confidence {self.confidence}. Must be 0.0-1.0"
            )

        # Validate year
        if not 1900 <= self.year <= 2100:
            raise ValueError(
                f"Invalid year {self.year}. Must be 1900-2100"
            )

        # Validate span
        if self.span_start < 0 or self.span_end < 0:
            raise ValueError("Span positions must be non-negative")
        if self.span_start >= self.span_end:
            raise ValueError("span_start must be less than span_end")

        # Validate page_no
        if self.page_no < 0:
            raise ValueError("page_no must be non-negative")

    @staticmethod
    def create_hash(text: str) -> str:
        """
        Create SHA256 hash of text for deduplication.

        Args:
            text: Text to hash (typically extract_30w)

        Returns:
            Lowercase hexadecimal SHA256 hash
        """
        return hashlib.sha256(text.encode('utf-8')).hexdigest()

    @staticmethod
    def generate_evidence_id() -> str:
        """Generate UUID v4 for evidence_id."""
        return str(uuid.uuid4())

    def to_dict(self) -> dict[str, Any]:
        """Convert evidence to dictionary for JSON serialization."""
        return {
            "evidence_id": self.evidence_id,
            "org_id": self.org_id,
            "year": self.year,
            "theme": self.theme,
            "stage_indicator": self.stage_indicator,
            "doc_id": self.doc_id,
            "page_no": self.page_no,
            "span_start": self.span_start,
            "span_end": self.span_end,
            "extract_30w": self.extract_30w,
            "hash_sha256": self.hash_sha256,
            "confidence": self.confidence,
            "evidence_type": self.evidence_type,
            "snapshot_id": self.snapshot_id
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Evidence":
        """Create Evidence instance from dictionary."""
        return cls(**data)


@dataclass
class Match:
    """
    Represents a pattern match before confidence scoring and stage assignment.

    Intermediate data structure used by matchers to return raw pattern matches
    before they are converted to Evidence objects.

    Attributes:
        pattern_name: Name of the regex pattern that matched
        match_text: The actual text that matched the pattern
        span_start: Character offset of match start
        span_end: Character offset of match end
        context_before: Text before the match (for 30w window)
        context_after: Text after the match (for 30w window)
        page_no: Approximate page number
        metadata: Optional additional metadata about the match
    """

    pattern_name: str
    match_text: str
    span_start: int
    span_end: int
    context_before: str
    context_after: str
    page_no: int
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate match fields."""
        if self.span_start < 0 or self.span_end < 0:
            raise ValueError("Span positions must be non-negative")
        if self.span_start >= self.span_end:
            raise ValueError("span_start must be less than span_end")
        if self.page_no < 0:
            raise ValueError("page_no must be non-negative")


@dataclass
class ExtractionResult:
    """
    Result of extracting evidence from a single filing.

    Attributes:
        company_name: Name of the company
        year: Fiscal year
        doc_id: Document identifier
        evidence_by_theme: Dictionary mapping theme to list of Evidence objects
        extraction_timestamp: ISO 8601 timestamp of extraction
        snapshot_id: Extraction run identifier
        metadata: Additional metadata (processing time, file size, etc.)
    """

    company_name: str
    year: int
    doc_id: str
    evidence_by_theme: dict[str, list[Evidence]]
    extraction_timestamp: str
    snapshot_id: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def get_total_evidence_count(self) -> int:
        """Get total count of evidence items across all themes."""
        return sum(len(ev_list) for ev_list in self.evidence_by_theme.values())

    def get_theme_count(self) -> int:
        """Get count of themes with evidence."""
        return sum(1 for ev_list in self.evidence_by_theme.values() if ev_list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "company_name": self.company_name,
            "year": self.year,
            "doc_id": self.doc_id,
            "evidence_by_theme": {
                theme: [ev.to_dict() for ev in evidence_list]
                for theme, evidence_list in self.evidence_by_theme.items()
            },
            "extraction_timestamp": self.extraction_timestamp,
            "snapshot_id": self.snapshot_id,
            "metadata": self.metadata,
            "summary": {
                "total_evidence_count": self.get_total_evidence_count(),
                "theme_count": self.get_theme_count()
            }
        }
