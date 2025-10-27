from typing import List, Dict

def build_graph_and_vectors(chunks: List[dict]) -> Dict[str, int]:
    # Minimal: pretend to index vectors and graph edges
    # Return simple stats to prove the stage ran
    node_count = len(chunks) + 2  # +company, +report
    edge_count = len(chunks)      # chunk -> report
    return {"nodes": node_count, "edges": edge_count}
