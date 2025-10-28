#!/usr/bin/env python3
"""Cross-platform live preflight gate for Docker + WSL readiness."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Iterable, Tuple


REPO_ROOT = Path(__file__).resolve().parent.parent
WSL_DOCTOR = REPO_ROOT / "scripts" / "wsl_docker_doctor.sh"
WIN_DOCTOR = REPO_ROOT / "scripts" / "wsl_docker_doctor.ps1"


class DoctorExecutionError(RuntimeError):
    """Raised when a doctor command fails to emit a JSON payload."""


def _find_powershell() -> Tuple[str, ...]:
    """Return a tuple representing the PowerShell command."""
    for candidate in ("pwsh", "powershell", "powershell.exe"):
        exe = shutil.which(candidate)
        if exe:
            return (
                exe,
                "-NoLogo",
                "-NoProfile",
                "-File",
                str(WIN_DOCTOR),
            )
    raise DoctorExecutionError("Unable to locate PowerShell binary (pwsh/powershell).")


def _run_and_parse(command: Iterable[str]) -> tuple[dict[str, Any], subprocess.CompletedProcess[str]]:
    """Run a command, return parsed JSON payload and the completed process."""
    env = os.environ.copy()
    env.setdefault("PYTHONUNBUFFERED", "1")

    result = subprocess.run(
        list(command),
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        env=env,
    )

    stdout = result.stdout.strip()
    json_line = ""
    for line in reversed(stdout.splitlines()):
        candidate = line.strip()
        if candidate.startswith("{") and candidate.endswith("}"):
            json_line = candidate
            break

    if not json_line:
        raise DoctorExecutionError(
            f"Expected JSON output from command {' '.join(command)}, but none was found.\n"
            f"Stdout:\n{result.stdout}\nStderr:\n{result.stderr}"
        )

    try:
        payload = json.loads(json_line)
    except json.JSONDecodeError as exc:
        raise DoctorExecutionError(
            f"Invalid JSON payload from {' '.join(command)}: {exc}\nPayload:\n{json_line}"
        ) from exc

    return payload, result


def _merge_actionables(wsl: dict[str, Any], win: dict[str, Any]) -> list[str]:
    """Build actionable guidance based on doctor payloads."""
    actions: list[str] = []

    def add(message: str, condition: bool) -> None:
        if condition and message not in actions:
            actions.append(message)

    add(
        "sudo groupadd docker || true && sudo usermod -aG docker $USER ; restart WSL session",
        bool(wsl.get("needs_group_fix")),
    )
    add(
        "Start Docker Desktop, then rerun: make doctor",
        not bool(win.get("docker_desktop_running", True)),
    )
    add(
        "Enable distro in Docker Desktop → Settings → Resources → WSL Integration",
        wsl.get("wsl_integration") == "likely_disabled",
    )
    add(
        "Move repo under a path without spaces or quote volume mounts",
        bool(wsl.get("path_has_spaces")),
    )
    add(
        "Install Compose v2 / enable Compose integration",
        not bool(wsl.get("compose_ok", True)),
    )
    return actions


def build_report(
    wsl_payload: dict[str, Any],
    wsl_return_code: int,
    win_payload: dict[str, Any],
    win_return_code: int,
) -> tuple[dict[str, Any], int]:
    """Merge doctor payloads into a single report and determine exit code."""
    merged: dict[str, Any] = {
        "status": "ok",
        "wsl_doctor": wsl_payload,
        "win_doctor": win_payload,
        "actionables": [],
    }

    doctor_errors = [
        wsl_payload.get("status") not in {"ok", "OK"},
        win_payload.get("status") not in {"ok", "OK"},
        wsl_return_code != 0,
        win_return_code != 0,
        not bool(wsl_payload.get("socket_perm_ok", True)),
        not bool(win_payload.get("docker_desktop_running", True)),
        bool(wsl_payload.get("needs_group_fix")),
    ]

    if any(doctor_errors):
        merged["status"] = "error"

    merged["actionables"] = _merge_actionables(wsl_payload, win_payload)

    exit_code = 0 if merged["status"] == "ok" else 1
    return merged, exit_code


def main() -> int:
    """Entry point."""
    wsl_payload, wsl_result = _run_and_parse(("bash", str(WSL_DOCTOR)))
    win_cmd = _find_powershell()
    win_payload, win_result = _run_and_parse(win_cmd)

    merged, exit_code = build_report(
        wsl_payload,
        wsl_result.returncode,
        win_payload,
        win_result.returncode,
    )
    print(json.dumps(merged))
    return exit_code


if __name__ == "__main__":
    try:
        sys.exit(main())
    except DoctorExecutionError as exc:
        payload = {"status": "error", "wsl_doctor": {}, "win_doctor": {}, "actionables": [str(exc)]}
        print(json.dumps(payload))
        sys.exit(1)
