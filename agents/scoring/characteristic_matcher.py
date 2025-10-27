"""Semantic matching of evidence to rubric characteristics (CP-2).

This module uses watsonx.ai embeddings and cosine similarity to match evidence
extracts to the most relevant ESG maturity characteristics.
"""

from dataclasses import dataclass, field
from typing import List, Tuple, Dict, Optional
import numpy as np

from agents.embedding.watsonx_embedder import WatsonxEmbedder
from agents.scoring.rubric_models import StageCharacteristic, MaturityRubric


@dataclass
class MatchResult:
    """Result of matching evidence to characteristic.

    Attributes:
        characteristic: Matched rubric characteristic
        similarity_score: Cosine similarity score (0-1)
        evidence_extract: Original evidence text
    """
    characteristic: StageCharacteristic
    similarity_score: float
    evidence_extract: str

    def __post_init__(self) -> None:
        """Validate match result fields."""
        if not (0.0 <= self.similarity_score <= 1.0):
            raise ValueError(
                f"Similarity score must be between 0 and 1, "
                f"got {self.similarity_score}"
            )


class CharacteristicMatcher:
    """Matcher for evidence extracts to rubric characteristics via semantic similarity.

    Uses watsonx.ai embeddings and cosine similarity to find the best-matching
    characteristic for each evidence extract, enabling automated ESG maturity scoring.

    Attributes:
        embedder: watsonx.ai embedding client
        similarity_threshold: Minimum similarity for valid match (default: 0.6)
        cache_embeddings: Whether to cache characteristic embeddings
    """

    def __init__(
        self,
        embedder: WatsonxEmbedder,
        similarity_threshold: float = 0.6,
        cache_embeddings: bool = True
    ) -> None:
        """Initialize characteristic matcher.

        Args:
            embedder: Configured watsonx.ai embedder
            similarity_threshold: Minimum similarity score for valid match
            cache_embeddings: Cache characteristic embeddings for efficiency

        Raises:
            ValueError: If similarity_threshold not in range [0, 1]
        """
        if not (0.0 <= similarity_threshold <= 1.0):
            raise ValueError(
                f"Similarity threshold must be between 0 and 1, "
                f"got {similarity_threshold}"
            )

        self.embedder = embedder
        self.similarity_threshold = similarity_threshold
        self.cache_embeddings = cache_embeddings
        self._characteristic_cache: Dict[str, np.ndarray] = {}

    def match_evidence_to_characteristic(
        self,
        evidence_extract: str,
        theme: str,
        rubric: MaturityRubric
    ) -> MatchResult:
        """Match evidence extract to best-fit characteristic via cosine similarity.

        Args:
            evidence_extract: Text evidence from sustainability report
            theme: Theme ID (e.g., "target_setting")
            rubric: Complete maturity rubric

        Returns:
            MatchResult containing best-matching characteristic and similarity score

        Raises:
            ValueError: If evidence is empty or theme not found in rubric
        """
        # Validate inputs
        if not evidence_extract or not evidence_extract.strip():
            raise ValueError("Evidence extract cannot be empty")

        if theme not in rubric.themes:
            raise ValueError(f"Theme '{theme}' not found in rubric")

        # Get all characteristics for theme
        theme_rubric = rubric.themes[theme]
        all_characteristics = theme_rubric.get_all_characteristics()

        if not all_characteristics:
            raise ValueError(f"No characteristics found for theme '{theme}'")

        # Generate embedding for evidence
        evidence_embedding = self.embedder.embed_text(evidence_extract)

        # Find best-matching characteristic
        best_match: Optional[Tuple[StageCharacteristic, float]] = None
        best_similarity = -1.0

        for characteristic in all_characteristics:
            # Get or generate characteristic embedding
            char_embedding = self._get_characteristic_embedding(characteristic)

            # Calculate cosine similarity
            similarity = self._cosine_similarity(evidence_embedding, char_embedding)

            if similarity > best_similarity:
                best_similarity = similarity
                best_match = (characteristic, similarity)

        if best_match is None:
            raise RuntimeError(
                f"Failed to find match for evidence in theme '{theme}'"
            )

        return MatchResult(
            characteristic=best_match[0],
            similarity_score=best_match[1],
            evidence_extract=evidence_extract
        )

    def match_batch(
        self,
        evidence_extracts: List[str],
        theme: str,
        rubric: MaturityRubric
    ) -> List[MatchResult]:
        """Match multiple evidence extracts efficiently.

        Args:
            evidence_extracts: List of evidence texts
            theme: Theme ID
            rubric: Maturity rubric

        Returns:
            List of MatchResults, one per evidence extract

        Raises:
            ValueError: If evidence_extracts is empty
        """
        if not evidence_extracts:
            raise ValueError("Evidence extracts list cannot be empty")

        results: List[MatchResult] = []
        for evidence in evidence_extracts:
            result = self.match_evidence_to_characteristic(
                evidence_extract=evidence,
                theme=theme,
                rubric=rubric
            )
            results.append(result)

        return results

    def _get_characteristic_embedding(
        self,
        characteristic: StageCharacteristic
    ) -> np.ndarray:
        """Get embedding for characteristic (with caching).

        Args:
            characteristic: Rubric characteristic

        Returns:
            Embedding vector for characteristic description
        """
        # Generate cache key from characteristic
        cache_key = f"{characteristic.theme}_{characteristic.stage}_{characteristic.description}"

        # Check cache
        if self.cache_embeddings and cache_key in self._characteristic_cache:
            return self._characteristic_cache[cache_key]

        # Generate embedding
        embedding = self.embedder.embed_text(characteristic.description)

        # Cache if enabled
        if self.cache_embeddings:
            self._characteristic_cache[cache_key] = embedding

        return embedding

    def _cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """Calculate cosine similarity between two vectors.

        Args:
            vec1: First embedding vector
            vec2: Second embedding vector

        Returns:
            Cosine similarity score in range [-1, 1]
            (1 = identical, 0 = orthogonal, -1 = opposite)
        """
        # Normalize vectors to unit length
        vec1_norm = vec1 / (np.linalg.norm(vec1) + 1e-10)
        vec2_norm = vec2 / (np.linalg.norm(vec2) + 1e-10)

        # Dot product of normalized vectors = cosine similarity
        similarity = np.dot(vec1_norm, vec2_norm)

        return float(similarity)

    def clear_cache(self) -> None:
        """Clear characteristic embedding cache."""
        self._characteristic_cache.clear()

    def get_cache_size(self) -> int:
        """Get number of cached characteristic embeddings.

        Returns:
            Number of characteristics in cache
        """
        return len(self._characteristic_cache)
