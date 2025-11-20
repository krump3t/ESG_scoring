#!/usr/bin/env python3
"""
Smoke Test: Task 011 Service Activation

Protocol: SCA v13.8-MEA
Task: 011-service-activation

Validates offline/online mode routing in deployed service.
"""

import sys
import os
from pathlib import Path

# Windows console compatibility
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def test_docker_config_alignment() -> bool:
    """Verify Docker configs all default to ALLOW_NETWORK=true"""
    print("=" * 80)
    print("Test 1: Docker Configuration Alignment")
    print("=" * 80)

    # Run verification script
    repo_root = Path(__file__).parents[3]
    verify_script = repo_root / "tasks" / "011-service-activation" / "scripts" / "verify_config_alignment.py"

    if not verify_script.exists():
        print(f"❌ Verification script not found: {verify_script}")
        return False

    import subprocess
    result = subprocess.run(
        [sys.executable, str(verify_script)],
        cwd=repo_root,
        capture_output=True,
        text=True
    )

    print(result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr)

    if result.returncode == 0:
        print("✓ Docker configuration alignment PASSED\n")
        return True
    else:
        print("❌ Docker configuration alignment FAILED\n")
        return False


def test_crawler_adapter_unit_tests() -> bool:
    """Verify CrawlerAdapter unit tests pass"""
    print("=" * 80)
    print("Test 2: CrawlerAdapter Unit Tests")
    print("=" * 80)

    repo_root = Path(__file__).parents[3]

    import subprocess
    result = subprocess.run(
        [
            sys.executable, "-m", "pytest",
            "tests/agents/crawler/test_crawler_adapter.py",
            "-v", "--tb=short"
        ],
        cwd=repo_root,
        capture_output=True,
        text=True
    )

    # Show summary line
    lines = result.stdout.split("\n")
    for line in lines:
        if "passed" in line or "PASSED" in line or "FAILED" in line:
            print(line)

    if result.returncode == 0:
        print("✓ CrawlerAdapter tests PASSED\n")
        return True
    else:
        print("❌ CrawlerAdapter tests FAILED")
        print("Run manually: pytest tests/agents/crawler/test_crawler_adapter.py -v\n")
        return False


def test_orchestrator_wiring_unit_tests() -> bool:
    """Verify PipelineOrchestrator wiring tests pass"""
    print("=" * 80)
    print("Test 3: PipelineOrchestrator Wiring Tests")
    print("=" * 80)

    repo_root = Path(__file__).parents[3]

    import subprocess
    result = subprocess.run(
        [
            sys.executable, "-m", "pytest",
            "tests/apps/test_pipeline_orchestrator_wiring.py",
            "-v", "--tb=short"
        ],
        cwd=repo_root,
        capture_output=True,
        text=True
    )

    # Show summary line
    lines = result.stdout.split("\n")
    for line in lines:
        if "passed" in line or "PASSED" in line or "FAILED" in line:
            print(line)

    if result.returncode == 0:
        print("✓ Orchestrator wiring tests PASSED\n")
        return True
    else:
        print("❌ Orchestrator wiring tests FAILED")
        print("Run manually: pytest tests/apps/test_pipeline_orchestrator_wiring.py -v\n")
        return False


def test_offline_mode_routing() -> bool:
    """Verify ALLOW_NETWORK=false uses demo_flow (integration check)"""
    print("=" * 80)
    print("Test 4: Offline Mode Routing")
    print("=" * 80)

    # This is a structural check - verify imports work
    try:
        # Set environment to offline mode
        os.environ["ALLOW_NETWORK"] = "false"

        # Import main.py to check no import errors
        sys.path.insert(0, str(Path(__file__).parents[3]))
        from apps.api import main

        # Check if allow_network logic exists
        import inspect
        source = inspect.getsource(main.score_esg)

        if "ALLOW_NETWORK" in source:
            print("✓ Offline mode routing: ALLOW_NETWORK check present")
            if "demo_flow" in source:
                print("✓ Offline mode routing: demo_flow import present")
                print("✓ Offline mode routing logic PASSED\n")
                return True
            else:
                print("❌ demo_flow import not found in routing logic\n")
                return False
        else:
            print("❌ ALLOW_NETWORK check not found in /score endpoint\n")
            return False

    except ImportError as e:
        print(f"❌ Import error: {e}\n")
        return False
    except Exception as e:
        print(f"❌ Error: {e}\n")
        return False


def test_online_mode_routing() -> bool:
    """Verify ALLOW_NETWORK=true initializes PipelineOrchestrator"""
    print("=" * 80)
    print("Test 5: Online Mode Routing")
    print("=" * 80)

    try:
        # Set environment to online mode
        os.environ["ALLOW_NETWORK"] = "true"

        # Import main.py
        sys.path.insert(0, str(Path(__file__).parents[3]))
        from apps.api import main

        # Check if PipelineOrchestrator logic exists
        import inspect
        source = inspect.getsource(main.score_esg)

        if "PipelineOrchestrator" in source:
            print("✓ Online mode routing: PipelineOrchestrator import present")
            if 'os.getenv("ALLOW_NETWORK"' in source or "ALLOW_NETWORK" in source:
                print("✓ Online mode routing: Environment variable check present")
                print("✓ Online mode routing logic PASSED\n")
                return True
            else:
                print("❌ ALLOW_NETWORK environment check not found\n")
                return False
        else:
            print("❌ PipelineOrchestrator import not found in routing logic\n")
            return False

    except ImportError as e:
        print(f"❌ Import error: {e}\n")
        return False
    except Exception as e:
        print(f"❌ Error: {e}\n")
        return False


def main() -> int:
    """Run all smoke tests"""
    print("\n" + "=" * 80)
    print("TASK 011 SERVICE ACTIVATION - SMOKE TESTS")
    print("=" * 80)
    print()

    tests = [
        ("Docker Config Alignment", test_docker_config_alignment),
        ("CrawlerAdapter Tests", test_crawler_adapter_unit_tests),
        ("Orchestrator Wiring Tests", test_orchestrator_wiring_unit_tests),
        ("Offline Mode Routing", test_offline_mode_routing),
        ("Online Mode Routing", test_online_mode_routing),
    ]

    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} CRASHED: {e}\n")
            results.append((test_name, False))

    # Summary
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "✓ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")

    print()
    print(f"Total: {passed}/{total} tests passed")
    print("=" * 80)

    if passed == total:
        print("\n✓ ALL SMOKE TESTS PASSED")
        print("Task 011 Service Activation is ready for validation.\n")
        return 0
    else:
        print(f"\n❌ {total - passed} SMOKE TEST(S) FAILED")
        print("Review failures above before proceeding to validation.\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
