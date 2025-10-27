"""
Extraction Contracts - Phase 3 (Asymmetric Extraction Paths)

Defines data contracts for extraction results, quality metrics, and errors.

Author: Scientific Coding Agent v13.8-MEA
Date: 2025-10-24
"""

from dataclasses import dataclass
from typing import List, Optional
from libs.models.esg_metrics import ESGMetrics


@dataclass(frozen=True)
class ExtractionQuality:
    """Quality metrics for extracted ESG data.

    All metrics are in the range [0.0, 1.0] where 1.0 = perfect quality.
    """

    field_completeness: float  # Fraction of non-None fields (0.0 to 1.0)
    type_correctness: float    # Fraction of fields with valid types (Pydantic guarantees 1.0)
    value_validity: float      # Fraction of fields passing range validation

    def __post_init__(self) -> None:
        """Validate quality metric ranges."""
        if not (0.0 <= self.field_completeness <= 1.0):
            raise ValueError(f"field_completeness must be in [0, 1], got {self.field_completeness}")
        if not (0.0 <= self.type_correctness <= 1.0):
            raise ValueError(f"type_correctness must be in [0, 1], got {self.type_correctness}")
        if not (0.0 <= self.value_validity <= 1.0):
            raise ValueError(f"value_validity must be in [0, 1], got {self.value_validity}")

    def overall_score(self) -> float:
        """Calculate weighted overall quality score.

        Weights:
        - field_completeness: 40%
        - type_correctness: 30%
        - value_validity: 30%

        Returns:
            Overall quality score in [0.0, 1.0]
        """
        return (
            0.4 * self.field_completeness
            + 0.3 * self.type_correctness
            + 0.3 * self.value_validity
        )


@dataclass(frozen=True)
class ExtractionError:
    """Error encountered during extraction.

    Used to report field-level or document-level errors without failing the entire extraction.
    """

    field_name: Optional[str]  # Field that caused the error (None for document-level errors)
    error_type: str            # Error type (e.g., "ValidationError", "MissingField", "ParseError")
    message: str               # Human-readable error message
    severity: str              # "warning" or "error"

    def __post_init__(self) -> None:
        """Validate severity."""
        if self.severity not in {"warning", "error"}:
            raise ValueError(f"severity must be 'warning' or 'error', got {self.severity}")


@dataclass(frozen=True)
class ExtractionResult:
    """Result of extracting ESG metrics from a company report.

    Combines extracted metrics, quality assessment, and any errors encountered.
    """

    metrics: Optional[ESGMetrics]  # Extracted metrics (None if extraction failed)
    quality: ExtractionQuality     # Quality metrics
    errors: List[ExtractionError]  # Errors encountered during extraction

    def is_success(self) -> bool:
        """Check if extraction succeeded (metrics extracted with acceptable quality)."""
        return self.metrics is not None

    def has_errors(self) -> bool:
        """Check if any errors were encountered."""
        return len(self.errors) > 0

    def error_severity_counts(self) -> dict[str, int]:
        """Count errors by severity level."""
        counts = {"warning": 0, "error": 0}
        for error in self.errors:
            counts[error.severity] += 1
        return counts
