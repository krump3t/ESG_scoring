from typing import Dict, Any, List
from .vector_store import VectorStore
from .graph_store import GraphStore

class HybridRetriever:
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
