"""
Parity Validator - Evidence ⊆ Top-K Hard Gate

Critical Path: Validates evidence IDs are subset of retrieval top-k (hard gate)

Implements:
- Evidence ⊆ top-k validation (set membership)
- Verdict: "PASS" or "FAIL" (binary, no warnings)
- Violation reporting (which evidence IDs not in top-k)
- Hard gate: raise ParityViolationError on FAIL (ADR-DEMO-001.2)

Author: SCA v13.8-MEA
Task: DEMO-001 Multi-Source E2E Demo
Protocol: No mocks, no placeholders, deterministic, authentic data only
"""
from typing import List, Dict, Any, Set


class ParityViolationError(Exception):
    """
    Raised when evidence parity validation fails

    This is a HARD GATE per ADR-DEMO-001.2:
    If evidence IDs are not in retrieval top-k, this indicates:
    - Evidence was "fabricated" (not from retrieval)
    - Scoring is not grounded in retrieved documents
    - Authenticity violation (regulatory non-compliance)
    """
    pass


class ParityValidator:
    """
    Validates evidence IDs are subset of retrieval top-k

    Core Algorithm:
    1. Convert evidence_ids and topk_ids to sets
    2. Check if evidence_ids ⊆ topk_ids (set subset)
    3. Calculate coverage = |evidence ∩ topk| / |evidence|
    4. Report violations (evidence IDs not in top-k)
    5. Return verdict: "PASS" (coverage=1.0) or "FAIL" (coverage<1.0)

    Hard Gate Mode:
    - validate_strict() raises ParityViolationError on FAIL
    - Used in pipeline to halt execution on violations
    """

    def __init__(self) -> None:
        """Initialize parity validator"""
        self.name = "ParityValidator"

    def validate(
        self,
        evidence_ids: List[str],
        topk_ids: List[str]
    ) -> Dict[str, Any]:
        """
        Validate evidence IDs are subset of top-k (inspection mode)

        Returns result dict for inspection/reporting (does not raise exception)

        Args:
            evidence_ids: List of evidence IDs selected for scoring
            topk_ids: List of top-k retrieval result IDs

        Returns:
            {
                "verdict": "PASS" | "FAIL",
                "coverage": float,  # 0.0-1.0 (1.0 = all evidence in top-k)
                "evidence_count": int,
                "topk_count": int,
                "violations": List[str],  # Evidence IDs not in top-k
                "valid_evidence": List[str]  # Evidence IDs in top-k
            }
        """
        # Handle None inputs
        if evidence_ids is None or topk_ids is None:
            raise TypeError("evidence_ids and topk_ids cannot be None")

        # Convert to sets (deduplicates and enables fast membership checks)
        evidence_set = set(evidence_ids)
        topk_set = set(topk_ids)

        # Find violations (evidence NOT in top-k)
        violations = evidence_set - topk_set  # Set difference

        # Find valid evidence (evidence IN top-k)
        valid_evidence = evidence_set & topk_set  # Set intersection

        # Calculate coverage
        if len(evidence_set) == 0:
            # Empty evidence: vacuous truth (∅ ⊆ topk)
            coverage = 1.0
        else:
            coverage = len(valid_evidence) / len(evidence_set)

        # Determine verdict
        verdict = "PASS" if coverage == 1.0 else "FAIL"

        # Build violation messages
        violation_messages = [
            f"Evidence ID '{ev_id}' not found in top-k retrieval results"
            for ev_id in sorted(violations)
        ]

        return {
            "verdict": verdict,
            "coverage": coverage,
            "evidence_count": len(evidence_set),
            "topk_count": len(topk_set),
            "violations": violation_messages,
            "valid_evidence": list(valid_evidence)
        }

    def validate_strict(
        self,
        evidence_ids: List[str],
        topk_ids: List[str]
    ) -> None:
        """
        Validate evidence IDs are subset of top-k (hard gate mode)

        Raises ParityViolationError on FAIL (used in pipeline to halt execution)

        Args:
            evidence_ids: List of evidence IDs selected for scoring
            topk_ids: List of top-k retrieval result IDs

        Raises:
            ParityViolationError: If any evidence ID not in top-k

        Returns:
            None (only returns on PASS, raises on FAIL)
        """
        result = self.validate(evidence_ids, topk_ids)

        if result["verdict"] == "FAIL":
            # Build error message
            violation_count = len(result["violations"])
            coverage = result["coverage"]

            error_message = (
                f"Parity validation FAILED: {violation_count} evidence IDs not in top-k retrieval results. "
                f"Coverage: {coverage:.1%} (required: 100%).\n"
                f"Violations:\n" + "\n".join(f"  - {v}" for v in result["violations"])
            )

            raise ParityViolationError(error_message)

    def validate_by_theme(
        self,
        evidence: List[Dict[str, Any]],
        topk_by_theme: Dict[str, List[str]]
    ) -> Dict[str, Dict[str, Any]]:
        """
        Validate parity per theme (for detailed reporting)

        Useful for understanding which themes have parity violations

        Args:
            evidence: List of evidence records (with theme_code and evidence_id)
            topk_by_theme: Dict mapping theme_code to list of top-k IDs

        Returns:
            Dict mapping theme_code to validation result
        """
        # Group evidence by theme
        evidence_by_theme = {}
        for ev in evidence:
            theme = ev.get("theme_code", "Unknown")
            if theme not in evidence_by_theme:
                evidence_by_theme[theme] = []
            evidence_by_theme[theme].append(ev["evidence_id"])

        # Validate each theme
        results = {}
        for theme, ev_ids in evidence_by_theme.items():
            topk_ids = topk_by_theme.get(theme, [])
            results[theme] = self.validate(ev_ids, topk_ids)

        return results

    def generate_parity_report(
        self,
        validation_result: Dict[str, Any],
        output_path: str
    ) -> None:
        """
        Generate parity validation report (topk_vs_evidence.json)

        This is one of the mandated artifacts per microprompt

        Args:
            validation_result: Result from validate()
            output_path: Path to write JSON report
        """
        import json
        from pathlib import Path

        # Build report
        report = {
            "parity_validation": {
                "verdict": validation_result["verdict"],
                "coverage": validation_result["coverage"],
                "evidence_count": validation_result["evidence_count"],
                "topk_count": validation_result["topk_count"],
                "violations_count": len(validation_result["violations"]),
                "violations": validation_result["violations"]
            },
            "metadata": {
                "validator": self.name,
                "requirement": "Evidence IDs must be subset of retrieval top-k (evidence ⊆ topk)",
                "mandate": "ADR-DEMO-001.2: Parity validation is a HARD GATE",
                "artifact_type": "topk_vs_evidence.json"
            }
        }

        # Write report
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2)

    def check_multi_source_parity(
        self,
        evidence: List[Dict[str, Any]],
        topk_ids: List[str]
    ) -> Dict[str, Any]:
        """
        Check parity with breakdown by source (SEC, CDP, PDF)

        Useful for understanding if specific sources have parity issues

        Args:
            evidence: List of evidence records (with doc_id)
            topk_ids: List of top-k retrieval result IDs

        Returns:
            {
                "overall": validation_result,
                "by_source": {
                    "sec_edgar": validation_result,
                    "cdp": validation_result,
                    "pdf": validation_result
                }
            }
        """
        # Extract evidence IDs
        evidence_ids = [ev["evidence_id"] for ev in evidence]

        # Overall validation
        overall_result = self.validate(evidence_ids, topk_ids)

        # Group evidence by source
        evidence_by_source = {}
        for ev in evidence:
            doc_id = ev.get("doc_id", "")

            # Infer source from doc_id
            if "sec-edgar" in doc_id or "sec_edgar" in doc_id:
                source = "sec_edgar"
            elif "cdp" in doc_id:
                source = "cdp"
            elif "pdf" in doc_id or "apple" in doc_id:
                source = "pdf"
            else:
                source = "unknown"

            if source not in evidence_by_source:
                evidence_by_source[source] = []
            evidence_by_source[source].append(ev["evidence_id"])

        # Validate each source
        by_source_results = {}
        for source, ev_ids in evidence_by_source.items():
            by_source_results[source] = self.validate(ev_ids, topk_ids)

        return {
            "overall": overall_result,
            "by_source": by_source_results
        }
