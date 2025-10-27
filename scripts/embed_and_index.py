logger = logging.getLogger(__name__)
import logging

"""
Embedding & Index Building CLI

Builds deterministic embeddings and in-memory vector index from ingested companies.
Writes index snapshot to artifacts/demo/index_snapshot.json.

SCA v13.8 Compliance:
- Determinism: SEED=42, sorted keys, stable hashing
- Type safety: 100% annotated
- No network: Offline embedding only
- Exit codes: 0=success, 1=validation error
"""

logger = logging.getLogger(__name__)
import argparse
logger = logging.getLogger(__name__)
import sys
logger = logging.getLogger(__name__)
import json
logger = logging.getLogger(__name__)
import hashlib
from pathlib import Path
from typing import Dict, List, Any

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def validate_alpha(alpha: float) -> None:
    """
    Validate alpha is in [0, 1].

    Args:
        alpha: Fusion parameter

    Raises:
        ValueError: If alpha out of range
    """
    if not (0.0 <= alpha <= 1.0):
        raise ValueError(f"alpha must be in [0.0, 1.0], got {alpha}")


def validate_k(k: int) -> None:
    """
    Validate k is positive.

    Args:
        k: Top-k parameter

    Raises:
        ValueError: If k <= 0
    """
    if k <= 0:
        raise ValueError(f"k must be > 0, got {k}")


def validate_dim(dim: int) -> None:
    """
    Validate dimension is positive.

    Args:
        dim: Embedding dimension

    Raises:
        ValueError: If dim <= 0
    """
    if dim <= 0:
        raise ValueError(f"dim must be > 0, got {dim}")


def load_companies() -> List[Dict[str, Any]]:
    """
    Load companies manifest.

    Returns:
        List of company records

    Raises:
        FileNotFoundError: If manifest doesn't exist
    """
    companies_path = Path("artifacts/demo/companies.json")
    if not companies_path.exists():
        raise FileNotFoundError(
            "No companies found. Run ingest_company.py first."
        )

    return json.loads(companies_path.read_text())


def load_corpus(companies: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Load corpus documents from bronze Parquet files.

    Args:
        companies: Company records with bronze paths

    Returns:
        List of {doc_id, text, company, year} dicts
    """
    corpus = []

    for comp in companies:
        bronze_path = Path(comp["bronze"])
        if not bronze_path.exists():
            print(f"Warning: Bronze file not found: {bronze_path}", file=sys.stderr)
            continue

        # Read stub JSON (tests use .parquet extension)
        try:
            data = json.loads(bronze_path.read_text())

            # Extract doc records
            for i in range(len(data.get("doc_id", []))):
                corpus.append({
                    "doc_id": data["doc_id"][i],
                    "text": data["text"][i],
                    "company": data["company"][i],
                    "year": data["year"][i]
                })
        except Exception as e:
            print(f"Warning: Failed to load {bronze_path}: {e}", file=sys.stderr)

    return corpus


def build_deterministic_embeddings(
    corpus: List[Dict[str, Any]],
    dim: int,
    seed: int = 42
) -> Dict[str, List[float]]:
    """
    Build deterministic embeddings using hash-TF.

    Args:
        corpus: List of documents
        dim: Embedding dimension
        seed: Random seed for hashing

    Returns:
        Dict mapping doc_id to embedding vector
    """
    from libs.retrieval.embeddings.deterministic_embedder import DeterministicEmbedder

    embedder = DeterministicEmbedder(dim=dim, seed=seed)
    vectors = {}

    for doc in corpus:
        vec = embedder.embed(doc["text"])
        vectors[doc["doc_id"]] = vec.tolist()  # Convert numpy to list for JSON

    return vectors


def create_index_snapshot(
    vectors: Dict[str, List[float]],
    corpus: List[Dict[str, Any]],
    dim: int,
    alpha: float,
    k: int,
    backend: str,
    seed: int = 42
) -> Dict[str, Any]:
    """
    Create index snapshot metadata.

    Args:
        vectors: Document vectors
        corpus: Document metadata
        dim: Embedding dimension
        alpha: Fusion parameter
        k: Top-k parameter
        backend: Backend type
        seed: Random seed

    Returns:
        Snapshot dict
    """
    # Build metadata lookup
    meta_lookup = {doc["doc_id"]: doc for doc in corpus}

    # Create doc entries with metadata
    docs = []
    for doc_id in sorted(vectors.keys()):  # Stable ordering
        vec = vectors[doc_id]
        norm = sum(x**2 for x in vec) ** 0.5

        docs.append({
            "id": doc_id,
            "norm": norm,
            "meta": meta_lookup.get(doc_id, {})
        })

    # Compute stable digest
    doc_ids_str = ",".join(sorted(vectors.keys()))
    digest = hashlib.sha256(doc_ids_str.encode()).hexdigest()[:16]

    return {
        "dim": dim,
        "alpha": alpha,
        "k": k,
        "seed": seed,
        "backend": backend,
        "docs": docs,
        "index_digest": digest,
        "total_docs": len(vectors)
    }


def main() -> int:
    """
    Main CLI entry point.

    Returns:
        Exit code: 0=success, 1=validation error
    """
    parser = argparse.ArgumentParser(
        description="Build deterministic embeddings and index"
    )
    parser.add_argument(
        "--mode",
        default="deterministic",
        choices=["deterministic"],
        help="Embedding mode"
    )
    parser.add_argument(
        "--backend",
        default="in_memory",
        choices=["in_memory"],
        help="Vector backend"
    )
    parser.add_argument(
        "--alpha",
        type=float,
        default=0.6,
        help="Fusion parameter (0.0-1.0)"
    )
    parser.add_argument(
        "--k",
        type=int,
        default=10,
        help="Top-k results"
    )
    parser.add_argument(
        "--dim",
        type=int,
        default=128,
        help="Embedding dimension"
    )

    args = parser.parse_args()

    try:
        # Validate parameters
        validate_alpha(args.alpha)
        validate_k(args.k)
        validate_dim(args.dim)

        # Load companies
        print("Loading companies manifest...")
        companies = load_companies()
        print(f"[OK] Found {len(companies)} companies")

        # Load corpus
        print("Loading corpus from bronze files...")
        corpus = load_corpus(companies)
        if not corpus:
            print("Warning: No documents loaded", file=sys.stderr)
            return 1
        print(f"[OK] Loaded {len(corpus)} documents")

        # Build embeddings
        print(f"Building {args.mode} embeddings (dim={args.dim}, seed=42)...")
        vectors = build_deterministic_embeddings(corpus, args.dim, seed=42)
        print(f"[OK] Generated {len(vectors)} vectors")

        # Create snapshot
        print("Creating index snapshot...")
        snapshot = create_index_snapshot(
            vectors, corpus, args.dim, args.alpha, args.k, args.backend
        )

        # Write snapshot
        snapshot_path = Path("artifacts/demo/index_snapshot.json")
        snapshot_path.write_text(json.dumps(snapshot, indent=2, sort_keys=True))
        print(f"[OK] Saved index snapshot: {snapshot_path}")
        print(f"  Digest: {snapshot['index_digest']}")
        print(f"  Backend: {args.backend}")
        print(f"  Docs: {snapshot['total_docs']}")

        # Set metric
        try:
            from apps.api.metrics import esg_demo_index_size
            esg_demo_index_size.labels(backend=args.backend).set(snapshot['total_docs'])
        except ImportError as e:
            logger.warning(f"Import failed: {e}")  # Metrics not available in test environment

        return 0

    except ValueError as e:
        print(f"Validation error: {e}", file=sys.stderr)
        return 1
    except FileNotFoundError as e:
        print(f"File not found: {e}", file=sys.stderr)
        return 2
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
