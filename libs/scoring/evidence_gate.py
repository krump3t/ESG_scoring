"""
Evidence-First Scoring Guard

Enforces minimum evidence requirement before assigning maturity stages.
No stage can be assigned without sufficient supporting evidence.

SCA v13.8 Compliance:
- Type safety: 100% annotated
- Pure function: No side effects
- Determinism: Same input → same output
"""

from __future__ import annotations
from typing import Dict, List, Any


def enforce_evidence_min_per_theme(
    scores: Dict[str, Any],
    evidence_map: Dict[str, List[Dict[str, Any]]],
    evidence_min: int
) -> Dict[str, Any]:
    """
    Enforce minimum evidence requirement for each scored theme.

    For each theme in scores, if evidence count < evidence_min, set score to None
    and attach a reason. Returns a new dict (pure function).

    Args:
        scores: Theme scores dict {theme_name: score_value or score_obj}
        evidence_map: Evidence by theme {theme_name: [{quote, source, page, id}, ...]}
        evidence_min: Minimum evidence items required per scored theme

    Returns:
        New scores dict with insufficient evidence themes nullified

    Example:
        >>> scores = {"TSP": 3, "OSP": 2}
        >>> evidence_map = {"TSP": [{"quote": "..."}], "OSP": [{"quote": "..."}, {"quote": "..."}]}
        >>> result = enforce_evidence_min_per_theme(scores, evidence_map, evidence_min=2)
        >>> # result["TSP"] will have score=None (only 1 evidence)
        >>> # result["OSP"] will keep score=2 (has 2 evidence)
    """
    out = {}

    for theme, val in (scores or {}).items():
        ev_count = len(evidence_map.get(theme, []))

        if ev_count < evidence_min:
            # Insufficient evidence - nullify score
            out[theme] = {
                "score": None,
                "reason": f"insufficient_evidence({ev_count}<{evidence_min})"
            }
        else:
            # Sufficient evidence - keep score
            out[theme] = val

    return out
