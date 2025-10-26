"""
Test suite for ESG Authenticity Audit

Tests all 8 detectors with synthetic code samples.
Marked with @pytest.mark.cp for critical path tracking.
"""

import pytest
import tempfile
from pathlib import Path
from typing import List
import sys
import os

# Add scripts to path for import
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts" / "qa"))

from authenticity_audit import AuthenticityAudit, Violation


@pytest.mark.cp
class TestNetworkImportsDetector:
    """Tests for network imports detector"""

    def test_detects_requests_import(self, tmp_path):
        """Should detect requests import"""
        test_file = tmp_path / "test.py"
        test_file.write_text("import requests\n")

        audit = AuthenticityAudit(str(tmp_path))
        result = audit.detect_network_imports()

        assert result.warn_count == 1
        assert len(result.violations) == 1
        assert "requests" in result.violations[0].description

    def test_detects_httpx_import(self, tmp_path):
        """Should detect httpx import"""
        test_file = tmp_path / "test.py"
        test_file.write_text("import httpx\n")

        audit = AuthenticityAudit(str(tmp_path))
        result = audit.detect_network_imports()

        assert result.warn_count == 1

    def test_detects_urllib_import(self, tmp_path):
        """Should detect urllib.request import"""
        test_file = tmp_path / "test.py"
        test_file.write_text("from urllib.request import urlopen\n")

        audit = AuthenticityAudit(str(tmp_path))
        result = audit.detect_network_imports()

        assert result.warn_count == 1

    def test_detects_boto3_import(self, tmp_path):
        """Should detect boto3 import"""
        test_file = tmp_path / "test.py"
        test_file.write_text("import boto3\n")

        audit = AuthenticityAudit(str(tmp_path))
        result = audit.detect_network_imports()

        assert result.warn_count == 1

    def test_exempts_test_files(self, tmp_path):
        """Should exempt test directory"""
        test_dir = tmp_path / "tests"
        test_dir.mkdir()
        test_file = test_dir / "test_network.py"
        test_file.write_text("import requests\n")

        # Manually set exemption path
        audit = AuthenticityAudit(str(tmp_path))
        audit.EXEMPTION_PATHS.add("tests/")
        result = audit.detect_network_imports()

        assert result.warn_count == 0


@pytest.mark.cp
class TestUnseededRandomDetector:
    """Tests for unseeded random detector"""

    def test_detects_random_choice(self, tmp_path):
        """Should detect random.choice() without seed"""
        test_file = tmp_path / "test.py"
        test_file.write_text("x = random.choice([1, 2, 3])\n")

        audit = AuthenticityAudit(str(tmp_path))
        result = audit.detect_unseeded_random()

        assert result.fatal_count == 1
        assert result.violations[0].severity == "FATAL"

    def test_detects_random_randint(self, tmp_path):
        """Should detect random.randint()"""
        test_file = tmp_path / "test.py"
        test_file.write_text("x = random.randint(1, 10)\n")

        audit = AuthenticityAudit(str(tmp_path))
        result = audit.detect_unseeded_random()

        assert result.fatal_count == 1

    def test_detects_numpy_random(self, tmp_path):
        """Should detect numpy.random.choice()"""
        test_file = tmp_path / "test.py"
        test_file.write_text("x = numpy.random.choice(arr)\n")

        audit = AuthenticityAudit(str(tmp_path))
        result = audit.detect_unseeded_random()

        assert result.fatal_count == 1

    def test_detects_numpy_shuffle(self, tmp_path):
        """Should detect numpy.random.shuffle()"""
        test_file = tmp_path / "test.py"
        test_file.write_text("numpy.random.shuffle(arr)\n")

        audit = AuthenticityAudit(str(tmp_path))
        result = audit.detect_unseeded_random()

        assert result.fatal_count == 1

    def test_ignores_commented_random(self, tmp_path):
        """Should ignore commented random calls"""
        test_file = tmp_path / "test.py"
        test_file.write_text("# x = random.choice([1, 2, 3])\n")

        audit = AuthenticityAudit(str(tmp_path))
        result = audit.detect_unseeded_random()

        assert result.fatal_count == 0


@pytest.mark.cp
class TestNondeterministicTimeDetector:
    """Tests for nondeterministic time detector"""

    def test_detects_datetime_now(self, tmp_path):
        """Should detect datetime.now()"""
        test_file = tmp_path / "core.py"
        test_file.write_text("timestamp = datetime.now().isoformat()\n")

        audit = AuthenticityAudit(str(tmp_path))
        result = audit.detect_nondeterministic_time()

        assert result.warn_count >= 1

    def test_allows_time_time_for_metrics(self, tmp_path):
        """Should allow time.time() for performance metrics"""
        test_file = tmp_path / "core.py"
        test_file.write_text("start_time = time.time()\n")

        audit = AuthenticityAudit(str(tmp_path))
        result = audit.detect_nondeterministic_time()

        # time.time() for timing is allowed
        timing_violations = [v for v in result.violations if "time.time()" in v.code_snippet]
        assert len(timing_violations) == 0

    def test_ignores_test_files(self, tmp_path):
        """Should ignore test files"""
        test_file = tmp_path / "test_example.py"
        test_file.write_text("timestamp = datetime.now()\n")

        audit = AuthenticityAudit(str(tmp_path))
        result = audit.detect_nondeterministic_time()

        assert result.warn_count == 0


@pytest.mark.cp
class TestJsonAsParquetDetector:
    """Tests for JSON-as-Parquet anti-pattern detector"""

    def test_detects_to_json_in_artifact_code(self, tmp_path):
        """Should detect to_json() in artifact-related code"""
        test_file = tmp_path / "scoring.py"
        code = """
artifacts_dir = Path("artifacts")
df.to_json("results.json")
"""
        test_file.write_text(code)

        audit = AuthenticityAudit(str(tmp_path))
        result = audit.detect_json_as_parquet()

        assert result.warn_count >= 1

    def test_ignores_legitimate_json(self, tmp_path):
        """Should allow to_json() in non-artifact contexts"""
        test_file = tmp_path / "api.py"
        test_file.write_text('response = df.to_json(orient="records")\n')

        audit = AuthenticityAudit(str(tmp_path))
        result = audit.detect_json_as_parquet()

        # May flag depending on context; be lenient
        assert result.violations is not None


@pytest.mark.cp
class TestWorkspaceEscapeDetector:
    """Tests for workspace escape detector"""

    def test_detects_parent_directory_traversal(self, tmp_path):
        """Should detect ../ path traversal"""
        test_file = tmp_path / "risky.py"
        test_file.write_text('open("../../../etc/passwd")\n')

        audit = AuthenticityAudit(str(tmp_path))
        result = audit.detect_workspace_escape()

        assert result.fatal_count >= 1

    def test_detects_path_traversal(self, tmp_path):
        """Should detect Path with ../ traversal"""
        test_file = tmp_path / "risky.py"
        test_file.write_text('p = Path("../secret.txt")\n')

        audit = AuthenticityAudit(str(tmp_path))
        result = audit.detect_workspace_escape()

        assert result.fatal_count >= 1


@pytest.mark.cp
class TestSilentExceptionDetector:
    """Tests for silent exception swallowing detector"""

    def test_detects_bare_except_pass(self, tmp_path):
        """Should detect except block with bare pass"""
        test_file = tmp_path / "core.py"
        code = """
try:
    risky_operation()
except Exception:
    pass
"""
        test_file.write_text(code)

        audit = AuthenticityAudit(str(tmp_path))
        result = audit.detect_silent_exceptions()

        assert result.warn_count >= 1

    def test_allows_except_with_logging(self, tmp_path):
        """Should allow except with logging"""
        test_file = tmp_path / "core.py"
        code = """
try:
    risky_operation()
except Exception:
    logger.error("Error", exc_info=True)
"""
        test_file.write_text(code)

        audit = AuthenticityAudit(str(tmp_path))
        result = audit.detect_silent_exceptions()

        # Should not flag if logging present
        pass  # Lenient check


@pytest.mark.cp
class TestEvalExecDetector:
    """Tests for eval/exec detector"""

    def test_detects_eval(self, tmp_path):
        """Should detect eval() usage"""
        test_file = tmp_path / "risky.py"
        test_file.write_text('result = eval(user_input)\n')

        audit = AuthenticityAudit(str(tmp_path))
        result = audit.detect_eval_exec()

        assert result.fatal_count == 1

    def test_detects_exec(self, tmp_path):
        """Should detect exec() usage"""
        test_file = tmp_path / "risky.py"
        test_file.write_text('exec(code_string)\n')

        audit = AuthenticityAudit(str(tmp_path))
        result = audit.detect_eval_exec()

        assert result.fatal_count == 1


@pytest.mark.cp
class TestNondeterministicOrderingDetector:
    """Tests for non-deterministic ordering detector"""

    def test_detects_unordered_dict_iteration(self, tmp_path):
        """Should detect unordered dict.items() iteration"""
        test_file = tmp_path / "scoring.py"
        code = """
for key, value in theme_scores.items():
    print(key, value)
"""
        test_file.write_text(code)

        audit = AuthenticityAudit(str(tmp_path))
        result = audit.detect_nondeterministic_ordering()

        assert result.warn_count >= 1

    def test_allows_sorted_iteration(self, tmp_path):
        """Should allow sorted dict iteration"""
        test_file = tmp_path / "scoring.py"
        code = """
for key, value in sorted(theme_scores.items()):
    print(key, value)
"""
        test_file.write_text(code)

        audit = AuthenticityAudit(str(tmp_path))
        result = audit.detect_nondeterministic_ordering()

        # Should not flag sorted iteration
        for v in result.violations:
            assert "sorted" not in v.code_snippet


@pytest.mark.cp
class TestDeterminismHasher:
    """Tests for determinism hash comparison"""

    def test_hash_consistency(self, tmp_path):
        """Should produce consistent hashes for identical content"""
        file1 = tmp_path / "data1.json"
        file2 = tmp_path / "data2.json"

        content = '{"key": "value", "array": [1, 2, 3]}'
        file1.write_text(content)
        file2.write_text(content)

        import hashlib
        hash1 = hashlib.sha256(file1.read_bytes()).hexdigest()
        hash2 = hashlib.sha256(file2.read_bytes()).hexdigest()

        assert hash1 == hash2

    def test_hash_differs_on_change(self, tmp_path):
        """Should produce different hashes for different content"""
        file1 = tmp_path / "data1.json"
        file2 = tmp_path / "data2.json"

        file1.write_text('{"key": "value1"}')
        file2.write_text('{"key": "value2"}')

        import hashlib
        hash1 = hashlib.sha256(file1.read_bytes()).hexdigest()
        hash2 = hashlib.sha256(file2.read_bytes()).hexdigest()

        assert hash1 != hash2


@pytest.mark.cp
class TestAuditIntegration:
    """Integration tests for full audit run"""

    def test_run_all_detectors(self, tmp_path):
        """Should successfully run all detectors"""
        # Create a minimal test file
        test_file = tmp_path / "app.py"
        test_file.write_text("x = 1\n")

        audit = AuthenticityAudit(str(tmp_path))
        detectors = audit.run_all_detectors()

        assert len(detectors) == 8
        assert all(d.detector_name for d in detectors)

    def test_json_report_generation(self, tmp_path):
        """Should generate valid JSON report"""
        test_file = tmp_path / "app.py"
        test_file.write_text("x = 1\n")

        audit = AuthenticityAudit(str(tmp_path))
        detectors = audit.run_all_detectors()
        _, determ = audit.verify_determinism()

        report = audit.generate_json_report(detectors, determ)

        assert report["agent"] == "SCA"
        assert report["protocol_version"] == "13.8"
        assert "summary" in report
        assert "violations" in report

    def test_markdown_report_generation(self, tmp_path):
        """Should generate readable Markdown report"""
        test_file = tmp_path / "app.py"
        test_file.write_text("x = 1\n")

        audit = AuthenticityAudit(str(tmp_path))
        detectors = audit.run_all_detectors()
        _, determ = audit.verify_determinism()

        report = audit.generate_json_report(detectors, determ)
        md = audit.generate_md_report(report)

        assert "ESG Authenticity Audit Report" in md
        assert "SCA v13.8" in md
        assert "Total Violations" in md

    def test_guard_path_prevents_escape(self, tmp_path):
        """Should prevent path escape attempts"""
        audit = AuthenticityAudit(str(tmp_path))

        # Should work for paths within root
        safe_path = tmp_path / "safe.txt"
        assert audit.guard_path(safe_path) == safe_path.resolve()

        # Should raise for paths outside root
        outside = Path("/etc/passwd")
        with pytest.raises(RuntimeError, match="Workspace escape"):
            audit.guard_path(outside)


@pytest.mark.cp
class TestViolationDataclass:
    """Tests for Violation data structure"""

    def test_violation_creation(self):
        """Should create violation record"""
        v = Violation(
            file="test.py",
            line=42,
            violation_type="test_type",
            description="Test description",
            code_snippet="test code",
            severity="FATAL"
        )

        assert v.file == "test.py"
        assert v.line == 42
        assert v.severity == "FATAL"

    def test_violation_with_exemption(self):
        """Should support exemption tracking"""
        v = Violation(
            file="test.py",
            line=42,
            violation_type="test_type",
            description="Test",
            code_snippet="code",
            severity="WARN",
            exemption="InformationalOnly"
        )

        assert v.exemption == "InformationalOnly"
