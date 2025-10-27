"""
Watsonx Embedder Adapter: Network-based Embedding Service

Adapter for IBM watsonx embedding API.
- Interface-compatible with DeterministicEmbedder
- Network guard prevents execution in test environment
- Disabled in tests via integration_flags.json

SCA v13.8 Compliance:
- No network in tests: PYTEST_CURRENT_TEST guard
- Type safety: 100% annotated
- Adapter pattern: Matches DeterministicEmbedder interface
"""

import numpy as np
import os
from typing import Union, List


class WatsonxEmbedder:
    """Watsonx embedding service adapter (network-based)."""

    def __init__(
        self,
        api_key: str,
        endpoint: str,
        model_id: str
    ) -> None:
        """
        Initialize watsonx embedder.

        Args:
            api_key: Watsonx API key
            endpoint: Watsonx API endpoint URL
            model_id: Embedding model identifier

        Raises:
            ValueError: If api_key, endpoint, or model_id empty
            ValueError: If endpoint is not a valid URL
        """
        if not api_key:
            raise ValueError("api_key cannot be empty")
        if not endpoint:
            raise ValueError("endpoint cannot be empty")
        if not model_id:
            raise ValueError("model_id cannot be empty")

        # Validate endpoint is a URL
        if not endpoint.startswith("http://") and not endpoint.startswith("https://"):
            raise ValueError(f"endpoint must be a valid URL, got: {endpoint}")

        self.api_key = api_key
        self.endpoint = endpoint
        self.model_id = model_id

    def _check_network_allowed(self) -> None:
        """
        Check if network calls are allowed.

        Raises:
            RuntimeError: If running in test environment
        """
        if "PYTEST_CURRENT_TEST" in os.environ:
            raise RuntimeError(
                "Network calls not allowed in test environment. "
                "Use DeterministicEmbedder for tests."
            )

    def embed(self, text: Union[str, List[str]]) -> Union[np.ndarray, List[np.ndarray]]:
        """
        Embed text(s) using watsonx API.

        Args:
            text: Single text string or list of text strings

        Returns:
            Single embedding (dim,) or list of embeddings

        Raises:
            RuntimeError: If called in test environment
        """
        self._check_network_allowed()

        # In production, this would call watsonx API
        # For now, raise to prevent accidental network usage
        raise NotImplementedError(
            "Watsonx API integration not implemented. "
            "Use integration_flags.watsonx_enabled=false for deterministic mode."
        )
