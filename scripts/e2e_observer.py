"""
E2E Execution Observer & Checkpoint Manager
SCA v13.8-MEA | Observability Infrastructure

Tracks execution progress, logs checkpoints, and generates observability artifacts.
"""
from __future__ import annotations
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


class E2EObserver:
    """Observer for E2E execution with checkpoint tracking and logging."""

    def __init__(self, workspace_dir: str):
        """Initialize observer with workspace directory."""
        self.workspace = Path(workspace_dir)
        self.logs_dir = self.workspace / "logs"
        self.checkpoints_file = self.workspace / "checkpoints.json"
        self.master_log_file = self.workspace / "master_execution.log"

        # Ensure directories exist
        self.logs_dir.mkdir(parents=True, exist_ok=True)

        # Initialize checkpoint tracking
        self.checkpoints: List[Dict[str, Any]] = []
        self.start_time = time.time()

        # Write initial master log header
        self._log_master(f"{'='*70}")
        self._log_master(f"E2E COLD START EXECUTION - SCA v13.8-MEA")
        self._log_master(f"Workspace: {self.workspace}")
        self._log_master(f"Start Time: {self._timestamp()}")
        self._log_master(f"{'='*70}\n")

    def _timestamp(self) -> str:
        """Get ISO timestamp."""
        return datetime.now(timezone.utc).isoformat()

    def _log_master(self, message: str) -> None:
        """Append message to master log."""
        with open(self.master_log_file, "a", encoding="utf-8") as f:
            f.write(f"{message}\n")

    def checkpoint(
        self,
        phase: int,
        name: str,
        status: str,
        duration: float,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Record a checkpoint.

        Args:
            phase: Phase number (1-10)
            name: Checkpoint name
            status: "pass", "fail", or "skip"
            duration: Duration in seconds
            details: Optional additional details
        """
        checkpoint_data = {
            "phase": phase,
            "name": name,
            "status": status,
            "timestamp": self._timestamp(),
            "duration_sec": round(duration, 2),
            "details": details or {},
        }

        self.checkpoints.append(checkpoint_data)

        # Write to checkpoints file
        self.checkpoints_file.write_text(
            json.dumps(
                {
                    "execution_id": self.workspace.name,
                    "start_time": self._timestamp(),
                    "checkpoints": self.checkpoints,
                },
                indent=2,
            ),
            encoding="utf-8",
        )

        # Log to master
        status_symbol = "✓" if status == "pass" else ("✗" if status == "fail" else "⊘")
        self._log_master(
            f"[CHECKPOINT {phase}] {status_symbol} {name} "
            f"({duration:.1f}s) - {status.upper()}"
        )
        if details:
            self._log_master(f"  Details: {json.dumps(details, indent=2)}")

    def phase_log(self, phase: int, name: str) -> Path:
        """Get log file path for a phase."""
        log_name = name.lower().replace(" ", "_").replace("/", "_")
        return self.logs_dir / f"phase{phase}_{log_name}.log"

    def log_phase_start(self, phase: int, name: str) -> None:
        """Log phase start."""
        self._log_master(f"\n{'='*70}")
        self._log_master(f"PHASE {phase}: {name}")
        self._log_master(f"{'='*70}")

    def log_phase_end(self, phase: int, name: str, status: str) -> None:
        """Log phase end."""
        self._log_master(f"Phase {phase} ({name}): {status.upper()}")
        self._log_master(f"{'='*70}\n")

    def summary(self) -> Dict[str, Any]:
        """Generate execution summary."""
        total_duration = time.time() - self.start_time
        passed = sum(1 for cp in self.checkpoints if cp["status"] == "pass")
        failed = sum(1 for cp in self.checkpoints if cp["status"] == "fail")
        skipped = sum(1 for cp in self.checkpoints if cp["status"] == "skip")

        return {
            "execution_id": self.workspace.name,
            "total_duration_sec": round(total_duration, 2),
            "checkpoints_total": len(self.checkpoints),
            "checkpoints_passed": passed,
            "checkpoints_failed": failed,
            "checkpoints_skipped": skipped,
            "overall_status": "PASS" if failed == 0 else "FAIL",
            "checkpoints": self.checkpoints,
        }

    def write_summary(self) -> None:
        """Write execution summary to file."""
        summary = self.summary()
        summary_file = self.workspace / "execution_summary.json"
        summary_file.write_text(json.dumps(summary, indent=2), encoding="utf-8")

        # Log to master
        self._log_master(f"\n{'='*70}")
        self._log_master(f"EXECUTION SUMMARY")
        self._log_master(f"{'='*70}")
        self._log_master(f"Status: {summary['overall_status']}")
        self._log_master(f"Duration: {summary['total_duration_sec']:.1f}s")
        self._log_master(f"Checkpoints: {summary['checkpoints_passed']} passed, "
                        f"{summary['checkpoints_failed']} failed, "
                        f"{summary['checkpoints_skipped']} skipped")
        self._log_master(f"{'='*70}\n")


def get_observer() -> E2EObserver:
    """Get observer instance for current execution."""
    workspace_file = Path("artifacts/e2e_run_timestamp.txt")
    if not workspace_file.exists():
        raise FileNotFoundError("No active E2E execution workspace found")

    timestamp = workspace_file.read_text().strip()
    workspace_dir = f"artifacts/e2e_run_{timestamp}"
    return E2EObserver(workspace_dir)


if __name__ == "__main__":
    # CLI usage
    import argparse

    ap = argparse.ArgumentParser(description="E2E Observer CLI")
    ap.add_argument("--checkpoint", type=int, help="Phase number")
    ap.add_argument("--name", help="Checkpoint name")
    ap.add_argument("--status", choices=["pass", "fail", "skip"], help="Status")
    ap.add_argument("--duration", type=float, default=0.0, help="Duration in seconds")
    ap.add_argument("--summary", action="store_true", help="Print summary")

    args = ap.parse_args()

    observer = get_observer()

    if args.summary:
        print(json.dumps(observer.summary(), indent=2))
    elif args.checkpoint and args.name and args.status:
        observer.checkpoint(args.checkpoint, args.name, args.status, args.duration)
        print(f"Checkpoint {args.checkpoint} recorded: {args.status}")
    else:
        print("Usage: python e2e_observer.py --checkpoint N --name NAME --status STATUS")
        sys.exit(1)
