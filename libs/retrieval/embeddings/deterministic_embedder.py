"""
Deterministic Embedder: Hash-TF → L2-norm → Cosine Similarity

Implements offline, reproducible text embeddings using:
1. Token hashing (via hash(f"{seed}:{token}") mod dim)
2. Term frequency (TF) vector construction
3. L2 normalization

SCA v13.8 Compliance:
- Deterministic: Fixed seed, stable hashing
- No network: Offline-only
- Type safety: 100% annotated
- No randomness: Pure hash-based mapping
"""

import hashlib
import numpy as np
from typing import Union, List


class DeterministicEmbedder:
    """Deterministic text embedder using hash-TF with L2 normalization."""

    def __init__(self, dim: int = 128, seed: int = 42) -> None:
        """
        Initialize deterministic embedder.

        Args:
            dim: Embedding dimension
            seed: Random seed for hash stability

        Raises:
            ValueError: If dim <= 0
        """
        if dim <= 0:
            raise ValueError(f"dim must be > 0, got {dim}")

        self.dim = dim
        self.seed = seed

    def _tokenize(self, text: str) -> List[str]:
        """
        Simple whitespace tokenizer with lowercasing.

        Args:
            text: Input text

        Returns:
            List of tokens
        """
        return text.lower().split()

    def _hash_token_to_index(self, token: str) -> int:
        """
        Hash token to embedding dimension index.

        Args:
            token: Token string

        Returns:
            Index in [0, dim)
        """
        # Use SHA256 for stable, collision-resistant hashing
        hash_input = f"{self.seed}:{token}"
        hash_digest = hashlib.sha256(hash_input.encode("utf-8")).hexdigest()
        hash_int = int(hash_digest, 16)
        return hash_int % self.dim

    def _embed_single(self, text: str) -> np.ndarray:
        """
        Embed single text into dense vector.

        Args:
            text: Input text

        Returns:
            L2-normalized embedding of shape (dim,)
        """
        tokens = self._tokenize(text)

        # Build TF vector
        vec = np.zeros(self.dim, dtype=np.float64)
        for token in tokens:
            idx = self._hash_token_to_index(token)
            vec[idx] += 1.0

        # L2 normalize
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm

        return vec

    def embed(self, text: Union[str, List[str]]) -> Union[np.ndarray, List[np.ndarray]]:
        """
        Embed text(s) into dense vector(s).

        Args:
            text: Single text string or list of text strings

        Returns:
            Single embedding (dim,) or list of embeddings

        Examples:
            >>> embedder = DeterministicEmbedder(dim=64, seed=42)
            >>> emb = embedder.embed("climate change")
            >>> emb.shape
            (64,)
            >>> embs = embedder.embed(["climate", "governance"])
            >>> len(embs)
            2
        """
        if isinstance(text, str):
            return self._embed_single(text)
        else:
            return [self._embed_single(t) for t in text]
