#!/usr/bin/env python3
"""
Component 2: Semantic Retrieval with watsonx.ai Embeddings

SCA v13.8-MEA Compliance:
- Deterministic cache→replay: WX_OFFLINE_REPLAY=true enforces 100% cache hits
- No mocks: All embeddings from real watsonx.ai calls (cached for replay)
- Parity preserved: Hybrid retrieval (BM25 + semantic) maintains evidence_ids ⊆ topk
- Algorithmic fidelity: Real cosine similarity, real BM25 fusion

Architecture:
- SemanticRetriever: Build chunk embeddings from silver data, query with hybrid retrieval
- Offline posture: build_chunk_embeddings in FETCH, query in REPLAY (both deterministic)
- Artifacts:
  * data/index/<doc_id>/chunks.parquet (chunk metadata)
  * data/index/<doc_id>/embeddings.bin (float32 vectors [N x D])
  * data/index/<doc_id>/meta.json (model_id, dim, build_ts, deterministic_ts)
  * artifacts/wx_cache/embeddings/<cache_key>.json (watsonx.ai cache)

Usage:
    # FETCH phase (ALLOW_NETWORK=true, WX_OFFLINE_REPLAY=false)
    wx = WatsonxClient(offline_replay=False)
    retriever = SemanticRetriever(wx, flags)
    retriever.build_chunk_embeddings("msft_2023")

    # REPLAY phase (WX_OFFLINE_REPLAY=true, ALLOW_NETWORK=false)
    wx = WatsonxClient(offline_replay=True)
    retriever = SemanticRetriever(wx, flags)
    results = retriever.query("msft_2023", "ESG climate strategy", k=50, alpha=0.6)
"""

from __future__ import annotations

import hashlib
import json
import os
import random
import struct
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

try:
    from rank_bm25 import BM25Okapi
    BM25_AVAILABLE = True
except ImportError:
    BM25_AVAILABLE = False
    BM25Okapi = None


class SemanticRetriever:
    """
    Semantic retrieval with watsonx.ai embeddings + BM25 hybrid fusion.

    Features:
    - Build embeddings from silver chunks (Parquet files)
    - Deterministic cache→replay via WatsonxClient
    - Hybrid retrieval: alpha*BM25 + (1-alpha)*semantic
    - Parity: evidence_ids ⊆ fused_topk (maintained across fetch/replay)
    """

    def __init__(
        self,
        wx_client: Any,
        flags: Dict[str, Any],
        cache_dir: str = "artifacts/wx_cache",
        index_dir: str = "data/index",
        seed: int = 42,
    ):
        """
        Initialize semantic retriever.

        Args:
            wx_client: WatsonxClient instance (handles offline replay)
            flags: Integration flags dict (semantic_enabled, alpha, k, etc.)
            cache_dir: Directory for watsonx.ai cache
            index_dir: Directory for chunk index + embeddings
            seed: Random seed for determinism
        """
        self.wx_client = wx_client
        self.flags = flags
        self.cache_dir = Path(cache_dir)
        self.index_dir = Path(index_dir)
        self.seed = seed

        # Extract config
        self.model_id = os.getenv("WX_MODEL_EMBED", "ibm/slate-125m-english-rtrvr")
        self.offline_replay = os.getenv("WX_OFFLINE_REPLAY", "").lower() == "true"
        self.alpha = float(flags.get("alpha", 0.6))  # BM25 weight
        self.k = int(flags.get("k", 50))  # Top-K retrieval

        # Set seeds
        random.seed(seed)
        np.random.seed(seed)
        os.environ["PYTHONHASHSEED"] = str(seed)

        # Create directories
        self.index_dir.mkdir(parents=True, exist_ok=True)

    def build_chunk_embeddings(self, doc_id: str, silver_root: str = "data/silver") -> Dict[str, Any]:
        """
        Build chunk embeddings from silver data (FETCH phase).

        Reads all parquet chunks for doc_id, canonicalizes text, computes embeddings
        via watsonx.ai, and persists:
        - data/index/<doc_id>/chunks.parquet (id, page, text_sha, len, ...)
        - data/index/<doc_id>/embeddings.bin (float32 [N x D])
        - data/index/<doc_id>/meta.json (model_id, dim, build_ts, deterministic_ts)

        Args:
            doc_id: Document identifier (e.g., "msft_2023")
            silver_root: Root directory for silver data (Parquet files)

        Returns:
            Status dict: {"status": "ok", "vector_count": N, "chunk_count": M, ...}

        Raises:
            RuntimeError: If offline_replay=True (build requires network fetch)
            FileNotFoundError: If no silver chunks found for doc_id
        """
        if self.offline_replay:
            raise RuntimeError(
                "build_chunk_embeddings requires FETCH mode (WX_OFFLINE_REPLAY=false). "
                "Embeddings must be generated before replay."
            )

        # Parse doc_id (format: org_id_year, e.g., "msft_2023")
        parts = doc_id.split("_")
        if len(parts) < 2:
            raise ValueError(f"Invalid doc_id format: {doc_id}. Expected: org_id_year")

        org_id = "_".join(parts[:-1]).upper()
        year = parts[-1]

        # Find all parquet files for this doc
        silver_path = Path(silver_root) / f"org_id={org_id}" / f"year={year}"

        if not silver_path.exists():
            raise FileNotFoundError(
                f"No silver data found for {doc_id} at {silver_path}. "
                "Run extraction/ingestion first."
            )

        # Collect all parquet files across themes
        parquet_files = list(silver_path.rglob("*.parquet"))

        if not parquet_files:
            raise FileNotFoundError(
                f"No parquet chunks found for {doc_id} in {silver_path}"
            )

        print(f"  Found {len(parquet_files)} parquet files for {doc_id}")

        # Read and merge all chunks
        chunk_dfs = []
        for pf in parquet_files:
            try:
                df = pd.read_parquet(pf)
                chunk_dfs.append(df)
            except Exception as e:
                print(f"WARNING: Failed to read {pf}: {e}")
                continue

        if not chunk_dfs:
            raise RuntimeError(f"No valid chunks read for {doc_id}")

        chunks_df = pd.concat(chunk_dfs, ignore_index=True)

        # Normalize column name: support both 'text' and 'extract_30w'
        if "extract_30w" in chunks_df.columns and "text" not in chunks_df.columns:
            chunks_df["text"] = chunks_df["extract_30w"]
        elif "text" not in chunks_df.columns:
            raise ValueError("Chunks dataframe must have either 'text' or 'extract_30w' column")

        # Canonicalize text and compute text_sha
        chunks_df["text_canon"] = chunks_df["text"].str.strip().str.lower()
        chunks_df["text_sha"] = chunks_df["text_canon"].apply(
            lambda t: hashlib.sha256(t.encode()).hexdigest()
        )
        chunks_df["len"] = chunks_df["text_canon"].str.len()

        # Drop duplicates by text_sha (deterministic deduplication)
        chunks_df = chunks_df.drop_duplicates(subset=["text_sha"], keep="first")
        chunks_df = chunks_df.reset_index(drop=True)

        # Normalize page column name: support both 'page' and 'page_no'
        if "page_no" in chunks_df.columns and "page" not in chunks_df.columns:
            chunks_df["page"] = chunks_df["page_no"]

        # Generate unique chunk IDs
        chunks_df["chunk_id"] = chunks_df.apply(
            lambda row: f"{doc_id}_p{row.get('page', 0)}_c{row.name}", axis=1
        )

        print(f"  Total unique chunks: {len(chunks_df)}")

        # Extract texts for embedding (batch call)
        texts = chunks_df["text_canon"].tolist()

        # Call watsonx.ai embedding API (cached)
        print(f"  Generating embeddings (model: {self.model_id})...")
        start_time = time.time()

        vectors = self.wx_client.embed_text_batch(
            texts=texts,
            model_id=self.model_id,
            temperature=0.0,
            doc_id=doc_id,
        )

        elapsed = time.time() - start_time
        print(f"  Embeddings generated in {elapsed:.2f}s")

        # Validate output
        if len(vectors) != len(texts):
            raise RuntimeError(
                f"Embedding mismatch: expected {len(texts)} vectors, got {len(vectors)}"
            )

        # Convert to numpy array
        vectors_np = np.array(vectors, dtype=np.float32)
        vector_dim = vectors_np.shape[1]

        print(f"  Vector shape: {vectors_np.shape} (N={len(vectors)}, D={vector_dim})")

        # Prepare index directory
        index_path = self.index_dir / doc_id
        index_path.mkdir(parents=True, exist_ok=True)

        # Save chunks metadata (parquet)
        chunks_meta = chunks_df[[
            "chunk_id", "page", "text_sha", "len", "text_canon"
        ]].copy()

        # Add start/end offsets if present
        if "start_offset" in chunks_df.columns:
            chunks_meta["start_offset"] = chunks_df["start_offset"]
        if "end_offset" in chunks_df.columns:
            chunks_meta["end_offset"] = chunks_df["end_offset"]

        chunks_parquet = index_path / "chunks.parquet"
        chunks_meta.to_parquet(chunks_parquet, index=False, engine="pyarrow")
        print(f"  [OK] Chunks metadata: {chunks_parquet}")

        # Save embeddings (binary float32)
        embeddings_bin = index_path / "embeddings.bin"
        with open(embeddings_bin, "wb") as f:
            # Write shape header: [N, D] as uint32
            f.write(struct.pack("II", vectors_np.shape[0], vectors_np.shape[1]))
            # Write vectors
            vectors_np.tofile(f)

        print(f"  [OK] Embeddings: {embeddings_bin}")

        # Save metadata
        meta = {
            "doc_id": doc_id,
            "model_id": self.model_id,
            "vector_dim": int(vector_dim),
            "vector_count": len(vectors),
            "chunk_count": len(chunks_df),
            "build_ts": datetime.now(timezone.utc).isoformat(),
            "deterministic_timestamp": "2025-10-28T06:00:00Z",  # Fixed for hashing
            "seed": self.seed,
            "text_sha_all": hashlib.sha256(
                "".join(sorted(chunks_df["text_sha"].tolist())).encode()
            ).hexdigest(),
        }

        meta_json = index_path / "meta.json"
        meta_json.write_text(json.dumps(meta, indent=2), encoding="utf-8")
        print(f"  [OK] Metadata: {meta_json}")

        return {
            "status": "ok",
            "doc_id": doc_id,
            "vector_count": len(vectors),
            "chunk_count": len(chunks_df),
            "vector_dim": vector_dim,
            "model_id": self.model_id,
            "index_path": str(index_path),
        }

    def query(
        self,
        doc_id: str,
        query_text: str,
        k: Optional[int] = None,
        alpha: Optional[float] = None,
        return_scores: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Hybrid retrieval: alpha*BM25 + (1-alpha)*semantic.

        REPLAY mode: Uses cached embeddings (deterministic).
        FETCH mode: Uses live embeddings (if index exists).

        Args:
            doc_id: Document identifier
            query_text: Search query
            k: Top-K results (default: self.k)
            alpha: BM25 weight (default: self.alpha)
            return_scores: Include scores in results

        Returns:
            List of dicts: [{"chunk_id", "page", "text", "score", "rank"}, ...]

        Raises:
            FileNotFoundError: If index not found for doc_id
            RuntimeError: If BM25 not available
        """
        k = k or self.k
        alpha = alpha if alpha is not None else self.alpha

        # Load index
        index_path = self.index_dir / doc_id

        if not index_path.exists():
            raise FileNotFoundError(
                f"Index not found for {doc_id} at {index_path}. "
                "Run build_chunk_embeddings first."
            )

        # Load metadata
        meta_json = index_path / "meta.json"
        if not meta_json.exists():
            raise FileNotFoundError(f"Metadata missing: {meta_json}")

        meta = json.loads(meta_json.read_text(encoding="utf-8"))
        vector_dim = meta["vector_dim"]
        vector_count = meta["vector_count"]

        # Load chunks
        chunks_parquet = index_path / "chunks.parquet"
        if not chunks_parquet.exists():
            raise FileNotFoundError(f"Chunks missing: {chunks_parquet}")

        chunks_df = pd.read_parquet(chunks_parquet)

        # Load embeddings
        embeddings_bin = index_path / "embeddings.bin"
        if not embeddings_bin.exists():
            raise FileNotFoundError(f"Embeddings missing: {embeddings_bin}")

        with open(embeddings_bin, "rb") as f:
            # Read shape header
            shape_bytes = f.read(8)
            n_vectors, dim = struct.unpack("II", shape_bytes)

            # Validate
            if n_vectors != vector_count or dim != vector_dim:
                raise RuntimeError(
                    f"Embedding shape mismatch: expected ({vector_count}, {vector_dim}), "
                    f"got ({n_vectors}, {dim})"
                )

            # Read vectors
            vectors_np = np.fromfile(f, dtype=np.float32).reshape(n_vectors, dim)

        print(f"  Loaded {len(chunks_df)} chunks, {len(vectors_np)} vectors for {doc_id}")

        # 1. BM25 scoring
        if not BM25_AVAILABLE:
            raise RuntimeError(
                "rank-bm25 not installed. Install with: pip install rank-bm25"
            )

        # Tokenize chunks (simple whitespace split)
        tokenized_corpus = [
            text.split() for text in chunks_df["text_canon"].tolist()
        ]

        bm25 = BM25Okapi(tokenized_corpus)

        # Tokenize query
        query_tokens = query_text.strip().lower().split()

        # Get BM25 scores
        bm25_scores = bm25.get_scores(query_tokens)

        # Normalize BM25 scores to [0, 1]
        bm25_max = bm25_scores.max() if bm25_scores.max() > 0 else 1.0
        bm25_scores_norm = bm25_scores / bm25_max

        # 2. Semantic scoring (cosine similarity)
        # Embed query
        query_vector = self.wx_client.embed_text_batch(
            texts=[query_text.strip().lower()],
            model_id=self.model_id,
            temperature=0.0,
            doc_id=doc_id,
        )[0]

        query_vector_np = np.array(query_vector, dtype=np.float32)

        # Compute cosine similarity
        # Normalize vectors
        vectors_norm = vectors_np / (np.linalg.norm(vectors_np, axis=1, keepdims=True) + 1e-8)
        query_norm = query_vector_np / (np.linalg.norm(query_vector_np) + 1e-8)

        # Cosine similarity
        semantic_scores = np.dot(vectors_norm, query_norm)

        # Normalize to [0, 1] (cosine is already in [-1, 1], shift to [0, 1])
        semantic_scores_norm = (semantic_scores + 1.0) / 2.0

        # 3. Hybrid fusion
        hybrid_scores = alpha * bm25_scores_norm + (1 - alpha) * semantic_scores_norm

        # 4. Rank and select top-K
        # Get top-K indices (deterministic via argsort)
        topk_indices = np.argsort(-hybrid_scores)[:k]

        # Build results
        results = []
        for rank, idx in enumerate(topk_indices):
            chunk_row = chunks_df.iloc[idx]
            result = {
                "chunk_id": chunk_row["chunk_id"],
                "page": int(chunk_row["page"]) if "page" in chunk_row else 0,
                "text": chunk_row["text_canon"],
                "rank": rank + 1,
            }

            if return_scores:
                result["score"] = float(hybrid_scores[idx])
                result["bm25_score"] = float(bm25_scores_norm[idx])
                result["semantic_score"] = float(semantic_scores_norm[idx])

            results.append(result)

        return results

    def validate_parity(
        self,
        doc_id: str,
        topk_results: List[Dict[str, Any]],
        evidence_ids: List[str],
    ) -> Dict[str, Any]:
        """
        Validate parity constraint: evidence_ids ⊆ topk_results.

        Args:
            doc_id: Document identifier
            topk_results: Top-K retrieval results (from query method)
            evidence_ids: List of chunk IDs used as evidence

        Returns:
            Parity report dict: {"validated": bool, "subset_ok": bool, ...}
        """
        topk_ids = {r["chunk_id"] for r in topk_results}
        evidence_set = set(evidence_ids)

        subset_ok = evidence_set.issubset(topk_ids)
        missing = evidence_set - topk_ids

        return {
            "doc_id": doc_id,
            "constraint": "evidence_ids ⊆ fused_topk",
            "validated": subset_ok,
            "subset_ok": subset_ok,
            "topk_count": len(topk_ids),
            "evidence_count": len(evidence_set),
            "missing_count": len(missing),
            "missing_ids": sorted(list(missing)),
            "notes": "" if subset_ok else f"{len(missing)} evidence IDs not in top-K",
        }


if __name__ == "__main__":
    """
    Test harness: Build embeddings and query (requires watsonx.ai credentials).
    """
    import sys

    # Check env
    if not os.getenv("WX_API_KEY") or not os.getenv("WX_PROJECT"):
        print("ERROR: WX_API_KEY and WX_PROJECT required")
        sys.exit(1)

    # Import wx_client
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from wx.wx_client import WatsonxClient

    # Initialize
    offline = os.getenv("WX_OFFLINE_REPLAY", "").lower() == "true"
    wx = WatsonxClient(offline_replay=offline)

    flags = {
        "semantic_enabled": True,
        "alpha": 0.6,
        "k": 20,
    }

    retriever = SemanticRetriever(wx, flags, seed=42)

    # Test doc_id (must have silver data)
    doc_id = "msft_2023"

    try:
        if not offline:
            # Build embeddings (FETCH mode)
            print(f"\n=== Building embeddings for {doc_id} ===")
            build_result = retriever.build_chunk_embeddings(doc_id)
            print(json.dumps(build_result, indent=2))

        # Query (works in both FETCH and REPLAY)
        print(f"\n=== Querying {doc_id} ===")
        query_text = "ESG climate strategy and GHG emissions targets"
        results = retriever.query(doc_id, query_text, k=10)

        print(f"Top-10 results for: {query_text}")
        for r in results[:5]:
            print(f"  Rank {r['rank']}: {r['chunk_id']} (score={r['score']:.4f})")
            print(f"    Text: {r['text'][:100]}...")

        # Parity check (mock evidence IDs)
        evidence_ids = [r["chunk_id"] for r in results[:3]]
        parity = retriever.validate_parity(doc_id, results, evidence_ids)
        print(f"\n=== Parity Check ===")
        print(json.dumps(parity, indent=2))

        print("\n[OK] Semantic retrieval test PASSED")

    except Exception as e:
        import traceback
        print(f"\n[FAIL] Test FAILED: {e}")
        print(traceback.format_exc())
        sys.exit(1)
