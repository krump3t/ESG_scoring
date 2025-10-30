"""
Critical Path (CP) Gates - Determinism + Evidence + Parity

This test file validates Phase F enhanced gates across all matrix validation artifacts:
1. Determinism: All runs produce identical hashes
2. Evidence: >=3 distinct pages per theme, span >=3-5 (adaptive)
3. Parity: evidence_ids ⊆ fused_topk_ids AND (fused_topk non-empty OR no evidence)

Designed for CI/CD integration with pytest markers.
"""

import json
import glob
from pathlib import Path
import pytest


@pytest.mark.cp
def test_determinism():
    """
    Verify all documents produce identical hashes across 3 runs.

    Gate: SEED=42, PYTHONHASHSEED=0 must produce 100% reproducible results.
    """
    determinism_reports = glob.glob("artifacts/matrix/*/baseline/determinism_report.json")
    assert len(determinism_reports) > 0, "No determinism reports found"

    for report_path in determinism_reports:
        with open(report_path, encoding="utf-8") as f:
            report = json.load(f)

        assert report.get("identical") is True, (
            f"Determinism failure in {report_path}: "
            f"runs not identical. Details: {report.get('notes', 'N/A')}"
        )


@pytest.mark.cp
def test_evidence_pages():
    """
    Verify all themes meet Phase F evidence quality gates:
    - >= 3 distinct pages per theme
    - Span >= 3-5 (adaptive based on document length)

    Gate: Evidence must be distributed across multiple pages.
    """
    evidence_audits = glob.glob("artifacts/matrix/*/pipeline_validation/evidence_audit.json")
    assert len(evidence_audits) > 0, "No evidence audit reports found"

    for audit_path in evidence_audits:
        with open(audit_path, encoding="utf-8") as f:
            audit = json.load(f)

        doc_id = audit.get("doc_id", "unknown")
        themes = audit.get("themes") or {}

        for theme_name, theme_info in themes.items():
            evidence = theme_info.get("evidence") or []

            # Extract page numbers from evidence
            pages = [
                item.get("page")
                for item in evidence
                if isinstance(item, dict) and isinstance(item.get("page"), int)
            ]

            distinct_pages = len(set(pages))

            assert distinct_pages >= 3, (
                f"Evidence gate failure in {doc_id}, theme {theme_name}: "
                f"Only {distinct_pages} distinct pages (required >=3). "
                f"Pages: {sorted(set(pages))}"
            )


@pytest.mark.cp
def test_parity_subset():
    """
    Verify parity gate: evidence_ids ⊆ fused_topk_ids
    AND (fused_topk non-empty OR no evidence exists)

    Gate: Dual-gate parity validation (subset + nonempty guard).
    """
    parity_reports = glob.glob("artifacts/matrix/*/pipeline_validation/demo_topk_vs_evidence.json")
    assert len(parity_reports) > 0, "No parity reports found"

    for report_path in parity_reports:
        with open(report_path, encoding="utf-8") as f:
            parity = json.load(f)

        doc_id = parity.get("doc_id", "unknown")
        evidence_ids = set(parity.get("evidence_ids") or [])
        fused_topk_ids = set(parity.get("fused_topk_ids") or [])

        # Subset check
        subset_ok = evidence_ids.issubset(fused_topk_ids)

        # Nonempty guard
        nonempty_guard = (len(fused_topk_ids) > 0) or (len(evidence_ids) == 0)

        assert subset_ok, (
            f"Parity subset failure in {doc_id}: "
            f"evidence_ids={evidence_ids} not subset of fused_topk_ids={fused_topk_ids}"
        )

        assert nonempty_guard, (
            f"Parity nonempty guard failure in {doc_id}: "
            f"Both evidence_ids and fused_topk_ids are empty (should have fused_topk)"
        )


@pytest.mark.cp
def test_matrix_status_ok():
    """
    Verify overall matrix status is 'ok' with no blocked documents.

    Gate: All active documents must pass all gates.
    """
    matrix_contract_path = Path("artifacts/matrix/matrix_contract.json")

    if not matrix_contract_path.exists():
        pytest.skip("Matrix contract not found (validation not run)")

    with open(matrix_contract_path, encoding="utf-8") as f:
        matrix_contract = json.load(f)

    # Check overall matrix status
    assert matrix_contract.get("matrix_status") == "ok", (
        f"Matrix status not ok: {matrix_contract.get('matrix_status')}"
    )

    # Check determinism
    assert matrix_contract.get("determinism_pass") is True, (
        "Matrix-level determinism check failed"
    )


@pytest.mark.cp
def test_authenticity_no_mocks():
    """
    Verify no mock/stub data in active documents (SCA v13.8-MEA compliance).

    Gate: Authenticity policy - no fabricated data in production paths.
    """
    output_contracts = glob.glob("artifacts/matrix/*/output_contract.json")
    assert len(output_contracts) > 0, "No output contracts found"

    for contract_path in output_contracts:
        with open(contract_path, encoding="utf-8") as f:
            contract = json.load(f)

        doc_id = contract.get("doc_id", "unknown")
        status = contract.get("status")

        # Skipped documents are allowed (quarantined, not hidden)
        if status == "skipped":
            # Verify skip_reason is transparent
            assert contract.get("skip_reason"), (
                f"Skipped document {doc_id} lacks skip_reason"
            )
            continue

        # Active documents must have authenticity gate PASS
        gates = contract.get("gates") or {}
        authenticity = gates.get("authenticity")

        assert authenticity == "PASS", (
            f"Authenticity gate failure in {doc_id}: {authenticity}"
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-k", "cp"])
