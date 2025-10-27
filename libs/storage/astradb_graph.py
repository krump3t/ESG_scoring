"""
AstraDB Graph Store implementation
Manages graph relationships between entities
NO MOCK FUNCTIONALITY - real database only
"""

import os
import json
import logging
from typing import List, Dict, Any, Optional, Set, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
from dotenv import load_dotenv
from uuid import uuid4
import time

# Load environment variables
load_dotenv()

# Configure logging
logger = logging.getLogger(__name__)

# Import AstraDB Python client (REQUIRED - no fallback)
from astrapy import DataAPIClient
from astrapy.exceptions import DataAPIException


@dataclass
class GraphNode:
    """Represents a node in the knowledge graph"""
    node_id: str
    node_type: str  # chunk, company, theme, indicator
    properties: Dict[str, Any]
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class GraphEdge:
    """Represents an edge in the knowledge graph"""
    edge_id: str
    source_id: str
    target_id: str
    edge_type: str  # references, belongs_to, related_to, measures
    properties: Dict[str, Any]
    weight: float = 1.0
    created_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class AstraDBGraphStore:
    """
    Graph store implementation using AstraDB collections - REAL DATABASE ONLY
    Manages relationships between ESG entities
    NO MOCK FUNCTIONALITY - fails if database unavailable
    """

    def __init__(self, config=None):
        self.config = config or self._load_config()

        # Validate required configuration
        if not self.config.get("application_token"):
            raise ValueError("ASTRA_DB_APPLICATION_TOKEN is required - no mock mode available")
        if not self.config.get("api_endpoint"):
            raise ValueError("ASTRA_DB_API_ENDPOINT is required - no mock mode available")

        self.client = None
        self.database = None
        self.nodes_collection = None
        self.edges_collection = None
        self.collection_prefix = "esg_"

        self._initialize_client()

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from environment"""
        return {
            "api_endpoint": os.getenv("ASTRA_DB_API_ENDPOINT", ""),
            "application_token": os.getenv("ASTRA_DB_APPLICATION_TOKEN", ""),
            "database_id": os.getenv("ASTRA_DB_DATABASE_ID", ""),
            "keyspace": os.getenv("ASTRA_DB_KEYSPACE", "default_keyspace")
        }

    def _initialize_client(self):
        """Initialize AstraDB client and graph collections - REQUIRED, no fallback"""
        try:
            # Create client
            self.client = DataAPIClient(self.config["application_token"])

            # Get database
            self.database = self.client.get_database_by_api_endpoint(
                self.config["api_endpoint"]
            )

            # Initialize graph collections
            self._init_graph_collections()

            logger.info("AstraDB Graph client initialized successfully with REAL database")

        except Exception as e:
            logger.error(f"Failed to initialize AstraDB Graph client: {e}")
            raise RuntimeError(f"Cannot initialize AstraDB Graph - real database required: {e}")

    def _init_graph_collections(self):
        """Initialize graph-specific collections"""
        if not self.database:
            raise RuntimeError("Database not initialized")

        try:
            # Create nodes collection
            nodes_collection_name = f"{self.collection_prefix}graph_nodes"
            try:
                self.nodes_collection = self.database.create_collection(
                    nodes_collection_name,
                    check_exists=True
                )
                logger.info(f"Initialized nodes collection: {nodes_collection_name}")
            except:
                self.nodes_collection = self.database.get_collection(nodes_collection_name)
                logger.info(f"Using existing nodes collection: {nodes_collection_name}")

            # Create edges collection
            edges_collection_name = f"{self.collection_prefix}graph_edges"
            try:
                self.edges_collection = self.database.create_collection(
                    edges_collection_name,
                    check_exists=True
                )
                logger.info(f"Initialized edges collection: {edges_collection_name}")
            except:
                self.edges_collection = self.database.get_collection(edges_collection_name)
                logger.info(f"Using existing edges collection: {edges_collection_name}")

            # Create indexes for efficient graph traversal
            self._create_indexes()

        except Exception as e:
            logger.error(f"Failed to initialize graph collections: {e}")
            raise RuntimeError(f"Cannot initialize graph collections: {e}")

    def _create_indexes(self):
        """Create indexes for efficient graph operations"""
        try:
            # Indexes would be created here if AstraDB supports them
            # For now, we rely on _id and filtering
            logger.debug("Graph indexes configured")
        except Exception as e:
            logger.warning(f"Could not create indexes: {e}")

    def upsert_node(
        self,
        node_id: str,
        node_type: str,
        properties: Dict[str, Any]
    ) -> bool:
        """
        Upsert a node in the graph - REAL DATABASE ONLY
        """
        if not self.nodes_collection:
            raise RuntimeError("Nodes collection not initialized")

        try:
            node = GraphNode(
                node_id=node_id,
                node_type=node_type,
                properties=properties,
                created_at=datetime.now().isoformat(),
                updated_at=datetime.now().isoformat()
            )

            document = {
                "_id": node_id,
                "node_type": node_type,
                "properties": properties,
                "created_at": node.created_at,
                "updated_at": node.updated_at
            }

            # Use replace_one with upsert
            try:
                result = self.nodes_collection.replace_one(
                    {"_id": node_id},
                    document,
                    upsert=True
                )
                return result is not None
            except Exception as replace_error:
                # Fallback to insert
                try:
                    result = self.nodes_collection.insert_one(document)
                    return result is not None
                except Exception as insert_error:
                    logger.error(f"Failed to upsert node {node_id}: {replace_error}, {insert_error}")
                    return False

        except Exception as e:
            logger.error(f"Failed to upsert node {node_id}: {e}")
            raise RuntimeError(f"Node upsert failed: {e}")

    def upsert_edge(
        self,
        edge_id: str,
        source_id: str,
        target_id: str,
        edge_type: str,
        properties: Optional[Dict[str, Any]] = None,
        weight: float = 1.0
    ) -> bool:
        """
        Upsert an edge in the graph - REAL DATABASE ONLY
        """
        if not self.edges_collection:
            raise RuntimeError("Edges collection not initialized")

        try:
            edge = GraphEdge(
                edge_id=edge_id,
                source_id=source_id,
                target_id=target_id,
                edge_type=edge_type,
                properties=properties or {},
                weight=weight,
                created_at=datetime.now().isoformat()
            )

            document = {
                "_id": edge_id,
                "source_id": source_id,
                "target_id": target_id,
                "edge_type": edge_type,
                "properties": properties or {},
                "weight": weight,
                "created_at": edge.created_at
            }

            # Use replace_one with upsert
            try:
                result = self.edges_collection.replace_one(
                    {"_id": edge_id},
                    document,
                    upsert=True
                )
                return result is not None
            except Exception as replace_error:
                # Fallback to insert
                try:
                    result = self.edges_collection.insert_one(document)
                    return result is not None
                except Exception as insert_error:
                    logger.error(f"Failed to upsert edge {edge_id}: {replace_error}, {insert_error}")
                    return False

        except Exception as e:
            logger.error(f"Failed to upsert edge {edge_id}: {e}")
            raise RuntimeError(f"Edge upsert failed: {e}")

    def get_node(self, node_id: str) -> Optional[GraphNode]:
        """
        Get a node by ID - REAL DATABASE ONLY
        """
        if not self.nodes_collection:
            raise RuntimeError("Nodes collection not initialized")

        try:
            doc = self.nodes_collection.find_one({"_id": node_id})
            if doc:
                return GraphNode(
                    node_id=doc["_id"],
                    node_type=doc.get("node_type", "unknown"),
                    properties=doc.get("properties", {}),
                    created_at=doc.get("created_at"),
                    updated_at=doc.get("updated_at")
                )
            return None
        except Exception as e:
            logger.error(f"Failed to get node {node_id}: {e}")
            raise RuntimeError(f"Node retrieval failed: {e}")

    def get_neighbors(
        self,
        node_id: str,
        edge_type: Optional[str] = None,
        direction: str = "both"
    ) -> List[Tuple[GraphNode, GraphEdge]]:
        """
        Get neighboring nodes - REAL DATABASE ONLY
        direction: 'out', 'in', or 'both'
        """
        if not self.edges_collection or not self.nodes_collection:
            raise RuntimeError("Collections not initialized")

        try:
            neighbors = []

            # Build query based on direction
            edge_query = {}
            if direction in ["out", "both"]:
                edge_query["$or"] = [{"source_id": node_id}]
            if direction in ["in", "both"]:
                if "$or" in edge_query:
                    edge_query["$or"].append({"target_id": node_id})
                else:
                    edge_query["$or"] = [{"target_id": node_id}]

            # Filter by edge type if specified
            if edge_type:
                edge_query["edge_type"] = edge_type

            # Find all edges
            edges = list(self.edges_collection.find(edge_query))

            # Get connected nodes
            for edge_doc in edges:
                # Determine neighbor ID
                if edge_doc["source_id"] == node_id:
                    neighbor_id = edge_doc["target_id"]
                else:
                    neighbor_id = edge_doc["source_id"]

                # Get neighbor node
                neighbor_node = self.get_node(neighbor_id)
                if neighbor_node:
                    edge = GraphEdge(
                        edge_id=edge_doc["_id"],
                        source_id=edge_doc["source_id"],
                        target_id=edge_doc["target_id"],
                        edge_type=edge_doc["edge_type"],
                        properties=edge_doc.get("properties", {}),
                        weight=edge_doc.get("weight", 1.0),
                        created_at=edge_doc.get("created_at")
                    )
                    neighbors.append((neighbor_node, edge))

            return neighbors

        except Exception as e:
            logger.error(f"Failed to get neighbors for {node_id}: {e}")
            raise RuntimeError(f"Neighbor retrieval failed: {e}")

    def find_path(
        self,
        start_id: str,
        end_id: str,
        max_depth: int = 5
    ) -> Optional[List[str]]:
        """
        Find shortest path between nodes using BFS - REAL DATABASE ONLY
        """
        if not self.edges_collection:
            raise RuntimeError("Edges collection not initialized")

        try:
            # BFS implementation
            visited = {start_id}
            queue = [(start_id, [start_id])]

            while queue and max_depth > 0:
                current_id, path = queue.pop(0)

                if current_id == end_id:
                    return path

                if len(path) >= max_depth:
                    continue

                # Get neighbors
                neighbors = self.get_neighbors(current_id)
                for neighbor_node, _ in neighbors:
                    if neighbor_node.node_id not in visited:
                        visited.add(neighbor_node.node_id)
                        new_path = path + [neighbor_node.node_id]
                        queue.append((neighbor_node.node_id, new_path))

            return None

        except Exception as e:
            logger.error(f"Failed to find path from {start_id} to {end_id}: {e}")
            raise RuntimeError(f"Path finding failed: {e}")

    def get_subgraph(
        self,
        center_id: str,
        max_depth: int = 2,
        edge_types: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Get subgraph around a node - REAL DATABASE ONLY
        """
        if not self.nodes_collection or not self.edges_collection:
            raise RuntimeError("Collections not initialized")

        try:
            nodes = {}
            edges = []
            visited = {center_id}
            queue = [(center_id, 0)]

            # BFS to explore subgraph
            while queue:
                current_id, depth = queue.pop(0)

                if depth >= max_depth:
                    continue

                # Get current node
                node = self.get_node(current_id)
                if node:
                    nodes[current_id] = node.to_dict()

                # Get neighbors
                neighbors = self.get_neighbors(current_id)
                for neighbor_node, edge in neighbors:
                    # Filter by edge type if specified
                    if edge_types and edge.edge_type not in edge_types:
                        continue

                    edges.append(edge.to_dict())

                    if neighbor_node.node_id not in visited:
                        visited.add(neighbor_node.node_id)
                        queue.append((neighbor_node.node_id, depth + 1))
                        nodes[neighbor_node.node_id] = neighbor_node.to_dict()

            return {
                "nodes": list(nodes.values()),
                "edges": edges,
                "center_id": center_id,
                "max_depth": max_depth
            }

        except Exception as e:
            logger.error(f"Failed to get subgraph for {center_id}: {e}")
            raise RuntimeError(f"Subgraph retrieval failed: {e}")

    def delete_node(self, node_id: str, cascade: bool = True) -> bool:
        """
        Delete a node and optionally its edges - REAL DATABASE ONLY
        """
        if not self.nodes_collection:
            raise RuntimeError("Nodes collection not initialized")

        try:
            # Delete associated edges if cascade
            if cascade and self.edges_collection:
                self.edges_collection.delete_many({
                    "$or": [
                        {"source_id": node_id},
                        {"target_id": node_id}
                    ]
                })

            # Delete node
            result = self.nodes_collection.delete_one({"_id": node_id})
            return result.deleted_count > 0 if hasattr(result, 'deleted_count') else False

        except Exception as e:
            logger.error(f"Failed to delete node {node_id}: {e}")
            raise RuntimeError(f"Node deletion failed: {e}")

    def delete_edge(self, edge_id: str) -> bool:
        """
        Delete an edge - REAL DATABASE ONLY
        """
        if not self.edges_collection:
            raise RuntimeError("Edges collection not initialized")

        try:
            result = self.edges_collection.delete_one({"_id": edge_id})
            return result.deleted_count > 0 if hasattr(result, 'deleted_count') else False
        except Exception as e:
            logger.error(f"Failed to delete edge {edge_id}: {e}")
            raise RuntimeError(f"Edge deletion failed: {e}")

    def clear_graph(self) -> bool:
        """
        Clear all nodes and edges - REAL DATABASE ONLY
        USE WITH CAUTION
        """
        if not self.nodes_collection or not self.edges_collection:
            raise RuntimeError("Collections not initialized")

        try:
            # Delete all edges
            self.edges_collection.delete_many({})
            # Delete all nodes
            self.nodes_collection.delete_many({})
            logger.info("Graph cleared successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to clear graph: {e}")
            raise RuntimeError(f"Graph clear failed: {e}")

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get graph statistics - REAL DATABASE ONLY
        """
        if not self.nodes_collection or not self.edges_collection:
            raise RuntimeError("Collections not initialized")

        try:
            # Count nodes by type
            node_types = {}
            all_nodes = list(self.nodes_collection.find({}))
            for node in all_nodes:
                node_type = node.get("node_type", "unknown")
                node_types[node_type] = node_types.get(node_type, 0) + 1

            # Count edges by type
            edge_types = {}
            all_edges = list(self.edges_collection.find({}))
            for edge in all_edges:
                edge_type = edge.get("edge_type", "unknown")
                edge_types[edge_type] = edge_types.get(edge_type, 0) + 1

            return {
                "total_nodes": len(all_nodes),
                "total_edges": len(all_edges),
                "node_types": node_types,
                "edge_types": edge_types,
                "average_degree": (2 * len(all_edges) / len(all_nodes)) if all_nodes else 0
            }

        except Exception as e:
            logger.error(f"Failed to get graph statistics: {e}")
            raise RuntimeError(f"Statistics retrieval failed: {e}")

    def test_connection(self) -> Dict[str, Any]:
        """Test AstraDB Graph connection and configuration - REAL ONLY"""
        results = {
            "connected": False,
            "token_valid": bool(self.config.get("application_token")),
            "endpoint_valid": bool(self.config.get("api_endpoint")),
            "nodes_collection": None,
            "edges_collection": None
        }

        try:
            # Check collections
            if self.nodes_collection:
                results["nodes_collection"] = "initialized"
            if self.edges_collection:
                results["edges_collection"] = "initialized"

            # Test operations
            test_node_id = f"test_node_{uuid4().hex[:8]}"
            test_edge_id = f"test_edge_{uuid4().hex[:8]}"

            # Test node creation
            if self.upsert_node(test_node_id, "test", {"test": True}):
                results["node_write"] = "success"

                # Test edge creation
                if self.upsert_edge(test_edge_id, test_node_id, test_node_id, "test_edge"):
                    results["edge_write"] = "success"

                    # Clean up
                    self.delete_edge(test_edge_id)
                    self.delete_node(test_node_id)
                    results["cleanup"] = "success"

            results["connected"] = True

        except Exception as e:
            results["error"] = str(e)
            results["connected"] = False

        return results


# Singleton instance
_graph_instance = None


def get_graph_store() -> AstraDBGraphStore:
    """Get singleton graph store instance - REAL DATABASE ONLY"""
    global _graph_instance
    if _graph_instance is None:
        _graph_instance = AstraDBGraphStore()
    return _graph_instance


# Export key classes
__all__ = ['AstraDBGraphStore', 'GraphNode', 'GraphEdge', 'get_graph_store']