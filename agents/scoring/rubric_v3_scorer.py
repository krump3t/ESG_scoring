"""Deterministic scorer for ESG rubric v3 artifacts."""

from __future__ import annotations

import math
from dataclasses import dataclass
from statistics import mean
from typing import Any, Dict, List, Mapping, Sequence

from agents.scoring.rubric_loader import RubricLoader
from agents.scoring.rubric_models import MaturityRubric, StageCharacteristic


@dataclass(frozen=True)
class DimensionScore:
    """Score for a single rubric dimension."""

    score: int
    evidence: str
    confidence: float
    stage_descriptor: str


class RubricV3Scorer:
    """Score ESG findings using the compiled rubric definition."""

    def __init__(
        self,
        loader: RubricLoader | None = None,
        rubric: MaturityRubric | None = None,
    ) -> None:
        self.loader = loader or RubricLoader()
        self.rubric: MaturityRubric = rubric or self.loader.load()
        self._theme_order: Sequence[str] = self.rubric.theme_order
        self._stage_keywords: Dict[str, Dict[int, Sequence[str]]] = {}
        self._stage_descriptors: Dict[str, Dict[int, str]] = {}
        self._prepare_lookup_structures()

    # ------------------------------------------------------------------ #
    # Public scoring API
    # ------------------------------------------------------------------ #
    def score_all_dimensions(self, finding: Mapping[str, Any]) -> Dict[str, DimensionScore]:
        """Score a finding across all rubric dimensions."""
        text = str(finding.get("finding_text", "") or "")
        framework = str(finding.get("framework", "") or "")

        scores: Dict[str, DimensionScore] = {}
        for code in self._theme_order:
            scores[code] = self._score_dimension(code, text, framework)
        return scores

    def calculate_overall_maturity(self, scores: Mapping[str, DimensionScore]) -> tuple[float, str]:
        """Aggregate dimension scores to overall maturity and descriptor label."""
        if not scores:
            raise ValueError("Score dictionary cannot be empty")

        average_score = mean(item.score for item in scores.values())
        label = self._overall_label(average_score)
        return round(average_score, 2), label

    def score_finding(self, finding: Mapping[str, Any]) -> Dict[str, Any]:
        scores = self.score_all_dimensions(finding)
        overall, label = self.calculate_overall_maturity(scores)
        aggregate_confidence = min(
            1.0,
            round(mean(item.confidence for item in scores.values()), 3),
        )
        return {
            "maturity_level": overall,
            "maturity_label": label,
            "confidence": aggregate_confidence,
            "dimension_breakdown": {
                code: payload.score for code, payload in scores.items()
            },
        }

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #
    def _prepare_lookup_structures(self) -> None:
        for theme in self.rubric.themes_in_order:
            self._stage_keywords[theme.code] = {}
            self._stage_descriptors[theme.code] = {}
            for stage in theme.ordered_stages:
                self._stage_keywords[theme.code][stage.stage] = stage.keywords
                self._stage_descriptors[theme.code][stage.stage] = stage.descriptor or stage.label

    def _score_dimension(self, theme_code: str, text: str, framework: str) -> DimensionScore:
        theme = self.rubric.get_theme(theme_code)
        combined = f"{text} {framework}".lower()

        best_stage = 0
        best_matches: List[str] = []
        for candidate in reversed(theme.ordered_stages):
            matches = _match_keywords(candidate, combined)
            if matches and (candidate.stage > best_stage or len(matches) > len(best_matches)):
                best_stage = candidate.stage
                best_matches = matches

        descriptor = self._stage_descriptors[theme_code][best_stage]
        evidence = descriptor
        if best_matches:
            evidence = f"Matched keywords: {', '.join(best_matches[:5])}"

        confidence = 0.45 + 0.12 * best_stage + 0.02 * min(len(best_matches), 5)
        confidence = round(max(0.0, min(confidence, 0.98)), 3)

        return DimensionScore(
            score=best_stage,
            evidence=evidence,
            confidence=confidence,
            stage_descriptor=descriptor or theme.get_stage(best_stage).label,
        )

    @staticmethod
    def _overall_label(score: float) -> str:
        bucket = int(math.floor(score))
        labels = {
            0: "Nascent",
            1: "Emerging",
            2: "Maturing",
            3: "Advanced",
            4: "Leading",
        }
        return labels.get(max(0, min(bucket, 4)), "Nascent")


def _match_keywords(stage: StageCharacteristic, corpus: str) -> List[str]:
    matches = [keyword for keyword in stage.keywords if keyword in corpus]
    return matches
