#!/usr/bin/env python3
"""
Dependency Lock CI Gate - SCA v13.8

Fails CI if requirements.txt contains:
- Wildcard version specs (*,  >=X.*)
- Unpinned dependencies (missing ==)

Exceptions allowed for: pip, setuptools, wheel

Usage:
    python scripts/check_dependencies.py [--requirements PATH]

Exit codes:
    0: All dependencies properly pinned
    1: Found unpinned or wildcard dependencies
"""

import sys
import re
from pathlib import Path
from typing import List, Tuple, Optional

# Allowed exceptions (can use >= or no pin)
ALLOWED_EXCEPTIONS = {"pip", "setuptools", "wheel"}


def parse_requirement_line(line: str) -> Optional[Tuple[str, str]]:
    """
    Parse a requirements.txt line into (package_name, version_spec).

    Args:
        line: Single line from requirements.txt

    Returns:
        Tuple of (package_name, version_spec) or None if comment/empty

    Example:
        >>> parse_requirement_line("numpy==1.24.0")
        ('numpy', '==1.24.0')
        >>> parse_requirement_line("pandas>=2.0.0")
        ('pandas', '>=2.0.0')
        >>> parse_requirement_line("# Comment line")
        None
    """
    # Strip whitespace and comments
    line = line.strip()
    if not line or line.startswith("#"):
        return None

    # Match package specs with comparison operators
    # Pattern: package-name[comparison_op]version
    match = re.match(
        r"^([a-zA-Z0-9_\-]+)\s*([><=!]+)\s*(.+)$",
        line
    )
    if match:
        package = match.group(1)
        operator = match.group(2)
        version = match.group(3)
        return (package, f"{operator}{version}")

    # Unpinned package (no version spec)
    match_unpinned = re.match(r"^([a-zA-Z0-9_\-]+)$", line)
    if match_unpinned:
        package = match_unpinned.group(1)
        return (package, "")

    return None


def check_dependency_lock(requirements_path: str) -> Tuple[bool, List[str]]:
    """
    Check if all dependencies in requirements.txt are properly pinned.

    Args:
        requirements_path: Path to requirements.txt file

    Returns:
        Tuple of (is_valid, error_messages)

    Validation rules:
        - Must use == for exact pinning (except allowed exceptions)
        - No wildcard versions (* in version spec)
        - Allowed exceptions: pip, setuptools, wheel
    """
    path = Path(requirements_path)
    if not path.exists():
        return False, [f"Requirements file not found: {requirements_path}"]

    errors: List[str] = []

    with open(path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    for line_num, line in enumerate(lines, start=1):
        parsed = parse_requirement_line(line)
        if parsed is None:
            continue  # Skip comments and empty lines

        package, version_spec = parsed

        # Skip allowed exceptions
        if package.lower() in ALLOWED_EXCEPTIONS:
            continue

        # Check for unpinned (no version spec)
        if not version_spec:
            errors.append(
                f"Line {line_num}: Package '{package}' is unpinned (no version spec). "
                f"Use '==' for exact pinning."
            )
            continue

        # Check for wildcard in version
        if "*" in version_spec:
            errors.append(
                f"Line {line_num}: Package '{package}' uses wildcard version '{version_spec}'. "
                f"Wildcards not allowed."
            )
            continue

        # Check for non-exact pinning (not using ==)
        if not version_spec.startswith("=="):
            errors.append(
                f"Line {line_num}: Package '{package}' uses non-exact version '{version_spec}'. "
                f"Use '==' for exact pinning (e.g., {package}==1.0.0)."
            )
            continue

    is_valid = len(errors) == 0
    return is_valid, errors


def main() -> int:
    """
    Main entry point for dependency check script.

    Returns:
        Exit code: 0 if valid, 1 if errors found
    """
    import argparse

    parser = argparse.ArgumentParser(
        description="Check if requirements.txt has properly pinned dependencies"
    )
    parser.add_argument(
        "--requirements",
        default="requirements.txt",
        help="Path to requirements.txt file (default: requirements.txt)"
    )

    args = parser.parse_args()

    print(f"Checking dependency lock: {args.requirements}")
    print("-" * 60)

    is_valid, errors = check_dependency_lock(args.requirements)

    if is_valid:
        print("[PASS] All dependencies properly pinned")
        return 0
    else:
        print(f"[FAIL] Found {len(errors)} dependency lock violations:")
        print()
        for error in errors:
            print(f"  * {error}")
        print()
        print("Allowed exceptions (can use >= or unpinned):")
        for exc in sorted(ALLOWED_EXCEPTIONS):
            print(f"  - {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
