"""
SCA v13.8-MEA Compliance Audit and Remediation

Validates and remediates task directory structure per SCA protocol.
"""

import json
import shutil
from pathlib import Path
from typing import List, Dict, Any

PROJECT_ROOT = Path(__file__).parent.parent

REQUIRED_SUBDIRS = ["context", "artifacts", "qa", "reports"]
REQUIRED_CONTEXT_FILES = [
    "hypothesis.md",
    "design.md",
    "evidence.json",
    "data_sources.json",
    "adr.md",
    "assumptions.md",
    "cp_paths.json"
]

def remove_malformed_directories():
    """Remove malformed task directories"""
    print("\n[Step 1] Removing malformed task directories...")

    malformed_patterns = [
        "tasks005-microsoft-full-analysis*",
        "tasks006-ghg-stage1-fix*"
    ]

    removed = []
    for pattern in malformed_patterns:
        for path in PROJECT_ROOT.glob(pattern):
            if path.is_dir() and path.name != "tasks":
                # Check if empty
                contents = list(path.iterdir())
                if not contents:
                    shutil.rmtree(path)
                    print(f"  [OK] Removed empty malformed directory: {path.name}")
                    removed.append(path.name)
                else:
                    print(f"  [WARN] NOT empty ({len(contents)} items): {path.name}")
                    print(f"    Contents: {[c.name for c in contents]}")

    return removed

def audit_task_structure() -> List[Dict[str, Any]]:
    """Audit all task directories for SCA compliance"""
    print("\n[Step 2] Auditing task directory structure...")

    tasks_dir = PROJECT_ROOT / "tasks"
    if not tasks_dir.exists():
        print(f"  ✗ Tasks directory not found: {tasks_dir}")
        return []

    task_dirs = [d for d in tasks_dir.iterdir() if d.is_dir() and d.name[0].isdigit()]
    task_dirs.sort()

    compliance_report = []

    for task_dir in task_dirs:
        task_name = task_dir.name
        issues = []

        # Check subdirectories
        for subdir in REQUIRED_SUBDIRS:
            subdir_path = task_dir / subdir
            if not subdir_path.exists():
                issues.append(f"Missing subdirectory: {subdir}")

        # Check context files
        context_path = task_dir / "context"
        if context_path.exists():
            for file in REQUIRED_CONTEXT_FILES:
                file_path = context_path / file
                if not file_path.exists():
                    issues.append(f"Missing context file: {file}")

        # Check cp_paths.json content
        cp_paths_file = context_path / "cp_paths.json"
        if cp_paths_file.exists():
            try:
                with open(cp_paths_file, 'r') as f:
                    cp_content = json.load(f)
                    if 'critical_path' not in cp_content:
                        issues.append("cp_paths.json missing 'critical_path' field")
            except Exception as e:
                issues.append(f"cp_paths.json invalid JSON: {e}")

        compliant = len(issues) == 0
        status = "[PASS] COMPLIANT" if compliant else "[FAIL] NON-COMPLIANT"

        print(f"  {status} : {task_name}")

        if issues:
            for issue in issues:
                print(f"    - {issue}")

        compliance_report.append({
            "task": task_name,
            "compliant": compliant,
            "issues": issues
        })

    return compliance_report

def print_summary(compliance_report: List[Dict[str, Any]]):
    """Print compliance summary"""
    print("\n[Step 3] Compliance Summary")

    total = len(compliance_report)
    compliant = sum(1 for t in compliance_report if t['compliant'])
    non_compliant = total - compliant

    print(f"  Total tasks: {total}")
    print(f"  Compliant: {compliant}")
    print(f"  Non-compliant: {non_compliant}")

    if non_compliant > 0:
        print(f"\n  [WARN] REMEDIATION REQUIRED for {non_compliant} tasks")
        print("  Next steps:")
        print("    1. Review non-compliant tasks above")
        print("    2. Create missing context artifacts")
        print("    3. Re-run this script to verify")
    else:
        print("\n  [OK] ALL TASKS COMPLIANT with SCA v13.8")

    # Save report
    report_path = PROJECT_ROOT / "tasks" / "COMPLIANCE_REPORT.json"
    with open(report_path, 'w') as f:
        json.dump(compliance_report, f, indent=2)

    print(f"\nCompliance report saved to: {report_path}")

def main():
    print("=" * 60)
    print("SCA v13.8-MEA Compliance Audit & Remediation")
    print("=" * 60)

    # Step 1: Remove malformed directories
    removed = remove_malformed_directories()

    # Step 2: Audit task structure
    compliance_report = audit_task_structure()

    # Step 3: Print summary
    print_summary(compliance_report)

    print("\n" + "=" * 60)
    print("Audit Complete")
    print("=" * 60)

if __name__ == "__main__":
    main()
