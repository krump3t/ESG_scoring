"""Unified hybrid retrieval API integrating BM25 + Vector + RRF.

This module provides a single interface for hybrid retrieval that combines:
- BM25 lexical search (keyword matching)
- Vector semantic search (Astra DB)
- RRF fusion (Reciprocal Rank Fusion)

Task: 033-hybrid-retrieval-fusion (Task 037 remediation)
Critical Path: Yes

FIXED (Task 037):
- Corrected imports: search_vector_astra (was search_astra), rrf_fusion (was fuse_rrf)
- Corrected signatures: BM25 requires (bm25_index, chunks_df), Vector requires (collection, embedding)
- Corrected parameters: RRF uses k_param (was k)
- Removed ALL mocks: Uses real BM25 indices, real embeddings, real Astra connections
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
from rank_bm25 import BM25Okapi

logger = logging.getLogger(__name__)

# Default parameters
DEFAULT_K_BM25 = 40
DEFAULT_K_VEC = 40
DEFAULT_RRF_K = 60


@dataclass
class RetrievalConfig:
    """Configuration for hybrid retrieval.

    Attributes:
        k_bm25: Number of results from BM25 search
        k_vec: Number of results from vector search
        rrf_k: RRF k parameter (fusion constant)
        enable_bm25: Enable BM25 leg
        enable_vector: Enable vector leg
    """
    k_bm25: int = DEFAULT_K_BM25
    k_vec: int = DEFAULT_K_VEC
    rrf_k: int = DEFAULT_RRF_K
    enable_bm25: bool = True
    enable_vector: bool = True

    def __post_init__(self):
        """Validate configuration."""
        if self.k_bm25 <= 0:
            raise ValueError(f"k_bm25 must be positive, got {self.k_bm25}")
        if self.k_vec <= 0:
            raise ValueError(f"k_vec must be positive, got {self.k_vec}")
        if self.rrf_k <= 0:
            raise ValueError(f"rrf_k must be positive, got {self.rrf_k}")
        if not self.enable_bm25 and not self.enable_vector:
            raise ValueError("At least one retrieval method must be enabled")


class HybridRetriever:
    """Unified hybrid retrieval combining BM25 + Vector + RRF.

    This class provides a single API for executing hybrid retrieval
    by orchestrating three components:
    1. BM25 search (lexical matching)
    2. Vector search (semantic similarity via AstraDB)
    3. RRF fusion (combining results)

    Usage (full hybrid mode):
        retriever = HybridRetriever(
            chunks_path="chunks.parquet",
            astra_endpoint="https://...",
            astra_token="AstraCS:...",
            collection_name="chunks"
        )
        results = retriever.retrieve("What are GHG emissions?")

    Usage (BM25-only mode, no Astra required):
        config = RetrievalConfig(enable_vector=False)
        retriever = HybridRetriever(
            chunks_path="chunks.parquet",
            config=config
        )
        results = retriever.retrieve("What are GHG emissions?")

    The retriever can operate in three modes:
    - BM25 only (enable_vector=False) - No Astra required
    - Vector only (enable_bm25=False) - Requires Astra
    - Hybrid (both enabled, default) - Requires Astra
    """

    def __init__(
        self,
        chunks_path: str,
        astra_endpoint: Optional[str] = None,
        astra_token: Optional[str] = None,
        collection_name: str = "chunks",
        embedding_model: str = "sentence-transformers/all-mpnet-base-v2",
        config: Optional[RetrievalConfig] = None
    ):
        """Initialize hybrid retriever with REAL infrastructure.

        Args:
            chunks_path: Path to chunks parquet file
            astra_endpoint: Astra DB endpoint (required if enable_vector=True)
            astra_token: Astra DB token (required if enable_vector=True)
            collection_name: Astra collection name
            embedding_model: Sentence transformer model ID
            config: Optional retrieval configuration

        Raises:
            ValueError: If configuration is invalid or Astra credentials missing when needed
            FileNotFoundError: If chunks file doesn't exist
        """
        self.config = config or RetrievalConfig()

        # Validate chunks file exists
        chunks_file = Path(chunks_path)
        if not chunks_file.exists():
            raise FileNotFoundError(f"Chunks file not found: {chunks_path}")

        # Load chunks DataFrame
        logger.info(f"Loading chunks from {chunks_path}")
        self.chunks_df = pd.read_parquet(chunks_path)
        logger.info(f"Loaded {len(self.chunks_df)} chunks")

        # Build BM25 index (always needed for BM25)
        if self.config.enable_bm25:
            logger.info("Building BM25 index...")
            from libs.retrieval.bm25_search import build_bm25_index
            self.bm25_index, self.tokenized_corpus = build_bm25_index(self.chunks_df)
            logger.info("BM25 index built successfully")
        else:
            self.bm25_index = None
            self.tokenized_corpus = None

        # Connect to Astra and load embedding model (only if vector search enabled)
        if self.config.enable_vector:
            # Check credentials
            if not astra_endpoint or not astra_token:
                # Try environment variables
                astra_endpoint = astra_endpoint or os.getenv('ASTRA_DB_ENDPOINT') or os.getenv('ASTRA_DB_API_ENDPOINT')
                astra_token = astra_token or os.getenv('ASTRA_DB_TOKEN') or os.getenv('ASTRA_DB_APPLICATION_TOKEN')

            if not astra_endpoint or not astra_token:
                raise ValueError(
                    "Astra credentials required when enable_vector=True. "
                    "Provide astra_endpoint + astra_token or set ASTRA_DB_ENDPOINT + ASTRA_DB_TOKEN env vars."
                )

            # Connect to Astra
            logger.info(f"Connecting to Astra DB: {collection_name}")
            from astrapy import DataAPIClient
            client = DataAPIClient(astra_token)
            database = client.get_database_by_api_endpoint(astra_endpoint)
            self.collection = database.get_collection(collection_name)
            logger.info("Astra connection established")

            # Load embedding model
            logger.info(f"Loading embedding model: {embedding_model}")
            from sentence_transformers import SentenceTransformer
            self.embedding_model = SentenceTransformer(embedding_model)
            logger.info("Embedding model loaded")
        else:
            self.collection = None
            self.embedding_model = None

    def retrieve(self, query: str) -> List[Dict[str, Any]]:
        """Execute hybrid retrieval for a query.

        Args:
            query: User query string

        Returns:
            List of retrieved results with scores

        Raises:
            ValueError: If query is empty
            RuntimeError: If retrieval fails
        """
        if not query or not query.strip():
            raise ValueError("Query cannot be empty")

        # Execute enabled retrieval methods
        bm25_results = []
        vector_results = []

        if self.config.enable_bm25:
            bm25_results = self._execute_bm25(query)

        if self.config.enable_vector:
            vector_results = self._execute_vector(query)

        # If only one method enabled, return those results
        if not self.config.enable_bm25:
            return vector_results
        if not self.config.enable_vector:
            return bm25_results

        # Fuse results with RRF
        fused_results = self._execute_fusion(bm25_results, vector_results)
        return fused_results

    def _execute_bm25(self, query: str) -> List[Dict[str, Any]]:
        """Execute BM25 lexical search with REAL BM25 index.

        Args:
            query: User query

        Returns:
            BM25 search results

        Raises:
            RuntimeError: If BM25 search fails
        """
        try:
            from libs.retrieval.bm25_search import search_bm25

            # Call with CORRECT signature: (bm25_index, chunks_df, query, k)
            results = search_bm25(
                self.bm25_index,      # Real BM25 index
                self.chunks_df,       # Real chunks DataFrame
                query,
                k=self.config.k_bm25
            )
            logger.info(f"BM25 search returned {len(results)} results")
            return results

        except Exception as e:
            logger.error(f"BM25 search failed: {e}")
            raise RuntimeError(f"BM25 search failed: {str(e)}")

    def _execute_vector(self, query: str) -> List[Dict[str, Any]]:
        """Execute vector semantic search with REAL Astra and embeddings.

        Args:
            query: User query

        Returns:
            Vector search results

        Raises:
            RuntimeError: If vector search fails
        """
        try:
            # CORRECT import: search_vector_astra (not search_astra)
            from libs.retrieval.vector_search_astra import search_vector_astra

            # Generate REAL embedding
            query_embedding = self.embedding_model.encode(
                [query],
                convert_to_numpy=True,
                normalize_embeddings=True
            )[0]

            # Call with CORRECT signature: (collection, query_embedding, k)
            results = search_vector_astra(
                self.collection,      # Real Astra collection
                query_embedding,      # Real embedding (768-dim numpy array)
                k=self.config.k_vec
            )
            logger.info(f"Vector search returned {len(results)} results")
            return results

        except Exception as e:
            logger.error(f"Vector search failed: {e}")
            raise RuntimeError(f"Vector search failed: {str(e)}")

    def _execute_fusion(
        self,
        bm25_results: List[Dict[str, Any]],
        vector_results: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Fuse BM25 and vector results using REAL RRF.

        Args:
            bm25_results: Results from BM25 search
            vector_results: Results from vector search

        Returns:
            Fused results with RRF scores

        Raises:
            RuntimeError: If fusion fails
        """
        try:
            # CORRECT import: rrf_fusion (not fuse_rrf)
            from libs.fusion.rrf_fusion import rrf_fusion

            # Call with CORRECT parameter name: k_param (not k)
            fused = rrf_fusion(
                bm25_results,
                vector_results,
                k_param=self.config.rrf_k  # CORRECT parameter name
            )
            logger.info(f"RRF fusion produced {len(fused)} results")
            return fused

        except Exception as e:
            logger.error(f"RRF fusion failed: {e}")
            raise RuntimeError(f"RRF fusion failed: {str(e)}")

    def retrieve_batch(self, queries: List[str]) -> List[List[Dict[str, Any]]]:
        """Execute hybrid retrieval for multiple queries.

        Args:
            queries: List of query strings

        Returns:
            List of result lists (one per query)

        Raises:
            ValueError: If queries is empty
        """
        if not queries:
            raise ValueError("Queries list cannot be empty")

        results = []
        for query in queries:
            try:
                query_results = self.retrieve(query)
                results.append(query_results)
            except Exception as e:
                logger.error(f"Retrieval failed for query '{query}': {e}")
                results.append([])  # Return empty results for failed queries

        return results

    def get_stats(self) -> Dict[str, Any]:
        """Get retrieval statistics and configuration.

        Returns:
            Dictionary with config and stats
        """
        return {
            "config": {
                "k_bm25": self.config.k_bm25,
                "k_vec": self.config.k_vec,
                "rrf_k": self.config.rrf_k,
                "enable_bm25": self.config.enable_bm25,
                "enable_vector": self.config.enable_vector
            },
            "mode": self._get_mode(),
            "chunks_loaded": len(self.chunks_df) if self.chunks_df is not None else 0,
            "bm25_ready": self.bm25_index is not None,
            "vector_ready": self.collection is not None
        }

    def _get_mode(self) -> str:
        """Get retrieval mode based on config.

        Returns:
            Mode string (bm25_only|vector_only|hybrid)
        """
        if self.config.enable_bm25 and self.config.enable_vector:
            return "hybrid"
        elif self.config.enable_bm25:
            return "bm25_only"
        else:
            return "vector_only"


# Convenience functions for common use cases

def retrieve_hybrid(
    chunks_path: str,
    query: str,
    astra_endpoint: Optional[str] = None,
    astra_token: Optional[str] = None,
    collection_name: str = "chunks",
    k_bm25: int = DEFAULT_K_BM25,
    k_vec: int = DEFAULT_K_VEC,
    rrf_k: int = DEFAULT_RRF_K
) -> List[Dict[str, Any]]:
    """Convenience function for hybrid retrieval.

    Args:
        chunks_path: Path to chunks parquet
        query: User query
        astra_endpoint: Astra DB endpoint
        astra_token: Astra DB token
        collection_name: Astra collection name
        k_bm25: Number of BM25 results
        k_vec: Number of vector results
        rrf_k: RRF k parameter

    Returns:
        Fused retrieval results
    """
    config = RetrievalConfig(k_bm25=k_bm25, k_vec=k_vec, rrf_k=rrf_k)
    retriever = HybridRetriever(
        chunks_path=chunks_path,
        astra_endpoint=astra_endpoint,
        astra_token=astra_token,
        collection_name=collection_name,
        config=config
    )
    return retriever.retrieve(query)


def retrieve_bm25_only(
    chunks_path: str,
    query: str,
    k: int = DEFAULT_K_BM25
) -> List[Dict[str, Any]]:
    """Convenience function for BM25-only retrieval (no Astra required).

    Args:
        chunks_path: Path to chunks parquet
        query: User query
        k: Number of results

    Returns:
        BM25 results
    """
    config = RetrievalConfig(k_bm25=k, enable_vector=False)
    retriever = HybridRetriever(chunks_path=chunks_path, config=config)
    return retriever.retrieve(query)


def retrieve_vector_only(
    chunks_path: str,
    query: str,
    astra_endpoint: Optional[str] = None,
    astra_token: Optional[str] = None,
    collection_name: str = "chunks",
    k: int = DEFAULT_K_VEC
) -> List[Dict[str, Any]]:
    """Convenience function for vector-only retrieval.

    Args:
        chunks_path: Path to chunks parquet
        query: User query
        astra_endpoint: Astra DB endpoint
        astra_token: Astra DB token
        collection_name: Astra collection name
        k: Number of results

    Returns:
        Vector results
    """
    config = RetrievalConfig(k_vec=k, enable_bm25=False)
    retriever = HybridRetriever(
        chunks_path=chunks_path,
        astra_endpoint=astra_endpoint,
        astra_token=astra_token,
        collection_name=collection_name,
        config=config
    )
    return retriever.retrieve(query)
