"""Scoring module for ESG maturity assessment.

NAMING: Phase 1 of naming refactor
  Golden import paths for scoring:
  - from apps.scoring import ThemeRubricV3 (canonical)
  - from apps.scoring import ThemeRubric (legacy, deprecated)
"""

from .rubric_v3_loader import ThemeRubricV3, ThemeRubric, RubricV3Loader, StageDescriptor

__all__ = ["ThemeRubricV3", "ThemeRubric", "RubricV3Loader", "StageDescriptor"]
