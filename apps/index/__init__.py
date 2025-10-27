"""Index module for graph and vector store integration.

NAMING: Phase 1 of naming refactor
  Golden import paths for index:
  - from apps.index import IndexedHybridRetriever (canonical)
  - from apps.index import HybridRetriever (legacy, deprecated)
  - from libs.retrieval import HybridRetriever (library variant, recommended)
"""

from .retriever import IndexedHybridRetriever, HybridRetriever
from .vector_store import VectorStore
from .graph_store import GraphStore

__all__ = ["IndexedHybridRetriever", "HybridRetriever", "VectorStore", "GraphStore"]
