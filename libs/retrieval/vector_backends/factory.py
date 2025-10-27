"""
Vector Backend Factory: Route to In-Memory vs AstraDB

Factory function to select vector backend based on integration flags.

SCA v13.8 Compliance:
- Type safety: 100% annotated
- No network in tests: Routes to VectorIndex
- Adapter pattern: Common interface
"""

from typing import Union
from libs.retrieval.vector_index import VectorIndex
from libs.retrieval.vector_backends.astradb_store import AstraDBStore
from libs.config.integration_flags import load_integration_flags
import json


def get_vector_backend(
    flags_path: str,
    dim: int,
    config_path: str = ""
) -> Union[VectorIndex, AstraDBStore]:
    """
    Get vector backend based on integration flags.

    Args:
        flags_path: Path to integration_flags.json
        dim: Embedding dimension
        config_path: Path to astradb_config.json (if astradb_enabled=true)

    Returns:
        VectorIndex or AstraDBStore instance

    Examples:
        >>> backend = get_vector_backend("configs/integration_flags.json", dim=128)
        >>> isinstance(backend, VectorIndex)
        True
    """
    flags = load_integration_flags(flags_path)

    if flags["astradb_enabled"]:
        # Load AstraDB config
        if not config_path:
            raise ValueError("config_path required when astradb_enabled=true")

        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)

        return AstraDBStore(
            token=config["token"],
            endpoint=config["endpoint"],
            keyspace=config["keyspace"]
        )
    else:
        # Use in-memory vector index
        return VectorIndex(dim=dim)
