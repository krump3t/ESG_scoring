"""Evidence extraction parser module.

NAMING: Phase 1 of naming refactor
  Golden import paths for parser:
  - from agents.parser import EvidenceExtractionResult (canonical)
  - from agents.parser import ExtractionResult (legacy, deprecated)
"""

from .models import Evidence, Match, EvidenceExtractionResult, ExtractionResult

__all__ = ["Evidence", "Match", "EvidenceExtractionResult", "ExtractionResult"]
