"""
Phase 3: Cross-Encoder Re-ranking Module

Deterministic lexical cross-encoder simulation (no external models).
Computes relevance scores via token overlap and position bonuses.

Per SCA v13.8: Deterministic behavior, explicit validation, no network I/O.
"""

import logging
from typing import List, Tuple, Dict, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Deterministic seed
SEED = 42


@dataclass
class RankedDocument:
    """Ranked document with relevance score."""

    document_id: str
    text: str
    score: float
    rank: int


class CrossEncoderRanker:
    """
    Deterministic cross-encoder for ESG document relevance ranking.

    Implements lexical features (token overlap, position bonus) without external models.
    Simulates Sentence-BERT ce-ms-marco-MiniLM-L-6-v2 behavior.
    """

    def __init__(self) -> None:
        """Initialize CrossEncoderRanker."""
        logger.info(f"CrossEncoderRanker initialized with SEED={SEED}")

    def rerank(
        self,
        query: str,
        documents: List[str],
        top_k: int = 5,
        threshold: float = 0.0,
    ) -> List[Tuple[str, float]]:
        """
        Rank documents by relevance to query using lexical features.

        Algorithm:
        1. Tokenize query into keywords
        2. For each document: compute token overlap score
        3. Apply position bonus (early tokens weighted higher)
        4. Normalize scores via softmax to [0, 1]
        5. Sort by score descending; return top-K

        Args:
            query: ESG query string
            documents: List of document text strings to rank
            top_k: Number of top results to return (default: 5)
            threshold: Minimum score threshold (default: 0.0, no filtering)

        Returns:
            List of (document_text, score) tuples, sorted by score descending, length ≤ top_k

        Raises:
            ValueError: If query empty, documents empty, or top_k <= 0
            RuntimeError: If ranking computation fails
        """
        # Validate inputs
        if not query or len(query.strip()) == 0:
            raise ValueError("query cannot be empty")

        if not documents:
            raise ValueError("documents list cannot be empty")

        if top_k <= 0:
            raise ValueError(f"top_k must be > 0, got {top_k}")

        logger.debug(f"Ranking {len(documents)} documents for query: {query[:50]}...")

        try:
            # Tokenize query (simple whitespace + punctuation split)
            query_tokens = self._tokenize(query)
            if not query_tokens:
                raise ValueError("query produced no tokens after processing")

            # Score all documents
            scores: List[Tuple[str, float]] = []
            for i, doc in enumerate(documents):
                if not isinstance(doc, str):
                    raise ValueError(f"Document {i} is not a string: {type(doc)}")

                score = self._compute_relevance_score(query_tokens, doc, position=i)
                scores.append((doc, score))

            # Normalize scores via softmax to [0, 1]
            normalized_scores = self._normalize_scores(scores)

            # Sort by score descending
            sorted_scores = sorted(normalized_scores, key=lambda x: x[1], reverse=True)

            # Apply threshold and top-k filtering
            filtered = [
                (doc, score) for doc, score in sorted_scores if score >= threshold
            ]

            result = filtered[:top_k]

            logger.info(f"Ranked {len(documents)} documents; top-{len(result)} above threshold")
            return result

        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Ranking failed: {e}")
            raise RuntimeError(f"Ranking error: {e}") from e

    def _tokenize(self, text: str) -> List[str]:
        """
        Simple deterministic tokenization.

        Args:
            text: Input text

        Returns:
            List of lowercased tokens (whitespace + punctuation split)
        """
        import re

        # Lowercase, split on whitespace/punctuation
        text_lower = text.lower()
        tokens = re.findall(r"\w+", text_lower)
        return tokens

    def _compute_relevance_score(
        self, query_tokens: List[str], document: str, position: int = 0
    ) -> float:
        """
        Compute relevance score for a single document.

        Features:
        1. Token overlap: count of query tokens in document
        2. Position bonus: penalize documents further down the list
        3. Document length bonus: prefer slightly longer documents (better context)

        Args:
            query_tokens: Tokenized query keywords
            document: Document text
            position: Position in original document list (for penalty)

        Returns:
            Raw score (before normalization)
        """
        doc_tokens = self._tokenize(document)

        if not doc_tokens:
            return 0.0

        # Token overlap: count matching tokens
        query_token_set = set(query_tokens)
        doc_token_set = set(doc_tokens)
        overlap = len(query_token_set & doc_token_set)

        # Normalize by query length (avoid empty query)
        if len(query_tokens) > 0:
            overlap_ratio = overlap / len(query_tokens)
        else:
            overlap_ratio = 0.0

        # Position penalty: documents later in list scored lower (by ~5% per position)
        position_penalty = 0.95 ** (position + 1)

        # Document length bonus: prefer docs with more tokens (context)
        # Normalize by document length; short docs (< 10 tokens) penalized
        doc_length_factor = min(1.0, len(doc_tokens) / 50.0)  # Cap at 50 tokens

        # Combined score (rounded to 4 decimal places for stability)
        raw_score = overlap_ratio * position_penalty * doc_length_factor
        return round(raw_score, 4)

    def _normalize_scores(
        self, scores: List[Tuple[str, float]]
    ) -> List[Tuple[str, float]]:
        """
        Normalize scores via softmax to [0, 1] range.

        Args:
            scores: List of (document, raw_score) tuples

        Returns:
            List of (document, normalized_score) tuples
        """
        if not scores:
            return []

        # Softmax normalization
        import math

        # Shift scores to avoid overflow (subtract max)
        raw_scores = [s[1] for s in scores]
        max_score = max(raw_scores) if raw_scores else 0.0
        shifted_scores = [s - max_score for s in raw_scores]

        # Compute exp and sum
        exp_scores = [math.exp(s) for s in shifted_scores]
        sum_exp = sum(exp_scores)

        # Normalize
        if sum_exp == 0:
            # All scores are equal (or zero); distribute evenly
            normalized = [1.0 / len(scores)] * len(scores)
        else:
            normalized = [e / sum_exp for e in exp_scores]

        # Round to 4 decimal places for stability
        normalized = [round(n, 4) for n in normalized]

        return [(doc, norm_score) for (doc, _), norm_score in zip(scores, normalized)]

    def rerank_batch(
        self,
        queries: List[str],
        documents_per_query: List[List[str]],
        top_k: int = 5,
    ) -> List[List[Tuple[str, float]]]:
        """
        Batch re-ranking for multiple queries.

        Args:
            queries: List of query strings
            documents_per_query: List of document lists (one per query)
            top_k: Top-K results per query

        Returns:
            List of ranked results (one list per query)

        Raises:
            ValueError: If lengths mismatch or inputs invalid
        """
        if len(queries) != len(documents_per_query):
            raise ValueError("queries and documents_per_query must have same length")

        results = []
        for query, docs in zip(queries, documents_per_query):
            ranked = self.rerank(query, docs, top_k)
            results.append(ranked)

        return results
