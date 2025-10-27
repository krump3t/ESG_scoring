"""
SCA Infrastructure Runner
Minimal runner for task execution and validation gates per SCA Protocol v13.8
"""
import sys
import json
import argparse
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime


class SCARunner:
    """SCA Protocol v13.8 compliant task runner"""

    def __init__(self, task_dir: Path):
        self.task_dir = task_dir
        self.context_dir = task_dir / "context"
        self.artifacts_dir = task_dir / "artifacts"
        self.qa_dir = task_dir / "qa"
        self.reports_dir = task_dir / "reports"

    def run_phase(self, phase: str) -> Dict[str, Any]:
        """Execute a single phase with gate validation"""
        print(f"\n=== SCA Runner: Phase {phase} ===")

        if phase == "context":
            return self._run_context_gate()
        elif phase == "validation":
            return self._run_validation_phase()
        else:
            return {"status": "blocked", "reason": f"Unknown phase: {phase}"}

    def _run_context_gate(self) -> Dict[str, Any]:
        """Validate context gate requirements"""
        required_files = [
            "hypothesis.md",
            "design.md",
            "evidence.json",
            "data_sources.json",
            "adr.md",
            "assumptions.md",
            "cp_paths.json"
        ]

        missing_files = []
        for filename in required_files:
            filepath = self.context_dir / filename
            if not filepath.exists():
                missing_files.append(filename)

        if missing_files:
            return {
                "status": "blocked",
                "gate": "context",
                "reason": f"Missing context files: {', '.join(missing_files)}"
            }

        return {
            "status": "pass",
            "gate": "context",
            "files_validated": required_files
        }

    def _run_validation_phase(self) -> Dict[str, Any]:
        """Run validation phase checks"""
        results = {
            "phase": "validation",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "gates": {}
        }

        # Check context gate
        context_result = self._run_context_gate()
        results["gates"]["context"] = context_result["status"]

        # Check for state.json and memory_sync.json
        state_file = self.artifacts_dir / "state.json"
        memory_sync_file = self.artifacts_dir / "memory_sync.json"

        if not state_file.exists():
            results["gates"]["traceability"] = "fail"
            results["status"] = "blocked"
            results["reason"] = "Missing artifacts/state.json"
            return results

        if not memory_sync_file.exists():
            results["gates"]["traceability"] = "fail"
            results["status"] = "blocked"
            results["reason"] = "Missing artifacts/memory_sync.json"
            return results

        results["gates"]["traceability"] = "pass"
        results["status"] = "pass"

        return results

    def load_state(self) -> Dict[str, Any]:
        """Load current task state from state.json"""
        state_file = self.artifacts_dir / "state.json"
        if not state_file.exists():
            return {}

        with open(state_file, 'r') as f:
            return json.load(f)

    def save_state(self, state: Dict[str, Any]) -> None:
        """Save task state to state.json"""
        state_file = self.artifacts_dir / "state.json"
        state["last_updated"] = datetime.utcnow().isoformat() + "Z"

        with open(state_file, 'w') as f:
            json.dump(state, f, indent=2)


def discover_task_dir(base_path: Path) -> Path:
    """Discover current task directory (newest in tasks/)"""
    tasks_dir = base_path / "tasks"
    if not tasks_dir.exists():
        raise FileNotFoundError("No tasks/ directory found")

    task_dirs = [d for d in tasks_dir.iterdir() if d.is_dir()]
    if not task_dirs:
        raise FileNotFoundError("No task directories found in tasks/")

    task_dirs.sort(reverse=True)
    return task_dirs[0]


def main():
    """Main entry point for SCA runner"""
    parser = argparse.ArgumentParser(description="SCA Protocol v13.8 Runner")
    parser.add_argument("--phase", choices=["context", "validation"],
                       default="validation", help="Phase to execute")
    parser.add_argument("--task-dir", type=Path, help="Task directory")

    args = parser.parse_args()

    if args.task_dir:
        task_dir = args.task_dir
    else:
        base_path = Path(__file__).parent.parent
        task_dir = discover_task_dir(base_path)

    print(f"Task Directory: {task_dir}")

    runner = SCARunner(task_dir)
    result = runner.run_phase(args.phase)

    print("\n=== Phase Result ===")
    print(json.dumps(result, indent=2))

    sys.exit(0 if result.get("status") == "pass" else 1)


if __name__ == "__main__":
    main()
