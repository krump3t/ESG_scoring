#!/usr/bin/env python3
import json
import pathlib
import fnmatch
from typing import List

def _match_globs(repo_root: pathlib.Path, patterns: List[str]) -> List[pathlib.Path]:
    files: List[pathlib.Path] = []
    norm_patterns = [g.replace("\\", "/") for g in patterns]
    print(f"[DEBUG] Normalized patterns: {norm_patterns}")
    print(f"[DEBUG] repo_root: {repo_root}")
    print(f"[DEBUG] repo_root exists: {repo_root.exists()}")

    py_files = list(repo_root.rglob("*.py"))
    print(f"[DEBUG] Total .py files found: {len(py_files)}")

    for p in py_files:
        up = str(p).replace("\\", "/")
        for patt in norm_patterns:
            if fnmatch.fnmatch(up, patt):
                files.append(p)
                if len(files) <= 5:
                    print(f"[DEBUG] Match: {up}")
                break

    return files

# Simulate validator behavior
task_dir = pathlib.Path(".")
base = task_dir
ctx = base / "context"
cfg = ctx / "cp_paths.json"

print(f"[DEBUG] task_dir: {task_dir.resolve()}")
print(f"[DEBUG] cfg: {cfg.resolve()}")
print(f"[DEBUG] cfg.exists(): {cfg.exists()}")

# Compute repo_root same way as validator
# repo_root = base.parent.parent (two levels up from task_dir)
repo_root_computed = base.parent.parent
print(f"[DEBUG] Computed repo_root: {repo_root_computed.resolve()}")

if cfg.exists():
    raw = json.loads(cfg.read_text(encoding="utf-8"))
    print(f"[DEBUG] Raw config: {raw}")
    print(f"[DEBUG] Config type: {type(raw)}")

    files = []

    # Case 1: simple list
    if isinstance(raw, list):
        print(f"[DEBUG] Config is list with {len(raw)} items")
        patterns = [str(x) for x in raw if isinstance(x, str)]
        print(f"[DEBUG] Extracted patterns: {patterns}")
        if patterns:
            files.extend(_match_globs(repo_root_computed, patterns))

    # Case 2: dict with "paths"
    elif isinstance(raw, dict):
        print(f"[DEBUG] Config is dict")
        paths = raw.get("paths", [])
        print(f"[DEBUG] paths list: {paths}")
        for item in paths:
            if isinstance(item, str):
                print(f"[DEBUG] Processing string pattern: {item}")
                files.extend(_match_globs(repo_root_computed, [item]))

    print(f"\n[RESULT] Total files found: {len(files)}")
    if files:
        for f in files[:5]:
            print(f"  {f.relative_to(repo_root_computed)}")
