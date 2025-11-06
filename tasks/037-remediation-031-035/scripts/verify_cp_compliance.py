#!/usr/bin/env python3
"""
Comprehensive CP Module Compliance Verification
Task 037 - Phase 2.5
Verifies all Critical Path modules are 100% compliant with ruff + mypy --strict
"""

import subprocess
import sys
from pathlib import Path
from typing import List, Tuple

# Define Critical Path modules
CP_MODULES = [
    "libs/retrieval/bm25_search.py",
    "libs/retrieval/vector_search_astra.py",
    "libs/fusion/rrf_fusion.py",
    "libs/chunking/structure_aware_chunker.py",
    "agents/retrieval/hybrid_retriever.py",
    "agents/orchestration/langgraph_orchestrator.py",
    "agents/scoring/rubric_v3_scorer.py",
    "agents/scoring/parity_validator.py"
]

def run_ruff(file_path: str) -> Tuple[bool, int]:
    """Run ruff on a file and return (passed, violation_count)."""
    try:
        result = subprocess.run(
            ["python", "-m", "ruff", "check", file_path],
            capture_output=True,
            text=True,
            cwd=r"C:\projects\Work Projects\ibm-projects\ESG Evaluation\prospecting-engine"
        )
        passed = result.returncode == 0
        violation_count = len(result.stdout.split('\n')) - 1 if result.stdout else 0
        return passed, violation_count
    except Exception as e:
        print(f"Error running ruff on {file_path}: {e}")
        return False, -1

def run_mypy(file_path: str) -> Tuple[bool, int, List[str]]:
    """Run mypy --strict on a file and return (passed, error_count, errors)."""
    try:
        result = subprocess.run(
            ["python", "-m", "mypy", file_path, "--strict", "--no-error-summary"],
            capture_output=True,
            text=True,
            cwd=r"C:\projects\Work Projects\ibm-projects\ESG Evaluation\prospecting-engine"
        )

        # Only count errors for the actual file being checked (not dependencies)
        file_stem = Path(file_path).name
        errors = []
        for line in result.stdout.split('\n'):
            if line.strip() and file_stem in line and 'error:' in line:
                errors.append(line)

        error_count = len(errors)
        passed = error_count == 0

        return passed, error_count, errors
    except Exception as e:
        print(f"Error running mypy on {file_path}: {e}")
        return False, -1, []

def verify_cp_compliance():
    """Verify all CP modules are 100% compliant."""
    print("="*60)
    print("CP MODULE COMPLIANCE VERIFICATION")
    print("Task 037 - Phase 2.5")
    print("="*60)

    project_root = Path(r"C:\projects\Work Projects\ibm-projects\ESG Evaluation\prospecting-engine")

    results = []
    all_passed = True

    for module in CP_MODULES:
        module_path = project_root / module
        if not module_path.exists():
            print(f"\n[MISSING] {module}")
            results.append((module, False, "MISSING"))
            all_passed = False
            continue

        print(f"\nVerifying: {module}")
        print("-" * 40)

        # Run ruff
        ruff_passed, ruff_violations = run_ruff(str(module_path))

        # Run mypy
        mypy_passed, mypy_errors, error_details = run_mypy(str(module_path))

        # Determine status
        if ruff_passed and mypy_passed:
            print(f"  [PASS] 100% compliant")
            print(f"    Ruff: PASS (0 violations)")
            print(f"    Mypy: PASS (0 errors)")
            results.append((module, True, "CLEAN"))
        else:
            print(f"  [FAIL] Issues found")
            if not ruff_passed:
                print(f"    Ruff: FAIL ({ruff_violations} violations)")
            else:
                print(f"    Ruff: PASS")

            if not mypy_passed:
                print(f"    Mypy: FAIL ({mypy_errors} errors)")
                for error in error_details[:3]:  # Show first 3 errors
                    print(f"      - {error}")
                if len(error_details) > 3:
                    print(f"      ... and {len(error_details) - 3} more")
            else:
                print(f"    Mypy: PASS")

            results.append((module, False, f"ruff:{not ruff_passed}, mypy:{not mypy_passed}"))
            all_passed = False

    # Summary
    print("\n" + "="*60)
    print("COMPLIANCE SUMMARY")
    print("="*60)

    clean_count = sum(1 for _, passed, _ in results if passed)
    total_count = len(results)

    print(f"\nTotal CP modules: {total_count}")
    print(f"Clean modules: {clean_count}")
    print(f"Compliance rate: {clean_count}/{total_count} ({100*clean_count//total_count}%)")

    print("\nModule Status:")
    for module, passed, status in results:
        emoji = "[OK]" if passed else "[FAIL]"
        print(f"  {emoji} {module}: {status}")

    print("\n" + "="*60)
    if all_passed:
        print("[SUCCESS] All CP modules are 100% compliant!")
        print("="*60)
        return 0
    else:
        print("[FAILURE] Some CP modules have violations")
        print("="*60)
        return 1

if __name__ == "__main__":
    sys.exit(verify_cp_compliance())