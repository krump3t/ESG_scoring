from typing import List, Dict, Any, Tuple
import math

class VectorStore:
    def __init__(self):
        self._store: Dict[str, Tuple[List[float], Dict[str, Any]]] = {}

    def upsert(self, _id: str, vector: List[float], metadata: Dict[str, Any]) -> None:
        self._store[_id] = (vector, metadata)

    def knn(self, query: List[float], k: int = 5, where: Dict[str, Any] | None = None) -> List[Tuple[str, float, Dict[str, Any]]]:
        def dot(a,b): return sum(x*y for x,y in zip(a,b))
        def norm(a): return math.sqrt(sum(x*x for x in a)) or 1.0
        qn = norm(query)
        scored = []
        for _id, (vec, meta) in self._store.items():
            if where:
                ok = True
                for key, val in where.items():
                    if meta.get(key) != val:
                        ok = False
                        break
                if not ok:
                    continue
            score = dot(query, vec) / (norm(vec) * qn)
            scored.append((_id, score, meta))
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:k]
