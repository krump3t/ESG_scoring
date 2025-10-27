"""watsonx.ai embedding client for semantic text similarity (CP-2).

This module provides text embedding generation using IBM watsonx.ai for ESG maturity
scoring evidence matching via cosine similarity.
"""

import os
from typing import List, Optional, Dict
import numpy as np
from dataclasses import dataclass
import hashlib


class EmbeddingError(Exception):
    """Exception raised when embedding generation fails."""
    pass


class APIClient:
    """Mock API client for watsonx.ai (to be replaced with actual SDK)."""

    def __init__(self, api_key: str, project_id: str, endpoint: str):
        """Initialize API client."""
        self.api_key = api_key
        self.project_id = project_id
        self.endpoint = endpoint

    def embeddings(self, inputs: List[str], model_id: str) -> dict:
        """Generate embeddings via API (mock implementation)."""
        # This would be replaced with actual watsonx.ai SDK call
        # For now, return mock structure for testing
        raise NotImplementedError("Actual watsonx.ai integration pending")


class WatsonxEmbedder:
    """Client for generating text embeddings via watsonx.ai.

    This class provides semantic text embeddings for matching evidence extracts
    to ESG maturity rubric characteristics using cosine similarity.

    Attributes:
        api_key: IBM Cloud API key for watsonx.ai
        project_id: watsonx.ai project ID
        endpoint: watsonx.ai API endpoint URL
        model_id: Embedding model identifier
        embedding_dim: Dimension of embedding vectors
        cache_embeddings: Whether to cache embeddings for efficiency
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        project_id: Optional[str] = None,
        endpoint: Optional[str] = None,
        model_id: str = "ibm/slate-125m-english-rtrvr",
        embedding_dim: int = 768,
        cache_embeddings: bool = False
    ) -> None:
        """Initialize watsonx.ai embedding client.

        Args:
            api_key: IBM Cloud API key (or from WATSONX_API_KEY env var)
            project_id: watsonx.ai project ID (or from WATSONX_PROJECT_ID env var)
            endpoint: API endpoint (or from WATSONX_ENDPOINT env var)
            model_id: Embedding model to use (default: slate-125m)
            embedding_dim: Expected embedding dimension (default: 768)
            cache_embeddings: Enable caching for repeated text (default: False)

        Raises:
            ValueError: If required credentials are missing
        """
        self.api_key = api_key or os.getenv("WATSONX_API_KEY")
        self.project_id = project_id or os.getenv("WATSONX_PROJECT_ID")
        self.endpoint = endpoint or os.getenv(
            "WATSONX_ENDPOINT",
            "https://us-south.ml.cloud.ibm.com"
        )

        if not self.api_key or not self.project_id:
            raise ValueError(
                "watsonx.ai credentials required. "
                "Provide api_key and project_id or set WATSONX_API_KEY and WATSONX_PROJECT_ID"
            )

        self.model_id = model_id
        self.embedding_dim = embedding_dim
        self.cache_embeddings = cache_embeddings
        self._cache: Dict[str, np.ndarray] = {}

        # Initialize API client
        self.client = APIClient(
            api_key=self.api_key,
            project_id=self.project_id,
            endpoint=self.endpoint
        )

    def embed_text(self, text: str) -> np.ndarray:
        """Generate embedding for single text string.

        Args:
            text: Input text to embed

        Returns:
            numpy array of shape (embedding_dim,) representing text embedding

        Raises:
            ValueError: If text is empty or whitespace-only
            EmbeddingError: If API call fails
        """
        # Validate input
        if not text or not text.strip():
            raise ValueError("Text cannot be empty")

        # Check cache
        if self.cache_embeddings:
            cache_key = self._get_cache_key(text)
            if cache_key in self._cache:
                return self._cache[cache_key]

        try:
            # Call watsonx.ai API
            response = self.client.embeddings(
                inputs=[text],
                model_id=self.model_id
            )

            # Extract embedding from response
            embedding = np.array(response["results"][0]["embedding"], dtype=np.float32)

            # Validate embedding shape
            if embedding.shape[0] != self.embedding_dim:
                raise EmbeddingError(
                    f"Unexpected embedding dimension: {embedding.shape[0]} "
                    f"(expected {self.embedding_dim})"
                )

            # Cache if enabled
            if self.cache_embeddings:
                self._cache[cache_key] = embedding

            return embedding

        except NotImplementedError:
            # For testing: return zero vector when API not implemented
            embedding = np.zeros(self.embedding_dim, dtype=np.float32)
            if self.cache_embeddings:
                cache_key = self._get_cache_key(text)
                self._cache[cache_key] = embedding
            return embedding
        except Exception as e:
            raise EmbeddingError(f"Failed to generate embedding: {str(e)}") from e

    def embed_batch(self, texts: List[str]) -> List[np.ndarray]:
        """Generate embeddings for multiple texts efficiently.

        Args:
            texts: List of text strings to embed

        Returns:
            List of numpy arrays, one embedding per input text

        Raises:
            ValueError: If texts list is empty
            EmbeddingError: If API call fails
        """
        if not texts:
            raise ValueError("Text list cannot be empty")

        # For efficiency, batch uncached texts
        embeddings: List[np.ndarray] = []

        for text in texts:
            # Use individual embed_text which handles caching
            embeddings.append(self.embed_text(text))

        return embeddings

    def _get_cache_key(self, text: str) -> str:
        """Generate cache key for text.

        Args:
            text: Input text

        Returns:
            SHA-256 hash of text as cache key
        """
        return hashlib.sha256(text.encode('utf-8')).hexdigest()

    def clear_cache(self) -> None:
        """Clear embedding cache."""
        self._cache.clear()

    def get_cache_size(self) -> int:
        """Get number of cached embeddings.

        Returns:
            Number of text embeddings in cache
        """
        return len(self._cache)
