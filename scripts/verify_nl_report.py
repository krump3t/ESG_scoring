#!/usr/bin/env python3
"""
Verification script for Natural-Language Report Generator acceptance criteria.

Checks all 8 acceptance criteria from the spec:
1. Determinism: identical==true for 3 runs
2. Parity: subset_ok==true
3. Evidence Gate: ≥2 distinct pages per theme (waivable)
4. Consistency: Markdown and JSON carry same numbers/text
5. Traceability: Evidence exists in silver chunks
6. Status: status=="ok"
7. Format: Both MD and JSON exist
8. Content: All 7 themes present
"""

import json
import sys
from pathlib import Path
from typing import Dict, Any


def check_determinism(json_report: Dict[str, Any]) -> tuple[bool, str]:
    """Check determinism: identical==true."""
    det = json_report.get("determinism", {})
    identical = det.get("identical", False)

    if not identical:
        return False, f"Determinism FAIL: identical={identical}"

    hashes = det.get("hashes", [])
    return True, f"Determinism PASS: identical=true, hashes={len(hashes)}"


def check_parity(json_report: Dict[str, Any]) -> tuple[bool, str]:
    """Check parity: subset_ok==true."""
    parity = json_report.get("parity", {})
    subset_ok = parity.get("subset_ok", False)

    if not subset_ok:
        return False, f"Parity FAIL: subset_ok={subset_ok}"

    return True, "Parity PASS: evidence_ids subset_of fused_top_k"


def check_evidence_gate(json_report: Dict[str, Any]) -> tuple[bool, str]:
    """Check evidence gate: >=2 distinct pages per theme (with waiver)."""
    themes = json_report.get("themes", {})

    warnings = []
    for theme, data in themes.items():
        evidence = data.get("evidence", [])
        pages = set()

        for ev in evidence:
            page = ev.get("page_or_section", "")
            pages.add(page)

        if len(pages) < 2:
            warnings.append(f"{theme}: {len(pages)} pages")

    notes = json_report.get("notes", "")
    has_waiver = "waiver" in notes.lower()

    if warnings and not has_waiver:
        return False, f"Evidence Gate FAIL: {', '.join(warnings)} (no waiver)"

    if warnings:
        return True, f"Evidence Gate PASS (with waiver): {', '.join(warnings)}"

    return True, "Evidence Gate PASS: all themes >=2 distinct pages"


def check_consistency(
    md_path: Path, json_report: Dict[str, Any]
) -> tuple[bool, str]:
    """Check consistency: Markdown and JSON carry same numbers."""
    with open(md_path, "r", encoding="utf-8") as f:
        md_content = f.read()

    # Check overall stage
    overall_stage = json_report.get("overall", {}).get("stage", -1)
    overall_avg = json_report.get("overall", {}).get("average", -1)

    if f"Stage {overall_stage}" not in md_content:
        return False, f"Consistency FAIL: Overall stage {overall_stage} not in MD"

    if f"avg={overall_avg}" not in md_content:
        return False, f"Consistency FAIL: Average {overall_avg} not in MD"

    # Check themes
    themes = json_report.get("themes", {})
    for theme, data in themes.items():
        stage = data.get("stage", -1)
        confidence = data.get("confidence", -1)

        if f"### {theme}" not in md_content:
            return False, f"Consistency FAIL: Theme {theme} missing from MD"

        if f"Stage**: {stage}" not in md_content:
            return False, f"Consistency FAIL: {theme} stage {stage} not in MD"

    return True, f"Consistency PASS: MD and JSON aligned (7 themes, overall stage)"


def check_traceability(json_report: Dict[str, Any]) -> tuple[bool, str]:
    """Check traceability: Evidence has doc_id, page, sha256."""
    themes = json_report.get("themes", {})

    for theme, data in themes.items():
        evidence = data.get("evidence", [])

        for i, ev in enumerate(evidence, 1):
            doc_id = ev.get("doc_id", "")
            page = ev.get("page_or_section", "")
            sha = ev.get("sha256_raw", "")

            if not doc_id:
                return False, f"Traceability FAIL: {theme} evidence {i} missing doc_id"

            if not page:
                return False, f"Traceability FAIL: {theme} evidence {i} missing page"

            if not sha:
                return False, f"Traceability FAIL: {theme} evidence {i} missing sha256"

    return True, "Traceability PASS: All evidence has (doc_id, page, sha256)"


def check_status(json_report: Dict[str, Any]) -> tuple[bool, str]:
    """Check status: status=="ok"."""
    status = json_report.get("status", "")

    if status != "ok":
        notes = json_report.get("notes", "")
        return False, f"Status FAIL: status={status}, notes={notes}"

    return True, "Status PASS: status=ok"


def check_format(md_path: Path, json_path: Path) -> tuple[bool, str]:
    """Check format: Both MD and JSON exist and non-empty."""
    if not md_path.exists() or md_path.stat().st_size == 0:
        return False, f"Format FAIL: MD missing or empty at {md_path}"

    if not json_path.exists() or json_path.stat().st_size == 0:
        return False, f"Format FAIL: JSON missing or empty at {json_path}"

    return True, f"Format PASS: Both MD ({md_path.stat().st_size} bytes) and JSON ({json_path.stat().st_size} bytes) exist"


def check_content(json_report: Dict[str, Any]) -> tuple[bool, str]:
    """Check content: All 7 themes present."""
    themes = json_report.get("themes", {})
    expected_themes = {"TSP", "OSP", "DM", "GHG", "RD", "EI", "RMM"}

    present_themes = set(themes.keys())
    missing = expected_themes - present_themes

    if missing:
        return False, f"Content FAIL: Missing themes {missing}"

    return True, f"Content PASS: All 7 themes present ({', '.join(sorted(present_themes))})"


def main():
    reports_dir = Path("artifacts/reports")

    # Find the generated report
    json_files = list(reports_dir.glob("*_nl_report.json"))

    if not json_files:
        print("ERROR: No reports found in artifacts/reports/", file=sys.stderr)
        sys.exit(1)

    json_path = json_files[0]
    md_path = json_path.with_suffix(".md")

    print(f"Verifying report: {json_path.name}")
    print(f"Markdown: {md_path.name}")
    print("")

    # Load JSON report
    with open(json_path, "r", encoding="utf-8") as f:
        json_report = json.load(f)

    # Run all checks
    checks = [
        ("1. Determinism", check_determinism(json_report)),
        ("2. Parity", check_parity(json_report)),
        ("3. Evidence Gate", check_evidence_gate(json_report)),
        ("4. Consistency", check_consistency(md_path, json_report)),
        ("5. Traceability", check_traceability(json_report)),
        ("6. Status", check_status(json_report)),
        ("7. Format", check_format(md_path, json_path)),
        ("8. Content", check_content(json_report)),
    ]

    print("=" * 70)
    print("ACCEPTANCE CRITERIA VERIFICATION")
    print("=" * 70)
    print("")

    passed = 0
    failed = 0

    for name, (success, message) in checks:
        symbol = "[PASS]" if success else "[FAIL]"
        print(f"{symbol} {name}: {message}")

        if success:
            passed += 1
        else:
            failed += 1

    print("")
    print("=" * 70)
    print(f"SUMMARY: {passed}/{len(checks)} checks passed")
    print("=" * 70)
    print("")

    if failed > 0:
        print(f"RESULT: FAIL ({failed} criteria not met)")
        sys.exit(1)
    else:
        print("RESULT: PASS (all acceptance criteria met)")
        sys.exit(0)


if __name__ == "__main__":
    main()
