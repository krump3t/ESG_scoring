#!/usr/bin/env python3
"""
Comprehensive CP Module Violation Analysis
Task 037 - Phase 2.1
Identifies all violations in Critical Path modules for targeted remediation
"""

import json
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Tuple

# Define Critical Path modules based on previous analysis
CP_MODULES = [
    "libs/retrieval/bm25_search.py",
    "libs/retrieval/vector_search_astra.py",
    "libs/fusion/rrf_fusion.py",  # Already fixed
    "libs/chunking/structure_aware_chunker.py",  # Already fixed
    "agents/retrieval/hybrid_retriever.py",
    "agents/orchestration/langgraph_orchestrator.py",  # Already fixed
    "agents/scoring/rubric_v3_scorer.py",
    "agents/scoring/parity_validator.py"  # Already fixed
]

def run_ruff_check(file_path: str) -> List[Dict]:
    """Run ruff on a single file and return violations."""
    try:
        result = subprocess.run(
            ["python", "-m", "ruff", "check", file_path, "--output-format", "json"],
            capture_output=True,
            text=True,
            cwd=r"C:\projects\Work Projects\ibm-projects\ESG Evaluation\prospecting-engine"
        )

        if result.stdout:
            violations = json.loads(result.stdout)
            return violations if isinstance(violations, list) else []
        return []
    except Exception as e:
        print(f"Error running ruff on {file_path}: {e}")
        return []

def run_mypy_check(file_path: str) -> List[Dict]:
    """Run mypy on a single file and return violations."""
    try:
        result = subprocess.run(
            ["python", "-m", "mypy", file_path, "--strict", "--no-error-summary", "--show-error-codes"],
            capture_output=True,
            text=True,
            cwd=r"C:\projects\Work Projects\ibm-projects\ESG Evaluation\prospecting-engine"
        )

        violations = []
        for line in result.stdout.split('\n'):
            if line.strip() and ':' in line and 'error:' in line:
                parts = line.split(':', 3)
                if len(parts) >= 4:
                    violations.append({
                        'file': parts[0],
                        'line': parts[1],
                        'type': 'mypy',
                        'message': parts[3].strip()
                    })
        return violations
    except Exception as e:
        print(f"Error running mypy on {file_path}: {e}")
        return []

def categorize_violations(violations: List[Dict]) -> Dict[str, List[Dict]]:
    """Categorize violations by type."""
    categories = {
        'imports': [],
        'line_length': [],
        'whitespace': [],
        'docstring': [],
        'type_hints': [],
        'complexity': [],
        'other': []
    }

    for v in violations:
        if 'code' in v:
            code = v['code']
            if code in ['I001', 'F401', 'F403', 'E401', 'E402']:
                categories['imports'].append(v)
            elif code in ['E501']:
                categories['line_length'].append(v)
            elif code in ['W291', 'W292', 'W293', 'E302', 'E303']:
                categories['whitespace'].append(v)
            elif code in ['D100', 'D101', 'D102', 'D103', 'D205', 'D400']:
                categories['docstring'].append(v)
            elif code.startswith('C90'):
                categories['complexity'].append(v)
            else:
                categories['other'].append(v)
        else:
            # Mypy violations
            if 'type' in v.get('message', '').lower():
                categories['type_hints'].append(v)
            else:
                categories['other'].append(v)

    return categories

def analyze_cp_modules():
    """Analyze all CP modules for violations."""
    print("="*60)
    print("CP MODULE VIOLATION ANALYSIS")
    print("="*60)

    project_root = Path(r"C:\projects\Work Projects\ibm-projects\ESG Evaluation\prospecting-engine")

    total_violations = 0
    module_status = {}
    detailed_violations = {}

    for module in CP_MODULES:
        module_path = project_root / module
        if not module_path.exists():
            print(f"\n[MISSING] {module}")
            module_status[module] = "MISSING"
            continue

        print(f"\nAnalyzing: {module}")
        print("-" * 40)

        # Run ruff
        ruff_violations = run_ruff_check(str(module_path))

        # Run mypy
        mypy_violations = run_mypy_check(str(module_path))

        all_violations = ruff_violations + mypy_violations
        violation_count = len(all_violations)

        if violation_count == 0:
            print(f"  [CLEAN] No violations found")
            module_status[module] = "CLEAN"
        else:
            print(f"  [VIOLATIONS] {violation_count} issues found")
            module_status[module] = f"{violation_count} violations"

            # Categorize violations
            categories = categorize_violations(all_violations)

            for category, items in categories.items():
                if items:
                    print(f"    - {category}: {len(items)}")

            detailed_violations[module] = all_violations
            total_violations += violation_count

    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)

    clean_modules = [m for m, s in module_status.items() if s == "CLEAN"]
    dirty_modules = [m for m, s in module_status.items() if s not in ["CLEAN", "MISSING"]]

    print(f"\nTotal CP modules: {len(CP_MODULES)}")
    print(f"Clean modules: {len(clean_modules)}")
    print(f"Modules with violations: {len(dirty_modules)}")
    print(f"Total violations: {total_violations}")

    print("\nModule Status:")
    for module, status in module_status.items():
        emoji = "[OK]" if status == "CLEAN" else "[FAIL]" if "violations" in str(status) else "[SKIP]"
        print(f"  {emoji} {module}: {status}")

    # Write detailed report
    report_path = project_root / "tasks/037-remediation-031-035/artifacts/cp_violations_detailed.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)

    with open(report_path, 'w') as f:
        json.dump({
            'summary': {
                'total_modules': len(CP_MODULES),
                'clean_modules': len(clean_modules),
                'modules_with_violations': len(dirty_modules),
                'total_violations': total_violations
            },
            'module_status': module_status,
            'detailed_violations': detailed_violations
        }, f, indent=2)

    print(f"\nDetailed report saved to: {report_path}")

    # Generate fix script
    if dirty_modules:
        generate_fix_script(dirty_modules, detailed_violations, project_root)

    return total_violations, module_status, detailed_violations

def generate_fix_script(dirty_modules: List[str], violations: Dict, project_root: Path):
    """Generate a script with specific fixes for each violation."""
    fix_script = []
    fix_script.append("#!/usr/bin/env python3")
    fix_script.append('"""')
    fix_script.append("Auto-generated fix script for CP module violations")
    fix_script.append("Task 037 - Phase 2.2-2.4")
    fix_script.append('"""')
    fix_script.append("")
    fix_script.append("# Fixes needed by module:")

    for module in dirty_modules:
        fix_script.append(f"\n# {module}:")
        module_violations = violations.get(module, [])

        # Group by violation type
        by_code = {}
        for v in module_violations:
            code = v.get('code', 'mypy')
            if code not in by_code:
                by_code[code] = []
            by_code[code].append(v)

        for code, items in by_code.items():
            fix_script.append(f"#   {code}: {len(items)} occurrences")
            if code == 'E501':
                fix_script.append("#     Fix: Split long lines")
            elif code == 'F401':
                fix_script.append("#     Fix: Remove unused imports")
            elif code == 'I001':
                fix_script.append("#     Fix: Sort imports")
            elif code == 'W291':
                fix_script.append("#     Fix: Remove trailing whitespace")
            elif code == 'ANN':
                fix_script.append("#     Fix: Add type annotations")

    script_path = project_root / "tasks/037-remediation-031-035/scripts/fix_cp_violations.py"
    with open(script_path, 'w') as f:
        f.write('\n'.join(fix_script))

    print(f"\nFix script generated: {script_path}")

if __name__ == "__main__":
    total, status, details = analyze_cp_modules()
    sys.exit(0 if total == 0 else 1)