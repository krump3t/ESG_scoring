#!/usr/bin/env python3
"""
Deterministic E2E ESG Scoring Orchestration.

Runs the prospecting-engine pipeline with configurable parameters and validates
reproducibility across multiple runs. Generates comprehensive output-contract JSON
with scoring results, evidence, and parity validation.

Usage:
    python scripts/orchestrate.py \\
        --company "Apple Inc" \\
        --year 2024 \\
        --query "climate strategy and GHG targets" \\
        [--runs 3] \\
        [--output artifacts/orchestrator/baseline] \\
        [--topk 5] \\
        [--alpha 0.6] \\
        [--semantic 0]

Output:
    artifacts/orchestrator/baseline/
    ├── run_1/
    │   ├── output.json           # Pipeline metadata
    │   ├── hash.txt              # SHA256 of output
    │   └── scoring_response.json # ESG scores + evidence
    ├── run_2/
    ├── run_3/
    └── determinism_report.json

Environment:
    SEED=42 (fixed, no randomness)
    PYTHONHASHSEED=0 (disable hash randomization)
    PROVIDER=local (offline fixtures, default)
    TOPK=5 (retrieval parameter)
    ALPHA=0.6 (fusion parameter for hybrid retrieval)
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Add repository root to sys.path for module imports
SCRIPT_DIR = Path(__file__).parent
REPO_ROOT = SCRIPT_DIR.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# Set deterministic seeds before imports
os.environ["PYTHONHASHSEED"] = "0"
os.environ["SEED"] = "42"


def setup_environment() -> None:
    """Set all required environment variables for deterministic execution."""
    os.environ.setdefault("LIVE_EMBEDDINGS", "false")
    os.environ.setdefault("ALLOW_NETWORK", "false")
    os.environ.setdefault("PROVIDER", "local")
    os.environ.setdefault("TOPK", "5")
    os.environ.setdefault("ALPHA", "0.6")
    os.environ["PYTHONHASHSEED"] = "0"  # Ensure it's set
    os.environ["SEED"] = "42"  # Ensure it's set


def run_pipeline(
    company: str,
    year: int,
    query: str,
    run_num: int,
    output_dir: Path,
    topk: int = 5,
    alpha: float = 0.6,
    semantic: bool = False,
) -> dict[str, Any]:
    """
    Execute one pipeline run with ESG scoring.

    Args:
        company: Company name for query
        year: Year for scoring
        query: Search query for evidence retrieval
        run_num: Run number (1, 2, or 3)
        output_dir: Output directory for this run
        topk: Top-K retrieval parameter
        alpha: Alpha parameter for retrieval fusion (not currently used)
        semantic: Enable semantic search (requires LIVE_EMBEDDINGS)

    Returns:
        Dict with keys: status, run_num, timestamp, output_hash, scores, parity
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        # Import pipeline
        from apps.pipeline.demo_flow import run_score

        # Run scoring pipeline
        result = run_score(
            company=company,
            year=year,
            query=query,
            semantic=semantic,
            alpha=alpha,
            k=topk,
            seed=42,
        )

        # Prepare output (use fixed timestamp for determinism)
        output = {
            "run_num": run_num,
            "timestamp": "2025-10-28T06:00:00Z",  # Fixed for deterministic hashing
            "status": "ok",
            "company": company,
            "year": year,
            "query": query,
            "topk": topk,
            "alpha": alpha,
            "semantic": semantic,
            "trace_id": result.get("trace_id"),
            "rubric_version": result.get("rubric_version"),
            "model_version": result.get("model_version"),
            "theme_count": len(result.get("scores", [])),
            "parity": result.get("parity", {}),
        }

        # Save JSON output
        output_file = output_dir / "output.json"
        output_file.write_text(json.dumps(output, indent=2))

        # Compute output hash
        output_hash = hashlib.sha256(output_file.read_bytes()).hexdigest()

        # Save output hash
        hash_file = output_dir / "hash.txt"
        hash_file.write_text(output_hash)

        # Save full scoring response (use fixed timestamp for determinism)
        scoring_file = output_dir / "scoring_response.json"
        scoring_response = {
            "timestamp": "2025-10-28T06:00:00Z",  # Fixed for deterministic hashing
            "company": company,
            "year": year,
            "query": query,
            "trace_id": result.get("trace_id"),
            "rubric_version": result.get("rubric_version"),
            "model_version": result.get("model_version"),
            "scores": result.get("scores", []),
            "parity": result.get("parity", {}),
        }
        scoring_file.write_text(json.dumps(scoring_response, indent=2))

        # Add hash to output
        output["output_hash"] = output_hash
        output_file.write_text(json.dumps(output, indent=2))

        return output

    except Exception as e:
        import traceback

        return {
            "run_num": run_num,
            "timestamp": "2025-10-28T06:00:00Z",  # Fixed for deterministic hashing
            "status": "error",
            "error": str(e),
            "traceback": traceback.format_exc(),
        }


def compare_runs(outputs: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Compare outputs across runs for determinism validation.

    Args:
        outputs: List of output dicts from each run

    Returns:
        Dict with determinism analysis
    """
    hashes = [
        out.get("output_hash", "") for out in outputs if out.get("status") == "ok"
    ]

    # Check if all hashes match
    deterministic = len(set(hashes)) == 1 and len(hashes) == len(outputs)

    return {
        "deterministic": deterministic,
        "total_runs": len(outputs),
        "successful_runs": sum(1 for o in outputs if o.get("status") == "ok"),
        "failed_runs": sum(1 for o in outputs if o.get("status") != "ok"),
        "unique_output_hashes": len(set(hashes)),
        "all_hashes": hashes,
        "message": (
            "[OK] DETERMINISTIC: All runs produced identical output hashes"
            if deterministic
            else "[FAIL] NON-DETERMINISTIC: Output hashes differ across runs"
        ),
    }


def main() -> int:
    """Run the deterministic E2E orchestration."""
    parser = argparse.ArgumentParser(
        description="Deterministic E2E ESG scoring orchestration"
    )
    parser.add_argument(
        "--company", type=str, required=True, help="Company name for evaluation"
    )
    parser.add_argument("--year", type=int, required=True, help="Year for evaluation")
    parser.add_argument(
        "--query", type=str, required=True, help="Search query for evidence retrieval"
    )
    parser.add_argument(
        "--runs", type=int, default=3, help="Number of runs (default: 3)"
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("artifacts/orchestrator/baseline"),
        help="Output directory",
    )
    parser.add_argument("--topk", type=int, default=5, help="Top-K retrieval (default: 5)")
    parser.add_argument(
        "--alpha", type=float, default=0.6, help="Alpha fusion parameter (default: 0.6)"
    )
    parser.add_argument(
        "--semantic",
        type=int,
        default=0,
        choices=[0, 1],
        help="Enable semantic search (default: 0=off)",
    )
    args = parser.parse_args()

    output_root = args.output
    output_root.mkdir(parents=True, exist_ok=True)

    print("=" * 70)
    print("ESG Scoring Orchestration: Prospecting-Engine")
    print("=" * 70)
    print(f"Company: {args.company}")
    print(f"Year: {args.year}")
    print(f"Query: {args.query}")
    print(f"Runs: {args.runs}")
    print(f"Output: {output_root}")
    print(f"Top-K: {args.topk}")
    print(f"Alpha: {args.alpha}")
    print(f"Semantic: {'ON' if args.semantic else 'OFF'}")
    print(f"Seed: 42 (fixed)")
    print(f"PYTHONHASHSEED: 0 (disabled)")
    print()

    # Setup environment
    setup_environment()
    os.environ["TOPK"] = str(args.topk)
    os.environ["ALPHA"] = str(args.alpha)

    # Run pipeline N times
    outputs = []
    for run_num in range(1, args.runs + 1):
        print(f"Run {run_num}/{args.runs}...", end=" ", flush=True)
        run_dir = output_root / f"run_{run_num}"
        output = run_pipeline(
            company=args.company,
            year=args.year,
            query=args.query,
            run_num=run_num,
            output_dir=run_dir,
            topk=args.topk,
            alpha=args.alpha,
            semantic=bool(args.semantic),
        )
        outputs.append(output)
        if output.get("status") == "ok":
            hash_val = output.get("output_hash", "N/A")[:16]
            theme_count = output.get("theme_count", 0)
            parity = output.get("parity", {}).get("parity_ok", False)
            parity_str = "[PARITY OK]" if parity else "[NO PARITY]"
            print(f"[OK] Hash: {hash_val}... Themes: {theme_count} {parity_str}")
        else:
            error_msg = output.get("error", "unknown")
            print(f"[FAIL] Error: {error_msg}")

    # Compare runs
    print()
    comparison = compare_runs(outputs)

    print("Determinism Check:")
    print(f"  {comparison['message']}")
    print(f"  Successful runs: {comparison['successful_runs']}/{comparison['total_runs']}")
    print(f"  Unique hashes: {comparison['unique_output_hashes']}")

    # Save determinism report
    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "project": "prospecting-engine",
        "task": "ESG Scoring Orchestration",
        "determinism": comparison,
        "runs": outputs,
        "parameters": {
            "company": args.company,
            "year": args.year,
            "query": args.query,
            "topk": args.topk,
            "alpha": args.alpha,
            "semantic": bool(args.semantic),
        },
        "seeds": {
            "PYTHONHASHSEED": os.environ.get("PYTHONHASHSEED", "unset"),
            "SEED": os.environ.get("SEED", "unset"),
            "PROVIDER": os.environ.get("PROVIDER", "unset"),
        },
    }

    report_file = output_root / "determinism_report.json"
    report_file.write_text(json.dumps(report, indent=2))
    print(f"  Report: {report_file}")

    # Determine exit code
    if comparison["deterministic"]:
        print()
        print("[PASS] Pipeline is fully deterministic!")
        return 0
    else:
        print()
        print("[FAIL] Pipeline is non-deterministic!")
        print("Investigate:")
        for i, output in enumerate(outputs, 1):
            if output.get("status") == "ok":
                print(f"  Run {i}: {output.get('output_hash')}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
