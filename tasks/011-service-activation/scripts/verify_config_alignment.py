#!/usr/bin/env python3
"""
Verify Docker Configuration Alignment: Task 011

Protocol: SCA v13.8-MEA
Task: 011-service-activation

Validates that all Docker configuration files default to ALLOW_NETWORK=true.
"""

import re
import sys
from pathlib import Path
from typing import List, Tuple

# Windows console compatibility
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')


def check_dockerfile(dockerfile_path: Path) -> Tuple[bool, str]:
    """
    Verify Dockerfile sets ALLOW_NETWORK=true.

    Args:
        dockerfile_path: Path to Dockerfile

    Returns:
        (success: bool, message: str)
    """
    try:
        content = dockerfile_path.read_text()

        # Look for ALLOW_NETWORK ENV setting
        pattern = r'ALLOW_NETWORK=(\w+)'
        match = re.search(pattern, content)

        if not match:
            return False, "Dockerfile: ALLOW_NETWORK not found"

        value = match.group(1)
        if value != "true":
            return False, f"Dockerfile: ALLOW_NETWORK={value} (expected: true)"

        return True, "Dockerfile: ✓ ALLOW_NETWORK=true"

    except Exception as e:
        return False, f"Dockerfile: Error reading file: {e}"


def check_docker_compose(compose_path: Path) -> Tuple[bool, str]:
    """
    Verify docker-compose.live.yml defaults ALLOW_NETWORK to true.

    Args:
        compose_path: Path to docker-compose.live.yml

    Returns:
        (success: bool, message: str)
    """
    try:
        content = compose_path.read_text()

        # Look for ALLOW_NETWORK environment variable with default
        pattern = r'ALLOW_NETWORK=\$\{ALLOW_NETWORK:-(\w+)\}'
        matches = re.findall(pattern, content)

        if not matches:
            return False, "docker-compose.live.yml: ALLOW_NETWORK not found"

        # Check all occurrences (should be in both api and runner services)
        failures = []
        for idx, value in enumerate(matches, 1):
            if value != "true":
                failures.append(f"occurrence {idx}: default={value}")

        if failures:
            return False, f"docker-compose.live.yml: {', '.join(failures)} (expected: true)"

        return True, f"docker-compose.live.yml: ✓ ALLOW_NETWORK defaults to true ({len(matches)} occurrences)"

    except Exception as e:
        return False, f"docker-compose.live.yml: Error reading file: {e}"


def check_env_example(env_path: Path) -> Tuple[bool, str]:
    """
    Verify .env.example sets ALLOW_NETWORK=true.

    Args:
        env_path: Path to .env.example

    Returns:
        (success: bool, message: str)
    """
    try:
        content = env_path.read_text()

        # Look for ALLOW_NETWORK setting (not in a comment)
        pattern = r'^ALLOW_NETWORK=(\w+)$'
        match = re.search(pattern, content, re.MULTILINE)

        if not match:
            return False, ".env.example: ALLOW_NETWORK not found"

        value = match.group(1)
        if value != "true":
            return False, f".env.example: ALLOW_NETWORK={value} (expected: true)"

        return True, ".env.example: ✓ ALLOW_NETWORK=true"

    except Exception as e:
        return False, f".env.example: Error reading file: {e}"


def main() -> int:
    """
    Main verification routine.

    Returns:
        0 if all checks pass, 1 if any check fails
    """
    # Define paths relative to repository root
    repo_root = Path(__file__).parents[3]

    checks: List[Tuple[Path, callable]] = [
        (repo_root / "Dockerfile", check_dockerfile),
        (repo_root / "docker-compose.live.yml", check_docker_compose),
        (repo_root / ".env.example", check_env_example),
    ]

    print("=" * 80)
    print("Docker Configuration Alignment Verification")
    print("Task: 011-service-activation")
    print("=" * 80)
    print()

    results = []
    for file_path, check_func in checks:
        if not file_path.exists():
            print(f"❌ {file_path.name}: File not found at {file_path}")
            results.append(False)
            continue

        success, message = check_func(file_path)
        results.append(success)

        icon = "✓" if success else "❌"
        print(f"{icon} {message}")

    print()
    print("=" * 80)

    if all(results):
        print("✓ ALL CHECKS PASSED: Configuration alignment verified")
        print()
        print("Summary:")
        print("  - All Docker configs default to ALLOW_NETWORK=true")
        print("  - Production-first philosophy enforced")
        print("  - CI/CD must override to false for offline mode")
        print("=" * 80)
        return 0
    else:
        failed_count = sum(1 for r in results if not r)
        print(f"❌ {failed_count} CHECK(S) FAILED: Configuration misalignment detected")
        print()
        print("Remediation:")
        print("  1. Review failed checks above")
        print("  2. Update files to default ALLOW_NETWORK=true")
        print("  3. See ADR-011-003 for rationale")
        print("=" * 80)
        return 1


if __name__ == "__main__":
    sys.exit(main())
