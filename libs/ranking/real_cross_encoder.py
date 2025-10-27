"""
Phase 4a: Real Sentence-BERT Cross-Encoder Ranker

Implements real cross-encoder/ms-marco-MiniLM-L-6-v2 model for ESG document ranking.
Replaces lexical simulation with authentic neural re-ranking.

SCA v13.8 Compliance:
- Authentic Computation: Real Sentence-BERT inference (no mocks)
- Determinism: torch.manual_seed(seed) for reproducible outputs
- Type Safety: 100% type hints with mypy --strict
- Failure Paths: Explicit exception handling for model loading/inference failures

Model Details:
- Name: cross-encoder/ms-marco-MiniLM-L-6-v2
- Architecture: BERT-based cross-encoder
- Training: MS MARCO passage ranking dataset
- Task: Query-document relevance scoring
"""

import logging
from typing import List, Tuple, Optional
import torch
from sentence_transformers import CrossEncoder
import numpy as np

logger = logging.getLogger(__name__)


class RealCrossEncoderRanker:
    """
    Real Sentence-BERT Cross-Encoder for ESG document re-ranking.

    Uses cross-encoder/ms-marco-MiniLM-L-6-v2 for neural relevance scoring.
    Provides deterministic inference via seeded random state.

    Attributes:
        model_name: HuggingFace model identifier
        seed: Random seed for deterministic inference
        device: Computation device (CPU or CUDA)
        model: Loaded CrossEncoder model
    """

    def __init__(
        self,
        model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2",
        seed: int = 42,
        device: Optional[str] = None
    ) -> None:
        """
        Initialize real Cross-Encoder model.

        Args:
            model_name: HuggingFace model identifier (default: cross-encoder/ms-marco-MiniLM-L-6-v2)
            seed: Random seed for deterministic inference (default: 42)
            device: Target device ('cpu', 'cuda', or None for auto-detect)

        Raises:
            ValueError: If seed < 0
            RuntimeError: If model loading fails
        """
        # Validate seed
        if seed < 0:
            raise ValueError(f"seed must be non-negative, got {seed}")

        self.model_name = model_name
        self.seed = seed

        # Set device
        if device is None:
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        else:
            self.device = device

        logger.info(
            f"Initializing RealCrossEncoderRanker: model={model_name}, "
            f"seed={seed}, device={self.device}"
        )

        # Set deterministic seed
        torch.manual_seed(seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed(seed)
            torch.backends.cudnn.deterministic = True
            torch.backends.cudnn.benchmark = False

        # Load model
        try:
            self.model = CrossEncoder(model_name, device=self.device)
            logger.info(f"Successfully loaded model: {model_name}")
        except Exception as e:
            logger.error(f"Failed to load model {model_name}: {e}")
            raise RuntimeError(f"Failed to load model {model_name}: {e}") from e

    def score(self, query: str, texts: List[str]) -> List[float]:
        """
        Score documents for relevance to query using real Cross-Encoder.

        Uses model.predict() for neural inference. Normalizes scores to [0, 1]
        via sigmoid activation.

        Args:
            query: User query or search string
            texts: List of document texts to score

        Returns:
            List of normalized relevance scores in [0, 1] range (same order as texts)

        Raises:
            TypeError: If query not str or texts not list
            ValueError: If query empty or texts empty
            RuntimeError: If model inference fails
        """
        # Validate inputs
        if not isinstance(query, str):
            raise TypeError(f"query must be str, got {type(query).__name__}")

        if not isinstance(texts, list):
            raise TypeError(f"texts must be list, got {type(texts).__name__}")

        if not query or len(query.strip()) == 0:
            raise ValueError("query cannot be empty")

        if len(texts) == 0:
            raise ValueError("texts cannot be empty")

        # Validate all texts are strings
        for i, text in enumerate(texts):
            if not isinstance(text, str):
                raise TypeError(
                    f"Each text must be str, got {type(text).__name__} at index {i}"
                )

        logger.debug(f"Scoring {len(texts)} documents for query: {query[:50]}...")

        try:
            # Create query-document pairs
            pairs = [(query, text) for text in texts]

            # Real model inference
            raw_scores = self.model.predict(pairs, show_progress_bar=False)

            # Normalize to [0, 1] via sigmoid
            # CrossEncoder outputs logits, sigmoid maps to probability
            normalized_scores = self._sigmoid(raw_scores)

            # Convert to list of floats
            result: List[float] = normalized_scores.tolist()

            logger.info(
                f"Scored {len(texts)} documents: "
                f"mean={np.mean(result):.3f}, std={np.std(result):.3f}"
            )

            return result

        except Exception as e:
            logger.error(f"Model inference failed: {e}")
            raise RuntimeError(f"Model inference failed: {e}") from e

    def rank(
        self,
        query: str,
        texts: List[str],
        top_k: Optional[int] = None
    ) -> List[int]:
        """
        Rank documents by relevance and return top-K indices.

        Args:
            query: User query or search string
            texts: List of document texts to rank
            top_k: Number of top results to return (None = all, default: None)

        Returns:
            List of indices sorted by relevance score descending (length ≤ top_k)

        Raises:
            TypeError: If query not str, texts not list, or top_k not int/None
            ValueError: If query empty, texts empty, or top_k < 0
            IndexError: If texts is empty list
            RuntimeError: If ranking fails
        """
        # Validate inputs
        if not isinstance(query, str):
            raise TypeError(f"query must be str, got {type(query).__name__}")

        if not isinstance(texts, list):
            raise TypeError(f"texts must be list, got {type(texts).__name__}")

        if len(texts) == 0:
            raise IndexError("texts cannot be empty")

        if top_k is not None and not isinstance(top_k, int):
            raise TypeError(f"k must be int or None, got {type(top_k).__name__}")

        if top_k is not None and top_k < 0:
            raise ValueError(f"k must be non-negative, got {top_k}")

        try:
            # Score all documents
            scores = self.score(query, texts)

            # Sort by score descending, return indices
            ranked_indices = sorted(
                range(len(scores)),
                key=lambda i: scores[i],
                reverse=True
            )

            # Apply top-k filtering
            if top_k is not None:
                if top_k == 0:
                    return []
                ranked_indices = ranked_indices[:top_k]

            logger.info(f"Ranked {len(texts)} documents, returning top-{len(ranked_indices)}")

            return ranked_indices

        except (TypeError, ValueError, IndexError):
            raise
        except Exception as e:
            logger.error(f"Ranking failed: {e}")
            raise RuntimeError(f"Ranking failed: {e}") from e

    def rerank(
        self,
        query: str,
        documents: List[str],
        top_k: int = 5,
        threshold: float = 0.0
    ) -> List[Tuple[str, float]]:
        """
        Re-rank documents and return top-K with scores.

        Convenience method compatible with existing CrossEncoderRanker API.

        Args:
            query: User query or search string
            documents: List of document texts to rank
            top_k: Number of top results to return (default: 5)
            threshold: Minimum score threshold (default: 0.0, no filtering)

        Returns:
            List of (document_text, score) tuples, sorted by score descending

        Raises:
            TypeError: If inputs invalid
            ValueError: If query/documents empty or top_k invalid
            RuntimeError: If re-ranking fails
        """
        # Validate top_k
        if top_k <= 0:
            raise ValueError(f"top_k must be > 0, got {top_k}")

        try:
            # Score all documents
            scores = self.score(query, documents)

            # Combine documents with scores
            doc_score_pairs: List[Tuple[str, float]] = list(zip(documents, scores))

            # Sort by score descending
            sorted_pairs = sorted(doc_score_pairs, key=lambda x: x[1], reverse=True)

            # Apply threshold and top-k filtering
            filtered = [
                (doc, score) for doc, score in sorted_pairs
                if score >= threshold
            ]

            result = filtered[:top_k]

            logger.info(
                f"Re-ranked {len(documents)} documents: "
                f"returned top-{len(result)} above threshold {threshold}"
            )

            return result

        except (TypeError, ValueError):
            raise
        except Exception as e:
            logger.error(f"Re-ranking failed: {e}")
            raise RuntimeError(f"Re-ranking failed: {e}") from e

    def _sigmoid(self, x: np.ndarray) -> np.ndarray:
        """
        Sigmoid activation function for score normalization.

        Maps logits to [0, 1] probability range.

        Args:
            x: Input array of logits

        Returns:
            Normalized scores in [0, 1]
        """
        result: np.ndarray = 1.0 / (1.0 + np.exp(-x))
        return result


def create_ranker(
    model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2",
    seed: int = 42
) -> RealCrossEncoderRanker:
    """
    Factory function to create RealCrossEncoderRanker.

    Args:
        model_name: HuggingFace model identifier (default: cross-encoder/ms-marco-MiniLM-L-6-v2)
        seed: Random seed for deterministic inference (default: 42)

    Returns:
        Initialized RealCrossEncoderRanker instance

    Raises:
        ValueError: If seed < 0
        RuntimeError: If model loading fails
    """
    return RealCrossEncoderRanker(model_name=model_name, seed=seed)
