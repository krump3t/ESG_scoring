"""
Hybrid Semantic Fusion: α-weighted Lexical + Semantic

Implements deterministic fusion of lexical (BM25/TF-IDF) and semantic (cosine KNN) scores:
- final_score = α * lexical_score + (1-α) * semantic_score
- Default α = 0.6 (60% lexical, 40% semantic)
- Missing IDs filled with 0.0
- Stable ordering by (-score, id)

SCA v13.8 Compliance:
- Deterministic: Fixed α, stable sorting
- No randomness: Pure weighted sum
- Type safety: 100% annotated
"""

from typing import Dict, List, Tuple


def fuse_lex_sem(
    lex_scores: Dict[str, float],
    sem_scores: Dict[str, float],
    alpha: float = 0.6
) -> List[Tuple[str, float]]:
    """
    Fuse lexical and semantic scores with α-weighting.

    Args:
        lex_scores: Lexical scores dict {doc_id: score}
        sem_scores: Semantic scores dict {doc_id: score}
        alpha: Weight for lexical scores (0=pure semantic, 1=pure lexical)

    Returns:
        List of (doc_id, fused_score) tuples, sorted by (-score, id)

    Raises:
        ValueError: If alpha not in [0, 1]

    Examples:
        >>> lex = {"doc1": 0.9, "doc2": 0.7}
        >>> sem = {"doc1": 0.3, "doc2": 0.8}
        >>> results = fuse_lex_sem(lex, sem, alpha=0.6)
        >>> results[0][0]  # Top doc_id
        'doc1'
    """
    if not (0.0 <= alpha <= 1.0):
        raise ValueError(f"alpha must be in [0, 1], got {alpha}")

    # Collect all doc_ids from both score dicts (sorted for deterministic traversal)
    all_ids = sorted(set(lex_scores.keys()) | set(sem_scores.keys()))

    # Compute fused scores
    fused: List[Tuple[str, float]] = []
    for doc_id in all_ids:
        lex_score = lex_scores.get(doc_id, 0.0)
        sem_score = sem_scores.get(doc_id, 0.0)

        final_score = alpha * lex_score + (1.0 - alpha) * sem_score
        fused.append((doc_id, final_score))

    # Sort by (-score, id) for stable ordering
    fused.sort(key=lambda x: (-x[1], x[0]))

    return fused
