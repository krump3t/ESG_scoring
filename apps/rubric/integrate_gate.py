from __future__ import annotations
from typing import Dict, Any, List
from apps.rubric.loader import load_rubric
from libs.scoring.evidence_gate import enforce_evidence_min_per_theme

def apply_policy(scores: Dict[str, Any], evidence: List[Dict[str, Any]]) -> Dict[str, Any]:
    # Build per-theme evidence map (expects evidence items to include "theme")
    ev_map: Dict[str, List[Dict[str, Any]]] = {}
    for ev in evidence or []:
        th = ev.get("theme") or ev.get("Theme")
        if th: ev_map.setdefault(th, []).append(ev)

    rubric = load_rubric()
    evidence_min = int(rubric.scoring_rules.get("evidence_min_per_stage_claim", 1))
    return enforce_evidence_min_per_theme(scores, ev_map, evidence_min)
