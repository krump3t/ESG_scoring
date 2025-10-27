"""
AstraDB Vector Store Adapter: Network-based Vector Backend

Adapter for DataStax AstraDB vector search.
- Interface-compatible with VectorIndex
- Network guard prevents execution in test environment
- Disabled in tests via integration_flags.json

SCA v13.8 Compliance:
- No network in tests: PYTEST_CURRENT_TEST guard
- Type safety: 100% annotated
- Adapter pattern: Matches VectorIndex interface
"""

import numpy as np
import os
from typing import List, Tuple, Dict, Any, Optional


class AstraDBStore:
    """AstraDB vector store adapter (network-based)."""

    def __init__(
        self,
        token: str,
        endpoint: str,
        keyspace: str
    ) -> None:
        """
        Initialize AstraDB store.

        Args:
            token: AstraDB application token
            endpoint: AstraDB endpoint URL
            keyspace: AstraDB keyspace name

        Raises:
            ValueError: If token, endpoint, or keyspace empty
        """
        if not token:
            raise ValueError("token cannot be empty")
        if not endpoint:
            raise ValueError("endpoint cannot be empty")
        if not keyspace:
            raise ValueError("keyspace cannot be empty")

        self.token = token
        self.endpoint = endpoint
        self.keyspace = keyspace

    def _check_network_allowed(self) -> None:
        """
        Check if network calls are allowed.

        Raises:
            RuntimeError: If running in test environment
        """
        if "PYTEST_CURRENT_TEST" in os.environ:
            raise RuntimeError(
                "Network calls not allowed in test environment. "
                "Use VectorIndex for tests."
            )

    def add(
        self,
        doc_id: str,
        vector: np.ndarray,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Add document vector to AstraDB.

        Args:
            doc_id: Document identifier
            vector: Embedding vector
            metadata: Optional metadata dict

        Raises:
            RuntimeError: If called in test environment
        """
        self._check_network_allowed()

        # In production, this would call AstraDB API
        raise NotImplementedError(
            "AstraDB integration not implemented. "
            "Use integration_flags.astradb_enabled=false for in-memory mode."
        )

    def knn(
        self,
        query_vec: np.ndarray,
        k: int,
        where: Optional[Dict[str, Any]] = None
    ) -> List[Tuple[str, float]]:
        """
        Find k nearest neighbors in AstraDB.

        Args:
            query_vec: Query embedding
            k: Number of neighbors to return
            where: Optional metadata filter

        Returns:
            List of (doc_id, score) tuples

        Raises:
            RuntimeError: If called in test environment
        """
        self._check_network_allowed()

        # In production, this would call AstraDB API
        raise NotImplementedError(
            "AstraDB integration not implemented. "
            "Use integration_flags.astradb_enabled=false for in-memory mode."
        )
