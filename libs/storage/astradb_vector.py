"""
AstraDB Vector Store implementation
Manages vector embeddings and similarity search
NO MOCK FUNCTIONALITY - real database only
"""

import os
import json
import logging
import hashlib
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
import numpy as np
from dotenv import load_dotenv
import time
from uuid import uuid4
from libs.utils.clock import get_clock
clock = get_clock()

# Load environment variables
load_dotenv()

# Configure logging
logger = logging.getLogger(__name__)

# Import AstraDB Python client (REQUIRED - no fallback)
from astrapy import DataAPIClient
from astrapy.constants import VectorMetric
from astrapy.exceptions import DataAPIException


@dataclass
class AstraDBConfig:
    """Configuration for AstraDB"""
    api_endpoint: str
    application_token: str
    database_id: str
    keyspace: str = "default_keyspace"
    collection_prefix: str = "esg_"
    embedding_dimension: int = 768
    similarity_metric: str = "cosine"

    @classmethod
    def from_env(cls) -> 'AstraDBConfig':
        """Load configuration from environment variables"""
        return cls(
            api_endpoint=os.getenv("ASTRA_DB_API_ENDPOINT", ""),
            application_token=os.getenv("ASTRA_DB_APPLICATION_TOKEN", ""),
            database_id=os.getenv("ASTRA_DB_DATABASE_ID", ""),
            keyspace=os.getenv("ASTRA_DB_KEYSPACE", "default_keyspace"),
            collection_prefix="esg_"  # Project-specific prefix
        )


class AstraDBVectorStore:
    """
    Production vector store using DataStax AstraDB - REAL DATABASE ONLY
    Manages embeddings and similarity search
    NO MOCK FUNCTIONALITY - fails if database unavailable
    """

    def __init__(self, config: Optional[AstraDBConfig] = None):
        self.config = config or AstraDBConfig.from_env()

        # Validate required configuration
        if not self.config.application_token:
            raise ValueError("ASTRA_DB_APPLICATION_TOKEN is required - no mock mode available")
        if not self.config.api_endpoint:
            raise ValueError("ASTRA_DB_API_ENDPOINT is required - no mock mode available")

        self.client = None
        self.database = None
        self.collections = {}

        self._initialize_client()

    def _initialize_client(self):
        """Initialize AstraDB client and collections - REQUIRED, no fallback"""
        try:
            # Create client
            self.client = DataAPIClient(self.config.application_token)

            # Get database
            self.database = self.client.get_database_by_api_endpoint(
                self.config.api_endpoint
            )

            # Initialize collections for different data types
            self._init_collections()

            logger.info("AstraDB client initialized successfully with REAL database")

        except Exception as e:
            logger.error(f"Failed to initialize AstraDB client: {e}")
            raise RuntimeError(f"Cannot initialize AstraDB - real database required: {e}")

    def _init_collections(self):
        """Initialize project-specific collections with vector support"""
        if not self.database:
            raise RuntimeError("Database not initialized")

        try:
            # Collection names with project prefix
            collections_config = {
                f"{self.config.collection_prefix}chunks": {
                    "dimension": self.config.embedding_dimension,
                    "metric": self.config.similarity_metric
                },
                f"{self.config.collection_prefix}companies": {
                    "dimension": self.config.embedding_dimension,
                    "metric": self.config.similarity_metric
                },
                f"{self.config.collection_prefix}themes": {
                    "dimension": self.config.embedding_dimension,
                    "metric": self.config.similarity_metric
                }
            }

            for collection_name, config in collections_config.items():
                try:
                    # Create or get collection with vector search capability
                    collection = self.database.create_collection(
                        collection_name,
                        dimension=config["dimension"],
                        metric=VectorMetric.COSINE if config["metric"] == "cosine" else VectorMetric.EUCLIDEAN,
                        check_exists=True  # Don't error if exists
                    )
                    self.collections[collection_name] = collection
                    logger.info(f"Initialized collection: {collection_name}")

                except Exception as e:
                    # Collection might already exist, try to get it
                    try:
                        collection = self.database.get_collection(collection_name)
                        self.collections[collection_name] = collection
                        logger.info(f"Using existing collection: {collection_name}")
                    except Exception as get_error:
                        logger.error(f"Failed to initialize collection {collection_name}: {e}, {get_error}")
                        raise RuntimeError(f"Cannot access collection {collection_name}: {e}")

        except Exception as e:
            logger.error(f"Failed to initialize collections: {e}")
            raise RuntimeError(f"Cannot initialize AstraDB collections: {e}")

    def upsert_chunk(
        self,
        chunk_id: str,
        embedding: np.ndarray,
        metadata: Dict[str, Any],
        collection_name: Optional[str] = None
    ) -> bool:
        """
        Upsert a chunk with its embedding - REAL DATABASE ONLY
        Returns success status
        """
        if collection_name is None:
            collection_name = f"{self.config.collection_prefix}chunks"

        if collection_name not in self.collections:
            raise RuntimeError(f"Collection {collection_name} not initialized")

        try:
            # Prepare document
            document = {
                "_id": chunk_id,
                "$vector": embedding.tolist(),
                "metadata": metadata,
                "timestamp": clock.now().isoformat()
            }

            # Add metadata fields at top level for filtering
            for key, value in metadata.items():
                if key in ["company", "year", "section", "source_url"]:
                    document[key] = value

            # Upsert to collection - use replace_one with upsert
            try:
                # Try to update existing document
                result = self.collections[collection_name].replace_one(
                    {"_id": chunk_id},
                    document,
                    upsert=True
                )
                return result is not None
            except Exception as replace_error:
                # If replace fails, try insert
                try:
                    result = self.collections[collection_name].insert_one(document)
                    return result is not None
                except Exception as insert_error:
                    logger.error(f"Failed to upsert chunk {chunk_id}: replace={replace_error}, insert={insert_error}")
                    return False

        except Exception as e:
            logger.error(f"Failed to upsert chunk {chunk_id}: {e}")
            raise RuntimeError(f"Database upsert failed: {e}")

    def upsert_batch(
        self,
        items: List[Tuple[str, np.ndarray, Dict[str, Any]]],
        collection_name: Optional[str] = None
    ) -> int:
        """
        Batch upsert multiple items - REAL DATABASE ONLY
        Returns number of successful upserts
        """
        if collection_name is None:
            collection_name = f"{self.config.collection_prefix}chunks"

        if collection_name not in self.collections:
            raise RuntimeError(f"Collection {collection_name} not initialized")

        success_count = 0

        try:
            # Prepare documents
            documents = []
            for chunk_id, embedding, metadata in items:
                document = {
                    "_id": chunk_id,
                    "$vector": embedding.tolist(),
                    "metadata": metadata,
                    "timestamp": clock.now().isoformat()
                }

                # Add filterable fields
                for key, value in metadata.items():
                    if key in ["company", "year", "section", "source_url"]:
                        document[key] = value

                documents.append(document)

            # Batch insert with upsert
            if documents:
                # AstraDB batch operations
                # Split into smaller batches if needed (AstraDB has limits)
                batch_size = 20
                for i in range(0, len(documents), batch_size):
                    batch = documents[i:i + batch_size]
                    try:
                        # Try batch insert
                        result = self.collections[collection_name].insert_many(
                            batch,
                            ordered=False  # Continue on errors
                        )
                        if result and hasattr(result, 'inserted_ids'):
                            success_count += len(result.inserted_ids)
                        else:
                            # Fallback to individual upserts
                            for doc in batch:
                                try:
                                    self.collections[collection_name].replace_one(
                                        {"_id": doc["_id"]},
                                        doc,
                                        upsert=True
                                    )
                                    success_count += 1
                                except Exception as e:
                                    logger.warning(f"Failed to upsert document {doc.get('_id', 'unknown')}: {e}")
                                    # Continue with next document
                    except DataAPIException as e:
                        # Handle duplicates by doing individual upserts
                        if "E11000" in str(e) or "duplicate" in str(e).lower():
                            for doc in batch:
                                try:
                                    self.collections[collection_name].replace_one(
                                        {"_id": doc["_id"]},
                                        doc,
                                        upsert=True
                                    )
                                    success_count += 1
                                except Exception as e:
                                    logger.warning(f"Failed to upsert document {doc.get('_id', 'unknown')}: {e}")
                                    # Continue with next document
                        else:
                            logger.error(f"Batch insert failed: {e}")

            return success_count

        except Exception as e:
            logger.error(f"Failed batch upsert: {e}")
            raise RuntimeError(f"Database batch upsert failed: {e}")

    def search(
        self,
        query_embedding: np.ndarray,
        k: int = 10,
        filter_criteria: Optional[Dict[str, Any]] = None,
        collection_name: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Vector similarity search - REAL DATABASE ONLY
        Returns list of similar documents
        """
        if collection_name is None:
            collection_name = f"{self.config.collection_prefix}chunks"

        if collection_name not in self.collections:
            raise RuntimeError(f"Collection {collection_name} not initialized")

        try:
            # Prepare search query
            search_query = {}
            if filter_criteria:
                search_query.update(filter_criteria)

            # Perform vector search
            results = self.collections[collection_name].find(
                filter=search_query,
                sort={"$vector": query_embedding.tolist()},
                limit=k,
                include_similarity=True
            )

            # Format results
            formatted_results = []
            for doc in results:
                formatted_results.append({
                    "id": doc.get("_id"),
                    "score": doc.get("$similarity", 0.0),
                    "metadata": doc.get("metadata", {}),
                    "company": doc.get("company"),
                    "year": doc.get("year"),
                    "section": doc.get("section")
                })

            return formatted_results

        except Exception as e:
            logger.error(f"Search failed: {e}")
            raise RuntimeError(f"Vector search failed: {e}")

    def get_by_id(
        self,
        document_id: str,
        collection_name: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get document by ID - REAL DATABASE ONLY
        """
        if collection_name is None:
            collection_name = f"{self.config.collection_prefix}chunks"

        if collection_name not in self.collections:
            raise RuntimeError(f"Collection {collection_name} not initialized")

        try:
            result = self.collections[collection_name].find_one({"_id": document_id})
            return result
        except Exception as e:
            logger.error(f"Failed to get document {document_id}: {e}")
            raise RuntimeError(f"Database read failed: {e}")

    def delete(
        self,
        document_id: str,
        collection_name: Optional[str] = None
    ) -> bool:
        """
        Delete document by ID - REAL DATABASE ONLY
        """
        if collection_name is None:
            collection_name = f"{self.config.collection_prefix}chunks"

        if collection_name not in self.collections:
            raise RuntimeError(f"Collection {collection_name} not initialized")

        try:
            result = self.collections[collection_name].delete_one({"_id": document_id})
            return result.deleted_count > 0 if hasattr(result, 'deleted_count') else False
        except Exception as e:
            logger.error(f"Failed to delete document {document_id}: {e}")
            raise RuntimeError(f"Database delete failed: {e}")

    def delete_by_filter(
        self,
        filter_criteria: Dict[str, Any],
        collection_name: Optional[str] = None
    ) -> int:
        """
        Delete documents matching filter - REAL DATABASE ONLY
        Returns number of deleted documents
        """
        if collection_name is None:
            collection_name = f"{self.config.collection_prefix}chunks"

        if collection_name not in self.collections:
            raise RuntimeError(f"Collection {collection_name} not initialized")

        try:
            result = self.collections[collection_name].delete_many(filter_criteria)
            return result.deleted_count if hasattr(result, 'deleted_count') else 0
        except Exception as e:
            logger.error(f"Failed to delete by filter: {e}")
            raise RuntimeError(f"Database delete failed: {e}")

    def count(
        self,
        filter_criteria: Optional[Dict[str, Any]] = None,
        collection_name: Optional[str] = None
    ) -> int:
        """
        Count documents - REAL DATABASE ONLY
        """
        if collection_name is None:
            collection_name = f"{self.config.collection_prefix}chunks"

        if collection_name not in self.collections:
            raise RuntimeError(f"Collection {collection_name} not initialized")

        try:
            if filter_criteria:
                return self.collections[collection_name].count_documents(filter_criteria)
            else:
                # For total count, use estimated_document_count if available
                try:
                    return self.collections[collection_name].estimated_document_count()
                except:
                    return self.collections[collection_name].count_documents({})
        except Exception as e:
            logger.error(f"Failed to count documents: {e}")
            raise RuntimeError(f"Database count failed: {e}")

    def hybrid_search(
        self,
        query_embedding: np.ndarray,
        filter_criteria: Dict[str, Any],
        k: int = 10,
        collection_name: Optional[str] = None,
        rerank: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Hybrid search combining vector similarity and metadata filtering - REAL DATABASE ONLY
        """
        if collection_name is None:
            collection_name = f"{self.config.collection_prefix}chunks"

        # Perform filtered vector search
        results = self.search(
            query_embedding=query_embedding,
            k=k * 2 if rerank else k,  # Get more results if reranking
            filter_criteria=filter_criteria,
            collection_name=collection_name
        )

        if not rerank:
            return results

        # Rerank based on combined score
        for result in results:
            # Combine similarity score with metadata relevance
            metadata_score = 0.0

            # Boost score based on metadata matches
            if filter_criteria:
                for key, value in filter_criteria.items():
                    if result.get(key) == value:
                        metadata_score += 0.1

            # Combined score (weighted)
            result["combined_score"] = (
                result.get("score", 0.0) * 0.8 +
                metadata_score * 0.2
            )

        # Sort by combined score
        sorted_results = sorted(
            results,
            key=lambda x: x.get("combined_score", 0.0),
            reverse=True
        )[:k]

        return sorted_results

    def test_connection(self) -> Dict[str, Any]:
        """Test AstraDB connection and configuration - REAL ONLY"""
        results = {
            "connected": False,
            "token_valid": bool(self.config.application_token),
            "endpoint_valid": bool(self.config.api_endpoint),
            "database_id": self.config.database_id,
            "keyspace": self.config.keyspace,
            "collections": []
        }

        try:
            # List collections
            results["collections"] = list(self.collections.keys())

            # Test write/read
            test_id = f"test_{uuid4().hex[:8]}"
            test_embedding = np.random.randn(self.config.embedding_dimension)
            test_metadata = {"test": True, "timestamp": clock.now().isoformat()}

            # Try to write
            if self.upsert_chunk(test_id, test_embedding, test_metadata):
                results["write_test"] = "success"

                # Try to read
                doc = self.get_by_id(test_id)
                if doc:
                    results["read_test"] = "success"

                    # Clean up
                    if self.delete(test_id):
                        results["cleanup"] = "success"
                    else:
                        results["cleanup"] = "failed"
                else:
                    results["read_test"] = "failed"
            else:
                results["write_test"] = "failed"

            results["connected"] = True

        except Exception as e:
            results["error"] = str(e)
            results["connected"] = False

        return results


# Singleton instance
_store_instance = None


def get_vector_store() -> AstraDBVectorStore:
    """Get singleton vector store instance - REAL DATABASE ONLY"""
    global _store_instance
    if _store_instance is None:
        _store_instance = AstraDBVectorStore()
    return _store_instance


# Export key classes
__all__ = ['AstraDBVectorStore', 'AstraDBConfig', 'get_vector_store']