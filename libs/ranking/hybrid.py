"""
Hybrid Ranking: Alpha-weighted fusion of lexical and cross-encoder scores.

This module provides a deterministic hybrid ranking function that combines:
1. Lexical scores (BM25/TF-IDF precomputed in candidate metadata)
2. Cross-encoder scores (computed on-demand by ranking model)

Final score = α·lex + (1−α)·ce, with deterministic tie-breaking.

SCA v13.8 Compliance:
- Deterministic: Same inputs → same outputs across runs
- Type-safe: 100% annotated, mypy --strict clean
- Offline: All computation local, no network calls
- Property-based: Tested with Hypothesis for edge cases
"""

from typing import Dict, List, Tuple, Any
import logging

logger = logging.getLogger(__name__)


def hybrid_rank(
    query: str,
    candidates: List[Tuple[str, Dict[str, Any]]],
    *,
    weights: Dict[str, float],
    model: Any,
    k: int,
) -> List[int]:
    """
    Hybrid ranking: fuse lexical + cross-encoder scores with alpha weighting.

    Combines precomputed lexical scores (in candidate metadata) with
    cross-encoder scores from the ranking model. Final score computed as:

        final = α·lex + (1−α)·ce

    where α = weights["lex"]. Ties broken by (lex desc, ce desc, doc_id asc).

    Args:
        query: Query string for cross-encoder scoring
        candidates: List of (text, metadata) tuples
                   metadata must include "lex" (float) and "doc_id" (int)
        weights: Dict with key "lex" mapping to alpha in [0, 1]
        model: CrossEncoderRanker instance with score() method
        k: Number of top results to return

    Returns:
        List of indices into candidates, sorted by final score (descending)

    Raises:
        TypeError: If arguments have wrong types
        ValueError: If weights invalid, candidates empty, or k invalid
        KeyError: If candidate metadata missing required fields
        IndexError: If candidates list is empty
    """
    # Type and value validation
    if not isinstance(query, str):
        raise TypeError(f"query must be str, got {type(query).__name__}")

    if not isinstance(candidates, list):
        raise TypeError(f"candidates must be list, got {type(candidates).__name__}")

    if len(candidates) == 0:
        raise IndexError("candidates cannot be empty")

    if not isinstance(weights, dict):
        raise TypeError(f"weights must be dict, got {type(weights).__name__}")

    if "lex" not in weights:
        raise KeyError("weights must contain 'lex' key")

    alpha = weights["lex"]
    if not isinstance(alpha, (int, float)):
        raise TypeError(f"weights['lex'] must be numeric, got {type(alpha).__name__}")

    if not (0.0 <= alpha <= 1.0):
        raise ValueError(f"weights['lex'] must be in [0, 1], got {alpha}")

    if not isinstance(k, int):
        raise TypeError(f"k must be int, got {type(k).__name__}")

    if k < 0:
        raise ValueError(f"k must be non-negative, got {k}")

    if model is None:
        raise ValueError("model cannot be None")

    # Validate candidates structure
    for i, candidate in enumerate(candidates):
        if not isinstance(candidate, tuple) or len(candidate) != 2:
            raise ValueError(
                f"candidate {i} must be (text, metadata) tuple, "
                f"got {type(candidate).__name__}"
            )

        text, metadata = candidate
        if not isinstance(text, str):
            raise TypeError(
                f"candidate {i} text must be str, got {type(text).__name__}"
            )

        if not isinstance(metadata, dict):
            raise TypeError(
                f"candidate {i} metadata must be dict, "
                f"got {type(metadata).__name__}"
            )

        if "lex" not in metadata:
            raise KeyError(f"candidate {i} metadata missing 'lex' field")

        if "doc_id" not in metadata:
            raise KeyError(f"candidate {i} metadata missing 'doc_id' field")

        lex_score = metadata["lex"]
        if not isinstance(lex_score, (int, float)):
            raise TypeError(
                f"candidate {i} lex score must be numeric, "
                f"got {type(lex_score).__name__}"
            )

        doc_id = metadata["doc_id"]
        if not isinstance(doc_id, (int, str)):
            raise TypeError(
                f"candidate {i} doc_id must be int or str, "
                f"got {type(doc_id).__name__}"
            )

    # Extract texts for cross-encoder scoring
    texts = [candidate[0] for candidate in candidates]

    # Compute cross-encoder scores
    try:
        ce_scores = model.score(query, texts)
    except Exception as e:
        raise RuntimeError(
            f"Failed to compute cross-encoder scores: {e}"
        ) from e

    if len(ce_scores) != len(candidates):
        raise ValueError(
            f"model.score() returned {len(ce_scores)} scores, "
            f"expected {len(candidates)}"
        )

    # Compute final scores: α·lex + (1−α)·ce
    final_scores: List[float] = []
    for i, (candidate, ce_score) in enumerate(zip(candidates, ce_scores)):
        _, metadata = candidate
        lex_score = metadata["lex"]

        # Normalize scores to [0, 1] if needed
        lex_norm = min(1.0, max(0.0, lex_score))
        ce_norm = min(1.0, max(0.0, ce_score))

        # Fuse with alpha weighting
        final = alpha * lex_norm + (1.0 - alpha) * ce_norm
        final_scores.append(final)

    # Create (index, final_score, lex_score, ce_score, doc_id) tuples for sorting
    scored_candidates = []
    for i, (candidate, ce_score, final_score) in enumerate(
        zip(candidates, ce_scores, final_scores)
    ):
        _, metadata = candidate
        lex_score = metadata["lex"]
        doc_id = metadata["doc_id"]

        scored_candidates.append(
            (i, final_score, lex_score, ce_score, doc_id)
        )

    # Sort by: final_score DESC, lex_score DESC, ce_score DESC, doc_id ASC
    # This ensures deterministic tie-breaking
    scored_candidates.sort(
        key=lambda x: (-x[1], -x[2], -x[3], x[4] if isinstance(x[4], int) else str(x[4]))
    )

    # Extract top-k indices
    result = [idx for idx, _, _, _, _ in scored_candidates[:k]]

    logger.debug(
        f"Hybrid ranked {len(candidates)} candidates with α={alpha}, "
        f"returning top {len(result)}"
    )
    return result
