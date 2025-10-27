"""
Retrieval Parity Checker: Evidence ⊆ Fused Top-K Validation

Verifies that all evidence doc_ids appear in fused top-k results.
Writes demo_topk_vs_evidence.json for audit trail.

SCA v13.8 Authenticity Refactor - CP Module
"""

from typing import Dict, List, Set, Tuple, Any
from pathlib import Path
import json
import logging

logger = logging.getLogger(__name__)


class ParityChecker:
    """Validates evidence parity invariant: evidence ⊆ fused top-k."""

    def __init__(self, output_dir: str = "artifacts/pipeline_validation"):
        """
        Initialize parity checker.

        Args:
            output_dir: Directory for demo_topk_vs_evidence.json
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def check_parity(
        self,
        query: str,
        evidence_ids: List[str],
        fused_top_k: List[Tuple[str, float]],
        k: int = 5
    ) -> Dict[str, Any]:
        """
        Check evidence ⊆ fused top-k invariant.

        Args:
            query: Search query
            evidence_ids: Evidence doc_ids used in scoring
            fused_top_k: Fused retrieval results [(doc_id, score), ...]
            k: Top-k cutoff (default 5)

        Returns:
            Parity report dict with verdict and missing evidence
        """
        # Extract top-k ids
        top_k_ids = {doc_id for doc_id, _ in fused_top_k[:k]}
        evidence_set = set(evidence_ids)

        # Check invariant
        missing = evidence_set - top_k_ids
        verdict = "PASS" if not missing else "FAIL"

        # Build report
        report = {
            "query": query,
            "evidence_ids": sorted(evidence_ids),
            "fused_top_k": [
                {"id": doc_id, "score": float(score)}
                for doc_id, score in fused_top_k[:k]
            ],
            "parity_verdict": verdict,
            "missing_evidence": sorted(list(missing)),
            "k": k
        }

        return report

    def save_report(
        self,
        report: Dict[str, Any],
        filename: str = "demo_topk_vs_evidence.json"
    ) -> Path:
        """
        Save parity report to JSON.

        Args:
            report: Parity report dict
            filename: Output filename

        Returns:
            Path to saved file
        """
        output_file = self.output_dir / filename

        try:
            output_file.write_text(json.dumps(report, indent=2))
            logger.info(f"Saved parity report to {output_file}")
            return output_file
        except Exception as e:
            logger.error(f"Failed to save parity report: {e}")
            raise

    def batch_check(
        self,
        queries: List[str],
        evidence_by_query: Dict[str, List[str]],
        fused_results_by_query: Dict[str, List[Tuple[str, float]]],
        k: int = 5
    ) -> Dict[str, Any]:
        """
        Check parity for multiple queries.

        Args:
            queries: List of queries
            evidence_by_query: Dict mapping query → evidence doc_ids
            fused_results_by_query: Dict mapping query → fused results
            k: Top-k cutoff

        Returns:
            Batch report with per-query verdicts and aggregate stats
        """
        reports = []
        all_pass = True

        for query in queries:
            evidence_ids = evidence_by_query.get(query, [])
            fused_top_k = fused_results_by_query.get(query, [])

            report = self.check_parity(query, evidence_ids, fused_top_k, k=k)
            reports.append(report)

            if report["parity_verdict"] != "PASS":
                all_pass = False

        batch_report = {
            "batch_verdict": "PASS" if all_pass else "FAIL",
            "total_queries": len(queries),
            "passing_queries": sum(1 for r in reports if r["parity_verdict"] == "PASS"),
            "failing_queries": sum(1 for r in reports if r["parity_verdict"] == "FAIL"),
            "per_query_reports": reports
        }

        return batch_report
