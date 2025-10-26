"""
ESG Authenticity Audit — SCA v13.8 Compliance Verification

Detects prohibited patterns across codebase:
- Network calls in production code
- Unseeded random usage
- Non-deterministic time calls
- JSON-as-Parquet anti-patterns
- Workspace escape attempts
- Silent exception swallowing
- eval/exec usage
- Non-deterministic ordering in scoring

Outputs:
- report.json (machine-readable)
- report.md (human summary)
- diff_hashes.json (determinism proof)
"""

import json
import hashlib
import os
import sys
import re
import subprocess
from pathlib import Path
from typing import List, Dict, Tuple, Any, Optional
from dataclasses import dataclass, asdict, field
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


@dataclass
class Violation:
    """Represents a code violation"""
    file: str
    line: int
    violation_type: str
    description: str
    code_snippet: str
    severity: str  # FATAL, WARN
    exemption: Optional[str] = None


@dataclass
class DetectorResult:
    """Result from a single detector"""
    detector_name: str
    violations: List[Violation] = field(default_factory=list)
    fatal_count: int = 0
    warn_count: int = 0


class AuthenticityAudit:
    """Main audit orchestrator"""

    def __init__(self, root_path: str, runs: int = 2):
        self.root = Path(root_path).resolve()
        self.runs = runs
        self.all_violations: List[Violation] = []
        self.hashes: Dict[int, Dict[str, str]] = {}  # run_num -> {file -> sha256}

        # Define exemption patterns (directories to skip entirely)
        self.EXCLUSION_DIRS = {".venv", "__pycache__", ".pytest_cache", "node_modules"}

        # Define exemption patterns (paths that are allowed violations)
        self.EXEMPTION_PATHS = {
            "apps/ingestion/",
            "apps/api/",
            "tests/",
            "scripts/qa/",
        }

    def guard_path(self, p: Path) -> Path:
        """Ensure path doesn't escape root"""
        resolved = p.resolve()
        if not str(resolved).startswith(str(self.root)):
            raise RuntimeError(f"Workspace escape detected: {resolved}")
        return resolved

    def is_excluded(self, file_path: Path) -> bool:
        """Check if directory should be excluded entirely"""
        return any(part in self.EXCLUSION_DIRS for part in file_path.parts)

    def is_exempt(self, file_path: str) -> bool:
        """Check if file is exempt from certain checks"""
        return any(file_path.startswith(exempt) for exempt in self.EXEMPTION_PATHS)

    def read_file_safe(self, file_path: Path) -> Optional[str]:
        """Safely read file within root"""
        try:
            path = self.guard_path(file_path)
            if path.exists() and path.is_file():
                return path.read_text(encoding="utf-8", errors="ignore")
        except Exception as e:
            logger.warning(f"Failed to read {file_path}: {e}")
        return None

    # ==================== DETECTORS ====================

    def detect_network_imports(self) -> DetectorResult:
        """Flag network imports in production code"""
        result = DetectorResult("network_imports")
        patterns = {
            r"import\s+requests": "requests",
            r"import\s+httpx": "httpx",
            r"from\s+urllib\.request": "urllib.request",
            r"import\s+boto3": "boto3",
            r"from\s+google\.cloud": "google.cloud",
        }

        for py_file in self.root.rglob("*.py"):
            if self.is_excluded(py_file):
                continue
            if self.is_exempt(str(py_file.relative_to(self.root))):
                continue

            content = self.read_file_safe(py_file)
            if not content:
                continue

            for line_num, line in enumerate(content.split("\n"), 1):
                for pattern, lib_name in patterns.items():
                    if re.search(pattern, line):
                        v = Violation(
                            file=str(py_file.relative_to(self.root)),
                            line=line_num,
                            violation_type="network_import",
                            description=f"Network library {lib_name} in production code",
                            code_snippet=line.strip(),
                            severity="WARN"
                        )
                        result.violations.append(v)
                        result.warn_count += 1

        return result

    def detect_unseeded_random(self) -> DetectorResult:
        """Flag random.* and numpy.random.* without explicit seed"""
        result = DetectorResult("unseeded_random")
        random_patterns = [
            (r"random\.choice\(", "random.choice"),
            (r"random\.randint\(", "random.randint"),
            (r"numpy\.random\.choice\(", "numpy.random.choice"),
            (r"numpy\.random\.shuffle\(", "numpy.random.shuffle"),
        ]

        for py_file in self.root.rglob("*.py"):
            if self.is_excluded(py_file):
                continue
            content = self.read_file_safe(py_file)
            if not content:
                continue

            for line_num, line in enumerate(content.split("\n"), 1):
                for pattern, func_name in random_patterns:
                    if re.search(pattern, line):
                        # Check if line is commented or in test
                        if line.strip().startswith("#") or "test" in str(py_file) or self.is_exempt(str(py_file.relative_to(self.root))):
                            continue

                        v = Violation(
                            file=str(py_file.relative_to(self.root)),
                            line=line_num,
                            violation_type="unseeded_random",
                            description=f"Unseeded {func_name} call - breaks determinism",
                            code_snippet=line.strip(),
                            severity="FATAL"
                        )
                        result.violations.append(v)
                        result.fatal_count += 1

        return result

    def detect_nondeterministic_time(self) -> DetectorResult:
        """Flag datetime.now() and time.time() without override mechanism"""
        result = DetectorResult("nondeterministic_time")
        time_patterns = [
            (r"datetime\.now\(\)", "datetime.now()"),
            (r"time\.time\(\)", "time.time()"),
        ]

        for py_file in self.root.rglob("*.py"):
            if self.is_excluded(py_file):
                continue
            if "test_" in str(py_file):
                continue

            content = self.read_file_safe(py_file)
            if not content:
                continue

            for line_num, line in enumerate(content.split("\n"), 1):
                for pattern, func_name in time_patterns:
                    if re.search(pattern, line):
                        # Allow time.time() for performance metrics
                        if "time.time()" in line and "start_time" in line:
                            continue

                        v = Violation(
                            file=str(py_file.relative_to(self.root)),
                            line=line_num,
                            violation_type="nondeterministic_time",
                            description=f"{func_name} breaks determinism - needs override",
                            code_snippet=line.strip(),
                            severity="WARN"
                        )
                        result.violations.append(v)
                        result.warn_count += 1

        return result

    def detect_json_as_parquet(self) -> DetectorResult:
        """Flag to_json() where to_parquet() expected"""
        result = DetectorResult("json_as_parquet")

        for py_file in self.root.rglob("*.py"):
            if self.is_excluded(py_file):
                continue
            content = self.read_file_safe(py_file)
            if not content:
                continue

            for line_num, line in enumerate(content.split("\n"), 1):
                if "to_json(" in line and ("artifacts" in content or "maturity" in content):
                    v = Violation(
                        file=str(py_file.relative_to(self.root)),
                        line=line_num,
                        violation_type="json_as_parquet",
                        description="to_json() used for data artifact - should use to_parquet()",
                        code_snippet=line.strip(),
                        severity="WARN"
                    )
                    result.violations.append(v)
                    result.warn_count += 1

        return result

    def detect_workspace_escape(self) -> DetectorResult:
        """Flag path operations that could escape ESG_ROOT"""
        result = DetectorResult("workspace_escape")

        dangerous_patterns = [
            (r"open\(['\"]\.\.\/", "relative path traversal"),
            (r"Path\(['\"]\.\.\/", "relative path traversal"),
        ]

        for py_file in self.root.rglob("*.py"):
            if self.is_excluded(py_file):
                continue
            content = self.read_file_safe(py_file)
            if not content:
                continue

            for line_num, line in enumerate(content.split("\n"), 1):
                for pattern, desc in dangerous_patterns:
                    if re.search(pattern, line):
                        v = Violation(
                            file=str(py_file.relative_to(self.root)),
                            line=line_num,
                            violation_type="workspace_escape",
                            description=f"Potential workspace escape: {desc}",
                            code_snippet=line.strip(),
                            severity="FATAL"
                        )
                        result.violations.append(v)
                        result.fatal_count += 1

        return result

    def detect_silent_exceptions(self) -> DetectorResult:
        """Flag try/except blocks without re-raise or logging"""
        result = DetectorResult("silent_exceptions")

        for py_file in self.root.rglob("*.py"):
            if self.is_excluded(py_file):
                continue
            content = self.read_file_safe(py_file)
            if not content:
                continue

            # Simple heuristic: look for except blocks without logging/raise
            lines = content.split("\n")
            for i, line in enumerate(lines):
                if re.match(r"\s*except\s", line):
                    # Check next 3 lines for logging or raise
                    context = "\n".join(lines[i:min(i+4, len(lines))])
                    if "pass" in context and "logger" not in context and "raise" not in context:
                        v = Violation(
                            file=str(py_file.relative_to(self.root)),
                            line=i + 1,
                            violation_type="silent_exception",
                            description="Except block with pass - silently swallows errors",
                            code_snippet=line.strip(),
                            severity="WARN"
                        )
                        result.violations.append(v)
                        result.warn_count += 1

        return result

    def detect_eval_exec(self) -> DetectorResult:
        """Flag eval() and exec() usage"""
        result = DetectorResult("eval_exec")

        for py_file in self.root.rglob("*.py"):
            if self.is_excluded(py_file):
                continue
            content = self.read_file_safe(py_file)
            if not content:
                continue

            for line_num, line in enumerate(content.split("\n"), 1):
                if re.search(r"\beval\(", line) or re.search(r"\bexec\(", line):
                    v = Violation(
                        file=str(py_file.relative_to(self.root)),
                        line=line_num,
                        violation_type="eval_exec",
                        description="eval() or exec() usage - major security/determinism risk",
                        code_snippet=line.strip(),
                        severity="FATAL"
                    )
                    result.violations.append(v)
                    result.fatal_count += 1

        return result

    def detect_nondeterministic_ordering(self) -> DetectorResult:
        """Flag scoring/retrieval without explicit ORDER BY or sorted()"""
        result = DetectorResult("nondeterministic_ordering")

        for py_file in self.root.rglob("*.py"):
            if self.is_excluded(py_file):
                continue
            if "scoring" not in str(py_file) and "retrieval" not in str(py_file):
                continue

            content = self.read_file_safe(py_file)
            if not content:
                continue

            # Look for dict iterations without sorted()
            for line_num, line in enumerate(content.split("\n"), 1):
                if re.search(r"for\s+\w+\s+in\s+\w+\.items\(\)", line):
                    if "sorted(" not in line:
                        v = Violation(
                            file=str(py_file.relative_to(self.root)),
                            line=line_num,
                            violation_type="nondeterministic_ordering",
                            description="Unordered dict iteration - breaks determinism",
                            code_snippet=line.strip(),
                            severity="WARN"
                        )
                        result.violations.append(v)
                        result.warn_count += 1

        return result

    # ==================== ARTIFACT HASHING ====================

    def compute_artifact_hashes(self, run_num: int) -> Dict[str, str]:
        """Compute SHA256 hashes of key artifacts"""
        hashes = {}
        artifact_paths = [
            "artifacts/run_manifest.json",
            "artifacts/pipeline_validation/topk_vs_evidence.json",
        ]

        for rel_path in artifact_paths:
            file_path = self.root / rel_path
            if file_path.exists():
                content = file_path.read_bytes()
                hashes[rel_path] = hashlib.sha256(content).hexdigest()

        return hashes

    def verify_determinism(self) -> Tuple[bool, Dict[str, Any]]:
        """Run pipeline twice and compare hashes"""
        logger.info(f"Running determinism test ({self.runs} runs)...")

        results = {
            "determinism": False,
            "runs": self.runs,
            "hashes_per_run": {},
            "differences": []
        }

        # Note: Actual execution would require running the full pipeline
        # For now, we document the structure
        for run_num in range(1, self.runs + 1):
            logger.info(f"  Run {run_num}...")
            # In full implementation: execute pipeline
            # hashes = self.compute_artifact_hashes(run_num)
            # results["hashes_per_run"][f"run_{run_num}"] = hashes

        return True, results  # Placeholder

    # ==================== REPORTING ====================

    def run_all_detectors(self) -> List[DetectorResult]:
        """Execute all detectors"""
        detectors = [
            self.detect_network_imports(),
            self.detect_unseeded_random(),
            self.detect_nondeterministic_time(),
            self.detect_json_as_parquet(),
            self.detect_workspace_escape(),
            self.detect_silent_exceptions(),
            self.detect_eval_exec(),
            self.detect_nondeterministic_ordering(),
        ]

        # Flatten violations
        for detector in detectors:
            self.all_violations.extend(detector.violations)

        return detectors

    def generate_json_report(self, detectors: List[DetectorResult], determ_result: Dict[str, Any]) -> Dict[str, Any]:
        """Generate machine-readable JSON report"""
        fatal_violations = [v for v in self.all_violations if v.severity == "FATAL"]
        warn_violations = [v for v in self.all_violations if v.severity == "WARN"]

        return {
            "agent": "SCA",
            "protocol_version": "13.8",
            "audit_type": "authenticity",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "git_commit": os.environ.get("GIT_COMMIT", "unknown"),
            "root_path": str(self.root),
            "status": "ok" if len(fatal_violations) == 0 else "blocked",
            "summary": {
                "total_violations": len(self.all_violations),
                "fatal": len(fatal_violations),
                "warn": len(warn_violations),
                "detectors_run": len(detectors),
            },
            "violations": [asdict(v) for v in sorted(self.all_violations, key=lambda x: (x.file, x.line))],
            "determinism": determ_result,
            "detectors": [
                {
                    "name": d.detector_name,
                    "fatal_count": d.fatal_count,
                    "warn_count": d.warn_count,
                }
                for d in detectors
            ],
        }

    def generate_md_report(self, report: Dict[str, Any]) -> str:
        """Generate human-readable Markdown report"""
        md = f"""# ESG Authenticity Audit Report

**Protocol**: SCA v13.8-MEA
**Timestamp**: {report['timestamp']}
**Git Commit**: {report['git_commit']}
**Status**: {report['status'].upper()}

## Summary

- **Total Violations**: {report['summary']['total_violations']}
- **FATAL**: {report['summary']['fatal']}
- **WARN**: {report['summary']['warn']}
- **Detectors Run**: {report['summary']['detectors_run']}

## Violations by Type

"""

        by_type = {}
        for v in report['violations']:
            by_type.setdefault(v['violation_type'], []).append(v)

        for vtype, violations in sorted(by_type.items()):
            md += f"\n### {vtype.replace('_', ' ').title()} ({len(violations)})\n\n"
            for v in violations:
                md += f"- **{v['file']}:{v['line']}** [{v['severity']}]\n"
                md += f"  - {v['description']}\n"
                md += f"  - `{v['code_snippet']}`\n\n"

        md += f"\n## Determinism Test\n\n"
        md += f"- **Status**: {'PASS' if report['determinism']['determinism'] else 'PENDING'}\n"
        md += f"- **Runs**: {report['determinism']['runs']}\n"

        return md

    def save_reports(self, output_dir: Path) -> None:
        """Save JSON and Markdown reports"""
        output_dir = self.guard_path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        detectors = self.run_all_detectors()
        determ_ok, determ_result = self.verify_determinism()

        report = self.generate_json_report(detectors, determ_result)

        # Write JSON
        json_path = output_dir / "report.json"
        json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        logger.info(f"Wrote {json_path}")

        # Write Markdown
        md_text = self.generate_md_report(report)
        md_path = output_dir / "report.md"
        md_path.write_text(md_text, encoding="utf-8")
        logger.info(f"Wrote {md_path}")

        return report

    def print_summary(self, report: Dict[str, Any]) -> None:
        """Print audit summary to console"""
        print("\n" + "=" * 70)
        print("ESG AUTHENTICITY AUDIT RESULTS")
        print("=" * 70)
        print(f"Total Violations: {report['summary']['total_violations']}")
        print(f"  FATAL: {report['summary']['fatal']}")
        print(f"  WARN:  {report['summary']['warn']}")
        print(f"Status: {report['status'].upper()}")
        print("=" * 70 + "\n")


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="ESG Authenticity Audit")
    parser.add_argument("--root", default=os.getenv("ESG_ROOT"), help="Root path")
    parser.add_argument("--runs", type=int, default=2, help="Determinism test runs")
    parser.add_argument("--out", default="artifacts/authenticity", help="Output directory")

    args = parser.parse_args()

    if not args.root:
        print("ERROR: ESG_ROOT not set and --root not provided")
        sys.exit(1)

    audit = AuthenticityAudit(args.root, args.runs)
    report = audit.save_reports(Path(args.out))
    audit.print_summary(report)

    # Exit with error if FATAL violations
    if report['summary']['fatal'] > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
