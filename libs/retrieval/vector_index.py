"""
Vector Index: In-Memory Cosine KNN

Implements deterministic cosine similarity KNN retrieval with:
- Stable ordering by (-score, id)
- Metadata filtering (where clause)
- Dimension validation
- No external dependencies

SCA v13.8 Compliance:
- Deterministic: Stable tie-breaking
- No network: In-memory only
- Type safety: 100% annotated
"""

import numpy as np
from typing import List, Tuple, Dict, Any, Optional


class VectorIndex:
    """In-memory vector index with cosine similarity KNN."""

    def __init__(self, dim: int) -> None:
        """
        Initialize vector index.

        Args:
            dim: Embedding dimension

        Raises:
            ValueError: If dim <= 0
        """
        if dim <= 0:
            raise ValueError(f"dim must be > 0, got {dim}")

        self.dim = dim
        self.vectors: Dict[str, np.ndarray] = {}
        self.metadata: Dict[str, Dict[str, Any]] = {}

    def add(
        self,
        doc_id: str,
        vector: np.ndarray,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Add document vector to index.

        Args:
            doc_id: Document identifier
            vector: Embedding vector of shape (dim,)
            metadata: Optional metadata dict

        Raises:
            ValueError: If vector dimension mismatch
        """
        if vector.shape[0] != self.dim:
            raise ValueError(
                f"Vector dimension {vector.shape[0]} != index dimension {self.dim}"
            )

        self.vectors[doc_id] = vector
        self.metadata[doc_id] = metadata or {}

    def _cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """
        Compute cosine similarity between two vectors.

        Args:
            vec1: First vector (normalized)
            vec2: Second vector (normalized)

        Returns:
            Cosine similarity in [-1, 1]
        """
        # Assume vectors are already L2-normalized
        return float(np.dot(vec1, vec2))

    def _matches_where(
        self,
        doc_id: str,
        where: Optional[Dict[str, Any]]
    ) -> bool:
        """
        Check if document matches where filter.

        Args:
            doc_id: Document identifier
            where: Filter dict (key: value pairs)

        Returns:
            True if all filters match
        """
        if where is None:
            return True

        doc_meta = self.metadata.get(doc_id, {})
        for key, value in where.items():
            if doc_meta.get(key) != value:
                return False
        return True

    def knn(
        self,
        query_vec: np.ndarray,
        k: int,
        where: Optional[Dict[str, Any]] = None
    ) -> List[Tuple[str, float]]:
        """
        Find k nearest neighbors by cosine similarity.

        Args:
            query_vec: Query embedding of shape (dim,)
            k: Number of neighbors to return
            where: Optional metadata filter

        Returns:
            List of (doc_id, score) tuples, sorted by (-score, id)

        Raises:
            ValueError: If query_vec dimension mismatch or k < 0
        """
        if query_vec.shape[0] != self.dim:
            raise ValueError(
                f"Query dimension {query_vec.shape[0]} != index dimension {self.dim}"
            )

        if k <= 0:
            return []

        # Compute similarities for all docs matching where filter
        scores: List[Tuple[str, float]] = []
        for doc_id, doc_vec in self.vectors.items():
            if not self._matches_where(doc_id, where):
                continue

            sim = self._cosine_similarity(query_vec, doc_vec)
            scores.append((doc_id, sim))

        # Sort by (-score, id) for stable ordering
        scores.sort(key=lambda x: (-x[1], x[0]))

        # Return top-k
        return scores[:k]
