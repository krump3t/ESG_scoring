#!/usr/bin/env python3
"""
Phase 2: Apply Clock Abstraction to All Files

Applies Clock-based determinism fixes to replace clock.time() and clock.now()
calls throughout the codebase.
"""

import re
import sys
from pathlib import Path
from typing import Tuple, List


def add_clock_import(content: str) -> Tuple[str, bool]:
    """Add Clock import if not present."""
    if 'from libs.utils.clock import get_clock' in content:
        return content, False  # Already imported

    # Find the right place to insert (after other imports)
    lines = content.split('\n')
    insert_pos = 0

    for i, line in enumerate(lines):
        if line.startswith('import ') or line.startswith('from '):
            insert_pos = i + 1
        elif insert_pos > 0 and not line.startswith('import ') and not line.startswith('from '):
            break

    # Insert import and clock initialization
    import_line = 'from libs.utils.clock import get_clock'
    clock_init = 'clock = get_clock()'

    lines.insert(insert_pos, import_line)
    lines.insert(insert_pos + 1, clock_init)

    return '\n'.join(lines), True


def replace_time_calls(content: str) -> Tuple[str, int]:
    """Replace clock.time() and clock.now() calls."""
    count = 0

    # Replace clock.time() → clock.time()
    def replace_time_time(match):
        nonlocal count
        count += 1
        return 'clock.time()'

    # Replace clock.now() → clock.now()
    def replace_datetime_now(match):
        nonlocal count
        count += 1
        return 'clock.now()'

    content = re.sub(r'\btime\.time\s*\(\)', replace_time_time, content)
    content = re.sub(r'\bdatetime\.now\s*\(\)', replace_datetime_now, content)

    return content, count


def process_file(file_path: Path) -> bool:
    """Process a file: add imports and replace time calls."""
    try:
        content = file_path.read_text(encoding='utf-8', errors='ignore')
        original_content = content

        # Skip if already processed
        if 'from libs.utils.clock import get_clock' in content and 'clock = get_clock()' in content:
            return False

        # Check if file has any time calls
        has_time_time = 'clock.time()' in content
        has_datetime_now = 'clock.now()' in content

        if not (has_time_time or has_datetime_now):
            return False

        # Add import
        content, import_added = add_clock_import(content)

        # Replace calls
        content, call_count = replace_time_calls(content)

        if call_count > 0:
            file_path.write_text(content, encoding='utf-8')
            print(f"[UPDATED] {file_path.relative_to(Path.cwd())}: {call_count} replacements")
            return True
        else:
            # Revert if no replacements were made
            file_path.write_text(original_content, encoding='utf-8')
            return False

    except Exception as e:
        print(f"[ERROR] Failed to process {file_path}: {e}", file=sys.stderr)
        return False


def main():
    """Apply Clock abstraction to relevant files."""
    root = Path.cwd()
    if root.name != 'prospecting-engine':
        print(f"[ERROR] Must run from project root. Currently in {root}")
        sys.exit(1)

    # Find all Python files
    py_files = list(root.rglob("*.py"))

    # Exclude directories
    exclude_dirs = {".venv", "__pycache__", ".pytest_cache", "node_modules", ".git"}
    py_files = [f for f in py_files if not any(part in exclude_dirs for part in f.parts)]

    # Priority: files with most violations
    priority_files = {
        "scripts/cp/compare_esg_analysis.py": 13,
        "apps/pipeline_orchestrator.py": 12,
        "scripts/run_scoring.py": 6,
        "apps/ingestion/crawler.py": 3,
        "agents/crawler/data_providers/base_provider.py": 2,
    }

    print("=" * 80)
    print("PHASE 2: Applying Clock Abstraction")
    print("=" * 80)
    print()

    updated_count = 0
    for rel_path in sorted(priority_files.keys()):
        file_path = root / rel_path
        if file_path.exists():
            if process_file(file_path):
                updated_count += 1

    print()
    print(f"Total files updated: {updated_count}")
    print()
    print("Next: python scripts/qa/authenticity_audit.py")


if __name__ == "__main__":
    main()
