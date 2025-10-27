#!/usr/bin/env python3
"""
Phase 2: Apply Clock Abstraction to ALL Files

Applies Clock-based determinism fixes to ALL files with clock.time() or clock.now() calls.
"""

import re
import sys
from pathlib import Path
from typing import Tuple


def add_clock_import(content: str) -> Tuple[str, bool]:
    """Add Clock import if not present."""
    if 'from libs.utils.clock import get_clock' in content:
        return content, False  # Already imported

    lines = content.split('\n')
    insert_pos = 0

    # Find the last import line
    for i, line in enumerate(lines):
        if line.startswith('import ') or line.startswith('from '):
            insert_pos = i + 1
        elif insert_pos > 0 and line and not line[0].isspace() and not (line.startswith('#') or line.startswith('"""')):
            break

    # Insert imports
    import_line = 'from libs.utils.clock import get_clock'
    clock_init = 'clock = get_clock()'

    # Check if we're in a class/function context that needs indentation
    lines.insert(insert_pos, import_line)
    lines.insert(insert_pos + 1, clock_init)

    return '\n'.join(lines), True


def replace_time_calls(content: str) -> Tuple[str, int]:
    """Replace clock.time() and clock.now() calls."""
    count = 0

    def replace_time_time(match):
        nonlocal count
        count += 1
        return 'clock.time()'

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

        # Skip if already fully processed
        if 'from libs.utils.clock import get_clock' in content:
            # Still need to replace calls
            content, call_count = replace_time_calls(content)
            if call_count > 0:
                file_path.write_text(content, encoding='utf-8')
                return True
            return False

        # Check if file has any time calls
        has_time_time = 'clock.time()' in content
        has_datetime_now = 'clock.now()' in content

        if not (has_time_time or has_datetime_now):
            return False

        # Skip test files for now (they have different patterns)
        if 'test' in str(file_path):
            return False

        # Add import
        content, import_added = add_clock_import(content)

        # Replace calls
        content, call_count = replace_time_calls(content)

        if call_count > 0:
            file_path.write_text(content, encoding='utf-8')
            return True

        return False

    except Exception as e:
        print(f"[WARN] {file_path}: {e}", file=sys.stderr)
        return False


def main():
    """Apply Clock abstraction to all files."""
    root = Path.cwd()
    if root.name != 'prospecting-engine':
        print(f"[ERROR] Must run from project root")
        sys.exit(1)

    # Find all Python files
    py_files = list(root.rglob("*.py"))

    # Exclude directories
    exclude_dirs = {".venv", "__pycache__", ".pytest_cache", "node_modules", ".git"}
    py_files = [f for f in py_files if not any(part in exclude_dirs for part in f.parts)]

    # Filter to files with time violations (exclude test files for automated processing)
    target_files = []
    for f in py_files:
        if 'test' in str(f):
            continue
        try:
            content = f.read_text(encoding='utf-8', errors='ignore')
            if 'clock.time()' in content or 'clock.now()' in content:
                target_files.append(f)
        except:
            pass

    print("=" * 80)
    print(f"PHASE 2: Applying Clock Abstraction to {len(target_files)} files")
    print("=" * 80)
    print()

    updated_count = 0
    for file_path in sorted(target_files):
        try:
            if process_file(file_path):
                print(f"[OK] {file_path.relative_to(root)}")
                updated_count += 1
        except Exception as e:
            print(f"[SKIP] {file_path.relative_to(root)}: {e}")

    print()
    print(f"Total files updated: {updated_count} / {len(target_files)}")
    print()
    print("Run audit to verify: python scripts/qa/authenticity_audit.py")


if __name__ == "__main__":
    main()
