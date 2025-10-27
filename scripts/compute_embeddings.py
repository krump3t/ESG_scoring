"""
Phase 5, STEP 2: Compute Embeddings from Real Parquet Corpus

Real IBM watsonx.ai Slate 125M embeddings for ESG documents.
Deterministic batch processing with SHA256 lineage tracking.

SCA v13.8 Compliance:
- Real API calls: watsonx.ai (no synthetic embeddings)
- Deterministic: Fixed batch order (published_at, id)
- Type hints: 100% annotated
- Failure paths: Explicit exception handling
- Authenticity: Immutable parquet + SHA256 manifest
"""

import logging
import json
import hashlib
import argparse
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
import sys

import pandas as pd
import numpy as np

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)


class EmbeddingsComputer:
    """Compute embeddings for ESG documents via watsonx.ai.

    Real API integration: Calls IBM watsonx.ai Slate model.
    Deterministic batch processing with full lineage tracking.
    """

    REQUIRED_INPUT_FIELDS = {"id", "text", "sha256"}
    OUTPUT_FIELDS = {"id", "sha256", "model", "dim", "vector", "created_at", "text_len"}

    def __init__(
        self,
        embedder: Any,  # WatsonXEmbedder instance
        batch_size: int = 5,
    ):
        """Initialize embeddings computer.

        Args:
            embedder: WatsonXEmbedder instance for API calls
            batch_size: Documents per batch (default: 5)
        """
        self.embedder = embedder
        self.batch_size = batch_size
        self.records: List[Dict[str, Any]] = []

        logger.info(f"EmbeddingsComputer initialized: batch_size={batch_size}")

    def compute_from_parquet(
        self,
        input_parquet: str,
        model_id: str = "ibm/slate-125m-english-rtrvr-v2",
    ) -> int:
        """Compute embeddings for all documents in Parquet.

        Args:
            input_parquet: Path to esg_documents.parquet
            model_id: Embedding model ID (default: Slate 125M)

        Returns:
            Number of embeddings computed

        Raises:
            FileNotFoundError: If Parquet not found
            ValueError: If Parquet invalid or empty
            RuntimeError: If embeddings API fails
        """
        input_path = Path(input_parquet)

        if not input_path.exists():
            raise FileNotFoundError(f"Input parquet not found: {input_parquet}")

        # Load Parquet
        try:
            df = pd.read_parquet(input_parquet)
        except Exception as e:
            raise ValueError(f"Failed to load parquet: {e}") from e

        if df.empty:
            raise ValueError("Input parquet is empty")

        # Validate required fields
        missing = self.REQUIRED_INPUT_FIELDS - set(df.columns)
        if missing:
            raise ValueError(f"Missing required fields: {missing}")

        logger.info(f"Loaded {len(df)} documents from {input_parquet}")

        # Sort deterministically: published_at, id
        df = df.sort_values(by=["published_at", "id"], ascending=[True, True])

        # Process in batches
        total = len(df)
        for batch_idx in range(0, total, self.batch_size):
            batch_df = df.iloc[batch_idx:batch_idx + self.batch_size]
            logger.info(
                f"Batch {batch_idx // self.batch_size + 1}/{(total + self.batch_size - 1) // self.batch_size}: "
                f"{len(batch_df)} documents"
            )

            # Embed texts in batch (truncate for Slate 512-token limit)
            # Conservative: ~4 chars per token, so 512 tokens ≈ 1500-2000 chars
            # But API is strict, so use 1000 chars (~250 tokens, well within limit)
            MAX_TEXT_LEN = 1000
            texts = [str(t)[:MAX_TEXT_LEN] for t in batch_df["text"].tolist()]
            logger.info(f"Truncated {len(texts)} texts to max {MAX_TEXT_LEN} chars")
            try:
                embeddings = self.embedder.embed_batch(texts, batch_size=len(texts))
            except Exception as e:
                raise RuntimeError(f"Embedding API failed at batch {batch_idx}: {e}") from e

            # Validate embeddings shape
            if embeddings.shape[0] != len(batch_df):
                raise RuntimeError(
                    f"Embedding count mismatch: got {embeddings.shape[0]}, "
                    f"expected {len(batch_df)}"
                )

            dim = embeddings.shape[1]
            logger.info(f"Computed embeddings: shape={embeddings.shape}")

            # Create records
            for idx, (_, row) in enumerate(batch_df.iterrows()):
                record = {
                    "id": str(row["id"]),
                    "sha256": str(row["sha256"]),
                    "model": model_id,
                    "dim": dim,
                    "vector": embeddings[idx].tolist(),  # Convert to list for JSON
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "text_len": len(str(row["text"])),
                }
                self.records.append(record)

        logger.info(f"Embeddings computation complete: {len(self.records)} records")
        return len(self.records)

    def to_parquet(self, output_path: str) -> None:
        """Write embeddings to Parquet (deterministically sorted).

        Args:
            output_path: Output embeddings parquet file path
        """
        if not self.records:
            raise ValueError("No embeddings to write")

        # Create DataFrame
        df = pd.DataFrame(self.records)

        # Sort deterministically: id
        df = df.sort_values(by=["id"], ascending=[True])

        # Create directories
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        # Write to Parquet
        df.to_parquet(output_file, index=False)

        logger.info(f"Wrote {len(self.records)} embeddings to {output_path}")

    def write_manifest(self, manifest_path: str, parquet_path: Optional[str] = None) -> None:
        """Write embeddings manifest with lineage and SHA256.

        Args:
            manifest_path: Output manifest JSON path
            parquet_path: Optional path to embeddings parquet (to compute hash)
        """
        if not self.records:
            raise ValueError("No embeddings to manifest")

        # Compute parquet hash if path provided
        parquet_hash = None
        if parquet_path:
            parquet_file = Path(parquet_path)
            if parquet_file.exists():
                with open(parquet_file, "rb") as f:
                    parquet_hash = hashlib.sha256(f.read()).hexdigest()
                logger.info(f"Parquet hash: {parquet_hash}")

        # Get model and dimension from first record
        model_id = self.records[0]["model"]
        dim = self.records[0]["dim"]

        manifest = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "record_count": len(self.records),
            "model": model_id,
            "embedding_dim": dim,
            "parquet_sha256": parquet_hash,
            "schema": {
                "fields": [
                    {"name": "id", "type": "string"},
                    {"name": "sha256", "type": "string"},
                    {"name": "model", "type": "string"},
                    {"name": "dim", "type": "integer"},
                    {"name": "vector", "type": "array"},
                    {"name": "created_at", "type": "datetime"},
                    {"name": "text_len", "type": "integer"},
                ]
            },
            "lineage": [
                {
                    "record_id": record["id"],
                    "document_sha256": record["sha256"],
                    "embedding_dim": record["dim"],
                    "model": record["model"],
                    "text_length": record["text_len"],
                }
                for record in self.records[:10]  # First 10 for brevity
            ],
        }

        manifest_file = Path(manifest_path)
        manifest_file.parent.mkdir(parents=True, exist_ok=True)

        with open(manifest_file, "w") as f:
            json.dump(manifest, f, indent=2)

        logger.info(f"Wrote embeddings manifest: {manifest_path}")


def main():
    """CLI entry point for embeddings computation."""
    parser = argparse.ArgumentParser(
        description="Compute real ESG document embeddings via watsonx.ai"
    )
    parser.add_argument("--in", dest="input_parquet", required=True,
                       help="Input parquet file (esg_documents.parquet)")
    parser.add_argument("--out", dest="output_parquet", required=True,
                       help="Output embeddings parquet file")
    parser.add_argument("--schema", help="Output schema JSON file (optional)")
    parser.add_argument("--manifest", help="Output manifest JSON file (optional)")
    parser.add_argument("--model", default="ibm/slate-125m-english-rtrvr-v2",
                       help="Embedding model ID (default: Slate 125M)")
    parser.add_argument("--project", help="Watsonx project ID (from env if not set)")
    parser.add_argument("--batch-size", type=int, default=5,
                       help="Batch size for API calls (default: 5)")

    args = parser.parse_args()

    try:
        # Create embedder
        from libs.embedding.watsonx_embedder import create_embedder

        embedder = create_embedder()

        # Create computer
        computer = EmbeddingsComputer(embedder, batch_size=args.batch_size)

        # Compute embeddings
        count = computer.compute_from_parquet(args.input_parquet, model_id=args.model)

        if count == 0:
            logger.error("No embeddings computed")
            sys.exit(1)

        # Write outputs
        computer.to_parquet(args.output_parquet)

        if args.manifest:
            computer.write_manifest(args.manifest, parquet_path=args.output_parquet)

        logger.info("Embeddings computation complete")

    except Exception as e:
        logger.error(f"Embeddings computation failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
