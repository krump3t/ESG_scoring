"""
Validate all tasks against SCA Protocol v13.7 requirements
"""
import json
from pathlib import Path
from typing import Dict, List, Tuple
import sys

TASKS_DIR = Path(r"C:\projects\Work Projects\ibm-projects\ESG Evaluation\prospecting-engine\tasks")

# Required context files per protocol
REQUIRED_CONTEXT_FILES = [
    "hypothesis.md",
    "design.md",
    "evidence.json",
    "data_sources.json",
    "cp_paths.json",
    "adr.md",
    "assumptions.md"
]

# Required directories per task
REQUIRED_DIRS = ["context", "artifacts", "qa", "reports"]


def validate_task_structure(task_path: Path) -> Tuple[bool, List[str]]:
    """Validate task directory structure"""
    issues = []

    # Check required directories exist
    for dir_name in REQUIRED_DIRS:
        dir_path = task_path / dir_name
        if not dir_path.exists():
            issues.append(f"Missing directory: {dir_name}/")
        elif not dir_path.is_dir():
            issues.append(f"Not a directory: {dir_name}/")

    return len(issues) == 0, issues


def validate_context_files(task_path: Path) -> Tuple[bool, List[str]]:
    """Validate all required context files exist and are non-empty"""
    issues = []
    context_dir = task_path / "context"

    if not context_dir.exists():
        issues.append("context/ directory missing")
        return False, issues

    for file_name in REQUIRED_CONTEXT_FILES:
        file_path = context_dir / file_name

        # Check file exists
        if not file_path.exists():
            issues.append(f"Missing required file: context/{file_name}")
            continue

        # Check file is non-empty
        try:
            content = file_path.read_text(encoding='utf-8')
            if len(content.strip()) == 0:
                issues.append(f"Empty file: context/{file_name}")
        except Exception as e:
            issues.append(f"Cannot read context/{file_name}: {e}")

    return len(issues) == 0, issues


def validate_hypothesis_md(task_path: Path) -> Tuple[bool, List[str]]:
    """Validate hypothesis.md has required sections"""
    issues = []
    file_path = task_path / "context" / "hypothesis.md"

    if not file_path.exists():
        return False, ["hypothesis.md missing"]

    content = file_path.read_text(encoding='utf-8')

    required_sections = [
        "Core Hypothesis",
        "Success Metrics",
        "Critical Path"
    ]

    for section in required_sections:
        if section not in content:
            issues.append(f"hypothesis.md missing section: {section}")

    return len(issues) == 0, issues


def validate_design_md(task_path: Path) -> Tuple[bool, List[str]]:
    """Validate design.md has required sections"""
    issues = []
    file_path = task_path / "context" / "design.md"

    if not file_path.exists():
        return False, ["design.md missing"]

    content = file_path.read_text(encoding='utf-8')

    required_sections = [
        "Design"
    ]

    for section in required_sections:
        if section not in content:
            issues.append(f"design.md missing section: {section}")

    # Should have some verification or success criteria
    if "success" not in content.lower() and "criteria" not in content.lower():
        issues.append("design.md should include success criteria or verification plan")

    return len(issues) == 0, issues


def validate_evidence_json(task_path: Path) -> Tuple[bool, List[str]]:
    """Validate evidence.json structure"""
    issues = []
    file_path = task_path / "context" / "evidence.json"

    if not file_path.exists():
        return False, ["evidence.json missing"]

    try:
        data = json.loads(file_path.read_text(encoding='utf-8'))

        # Must have sources array
        if "sources" not in data:
            issues.append("evidence.json missing 'sources' array")
            return False, issues

        sources = data["sources"]

        # Count P1 sources
        p1_sources = [s for s in sources if s.get("priority") == "P1"]

        if len(p1_sources) < 3:
            issues.append(f"evidence.json requires >=3 P1 sources, found {len(p1_sources)}")

        # Validate each source has required fields
        for i, source in enumerate(sources):
            required_fields = ["id", "title", "priority"]
            for field in required_fields:
                if field not in source:
                    issues.append(f"Source {i} missing required field: {field}")

            # Check synthesis length if present
            if "synthesis" in source:
                word_count = len(source["synthesis"].split())
                if word_count > 50:
                    issues.append(f"Source {i} synthesis too long: {word_count} words (max 50)")

    except json.JSONDecodeError as e:
        issues.append(f"evidence.json invalid JSON: {e}")
    except Exception as e:
        issues.append(f"evidence.json validation error: {e}")

    return len(issues) == 0, issues


def validate_data_sources_json(task_path: Path) -> Tuple[bool, List[str]]:
    """Validate data_sources.json structure"""
    issues = []
    file_path = task_path / "context" / "data_sources.json"

    if not file_path.exists():
        return False, ["data_sources.json missing"]

    try:
        data = json.loads(file_path.read_text(encoding='utf-8'))

        if "sources" not in data:
            issues.append("data_sources.json missing 'sources' array")
            return False, issues

        # Validate each source has sha256 and pii_flag
        for i, source in enumerate(data["sources"]):
            if "sha256" not in source:
                issues.append(f"Source {i} missing 'sha256' field")
            if "pii_flag" not in source:
                issues.append(f"Source {i} missing 'pii_flag' field")
            if "provenance" not in source:
                issues.append(f"Source {i} missing 'provenance' field")

    except json.JSONDecodeError as e:
        issues.append(f"data_sources.json invalid JSON: {e}")
    except Exception as e:
        issues.append(f"data_sources.json validation error: {e}")

    return len(issues) == 0, issues


def validate_cp_paths_json(task_path: Path) -> Tuple[bool, List[str]]:
    """Validate cp_paths.json structure"""
    issues = []
    file_path = task_path / "context" / "cp_paths.json"

    if not file_path.exists():
        return False, ["cp_paths.json missing"]

    try:
        data = json.loads(file_path.read_text(encoding='utf-8'))

        if "critical_paths" not in data:
            issues.append("cp_paths.json missing 'critical_paths' array")

        # Should have coverage requirements
        if "coverage_requirements" in data:
            reqs = data["coverage_requirements"]
            if "line" not in reqs or reqs["line"] < 0.95:
                issues.append("cp_paths.json line coverage requirement should be >= 0.95")
            if "branch" not in reqs or reqs["branch"] < 0.95:
                issues.append("cp_paths.json branch coverage requirement should be >= 0.95")

    except json.JSONDecodeError as e:
        issues.append(f"cp_paths.json invalid JSON: {e}")
    except Exception as e:
        issues.append(f"cp_paths.json validation error: {e}")

    return len(issues) == 0, issues


def validate_adr_md(task_path: Path) -> Tuple[bool, List[str]]:
    """Validate adr.md has at least one ADR"""
    issues = []
    file_path = task_path / "context" / "adr.md"

    if not file_path.exists():
        return False, ["adr.md missing"]

    content = file_path.read_text(encoding='utf-8')

    if len(content.strip()) < 20:
        issues.append("adr.md appears empty or too short")

    # Should have "ADR" somewhere
    if "ADR" not in content:
        issues.append("adr.md should contain at least one Architecture Decision Record (ADR)")

    return len(issues) == 0, issues


def validate_assumptions_md(task_path: Path) -> Tuple[bool, List[str]]:
    """Validate assumptions.md is non-empty"""
    issues = []
    file_path = task_path / "context" / "assumptions.md"

    if not file_path.exists():
        return False, ["assumptions.md missing"]

    content = file_path.read_text(encoding='utf-8')

    if len(content.strip()) < 20:
        issues.append("assumptions.md appears empty or too short")

    return len(issues) == 0, issues


def validate_task(task_path: Path) -> Dict:
    """Validate a single task against all protocol requirements"""
    task_name = task_path.name
    results = {
        "task": task_name,
        "compliant": True,
        "checks": {}
    }

    # Run all validations
    checks = [
        ("directory_structure", validate_task_structure),
        ("context_files_exist", validate_context_files),
        ("hypothesis_md", validate_hypothesis_md),
        ("design_md", validate_design_md),
        ("evidence_json", validate_evidence_json),
        ("data_sources_json", validate_data_sources_json),
        ("cp_paths_json", validate_cp_paths_json),
        ("adr_md", validate_adr_md),
        ("assumptions_md", validate_assumptions_md)
    ]

    for check_name, check_func in checks:
        passed, issues = check_func(task_path)
        results["checks"][check_name] = {
            "passed": passed,
            "issues": issues
        }
        if not passed:
            results["compliant"] = False

    return results


def main():
    print("\n" + "=" * 80)
    print(" SCA PROTOCOL v13.7 COMPLIANCE VALIDATION")
    print("=" * 80)

    # Find all task directories
    task_dirs = sorted([d for d in TASKS_DIR.iterdir() if d.is_dir() and d.name.startswith("00")])

    print(f"\nFound {len(task_dirs)} tasks to validate\n")

    all_results = []
    total_compliant = 0

    for task_dir in task_dirs:
        print(f"Validating: {task_dir.name}")
        print("-" * 80)

        results = validate_task(task_dir)
        all_results.append(results)

        if results["compliant"]:
            print(f"  [OK] Task is COMPLIANT")
            total_compliant += 1
        else:
            print(f"  [FAIL] Task is NOT COMPLIANT")

            # Print issues
            for check_name, check_result in results["checks"].items():
                if not check_result["passed"]:
                    print(f"\n  {check_name}:")
                    for issue in check_result["issues"]:
                        print(f"    - {issue}")

        print()

    # Summary
    print("=" * 80)
    print(" VALIDATION SUMMARY")
    print("=" * 80)
    print(f"\nTotal Tasks: {len(task_dirs)}")
    print(f"Compliant: {total_compliant}")
    print(f"Non-Compliant: {len(task_dirs) - total_compliant}")

    if total_compliant == len(task_dirs):
        print("\n[SUCCESS] All tasks are protocol compliant!")
        print("\nReady to proceed with Task 001 execution.")
    else:
        print("\n[BLOCKED] Some tasks are not compliant.")
        print("\nRemediation required before proceeding.")
        sys.exit(1)

    # Save results
    output_file = TASKS_DIR / "validation_report.json"
    with open(output_file, 'w') as f:
        json.dump({
            "validation_date": "2025-10-21T18:35:00Z",
            "protocol_version": "13.7",
            "total_tasks": len(task_dirs),
            "compliant_tasks": total_compliant,
            "results": all_results
        }, f, indent=2)

    print(f"\nValidation report saved to: {output_file}")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()
