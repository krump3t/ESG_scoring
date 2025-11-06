#!/usr/bin/env python3
"""CLI wrapper for hybrid retrieval with REAL infrastructure.

Executes BM25, vector, or hybrid retrieval using real BM25 indices,
real Astra DB connections, and real embeddings.

Usage:
  # BM25-only mode (no Astra required):
  python hybrid_cli.py --mode bm25 --query "What are ESG metrics?" --chunks chunks.parquet --out results.json

  # Hybrid mode (requires Astra):
  python hybrid_cli.py --mode hybrid --query "What are ESG metrics?" --chunks chunks.parquet \
    --astra-endpoint $ASTRA_DB_ENDPOINT --astra-token $ASTRA_DB_TOKEN --out results.json

  # Or use environment variables:
  export ASTRA_DB_ENDPOINT="https://..."
  export ASTRA_DB_TOKEN="AstraCS:..."
  python hybrid_cli.py --mode hybrid --query "What are ESG metrics?" --chunks chunks.parquet --out results.json
"""

import argparse
import json
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.retrieval.hybrid_retriever import HybridRetriever, RetrievalConfig


def main():
    """CLI entry point for hybrid retrieval."""
    parser = argparse.ArgumentParser(
        description="Execute hybrid retrieval with real BM25, vector, and RRF",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    # Required arguments
    parser.add_argument('--query', required=True, help='Search query')
    parser.add_argument('--chunks', required=True, help='Path to chunks parquet file')
    parser.add_argument('--out', required=True, help='Output JSON file path')

    # Mode selection
    parser.add_argument(
        '--mode',
        choices=['bm25', 'vector', 'hybrid'],
        default='hybrid',
        help='Retrieval mode (default: hybrid)'
    )

    # Astra credentials (optional, can use env vars)
    parser.add_argument(
        '--astra-endpoint',
        help='Astra DB endpoint (or ASTRA_DB_ENDPOINT env var)'
    )
    parser.add_argument(
        '--astra-token',
        help='Astra DB token (or ASTRA_DB_TOKEN env var)'
    )
    parser.add_argument(
        '--collection',
        default='chunks',
        help='Astra collection name (default: chunks)'
    )

    # Retrieval parameters
    parser.add_argument(
        '--k-bm25',
        type=int,
        default=40,
        help='Number of BM25 results (default: 40)'
    )
    parser.add_argument(
        '--k-vec',
        type=int,
        default=40,
        help='Number of vector results (default: 40)'
    )
    parser.add_argument(
        '--rrf-k',
        type=int,
        default=60,
        help='RRF k parameter (default: 60)'
    )

    # Embedding model
    parser.add_argument(
        '--embedding-model',
        default='sentence-transformers/all-mpnet-base-v2',
        help='Embedding model ID (default: all-mpnet-base-v2)'
    )

    args = parser.parse_args()

    # Validate chunks file exists
    if not Path(args.chunks).exists():
        print(f"ERROR: Chunks file not found: {args.chunks}", file=sys.stderr)
        sys.exit(1)

    # Get Astra credentials from args or environment
    astra_endpoint = args.astra_endpoint or os.getenv('ASTRA_DB_ENDPOINT') or os.getenv('ASTRA_DB_API_ENDPOINT')
    astra_token = args.astra_token or os.getenv('ASTRA_DB_TOKEN') or os.getenv('ASTRA_DB_APPLICATION_TOKEN')

    # Configure retrieval based on mode
    if args.mode == 'bm25':
        config = RetrievalConfig(
            k_bm25=args.k_bm25,
            enable_bm25=True,
            enable_vector=False
        )
    elif args.mode == 'vector':
        config = RetrievalConfig(
            k_vec=args.k_vec,
            enable_bm25=False,
            enable_vector=True
        )
    else:  # hybrid
        config = RetrievalConfig(
            k_bm25=args.k_bm25,
            k_vec=args.k_vec,
            rrf_k=args.rrf_k,
            enable_bm25=True,
            enable_vector=True
        )

    # Check Astra credentials if vector search enabled
    if config.enable_vector:
        if not astra_endpoint or not astra_token:
            print(
                "ERROR: Astra credentials required for vector/hybrid mode.\n"
                "Provide --astra-endpoint + --astra-token or set environment variables:\n"
                "  ASTRA_DB_ENDPOINT\n"
                "  ASTRA_DB_TOKEN",
                file=sys.stderr
            )
            sys.exit(1)

    try:
        print(f"Initializing {args.mode} retriever...")
        print(f"  Chunks: {args.chunks}")
        if config.enable_bm25:
            print(f"  BM25: enabled (k={args.k_bm25})")
        if config.enable_vector:
            print(f"  Vector: enabled (k={args.k_vec})")
            print(f"  Astra: {astra_endpoint}")
            print(f"  Model: {args.embedding_model}")
        if config.enable_bm25 and config.enable_vector:
            print(f"  RRF: k={args.rrf_k}")

        # Instantiate retriever with REAL infrastructure
        retriever = HybridRetriever(
            chunks_path=args.chunks,
            astra_endpoint=astra_endpoint,
            astra_token=astra_token,
            collection_name=args.collection,
            embedding_model=args.embedding_model,
            config=config
        )

        print(f"\nExecuting retrieval for query: {args.query}")

        # Execute REAL retrieval
        results = retriever.retrieve(args.query)

        print(f"Retrieved {len(results)} results")

        # Write results to output file
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        with open(args.out, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

        print(f"SUCCESS: Results written to {args.out}")
        sys.exit(0)

    except FileNotFoundError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: Retrieval failed: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
