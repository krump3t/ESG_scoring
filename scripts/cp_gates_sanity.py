#!/usr/bin/env python3
"""
CP Gates Sanity Check - Quick validation of critical gates

Validates:
1. Determinism: All runs produce identical hashes
2. Evidence: >=3 distinct pages per theme
3. Parity: evidence_ids ⊆ fused_topk_ids + nonempty guard

Exit codes:
    0 - All gates pass
    1 - Gate failure
"""

import json
import glob
import sys


def main():
    """Run quick CP gates validation."""
    failures = []

    # 1. Determinism gate
    print("Checking determinism gate...")
    determinism_reports = glob.glob("artifacts/matrix/*/baseline/determinism_report.json")
    for report_path in determinism_reports:
        with open(report_path, encoding="utf-8") as f:
            report = json.load(f)
        if report.get("identical") is not True:
            failures.append(f"determinism_fail: {report_path}")

    # 2. Evidence gate (>=3 distinct pages)
    print("Checking evidence gate...")
    evidence_audits = glob.glob("artifacts/matrix/*/pipeline_validation/evidence_audit.json")
    for audit_path in evidence_audits:
        with open(audit_path, encoding="utf-8") as f:
            audit = json.load(f)

        doc_id = audit.get("doc_id", "unknown")
        themes = audit.get("themes") or {}

        for theme_name, theme_info in themes.items():
            # Check if theme passed (gate_details present)
            if not theme_info.get("passed", False):
                failures.append(f"evidence_fail: {doc_id} theme={theme_name} (theme not passed)")
                continue

            # Check unique_pages count
            unique_pages = theme_info.get("unique_pages", 0)
            if unique_pages < 3:
                failures.append(f"evidence_fail: {doc_id} theme={theme_name} pages={unique_pages}")

    # 3. Parity gate
    print("Checking parity gate...")
    parity_reports = glob.glob("artifacts/matrix/*/pipeline_validation/demo_topk_vs_evidence.json")
    for report_path in parity_reports:
        with open(report_path, encoding="utf-8") as f:
            parity = json.load(f)

        doc_id = parity.get("doc_id", "unknown")
        evidence_ids = set(parity.get("evidence_ids") or [])
        fused_topk_ids = set(parity.get("fused_topk_ids") or [])

        # Nonempty guard
        if len(evidence_ids) > 0 and len(fused_topk_ids) == 0:
            failures.append(f"parity_fail: {doc_id} (nonempty guard: evidence exists but no topk)")

        # Subset check
        if not evidence_ids.issubset(fused_topk_ids):
            failures.append(f"parity_fail: {doc_id} (subset: evidence not subset of topk)")

    if failures:
        print("\nCP_GATES_FAIL")
        for failure in failures:
            print(f"  - {failure}")
        return 1

    print("\nCP_GATES_OK - All critical gates pass")
    return 0


if __name__ == "__main__":
    sys.exit(main())
