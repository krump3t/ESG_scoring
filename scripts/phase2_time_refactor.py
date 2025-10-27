#!/usr/bin/env python3
"""
Phase 2 Time Function Refactoring Script

Replaces clock.now() and clock.time() calls with Clock abstraction
for deterministic testing support.

This script:
1. Identifies all clock.time() and clock.now() calls
2. Generates replacement code using Clock abstraction
3. Applies replacements with safety checks
"""

import re
import sys
from pathlib import Path
from typing import List, Tuple


def find_time_calls(file_path: Path) -> List[Tuple[int, str, str]]:
    """Find all clock.time() and clock.now() calls with line numbers."""
    calls = []
    try:
        content = file_path.read_text(encoding='utf-8', errors='ignore')
        for line_num, line in enumerate(content.split('\n'), 1):
            # Skip comments and docstrings
            if line.strip().startswith('#') or line.strip().startswith('"""') or line.strip().startswith("'''"):
                continue

            # Detect clock.time()
            if re.search(r'\btime\.time\s*\(\)', line):
                calls.append((line_num, line, 'clock.time()'))

            # Detect clock.now()
            if re.search(r'\bdatetime\.now\s*\(\)', line):
                calls.append((line_num, line, 'clock.now()'))

    except Exception as e:
        print(f"Error reading {file_path}: {e}", file=sys.stderr)

    return calls


def generate_replacement(call_type: str, context: str) -> str:
    """Generate Clock-based replacement for a time function."""
    if call_type == 'clock.time()':
        return 'clock.time()'
    elif call_type == 'clock.now()':
        return 'clock.now()'
    return None


def process_file(file_path: Path) -> bool:
    """Process a single file, replacing time calls with Clock abstraction."""
    try:
        calls = find_time_calls(file_path)
        if not calls:
            return True

        content = file_path.read_text(encoding='utf-8', errors='ignore')
        lines = content.split('\n')

        # Check if Clock is already imported
        has_clock_import = any('from libs.utils.clock import' in line for line in lines)
        has_clock_usage = any('get_clock' in line for line in lines)

        if not has_clock_import and not has_clock_usage and calls:
            # Would need to add import - for now just report
            print(f"[INFO] {file_path}: {len(calls)} time calls found")
            for line_num, line, call_type in calls:
                print(f"       Line {line_num}: {call_type}")

        return False  # Return False = needs manual review

    except Exception as e:
        print(f"[ERROR] Failed to process {file_path}: {e}", file=sys.stderr)
        return False


def main():
    """Main entry point."""
    root = Path(__file__).parent.parent
    py_files = list(root.rglob("*.py"))

    # Skip test files, venv, __pycache__
    exclude_dirs = {".venv", "__pycache__", ".pytest_cache", "node_modules"}
    py_files = [f for f in py_files if not any(part in exclude_dirs for part in f.parts)]

    # Focus on key files from audit
    priority_files = [
        "scripts/cp/compare_esg_analysis.py",
        "apps/pipeline_orchestrator.py",
        "scripts/run_scoring.py",
        "apps/ingestion/crawler.py",
        "agents/crawler/data_providers/base_provider.py",
    ]

    print("=" * 80)
    print("PHASE 2: Time Function Refactoring")
    print("=" * 80)
    print()

    for priority_file in priority_files:
        file_path = root / priority_file
        if file_path.exists():
            print(f"\nChecking {priority_file}...")
            process_file(file_path)

    print()
    print("=" * 80)
    print("Manual Review Required:")
    print("=" * 80)
    print("""
For each file, follow this pattern:

1. Add import at top:
   from libs.utils.clock import get_clock
   clock = get_clock()

2. Replace:
   - clock.time() → clock.time()
   - clock.now() → clock.now()

3. Handle module-level time calls (move to function scope if needed)

4. Run audit to verify: python scripts/qa/authenticity_audit.py
""")


if __name__ == "__main__":
    main()
