"""
Create AstraDB collections with proper vector support
Ensures collections are configured for vector similarity search
"""

import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import logging
from dotenv import load_dotenv
from astrapy import DataAPIClient
from astrapy.constants import VectorMetric

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_vector_collections():
    """Create all required collections with vector support"""

    # Get configuration from environment
    api_endpoint = os.getenv("ASTRA_DB_API_ENDPOINT")
    application_token = os.getenv("ASTRA_DB_APPLICATION_TOKEN")

    if not api_endpoint or not application_token:
        raise ValueError("Missing required environment variables")

    # Initialize client
    client = DataAPIClient(application_token)
    database = client.get_database_by_api_endpoint(api_endpoint)

    # Define collections to create
    collections_config = {
        "esg_chunks": {
            "dimension": 768,
            "metric": VectorMetric.COSINE,
            "description": "ESG document chunks with embeddings"
        },
        "esg_companies": {
            "dimension": 768,
            "metric": VectorMetric.COSINE,
            "description": "Company profiles with embeddings"
        },
        "esg_themes": {
            "dimension": 768,
            "metric": VectorMetric.COSINE,
            "description": "ESG themes with embeddings"
        },
        "esg_graph_nodes": {
            "dimension": None,  # No vector for graph nodes
            "description": "Graph nodes for knowledge graph"
        },
        "esg_graph_edges": {
            "dimension": None,  # No vector for graph edges
            "description": "Graph edges for knowledge graph"
        }
    }

    # List existing collections
    existing_collections = []
    try:
        existing_collections = database.list_collection_names()
        logger.info(f"Existing collections: {existing_collections}")
    except Exception as e:
        logger.warning(f"Could not list collections: {e}")

    # Create or recreate collections
    for collection_name, config in collections_config.items():
        try:
            # Drop existing collection if it exists
            if collection_name in existing_collections:
                logger.info(f"Dropping existing collection: {collection_name}")
                database.drop_collection(collection_name)

            # Create new collection with proper configuration
            if config.get("dimension"):
                # Create vector collection with definition
                collection_definition = {
                    "vector": {
                        "dimension": config["dimension"],
                        "metric": config.get("metric", VectorMetric.COSINE).value if hasattr(config.get("metric", VectorMetric.COSINE), 'value') else "cosine"
                    }
                }
                collection = database.create_collection(
                    name=collection_name,
                    definition=collection_definition
                )
                logger.info(f"Created vector collection: {collection_name} (dimension={config['dimension']})")
            else:
                # Create regular collection (for graph)
                collection = database.create_collection(name=collection_name)
                logger.info(f"Created regular collection: {collection_name}")

        except Exception as e:
            logger.error(f"Failed to create collection {collection_name}: {e}")
            # Try to get existing collection as fallback
            try:
                collection = database.get_collection(collection_name)
                logger.info(f"Using existing collection: {collection_name}")
            except:
                logger.error(f"Could not access collection {collection_name}")

    # Verify collections
    logger.info("\nVerifying collections...")
    final_collections = database.list_collection_names()
    logger.info(f"Final collections: {final_collections}")

    # Test vector operations on esg_chunks
    logger.info("\nTesting vector operations...")
    try:
        import numpy as np
        chunks_collection = database.get_collection("esg_chunks")

        # Insert test document
        test_doc = {
            "_id": "test_vector_001",
            "$vector": np.random.randn(768).tolist(),
            "text": "Test document for vector search",
            "company": "TestCorp",
            "year": 2024
        }

        result = chunks_collection.insert_one(test_doc)
        logger.info(f"Test insert successful: {result.inserted_id}")

        # Test vector search
        query_vector = np.random.randn(768).tolist()
        results = chunks_collection.find(
            sort={"$vector": query_vector},
            limit=1
        )

        for doc in results:
            logger.info(f"Vector search found: {doc['_id']}")

        # Clean up test document
        chunks_collection.delete_one({"_id": "test_vector_001"})
        logger.info("Test document cleaned up")

    except Exception as e:
        logger.error(f"Vector operations test failed: {e}")

    logger.info("\nCollection setup complete!")


if __name__ == "__main__":
    try:
        create_vector_collections()
    except Exception as e:
        logger.error(f"Failed to create collections: {e}")
        sys.exit(1)