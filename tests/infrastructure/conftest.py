"""
pytest Configuration for Phase 1 Infrastructure Tests

Implements SCA v13.8 MEA traceability requirements:
- Capture run_log.txt with all test execution events
- Generate run_manifest.json with files touched
- Create run_events.jsonl with detailed execution trace
- Measure coverage with pytest-cov
"""

import json
import time
from pathlib import Path
from typing import Dict, Any, List
import subprocess
import sys

import pytest


# ============================================================================
# Global Test Context (SCA v13.8 Traceability)
# ============================================================================

class TestContext:
    """Capture test execution context for MEA compliance."""

    def __init__(self):
        self.start_time = time.time()
        self.run_id = f"phase1-{int(self.start_time)}"
        self.task_dir = Path(__file__).parent.parent.parent
        self.qa_dir = self.task_dir / "qa"
        self.artifacts_dir = self.task_dir / "artifacts"
        self.qa_dir.mkdir(exist_ok=True)
        self.artifacts_dir.mkdir(exist_ok=True)

        self.log_file = self.qa_dir / "run_log.txt"
        self.manifest_file = self.artifacts_dir / "run_manifest.json"
        self.events_file = self.artifacts_dir / "run_events.jsonl"

        self.events: List[Dict[str, Any]] = []
        self.files_touched: List[str] = []

    def log(self, message: str, level: str = "INFO"):
        """Write to run_log.txt with timestamp."""
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"{timestamp} [{level}] {message}"

        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(log_entry + "\n")

        # Also print to console
        print(log_entry)

    def record_event(self, event_type: str, data: Dict[str, Any]):
        """Record detailed execution event to run_events.jsonl."""
        event = {
            "timestamp": time.time(),
            "type": event_type,
            "data": data
        }

        self.events.append(event)

        # Append to JSONL file
        with open(self.events_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(event) + "\n")

    def track_file(self, filepath: str):
        """Track files touched during test execution."""
        if filepath not in self.files_touched:
            self.files_touched.append(filepath)

    def save_manifest(self):
        """Save run_manifest.json with all files touched."""
        manifest = {
            "run_id": self.run_id,
            "task_dir": str(self.task_dir),
            "start_time": self.start_time,
            "end_time": time.time(),
            "duration_seconds": time.time() - self.start_time,
            "files_touched": self.files_touched,
            "test_files": [
                "tests/infrastructure/test_docker_services.py",
                "tests/infrastructure/test_docker_properties.py",
                "tests/infrastructure/test_cloud_connectivity.py"
            ],
            "total_events": len(self.events)
        }

        with open(self.manifest_file, "w") as f:
            json.dump(manifest, f, indent=2)


# Global test context instance
_test_context = TestContext()


# ============================================================================
# Pytest Hooks (SCA v13.8 Traceability)
# ============================================================================

def pytest_configure(config):
    """Initialize test run."""
    _test_context.log("=" * 80)
    _test_context.log("PHASE 1: PRODUCTION INTEGRATION - INFRASTRUCTURE TESTS")
    _test_context.log("=" * 80)
    _test_context.log(f"Run ID: {_test_context.run_id}")
    _test_context.log(f"Python: {sys.version}")
    _test_context.log(f"pytest: {pytest.__version__}")
    _test_context.log("")


def pytest_runtest_logreport(report):
    """Capture test results in run_events.jsonl."""
    if report.when == "call":  # Only capture actual test execution
        test_name = report.nodeid
        outcome = report.outcome  # passed, failed, skipped

        _test_context.record_event(
            "test_result",
            {
                "test_name": test_name,
                "outcome": outcome,
                "duration_seconds": report.duration if hasattr(report, "duration") else None,
                "markers": [m.name for m in report.user_properties] if hasattr(report, "user_properties") else []
            }
        )

        # Log to run_log.txt (without unicode to avoid encoding issues)
        status_icon = "[PASS]" if outcome == "passed" else "[FAIL]" if outcome == "failed" else "[SKIP]"
        _test_context.log(f"{status_icon} {test_name} [{outcome}]")


def pytest_sessionfinish(session, exitstatus):
    """Finalize test run and save artifacts."""
    try:
        _test_context.log("")
        # Get test counts safely
        passed = getattr(session, 'testspassed', 0) if hasattr(session, 'testspassed') else 0
        failed = getattr(session, 'testsfailed', 0) if hasattr(session, 'testsfailed') else 0
        _test_context.log(f"Exit status: {exitstatus}")
        _test_context.log("")

        # Save manifest
        _test_context.save_manifest()

        _test_context.log("")
        _test_context.log("=" * 80)
        _test_context.log("PHASE 1 TEST RUN COMPLETE")
        _test_context.log("=" * 80)
        _test_context.log(f"Run log: {_test_context.log_file}")
        _test_context.log(f"Manifest: {_test_context.manifest_file}")
        _test_context.log(f"Events: {_test_context.events_file}")
    except Exception as e:
        # Don't fail session finish if there's an error
        print(f"Warning: Error in pytest_sessionfinish: {e}")


# ============================================================================
# Pytest Fixtures for Traceability
# ============================================================================

@pytest.fixture(scope="session")
def test_context():
    """Provide test context to all tests."""
    return _test_context


@pytest.fixture(autouse=True)
def record_test_file(request, test_context):
    """Automatically track test files."""
    test_context.track_file(str(request.fspath))


# ============================================================================
# Pytest Markers (Custom)
# ============================================================================

def pytest_configure(config):
    """Register custom pytest markers."""
    config.addinivalue_line(
        "markers", "cp: critical path test (subject to strict gates)"
    )
    config.addinivalue_line(
        "markers", "cloud: requires cloud credentials (watsonx.ai, AstraDB)"
    )
    config.addinivalue_line(
        "markers", "integration: integration test (requires running services)"
    )
    config.addinivalue_line(
        "markers", "infrastructure: infrastructure service test"
    )
    config.addinivalue_line(
        "markers", "property: property-based test using hypothesis"
    )
    config.addinivalue_line(
        "markers", "slow: slow test (may take 5+ seconds)"
    )
    config.addinivalue_line(
        "markers", "failure_path: tests failure/error handling"
    )
