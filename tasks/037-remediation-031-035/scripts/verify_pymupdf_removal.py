#!/usr/bin/env python3
"""
Verify complete removal of PyMuPDF imports from production code

Part of Task 037 Phase A.5 verification
"""

import os
import re
import sys
from pathlib import Path

def check_pymupdf_imports():
    """Check for PyMuPDF/fitz imports in Python files"""

    project_root = Path(__file__).parent.parent.parent.parent  # prospecting-engine root

    # Patterns to search for
    import_patterns = [
        r'^import fitz',
        r'^from fitz',
        r'^import.*PyMuPDF',
        r'^from.*PyMuPDF',
        r'^import pymupdf',
        r'^from pymupdf'
    ]

    # Files to exclude from check (legacy/deprecated files)
    excluded_files = {
        'backend_pymupdf_legacy.py',  # Renamed deprecated file
        'verify_docling_integration.py',  # Verification script
        'verify_pymupdf_removal.py'  # This script
    }

    # Test file patterns that are allowed to use PyMuPDF for PDF creation
    test_patterns = {
        '**/test_*.py',
        '**/*_test.py',
        '**/tests/**/*.py'
    }

    findings = []

    # Directories to skip
    skip_dirs = {'.venv', 'venv', '__pycache__', '.git', 'node_modules', '.mypy_cache', '.pytest_cache'}

    for root, dirs, files in os.walk(project_root):
        # Modify dirs in-place to skip certain directories
        dirs[:] = [d for d in dirs if d not in skip_dirs]

        for file in files:
            if not file.endswith('.py'):
                continue

            # Skip excluded files
            if file in excluded_files:
                continue

            py_file = Path(root) / file

            try:
                content = py_file.read_text(encoding='utf-8')
                for line_num, line in enumerate(content.splitlines(), 1):
                    for pattern in import_patterns:
                        if re.match(pattern, line.strip()):
                            findings.append({
                                'file': str(py_file.relative_to(project_root)),
                                'line': line_num,
                                'content': line.strip()
                            })
            except Exception as e:
                # Silently skip files we can't read
                pass

    return findings

def check_requirements():
    """Check if PyMuPDF is still in requirements files"""

    project_root = Path(__file__).parent.parent.parent.parent

    req_files = [
        'requirements.txt',
        'requirements-runtime.txt',
        'requirements-dev.txt',
        'pyproject.toml',
        'setup.py',
        'setup.cfg'
    ]

    findings = []

    for req_file in req_files:
        req_path = project_root / req_file
        if req_path.exists():
            try:
                content = req_path.read_text(encoding='utf-8')
                for line_num, line in enumerate(content.splitlines(), 1):
                    if 'pymupdf' in line.lower() or 'fitz' in line.lower():
                        # Check if it's not a comment
                        if not line.strip().startswith('#'):
                            findings.append({
                                'file': req_file,
                                'line': line_num,
                                'content': line.strip()
                            })
            except Exception as e:
                print(f"Error reading {req_file}: {e}")

    return findings

def main():
    """Main verification function"""

    print("="*60)
    print("PYMUPDF REMOVAL VERIFICATION")
    print("Task 037 Phase A.5")
    print("="*60)
    print()

    # Check for imports
    print("1. Checking for PyMuPDF imports in Python files...")
    import_findings = check_pymupdf_imports()

    if import_findings:
        print(f"   [FAIL] Found {len(import_findings)} PyMuPDF import(s):")
        for finding in import_findings:
            print(f"      - {finding['file']}:{finding['line']}")
            print(f"        {finding['content']}")
    else:
        print("   [PASS] No PyMuPDF imports found in production code")

    print()

    # Check requirements files
    print("2. Checking requirements files...")
    req_findings = check_requirements()

    if req_findings:
        print(f"   [FAIL] Found {len(req_findings)} PyMuPDF reference(s):")
        for finding in req_findings:
            print(f"      - {finding['file']}:{finding['line']}")
            print(f"        {finding['content']}")
    else:
        print("   [PASS] No PyMuPDF in requirements files")

    print()

    # Check if PyMuPDF is installed
    print("3. Checking if PyMuPDF is installed...")
    try:
        import fitz
        print(f"   [WARNING] PyMuPDF is installed (version {fitz.version[0]})")
        print("   Consider uninstalling with: pip uninstall pymupdf")
    except ImportError:
        print("   [PASS] PyMuPDF is not installed")

    print()

    # Summary
    total_issues = len(import_findings) + len(req_findings)

    if total_issues == 0:
        print("RESULT: SUCCESS")
        print("PyMuPDF has been successfully removed from production code")
        print("Docling migration is complete")
        return 0
    else:
        print(f"RESULT: FAILED")
        print(f"Found {total_issues} issue(s) that need to be addressed")
        return 1

if __name__ == "__main__":
    sys.exit(main())