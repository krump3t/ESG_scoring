"""
Explainability Handler for Score Explanations
Critical Path: Provides detailed reasoning for maturity scores
"""
from typing import List, Dict, Any, Optional
import logging
from collections import defaultdict

from mcp_server.models.requests import ExplainScoreRequest
from mcp_server.models.responses import (
    ExplainScoreResponse,
    ScoreExplanation,
    FindingEvidence
)

logger = logging.getLogger(__name__)


async def handle_explain_score(
    request: ExplainScoreRequest,
    run_id: str
) -> ExplainScoreResponse:
    """
    Handle score explanation request

    Args:
        request: Explain score request
        run_id: Run identifier for traceability

    Returns:
        Score explanation response with detailed reasoning
    """
    logger.info(f"[{run_id}] Explain score: org={request.org_id}, year={request.year}, theme={request.theme}")

    # Query gold layer for scores
    scores = await query_scores_for_explanation(
        request.org_id,
        request.year,
        request.theme,
        request.score_id
    )

    if not scores:
        # Return default response
        return ExplainScoreResponse(
            success=False,
            org_id=request.org_id,
            year=request.year,
            theme=request.theme,
            explanation=ScoreExplanation(
                score_id="none",
                maturity_level=0,
                maturity_label="None",
                reasoning="No scores found for this organization/year/theme",
                evidence=[],
                framework_mappings={},
                confidence_breakdown={}
            ),
            metadata={
                "timestamp": _get_timestamp(),
                "run_id": run_id,
                "error": "No data available"
            }
        )

    # Build explanation
    explanation = build_explanation(scores, request.theme)

    response = ExplainScoreResponse(
        success=True,
        org_id=request.org_id,
        year=request.year,
        theme=request.theme,
        explanation=explanation,
        metadata={
            "timestamp": _get_timestamp(),
            "run_id": run_id,
            "scores_analyzed": len(scores)
        }
    )

    logger.info(f"[{run_id}] Explanation complete: {len(explanation.evidence)} evidence points")

    return response


async def query_scores_for_explanation(
    org_id: str,
    year: int,
    theme: str,
    score_id: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Query scores for explanation - REAL DATA ONLY

    Queries actual gold layer Parquet files

    Args:
        org_id: Organization identifier
        year: Reporting year
        theme: ESG theme
        score_id: Optional specific score ID

    Returns:
        List of score dictionaries from actual storage
    """
    from mcp_server.orchestrator import PipelineOrchestrator

    logger.info(f"Querying REAL scores for explanation: org_id={org_id}, year={year}, theme={theme}")

    # Use real orchestrator
    orchestrator = PipelineOrchestrator()

    # Get actual scores
    scores = orchestrator.get_maturity_scores(org_id, year, theme)

    # Filter by score_id if specified
    if score_id:
        scores = [s for s in scores if s.get('score_id') == score_id]

    logger.info(f"Retrieved {len(scores)} REAL scores for explanation")

    return scores


def build_explanation(
    scores: List[Dict[str, Any]],
    theme: str
) -> ScoreExplanation:
    """
    Build detailed explanation from scores

    Args:
        scores: List of score dictionaries
        theme: ESG theme

    Returns:
        Score explanation with reasoning and evidence
    """
    if not scores:
        return ScoreExplanation(
            score_id="none",
            maturity_level=0,
            maturity_label="None",
            reasoning="No evidence available",
            evidence=[],
            framework_mappings={},
            confidence_breakdown={}
        )

    # Use highest-confidence score as primary
    primary_score = max(scores, key=lambda x: x.get('confidence', 0.0))

    # Build reasoning
    reasoning = build_reasoning_text(primary_score, scores, theme)

    # Extract evidence
    evidence = extract_evidence_points(scores)

    # Build framework mappings
    framework_mappings = build_framework_mappings(scores)

    # Build confidence breakdown
    confidence_breakdown = build_confidence_breakdown(scores)

    return ScoreExplanation(
        score_id=primary_score.get('score_id', 'unknown'),
        maturity_level=primary_score.get('maturity_level', 0),
        maturity_label=primary_score.get('maturity_label', 'Unknown'),
        reasoning=reasoning,
        evidence=evidence,
        framework_mappings=framework_mappings,
        confidence_breakdown=confidence_breakdown
    )


def build_reasoning_text(
    primary_score: Dict[str, Any],
    all_scores: List[Dict[str, Any]],
    theme: str
) -> str:
    """Build natural language reasoning"""
    maturity_level = primary_score.get('maturity_level', 0)
    maturity_label = primary_score.get('maturity_label', 'Unknown')
    confidence = primary_score.get('confidence', 0.0)
    framework = primary_score.get('framework', '')

    reasoning_parts = []

    # Main assessment
    reasoning_parts.append(
        f"The organization achieved a maturity level of {maturity_level} ({maturity_label}) "
        f"for {theme} with {confidence:.0%} confidence."
    )

    # Framework mentions
    if framework:
        reasoning_parts.append(
            f"This assessment is based on evidence aligned with the {framework} framework."
        )

    # Evidence count
    evidence_count = len(all_scores)
    reasoning_parts.append(
        f"The score is supported by {evidence_count} distinct finding(s) "
        f"from the organization's sustainability disclosure."
    )

    # Key strengths
    high_conf_scores = [s for s in all_scores if s.get('confidence', 0) > 0.75]
    if high_conf_scores:
        reasoning_parts.append(
            f"Strong evidence was found in {len(high_conf_scores)} findings with high confidence (>75%)."
        )

    return " ".join(reasoning_parts)


def extract_evidence_points(
    scores: List[Dict[str, Any]]
) -> List[FindingEvidence]:
    """Extract evidence points from scores"""
    evidence = []

    # Sort by confidence
    sorted_scores = sorted(
        scores,
        key=lambda x: x.get('confidence', 0.0),
        reverse=True
    )

    for score in sorted_scores:
        finding = FindingEvidence(
            finding_id=score.get('finding_id', 'unknown'),
            finding_text=score.get('reasoning', 'Evidence not available'),
            page_number=0,  # Would fetch from silver layer
            framework=score.get('framework', ''),
            confidence=score.get('confidence', 0.0)
        )
        evidence.append(finding)

    return evidence


def build_framework_mappings(
    scores: List[Dict[str, Any]]
) -> Dict[str, int]:
    """Build framework to maturity level mappings"""
    framework_scores = defaultdict(list)

    for score in scores:
        framework = score.get('framework', 'Unknown')
        maturity = score.get('maturity_level', 0)
        if framework:
            framework_scores[framework].append(maturity)

    # Average maturity per framework
    framework_mappings = {}
    for framework, levels in framework_scores.items():
        avg_level = round(sum(levels) / len(levels)) if levels else 0
        framework_mappings[framework] = avg_level

    return framework_mappings


def build_confidence_breakdown(
    scores: List[Dict[str, Any]]
) -> Dict[str, float]:
    """Build confidence breakdown by factor"""
    breakdown = {}

    # Calculate average confidence
    confidences = [s.get('confidence', 0.0) for s in scores]
    avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0

    breakdown['overall'] = round(avg_confidence, 3)

    # Evidence quality (based on confidence variance)
    if len(confidences) > 1:
        variance = sum((c - avg_confidence) ** 2 for c in confidences) / len(confidences)
        consistency = max(0.0, 1.0 - variance)
        breakdown['consistency'] = round(consistency, 3)

    # Framework alignment (has framework or not)
    with_framework = sum(1 for s in scores if s.get('framework'))
    framework_ratio = with_framework / len(scores) if scores else 0.0
    breakdown['framework_alignment'] = round(framework_ratio, 3)

    return breakdown


def _get_timestamp() -> str:
    """Get current timestamp in ISO format"""
    from datetime import datetime
    return datetime.utcnow().isoformat() + "Z"
