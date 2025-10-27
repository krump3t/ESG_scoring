"""
App-layer retriever combining vector and graph search.

NAMING: Phase 1 of naming refactor
  - Canonical: IndexedHybridRetriever (distinct from libs.retrieval.HybridRetriever)
  - Legacy alias: HybridRetriever (deprecated, import-time warning)
"""

from typing import Dict, Any, List, TypeAlias
import warnings as _w
from .vector_store import VectorStore
from .graph_store import GraphStore


class IndexedHybridRetriever:
    """Hybrid retriever for app-layer (with graph enrichment).

    CANONICAL NAME: Use IndexedHybridRetriever.
    Distinct from libs.retrieval.HybridRetriever (library variant).
    """
    def __init__(self, vs: VectorStore, gs: GraphStore):
        self.vs = vs
        self.gs = gs

    def retrieve(self, query_vector: list[float], k: int = 8, where: Dict[str, Any] | None = None) -> List[Dict[str, Any]]:
        base = self.vs.knn(query_vector, k=k, where=where)
        enriched = []
        seen = set()
        for _id, score, meta in base:
            enriched.append({"id": _id, "score": score, "meta": meta})
            seen.add(_id)
            for nbr_id, rel in self.gs.neighbors(_id):
                if nbr_id not in seen:
                    enriched.append({"id": nbr_id, "score": score * 0.9, "meta": {"via": rel}})
                    seen.add(nbr_id)
        return enriched


# ============================================================================
# LEGACY ALIAS (Phase 1: Naming Refactor)
# ============================================================================
# Emit warning once at module import time (not at instantiation)
_w.warn(
    "apps.index.retriever.HybridRetriever is deprecated; "
    "use IndexedHybridRetriever instead (or use libs.retrieval.HybridRetriever for library variant). "
    "This alias will be removed in Phase 3 (see NAMING_REFACTOR_ROLLING_PLAN.md).",
    DeprecationWarning,
    stacklevel=2
)

# Assignment alias for import compatibility
HybridRetriever: TypeAlias = IndexedHybridRetriever

__all__ = ["IndexedHybridRetriever", "HybridRetriever"]
