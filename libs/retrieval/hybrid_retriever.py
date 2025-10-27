"""
Hybrid Retrieval System
Combines vector similarity search with graph traversal for enhanced retrieval
"""

import logging
from typing import List, Dict, Any, Optional, Set, Tuple
from dataclasses import dataclass, asdict
import numpy as np
from datetime import datetime
import hashlib

from libs.storage.astradb_vector import get_vector_store, AstraDBVectorStore
from libs.storage.astradb_graph import get_graph_store, AstraDBGraphStore
from libs.llm.watsonx_client import get_watsonx_client, WatsonXClient

# Configure logging
logger = logging.getLogger(__name__)


@dataclass
class RetrievalResult:
    """Result from hybrid retrieval"""
    chunk_id: str
    score: float
    text: str
    metadata: Dict[str, Any]
    retrieval_method: str  # 'vector', 'graph', 'hybrid'
    graph_distance: Optional[int] = None  # Hops from seed if from graph

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class HybridRetriever:
    """
    Hybrid retrieval system combining vector and graph search
    """

    def __init__(
        self,
        vector_store: Optional[AstraDBVectorStore] = None,
        graph_store: Optional[AstraDBGraphStore] = None,
        llm_client: Optional[WatsonXClient] = None,
        vector_weight: float = 0.7,  # Weight for vector search vs graph
        expansion_hops: int = 1,  # Graph expansion depth
        rerank: bool = True  # Whether to rerank results
    ):
        self.vector_store = vector_store or get_vector_store()
        self.graph_store = graph_store or get_graph_store()
        self.llm_client = llm_client or get_watsonx_client()
        self.vector_weight = vector_weight
        self.expansion_hops = expansion_hops
        self.rerank = rerank

    def retrieve(
        self,
        query: str,
        company: Optional[str] = None,
        year: Optional[int] = None,
        theme: Optional[str] = None,
        k: int = 20,
        use_graph: bool = True,
        use_vector: bool = True
    ) -> List[RetrievalResult]:
        """
        Main retrieval method combining vector and graph search
        """
        results = []

        # Generate query embedding
        query_embedding = self.llm_client.generate_embedding(query)
        if query_embedding is None:
            logger.error("Failed to generate query embedding")
            return []

        # Build filter for targeted search
        filter_dict = {}
        if company:
            filter_dict["company"] = company
        if year:
            filter_dict["year"] = year
        if theme:
            filter_dict["section"] = theme

        # Vector search
        vector_results = []
        if use_vector:
            vector_results = self._vector_search(
                query_embedding,
                filter_dict,
                k * 2  # Get more candidates
            )

        # Graph search
        graph_results = []
        if use_graph:
            graph_results = self._graph_search(
                query,
                company,
                theme,
                k
            )

        # Combine results
        combined_results = self._combine_results(
            vector_results,
            graph_results,
            k
        )

        # Rerank if enabled
        if self.rerank and len(combined_results) > 0:
            combined_results = self._rerank_results(
                query,
                combined_results,
                k
            )

        return combined_results[:k]

    def _vector_search(
        self,
        query_embedding: np.ndarray,
        filter_dict: Dict[str, Any],
        k: int
    ) -> List[RetrievalResult]:
        """Perform vector similarity search"""
        results = []

        try:
            # Search in vector store
            search_results = self.vector_store.search(
                query_embedding=query_embedding,
                k=k,
                filter_criteria=filter_dict
            )

            # Convert to RetrievalResult
            for res in search_results:
                result = RetrievalResult(
                    chunk_id=res["id"],
                    score=res.get("score", 0.0),
                    text=res.get("metadata", {}).get("text", ""),
                    metadata=res.get("metadata", {}),
                    retrieval_method="vector"
                )
                results.append(result)

        except Exception as e:
            logger.error(f"Vector search failed: {e}")

        return results

    def _graph_search(
        self,
        query: str,
        company: Optional[str],
        theme: Optional[str],
        k: int
    ) -> List[RetrievalResult]:
        """Perform graph-based search"""
        results = []

        try:
            # Find seed nodes based on query context
            seed_nodes = self._find_seed_nodes(query, company, theme)

            if not seed_nodes:
                return []

            # Expand from seed nodes
            expanded = self.graph_store.expand_neighborhood(
                node_ids=seed_nodes,
                max_hops=self.expansion_hops,
                edge_types=["references", "related_to", "measures"]
            )

            # Score and rank graph results
            scored_nodes = self._score_graph_nodes(
                query,
                expanded["nodes"],
                seed_nodes
            )

            # Convert to RetrievalResult
            for node, score, distance in scored_nodes[:k]:
                if node.node_type == "chunk":
                    result = RetrievalResult(
                        chunk_id=node.node_id,
                        score=score,
                        text=node.properties.get("text", ""),
                        metadata=node.properties,
                        retrieval_method="graph",
                        graph_distance=distance
                    )
                    results.append(result)

        except Exception as e:
            logger.error(f"Graph search failed: {e}")

        return results

    def _find_seed_nodes(
        self,
        query: str,
        company: Optional[str],
        theme: Optional[str]
    ) -> List[str]:
        """Find starting nodes for graph traversal"""
        seed_nodes = []

        try:
            # Find company node
            if company:
                subgraph = self.graph_store.get_subgraph(
                    node_type="company",
                    properties_filter={"name": company},
                    limit=1
                )
                for node in subgraph["nodes"]:
                    seed_nodes.append(node.node_id)

            # Find theme nodes
            if theme:
                subgraph = self.graph_store.get_subgraph(
                    node_type="theme",
                    properties_filter={"name": theme},
                    limit=3
                )
                for node in subgraph["nodes"]:
                    seed_nodes.append(node.node_id)

            # If no specific seeds, use top vector results as seeds
            if not seed_nodes:
                # Quick vector search for seed nodes
                query_embedding = self.llm_client.generate_embedding(query)
                if query_embedding is not None:
                    vector_results = self.vector_store.search(
                        query_embedding=query_embedding,
                        k=3
                    )
                    for res in vector_results:
                        seed_nodes.append(res["id"])

        except Exception as e:
            logger.error(f"Failed to find seed nodes: {e}")

        return seed_nodes

    def _score_graph_nodes(
        self,
        query: str,
        nodes: List[Any],
        seed_nodes: List[str]
    ) -> List[Tuple[Any, float, int]]:
        """Score and rank nodes from graph traversal"""
        scored = []

        # Calculate distances from seeds
        distances = self._calculate_distances(nodes, seed_nodes)

        for node in nodes:
            if node.node_type != "chunk":
                continue

            # Base score from graph distance
            distance = distances.get(node.node_id, self.expansion_hops + 1)
            distance_score = 1.0 / (distance + 1)  # Closer = higher score

            # Relevance score based on properties
            relevance_score = self._calculate_relevance(
                query,
                node.properties
            )

            # Combined score
            score = 0.5 * distance_score + 0.5 * relevance_score

            scored.append((node, score, distance))

        # Sort by score
        scored.sort(key=lambda x: x[1], reverse=True)

        return scored

    def _calculate_distances(
        self,
        nodes: List[Any],
        seed_nodes: List[str]
    ) -> Dict[str, int]:
        """Calculate minimum distance from seed nodes"""
        distances = {}

        # BFS from seed nodes
        queue = [(seed, 0) for seed in seed_nodes]
        visited = set(seed_nodes)

        while queue:
            node_id, dist = queue.pop(0)
            distances[node_id] = min(distances.get(node_id, float('inf')), dist)

            if dist < self.expansion_hops:
                # Get neighbors
                neighbors = self.graph_store.get_neighbors(node_id)
                for neighbor, _ in neighbors:
                    if neighbor.node_id not in visited:
                        visited.add(neighbor.node_id)
                        queue.append((neighbor.node_id, dist + 1))

        return distances

    def _calculate_relevance(
        self,
        query: str,
        properties: Dict[str, Any]
    ) -> float:
        """Calculate relevance score based on properties"""
        score = 0.0
        query_lower = query.lower()

        # Check text content
        text = properties.get("text", "").lower()
        if text:
            # Simple keyword matching (could be enhanced)
            query_terms = query_lower.split()
            matches = sum(1 for term in query_terms if term in text)
            score += min(matches / len(query_terms), 1.0) * 0.5

        # Check metadata relevance
        section = properties.get("section", "").lower()
        if section and any(term in section for term in query_lower.split()):
            score += 0.3

        # Check for specific indicators
        indicators = properties.get("indicators", [])
        if indicators:
            score += 0.2

        return min(score, 1.0)

    def _combine_results(
        self,
        vector_results: List[RetrievalResult],
        graph_results: List[RetrievalResult],
        k: int
    ) -> List[RetrievalResult]:
        """Combine vector and graph results with deduplication"""
        combined = {}

        # Add vector results
        for result in vector_results:
            combined[result.chunk_id] = result

        # Add/merge graph results
        for result in graph_results:
            if result.chunk_id in combined:
                # Merge scores
                existing = combined[result.chunk_id]
                merged_score = (
                    self.vector_weight * existing.score +
                    (1 - self.vector_weight) * result.score
                )
                existing.score = merged_score
                existing.retrieval_method = "hybrid"
                existing.graph_distance = result.graph_distance
            else:
                # Adjust score for graph-only results
                result.score *= (1 - self.vector_weight)
                combined[result.chunk_id] = result

        # Sort by score
        sorted_results = sorted(
            combined.values(),
            key=lambda x: x.score,
            reverse=True
        )

        return sorted_results

    def _rerank_results(
        self,
        query: str,
        results: List[RetrievalResult],
        k: int
    ) -> List[RetrievalResult]:
        """Rerank results using LLM for better relevance"""
        try:
            # Prepare batch for reranking
            rerank_batch = []
            for result in results[:k * 2]:  # Rerank top candidates
                rerank_batch.append({
                    "chunk_id": result.chunk_id,
                    "text": result.text[:500],  # Truncate for efficiency
                    "original_score": result.score
                })

            # Create reranking prompt
            prompt = f"""Rank these text chunks by relevance to the query: "{query}"

Chunks:
"""
            for i, item in enumerate(rerank_batch):
                prompt += f"\n{i+1}. {item['text'][:200]}..."

            prompt += "\n\nReturn a JSON array of chunk indices in order of relevance."

            # Get LLM ranking (simplified - in production would parse response)
            # For now, just apply small adjustments based on method
            for result in results:
                if result.retrieval_method == "hybrid":
                    result.score *= 1.1  # Boost hybrid results
                elif result.retrieval_method == "graph" and result.graph_distance == 1:
                    result.score *= 1.05  # Boost direct neighbors

            # Re-sort
            results.sort(key=lambda x: x.score, reverse=True)

        except Exception as e:
            logger.error(f"Reranking failed: {e}")

        return results

    def build_context(
        self,
        results: List[RetrievalResult],
        max_tokens: int = 3000
    ) -> str:
        """Build context string from retrieval results"""
        context_parts = []
        token_count = 0

        for result in results:
            # Estimate tokens (rough approximation)
            text = result.text
            estimated_tokens = len(text) // 4

            if token_count + estimated_tokens > max_tokens:
                # Truncate to fit
                remaining_tokens = max_tokens - token_count
                remaining_chars = remaining_tokens * 4
                text = text[:remaining_chars] + "..."

            context_parts.append(f"[{result.chunk_id}]\n{text}\n")
            token_count += estimated_tokens

            if token_count >= max_tokens:
                break

        return "\n".join(context_parts)

    def trace_provenance(
        self,
        chunk_id: str
    ) -> Dict[str, Any]:
        """Trace the provenance of a chunk through the graph"""
        provenance = {
            "chunk_id": chunk_id,
            "source_path": [],
            "related_entities": {
                "companies": [],
                "themes": [],
                "indicators": []
            }
        }

        try:
            # Get chunk node
            node = self.graph_store.get_node(chunk_id)
            if not node:
                return provenance

            # Get all relationships
            neighbors = self.graph_store.get_neighbors(chunk_id)

            for neighbor, edge in neighbors:
                # Categorize by type
                if neighbor.node_type == "company":
                    provenance["related_entities"]["companies"].append({
                        "id": neighbor.node_id,
                        "name": neighbor.properties.get("name"),
                        "relation": edge.edge_type
                    })
                elif neighbor.node_type == "theme":
                    provenance["related_entities"]["themes"].append({
                        "id": neighbor.node_id,
                        "name": neighbor.properties.get("name"),
                        "relation": edge.edge_type
                    })
                elif neighbor.node_type == "indicator":
                    provenance["related_entities"]["indicators"].append({
                        "id": neighbor.node_id,
                        "name": neighbor.properties.get("name"),
                        "value": neighbor.properties.get("value"),
                        "relation": edge.edge_type
                    })

                # Build source path
                if edge.edge_type == "extracted_from":
                    provenance["source_path"].append(neighbor.node_id)

        except Exception as e:
            logger.error(f"Failed to trace provenance: {e}")

        return provenance


def test_hybrid_retrieval():
    """Test the hybrid retrieval system"""
    logging.basicConfig(level=logging.INFO)

    retriever = HybridRetriever()

    # Test retrieval
    query = "What are Microsoft's carbon reduction targets?"
    results = retriever.retrieve(
        query=query,
        company="Microsoft",
        theme="Climate Action",
        k=10
    )

    print(f"\nQuery: {query}")
    print(f"Found {len(results)} results\n")

    for i, result in enumerate(results[:5]):
        print(f"{i+1}. [{result.retrieval_method}] Score: {result.score:.3f}")
        print(f"   Chunk: {result.chunk_id}")
        if result.graph_distance is not None:
            print(f"   Graph distance: {result.graph_distance}")
        print(f"   Text: {result.text[:200]}...")
        print()

    # Build context
    context = retriever.build_context(results, max_tokens=1000)
    print(f"Context length: {len(context)} chars")

    return results


if __name__ == "__main__":
    test_hybrid_retrieval()