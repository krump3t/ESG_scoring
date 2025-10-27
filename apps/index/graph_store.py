from typing import Dict, List, Tuple
from .ontology import Node, Edge

class GraphStore:
    def __init__(self):
        self.nodes: Dict[str, Node] = {}
        self.edges: List[Edge] = []

    def upsert_node(self, node: Node) -> None:
        self.nodes[node.id] = node

    def add_edge(self, edge: Edge) -> None:
        self.edges.append(edge)

    def neighbors(self, node_id: str) -> List[Tuple[str, str]]:
        out = []
        for e in self.edges:
            if e.src == node_id:
                out.append((e.dst, e.rel.value))
        return out
