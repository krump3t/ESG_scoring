"""
Parity Validation Utility - Phase F Hardening

Centralizes parity validation logic with nonempty guard.

Phase F Enhancement:
- Subset check: evidence_ids ⊆ fused_topk_ids
- Nonempty guard: fused_topk non-empty OR no evidence exists
  (prevents false pass when both are empty)

Key Invariants:
1. Evidence must be sourced from retrieval results (subset requirement)
2. If evidence exists, retrieval must have produced results (nonempty guard)
3. Empty evidence with empty retrieval is acceptable (no scoring occurred)
"""

from typing import List, Dict, Any, Set, Optional


def parity_result(
    evidence_ids: Optional[List[str]],
    fused_topk_ids: Optional[List[str]]
) -> Dict[str, Any]:
    """
    Validate parity between evidence and retrieval results with nonempty guard.

    Phase F Parity Gates:
    1. **Subset Gate**: evidence_ids ⊆ fused_topk_ids
       - Every evidence item must come from retrieval results
       - Prevents fabricated/hallucinated evidence

    2. **Nonempty Guard**: fused_topk non-empty OR evidence is empty
       - If evidence exists, retrieval must have run
       - Prevents false PASS when both lists are empty
       - Allows empty-evidence case (theme had no scoring)

    Args:
        evidence_ids: List of evidence chunk IDs (None/empty = no evidence)
        fused_topk_ids: List of retrieval result IDs (None/empty = no retrieval)

    Returns:
        Dict with validation results:
        - subset_ok: bool - True if evidence ⊆ retrieval
        - fused_nonempty_or_no_evidence: bool - Nonempty guard result
        - passed: bool - True if BOTH gates pass
        - missing_ids: List[str] - Evidence IDs not in retrieval (parity violations)
        - coverage: float - Fraction of evidence found in retrieval (0.0-1.0)
        - evidence_count: int - Total evidence items
        - retrieval_count: int - Total retrieval items
        - gates: Dict[str, bool] - Individual gate results

    Example (PASS):
        >>> parity_result(["a", "b"], ["a", "b", "c", "d"])
        {
            "subset_ok": True,
            "fused_nonempty_or_no_evidence": True,
            "passed": True,
            "missing_ids": [],
            "coverage": 1.0,
            "evidence_count": 2,
            "retrieval_count": 4
        }

    Example (FAIL - missing evidence):
        >>> parity_result(["a", "x", "y"], ["a", "b", "c"])
        {
            "subset_ok": False,
            "fused_nonempty_or_no_evidence": True,
            "passed": False,
            "missing_ids": ["x", "y"],
            "coverage": 0.33,
            ...
        }

    Example (FAIL - nonempty guard):
        >>> parity_result(["a", "b"], [])
        {
            "subset_ok": True,  # Vacuously true (empty retrieval)
            "fused_nonempty_or_no_evidence": False,  # GUARD TRIGGERED
            "passed": False,
            "missing_ids": [],
            "coverage": 0.0,
            ...
        }

    Example (PASS - no evidence, no retrieval):
        >>> parity_result([], [])
        {
            "subset_ok": True,
            "fused_nonempty_or_no_evidence": True,  # No evidence exists
            "passed": True,
            "missing_ids": [],
            "coverage": 1.0,
            ...
        }
    """
    # Normalize inputs
    ev_list = evidence_ids or []
    top_list = fused_topk_ids or []

    # Filter empty strings and None
    ev_set: Set[str] = {e for e in ev_list if e}
    top_set: Set[str] = {t for t in top_list if t}

    # Gate 1: Subset check
    missing = ev_set - top_set
    subset_ok = len(missing) == 0

    # Gate 2: Nonempty guard
    # PASS if: (retrieval has results) OR (no evidence exists)
    # FAIL if: (retrieval empty) AND (evidence exists)
    fused_nonempty_or_no_evidence = (len(top_set) > 0) or (len(ev_set) == 0)

    # Coverage calculation
    if len(ev_set) == 0:
        coverage = 1.0  # No evidence = 100% coverage (vacuous truth)
    else:
        valid_evidence = ev_set & top_set
        coverage = len(valid_evidence) / len(ev_set)

    # Overall result
    passed = subset_ok and fused_nonempty_or_no_evidence

    return {
        "subset_ok": subset_ok,
        "fused_nonempty_or_no_evidence": fused_nonempty_or_no_evidence,
        "passed": passed,
        "missing_ids": sorted(list(missing)),
        "coverage": round(coverage, 4),
        "evidence_count": len(ev_set),
        "retrieval_count": len(top_set),
        "gates": {
            "subset": subset_ok,
            "nonempty_guard": fused_nonempty_or_no_evidence
        }
    }


def parity_summary(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Aggregate parity results across multiple themes/documents.

    Args:
        results: List of parity_result() outputs

    Returns:
        Summary dict:
        - total_checks: int
        - passed: int
        - failed: int
        - pass_rate: float
        - total_violations: int (sum of missing_ids across all checks)
        - avg_coverage: float
        - gate_failures: Dict[gate_name, count]
    """
    total = len(results)
    passed_count = sum(1 for r in results if r["passed"])
    total_violations = sum(len(r["missing_ids"]) for r in results)
    avg_coverage = sum(r["coverage"] for r in results) / total if total > 0 else 0.0

    # Count gate-specific failures
    subset_failures = sum(1 for r in results if not r["gates"]["subset"])
    nonempty_guard_failures = sum(1 for r in results if not r["gates"]["nonempty_guard"])

    return {
        "total_checks": total,
        "passed": passed_count,
        "failed": total - passed_count,
        "pass_rate": round(passed_count / total, 4) if total > 0 else 0.0,
        "total_violations": total_violations,
        "avg_coverage": round(avg_coverage, 4),
        "gate_failures": {
            "subset": subset_failures,
            "nonempty_guard": nonempty_guard_failures
        }
    }


def validate_parity_strict(
    evidence_ids: Optional[List[str]],
    fused_topk_ids: Optional[List[str]],
    context: str = ""
) -> None:
    """
    Strict parity validation with exception on failure.

    Raises:
        ValueError: If parity gates fail (with diagnostic details)

    Args:
        evidence_ids: List of evidence chunk IDs
        fused_topk_ids: List of retrieval result IDs
        context: Optional context string for error message (e.g., "theme=GHG, doc=AAPL_2023")
    """
    result = parity_result(evidence_ids, fused_topk_ids)

    if not result["passed"]:
        error_details = []

        if not result["gates"]["subset"]:
            error_details.append(
                f"Subset gate FAILED: {len(result['missing_ids'])} evidence IDs not in retrieval results"
            )
            error_details.append(f"  Missing IDs: {result['missing_ids'][:10]}")  # Show first 10

        if not result["gates"]["nonempty_guard"]:
            error_details.append(
                "Nonempty guard FAILED: Evidence exists but retrieval returned no results"
            )

        error_details.append(f"  Coverage: {result['coverage']:.1%}")
        error_details.append(f"  Evidence count: {result['evidence_count']}")
        error_details.append(f"  Retrieval count: {result['retrieval_count']}")

        context_msg = f" [{context}]" if context else ""
        raise ValueError(
            f"Parity violation{context_msg}:\n" + "\n".join(error_details)
        )
