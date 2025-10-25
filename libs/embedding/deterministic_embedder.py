"""
Deterministic Embedder for SCA Compliance.

Generates reproducible embeddings using hash-based TF vectors.
- Seed: 42 (fixed for determinism)
- Algorithm: Hash-TF with stable output
- Format: Dense numpy arrays

SCA v13.8 Compliance:
- Determinism: Fixed seed, sorted terms
- Type safety: 100% annotated
- No network: Pure hash-based embeddings (offline)
"""

import hashlib
import numpy as np
from typing import List


class DeterministicEmbedder:
    """Deterministic embedder using hash-TF algorithm."""

    def __init__(self, dim: int = 128, seed: int = 42) -> None:
        """
        Initialize embedder.

        Args:
            dim: Embedding dimension
            seed: Random seed for determinism
        """
        self.dim = dim
        self.seed = seed
        # Seed the RNG for reproducibility
        np.random.seed(seed)

    def embed(self, text: str) -> np.ndarray:
        """
        Embed text using hash-TF.

        Args:
            text: Input text to embed

        Returns:
            Embedding vector as numpy array (dim,)
        """
        # Tokenize and compute term frequency
        terms = text.lower().split()
        if not terms:
            return np.zeros(self.dim, dtype=np.float32)

        # Count term frequency
        tf = {}
        for term in terms:
            tf[term] = tf.get(term, 0) + 1

        # Initialize embedding vector
        vec = np.zeros(self.dim, dtype=np.float32)

        # Hash each unique term and accumulate
        for term, count in sorted(tf.items()):  # Stable ordering
            # Hash term to bucket
            h = int(hashlib.md5(term.encode()).hexdigest(), 16)
            bucket = h % self.dim
            # Add TF value
            vec[bucket] += count

        # Normalize
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm

        return vec
