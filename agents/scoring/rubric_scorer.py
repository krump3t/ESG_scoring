"""
Rubric Scorer: Evidence-First ESG Maturity Scoring

Loads rubric from rubrics/maturity_v3.json (canonical source).
Enforces ≥2 quotes per theme; refuses stage > 0 without sufficient evidence.

SCA v13.8 Authenticity Refactor - CP Module
"""

from typing import Dict, List, Any, Optional
from pathlib import Path
import json
import logging

logger = logging.getLogger(__name__)


class RubricScorer:
    """Evidence-first scorer for ESG maturity."""

    # Minimum quotes required per theme
    MIN_QUOTES_PER_THEME = 2

    def __init__(self, rubric_path: str = "rubrics/maturity_v3.json"):
        """
        Initialize scorer with canonical rubric.

        Args:
            rubric_path: Path to maturity_v3.json (canonical)
        """
        self.rubric_path = Path(rubric_path)
        self.rubric = self._load_rubric()

    def _load_rubric(self) -> Dict[str, Any]:
        """Load canonical rubric from JSON."""
        if not self.rubric_path.exists():
            raise FileNotFoundError(f"Rubric not found at {self.rubric_path}")

        try:
            rubric = json.loads(self.rubric_path.read_text())
            if not isinstance(rubric, dict):
                raise ValueError("Rubric must be a JSON object")
            return rubric
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in rubric: {e}")

    def score(
        self,
        theme: str,
        evidence: List[Dict[str, Any]],
        org_id: str,
        year: Optional[int] = None,
        snapshot_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Score a theme with evidence-first enforcement.

        Args:
            theme: ESG theme (e.g., "Climate")
            evidence: List of evidence records with extract_30w, doc_id
            org_id: Organization ID
            year: Reporting year (optional)
            snapshot_id: Snapshot ID (optional)

        Returns:
            Score record with stage, confidence, evidence_ids
        """
        # Enforce: stage 0 if < MIN_QUOTES_PER_THEME quotes
        if len(evidence) < self.MIN_QUOTES_PER_THEME:
            return {
                "org_id": org_id,
                "theme_code": theme,
                "stage": 0,
                "confidence": 0.0,
                "evidence_ids": [],
                "frameworks": [],
                "year": year or 0,
                "snapshot_id": snapshot_id or "",
                "doc_manifest_uri": "artifacts/ingestion/manifest.json"
            }

        # With ≥2 quotes, assess evidence quality to determine stage
        stage, confidence = self._assess_evidence(theme, evidence)

        evidence_ids = [
            ev.get("evidence_id", f"ev_{i}")
            for i, ev in enumerate(evidence)
        ]

        return {
            "org_id": org_id,
            "theme_code": theme,
            "stage": stage,
            "confidence": confidence,
            "evidence_ids": evidence_ids,
            "frameworks": self._extract_frameworks(evidence),
            "year": year or 0,
            "snapshot_id": snapshot_id or "",
            "doc_manifest_uri": "artifacts/ingestion/manifest.json"
        }

    def _assess_evidence(self, theme: str, evidence: List[Dict[str, Any]]) -> tuple[int, float]:
        """
        Assess evidence quality to determine stage and confidence.

        Args:
            theme: ESG theme
            evidence: Evidence records (guaranteed ≥2 quotes)

        Returns:
            (stage: int, confidence: float)
        """
        # Basic heuristic: word count and keywords
        total_words = sum(
            len(ev.get("extract_30w", "").split())
            for ev in evidence
        )

        avg_words = total_words / len(evidence) if evidence else 0

        # Stages based on evidence quality
        if avg_words < 10:
            stage = 1
            confidence = 0.5
        elif avg_words < 20:
            stage = 2
            confidence = 0.65
        else:
            stage = 3
            confidence = 0.8

        # Cap at stage 4 if very comprehensive
        if len(evidence) >= 5 and avg_words >= 25:
            stage = 4
            confidence = 0.9

        return stage, min(confidence, 1.0)

    def _extract_frameworks(self, evidence: List[Dict[str, Any]]) -> List[str]:
        """Extract frameworks mentioned in evidence."""
        frameworks = set()

        framework_keywords = {
            "TCFD": ["TCFD", "Task Force on Climate"],
            "GRI": ["GRI", "Global Reporting Initiative"],
            "SASB": ["SASB"],
            "CDP": ["CDP"],
            "SBTi": ["SBTi", "Science Based Targets"],
            "GHG Protocol": ["GHG Protocol"],
            "RE100": ["RE100"],
            "ISO 14001": ["ISO 14001"],
            "ISSB": ["ISSB"]
        }

        for ev in evidence:
            text = ev.get("extract_30w", "").lower()
            for framework, keywords in framework_keywords.items():
                if any(kw.lower() in text for kw in keywords):
                    frameworks.add(framework)

        return sorted(list(frameworks))
