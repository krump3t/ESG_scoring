#!/usr/bin/env python3
"""
Component 2 Integration Script: Semantic Retrieval FETCH+REPLAY Workflow

Purpose:
  Demonstrate end-to-end semantic retrieval with watsonx.ai embeddings:
  1. FETCH phase: Build embeddings from silver data
  2. REPLAY phase: Query with cached embeddings (deterministic)

SCA v13.8-MEA Compliance:
- Determinism: SEED=42, PYTHONHASHSEED=0
- Offline replay: WX_OFFLINE_REPLAY=true enforces cache-only mode
- Parity validation: evidence_ids subset of fused_topk
- Traceability: All artifacts logged

Usage:
  # FETCH phase (requires WX_API_KEY, WX_PROJECT)
  export WX_API_KEY=...
  export WX_PROJECT=...
  export SEED=42
  export PYTHONHASHSEED=0
  python scripts/semantic_fetch_replay.py --phase fetch --doc-id msft_2023

  # REPLAY phase (offline, cache-only)
  export WX_OFFLINE_REPLAY=true
  export SEED=42
  export PYTHONHASHSEED=0
  python scripts/semantic_fetch_replay.py --phase replay --doc-id msft_2023
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from libs.wx.wx_client import WatsonxClient
from libs.retrieval.semantic_wx import SemanticRetriever


def fetch_phase(doc_id: str, silver_root: str = "data/silver") -> dict:
    """
    FETCH phase: Build embeddings from silver data.

    Args:
        doc_id: Document identifier (e.g., "msft_2023")
        silver_root: Root directory for silver data

    Returns:
        Build result dict with status, vector_count, etc.
    """
    print(f"\n{'='*70}")
    print(f"FETCH PHASE: Building embeddings for {doc_id}")
    print(f"{'='*70}\n")

    # Check prerequisites
    if not os.getenv("WX_API_KEY") or not os.getenv("WX_PROJECT"):
        print("ERROR: WX_API_KEY and WX_PROJECT required for FETCH phase")
        sys.exit(1)

    # Ensure offline replay is disabled
    os.environ["WX_OFFLINE_REPLAY"] = "false"

    # Load flags
    flags_path = Path("configs/integration_flags.json")
    if not flags_path.exists():
        print(f"WARNING: {flags_path} not found, using defaults")
        flags = {
            "semantic_enabled": True,
            "alpha": 0.6,
            "k": 50,
        }
    else:
        flags = json.loads(flags_path.read_text())

    print(f"Integration flags: {flags}")

    # Initialize clients
    wx = WatsonxClient(offline_replay=False)
    retriever = SemanticRetriever(wx, flags, seed=42)

    # Build embeddings
    print(f"\nBuilding embeddings for {doc_id}...")
    build_result = retriever.build_chunk_embeddings(doc_id, silver_root=silver_root)

    print(f"\n{'='*70}")
    print("FETCH PHASE COMPLETE")
    print(f"{'='*70}\n")
    print(json.dumps(build_result, indent=2))

    return build_result


def replay_phase(
    doc_id: str,
    query: str = "ESG climate strategy and GHG emissions targets",
    k: int = 50,
    alpha: float = 0.6,
) -> dict:
    """
    REPLAY phase: Query with cached embeddings (deterministic).

    Args:
        doc_id: Document identifier
        query: Search query
        k: Top-K results
        alpha: BM25 weight

    Returns:
        Query results dict with topk, parity, etc.
    """
    print(f"\n{'='*70}")
    print(f"REPLAY PHASE: Querying {doc_id} (offline, cache-only)")
    print(f"{'='*70}\n")

    # Ensure offline replay is enabled
    os.environ["WX_OFFLINE_REPLAY"] = "true"

    # Load flags
    flags_path = Path("configs/integration_flags.json")
    if not flags_path.exists():
        flags = {
            "semantic_enabled": True,
            "alpha": alpha,
            "k": k,
        }
    else:
        flags = json.loads(flags_path.read_text())
        flags["alpha"] = alpha
        flags["k"] = k

    print(f"Integration flags: {flags}")
    print(f"Query: {query}")
    print(f"Top-K: {k}, Alpha: {alpha}\n")

    # Initialize clients (offline mode)
    wx = WatsonxClient(offline_replay=True)
    retriever = SemanticRetriever(wx, flags, seed=42)

    # Query
    print(f"Querying {doc_id}...")
    results = retriever.query(doc_id, query, k=k, alpha=alpha)

    # Display top 10 results
    print(f"\nTop-10 Results:")
    for r in results[:10]:
        print(f"  Rank {r['rank']:2d}: {r['chunk_id'][:30]:<30} (score={r['score']:.4f})")
        print(f"            BM25={r['bm25_score']:.4f}, Semantic={r['semantic_score']:.4f}")
        print(f"            Text: {r['text'][:80]}...")
        print()

    # Parity validation (mock: use top 5 as evidence)
    evidence_ids = [r["chunk_id"] for r in results[:5]]
    parity = retriever.validate_parity(doc_id, results, evidence_ids)

    print(f"\n{'='*70}")
    print("Parity Validation (evidence_ids subset of topk)")
    print(f"{'='*70}\n")
    print(json.dumps(parity, indent=2))

    print(f"\n{'='*70}")
    print("REPLAY PHASE COMPLETE")
    print(f"{'='*70}\n")

    return {
        "doc_id": doc_id,
        "query": query,
        "k": k,
        "alpha": alpha,
        "topk_count": len(results),
        "parity": parity,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def main():
    ap = argparse.ArgumentParser(
        description="Semantic Retrieval FETCH+REPLAY Integration Script"
    )
    ap.add_argument(
        "--phase",
        required=True,
        choices=["fetch", "replay"],
        help="Phase to run: fetch (build embeddings) or replay (query)",
    )
    ap.add_argument(
        "--doc-id",
        required=True,
        help="Document identifier (e.g., msft_2023)",
    )
    ap.add_argument(
        "--query",
        default="ESG climate strategy and GHG emissions targets",
        help="Search query (replay phase only)",
    )
    ap.add_argument(
        "--k",
        type=int,
        default=50,
        help="Top-K results (replay phase only)",
    )
    ap.add_argument(
        "--alpha",
        type=float,
        default=0.6,
        help="BM25 weight (replay phase only)",
    )
    ap.add_argument(
        "--silver-root",
        default="data/silver",
        help="Silver data root directory (fetch phase only)",
    )

    args = ap.parse_args()

    # Set determinism env vars
    os.environ["SEED"] = "42"
    os.environ["PYTHONHASHSEED"] = "0"

    try:
        if args.phase == "fetch":
            result = fetch_phase(args.doc_id, silver_root=args.silver_root)
            sys.exit(0 if result["status"] == "ok" else 1)

        elif args.phase == "replay":
            result = replay_phase(
                args.doc_id,
                query=args.query,
                k=args.k,
                alpha=args.alpha,
            )
            sys.exit(0 if result["parity"]["validated"] else 1)

    except Exception as e:
        import traceback

        print(f"\n{'='*70}")
        print(f"ERROR: {e}")
        print(f"{'='*70}\n")
        print(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    main()
