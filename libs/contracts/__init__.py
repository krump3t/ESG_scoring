"""Data ingestion and extraction contracts (Pydantic models).

NAMING: Phase 1 of naming refactor
  Golden import paths for contracts:
  - from libs.contracts import MetricsExtractionResult (canonical)
  - from libs.contracts import ExtractionResult (legacy, deprecated)
"""

from .ingestion_contracts import CompanyRef, SourceRef, CompanyReport
from .extraction_contracts import (
    ExtractionQuality,
    ExtractionError,
    MetricsExtractionResult,
    ExtractionResult,  # legacy alias
)

__all__ = [
    "CompanyRef",
    "SourceRef",
    "CompanyReport",
    "ExtractionQuality",
    "ExtractionError",
    "MetricsExtractionResult",
    "ExtractionResult",  # legacy
]
