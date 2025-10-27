"""
Query Handler for ESG Maturity Queries
Critical Path: Queries gold layer and returns aggregated maturity scores
"""
from typing import List, Dict, Any, Optional
import logging
from collections import defaultdict

from mcp_server.models.requests import MaturityQueryRequest
from mcp_server.models.responses import (
    MaturityQueryResponse,
    FindingEvidence
)

logger = logging.getLogger(__name__)


async def handle_maturity_query(
    request: MaturityQueryRequest,
    run_id: str
) -> MaturityQueryResponse:
    """
    Handle maturity query request

    Args:
        request: Maturity query request
        run_id: Run identifier for traceability

    Returns:
        Maturity query response with aggregated scores
    """
    logger.info(f"[{run_id}] Maturity query: org={request.org_id}, year={request.year}, theme={request.theme}")

    # Query REAL gold layer - executes pipeline if needed
    scores = await query_gold_layer(
        request.org_id,
        request.year,
        request.theme
    )

    if not scores:
        # Return default response if no data
        return MaturityQueryResponse(
            success=True,
            org_id=request.org_id,
            year=request.year,
            theme=request.theme or "All",
            maturity_level=0,
            maturity_label="None",
            confidence=0.0,
            findings_count=0,
            key_findings=[],
            metadata={
                "timestamp": _get_timestamp(),
                "run_id": run_id,
                "message": "No scores found for this organization/year/theme"
            }
        )

    # Aggregate scores
    aggregated = aggregate_scores(scores, request.theme)

    # Get top evidence
    key_findings = extract_key_findings(scores, limit=5)

    response = MaturityQueryResponse(
        success=True,
        org_id=request.org_id,
        year=request.year,
        theme=request.theme or "Overall",
        maturity_level=aggregated['avg_maturity_level'],
        maturity_label=aggregated['maturity_label'],
        confidence=aggregated['avg_confidence'],
        findings_count=aggregated['total_findings'],
        key_findings=key_findings,
        snapshot_id=aggregated.get('snapshot_id'),
        metadata={
            "timestamp": _get_timestamp(),
            "run_id": run_id,
            "themes_analyzed": aggregated.get('themes', []),
            "score_distribution": aggregated.get('distribution', {})
        }
    )

    logger.info(f"[{run_id}] Query complete: maturity={response.maturity_level}, confidence={response.confidence:.2f}")

    return response


async def query_gold_layer(
    org_id: str,
    year: int,
    theme: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Query gold layer for scores - REAL DATA ONLY

    Queries actual Parquet files from MinIO gold layer
    Executes pipeline if data doesn't exist

    Args:
        org_id: Organization identifier
        year: Reporting year
        theme: Optional theme filter

    Returns:
        List of score dictionaries from actual gold layer
    """
    from mcp_server.orchestrator import PipelineOrchestrator

    logger.info(f"Querying REAL gold layer: org_id={org_id}, year={year}, theme={theme}")

    # Use real orchestrator to get scores
    orchestrator = PipelineOrchestrator()

    # This will execute pipeline if needed, then return real scores
    scores = orchestrator.get_maturity_scores(org_id, year, theme)

    logger.info(f"Retrieved {len(scores)} REAL scores from gold layer")

    return scores


def aggregate_scores(
    scores: List[Dict[str, Any]],
    theme_filter: Optional[str] = None
) -> Dict[str, Any]:
    """
    Aggregate scores across findings

    Args:
        scores: List of score dictionaries
        theme_filter: Optional theme filter

    Returns:
        Aggregated score statistics
    """
    if not scores:
        return {
            'avg_maturity_level': 0,
            'maturity_label': 'None',
            'avg_confidence': 0.0,
            'total_findings': 0,
            'themes': [],
            'distribution': {}
        }

    # Filter by theme if specified
    if theme_filter:
        scores = [s for s in scores if s.get('theme') == theme_filter]

    # Calculate averages
    maturity_levels = [s.get('maturity_level', 0) for s in scores]
    confidences = [s.get('confidence', 0.0) for s in scores]

    avg_maturity = sum(maturity_levels) / len(maturity_levels) if maturity_levels else 0
    avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0

    # Round average maturity to nearest integer
    avg_maturity_int = round(avg_maturity)

    # Map to label
    maturity_labels = {
        0: 'None',
        1: 'Basic',
        2: 'Intermediate',
        3: 'Advanced',
        4: 'Leading',
        5: 'Best-in-Class'
    }
    maturity_label = maturity_labels.get(avg_maturity_int, 'Unknown')

    # Get unique themes
    themes = list(set(s.get('theme', 'Unknown') for s in scores))

    # Calculate distribution
    distribution = {}
    for level in range(6):
        count = sum(1 for s in scores if s.get('maturity_level') == level)
        if count > 0:
            distribution[f"level_{level}"] = count

    # Get latest snapshot ID
    snapshot_id = max((s.get('gold_snapshot_id', 0) for s in scores), default=None)

    return {
        'avg_maturity_level': avg_maturity_int,
        'maturity_label': maturity_label,
        'avg_confidence': round(avg_confidence, 3),
        'total_findings': len(scores),
        'themes': themes,
        'distribution': distribution,
        'snapshot_id': snapshot_id
    }


def extract_key_findings(
    scores: List[Dict[str, Any]],
    limit: int = 5
) -> List[FindingEvidence]:
    """
    Extract top findings as evidence

    Args:
        scores: List of score dictionaries
        limit: Maximum number of findings to return

    Returns:
        List of finding evidence
    """
    # Sort by confidence (highest first)
    sorted_scores = sorted(
        scores,
        key=lambda x: x.get('confidence', 0.0),
        reverse=True
    )

    findings = []
    for score in sorted_scores[:limit]:
        # Would fetch actual finding text from silver layer in production
        finding = FindingEvidence(
            finding_id=score.get('finding_id', 'unknown'),
            finding_text=score.get('evidence_summary', 'Evidence not available'),
            page_number=0,  # Would fetch from silver layer
            framework=score.get('framework', ''),
            confidence=score.get('confidence', 0.0)
        )
        findings.append(finding)

    return findings


def _get_timestamp() -> str:
    """Get current timestamp in ISO format"""
    from datetime import datetime
    return datetime.utcnow().isoformat() + "Z"
