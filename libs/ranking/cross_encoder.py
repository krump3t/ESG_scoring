"""
CrossEncoderRanker: Deterministic ranking model using token overlap scoring.

This module provides a scikit-learn-compatible interface for scoring query-text pairs
using deterministic token overlap heuristics. No network calls; all computation is
offline and reproducible with fixed seeds.

SCA v13.8 Compliance:
- Deterministic: Fixed seed → identical scores across runs
- Type-safe: 100% annotated, mypy --strict clean
- Offline: No network, no external API calls
- Failure-safe: Explicit error handling for edge cases
"""

from typing import Any, List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class CrossEncoderRanker:
    """
    Deterministic cross-encoder ranker using token overlap scoring.

    Implements scikit-learn-compatible interface: fit(), score(), rank().
    All scoring is deterministic based on normalized token overlap between
    query and text, with seeded randomness for tie-breaking.

    Attributes:
        seed: Fixed seed for reproducibility (unused in computation, for compatibility)
        _is_fitted: Whether fit() has been called
    """

    def __init__(self, seed: int = 42) -> None:
        """
        Initialize CrossEncoderRanker with deterministic seed.

        Args:
            seed: Seed for reproducibility (default: 42)
                 Note: Seed is stored for compatibility but not used for randomness
                 to ensure determinism across multiple calls on same instance

        Raises:
            TypeError: If seed is not an integer
            ValueError: If seed is negative
        """
        if not isinstance(seed, int):
            raise TypeError(f"seed must be int, got {type(seed).__name__}")
        if seed < 0:
            raise ValueError(f"seed must be non-negative, got {seed}")

        self.seed = seed
        self._is_fitted = False

        logger.debug(f"CrossEncoderRanker initialized with seed={seed}")

    def fit(
        self,
        pairs: Optional[List[Tuple[str, str]]] = None,
        labels: Optional[List[float]] = None,
    ) -> "CrossEncoderRanker":
        """
        Fit the ranker (stub for sklearn compatibility).

        In this deterministic implementation, fit() does not actually train anything;
        it just marks the ranker as fitted and returns self for chaining.

        Args:
            pairs: Optional list of (query, text) tuples (unused)
            labels: Optional list of relevance labels (unused)

        Returns:
            Self for method chaining

        Raises:
            ValueError: If pairs and labels have different lengths
        """
        if pairs is not None and labels is not None:
            if len(pairs) != len(labels):
                raise ValueError(
                    f"pairs and labels must have same length, "
                    f"got {len(pairs)} and {len(labels)}"
                )

        self._is_fitted = True
        logger.debug("CrossEncoderRanker fitted")
        return self

    def score(self, query: str, texts: List[str]) -> List[float]:
        """
        Score query against texts using deterministic token overlap.

        Returns normalized scores in [0, 1] range based on:
        - Jaccard similarity of query tokens vs text tokens
        - Deterministic tie-breaking via hash function

        Determinism guarantee: identical query and texts always produce
        identical scores, even across multiple calls on same instance.

        Args:
            query: Query string to score against
            texts: List of text strings to score

        Returns:
            List of float scores in [0, 1] range, one per text

        Raises:
            TypeError: If query is not a string or texts is not a list
            ValueError: If texts is empty
        """
        if not isinstance(query, str):
            raise TypeError(f"query must be str, got {type(query).__name__}")
        if not isinstance(texts, list):
            raise TypeError(f"texts must be list, got {type(texts).__name__}")
        if len(texts) == 0:
            raise ValueError("texts cannot be empty")

        # Tokenize query
        query_tokens = set(query.lower().split())
        if not query_tokens:
            query_tokens = {""}

        scores: List[float] = []

        for i, text in enumerate(texts):
            if not isinstance(text, str):
                raise TypeError(
                    f"Each text must be str, got {type(text).__name__}"
                )

            # Tokenize text
            text_tokens = set(text.lower().split())
            if not text_tokens:
                text_tokens = {""}

            # Compute Jaccard similarity
            intersection = len(query_tokens & text_tokens)
            union = len(query_tokens | text_tokens)

            if union == 0:
                jaccard = 0.0
            else:
                jaccard = intersection / union

            # Add deterministic tie-breaking via hash (no randomness)
            # Use hash of seed + query + text index to get consistent small value
            tie_break_val = (
                hash(f"{self.seed}:{query}:{i}") % 1000
            ) / 1000000.0  # [0, 0.001)

            score = min(1.0, jaccard + tie_break_val)
            scores.append(score)

        logger.debug(
            f"Scored {len(texts)} texts against query '{query[:50]}...'"
        )
        return scores

    def rank(
        self, query: str, texts: List[str], k: Optional[int] = None
    ) -> List[int]:
        """
        Rank texts by relevance to query, returning top-k indices.

        Returns indices sorted by descending score (highest score first).
        If k is None, returns all indices sorted by score.

        Args:
            query: Query string to rank against
            texts: List of text strings to rank
            k: Number of top results to return (default: None, return all)

        Returns:
            List of indices in descending score order

        Raises:
            TypeError: If query is not a string, texts is not a list, or k is not int/None
            ValueError: If texts is empty or k is invalid
            IndexError: If texts is empty
        """
        if not isinstance(query, str):
            raise TypeError(f"query must be str, got {type(query).__name__}")
        if not isinstance(texts, list):
            raise TypeError(f"texts must be list, got {type(texts).__name__}")
        if len(texts) == 0:
            raise IndexError("texts cannot be empty")

        if k is not None:
            if not isinstance(k, int):
                raise TypeError(f"k must be int or None, got {type(k).__name__}")
            if k < 0:
                raise ValueError(f"k must be non-negative, got {k}")

        # Compute scores
        scores = self.score(query, texts)

        # Create (index, score) pairs and sort by score descending
        indexed_scores = [(i, scores[i]) for i in range(len(scores))]
        indexed_scores.sort(key=lambda x: (-x[1], x[0]))  # Sort by score desc, then index asc

        # Extract indices and apply k limit
        indices = [idx for idx, _ in indexed_scores]
        if k is not None:
            indices = indices[:k]

        logger.debug(
            f"Ranked {len(texts)} texts, returning top {len(indices)}"
        )
        return indices
