"""
Embedder Factory: Route to Deterministic vs Watsonx

Factory function to select embedder based on integration flags.

SCA v13.8 Compliance:
- Type safety: 100% annotated
- No network in tests: Routes to DeterministicEmbedder
- Adapter pattern: Common interface
"""

from typing import Union
from libs.retrieval.embeddings.deterministic_embedder import DeterministicEmbedder
from libs.retrieval.embeddings.watsonx_embedder import WatsonxEmbedder
from libs.config.integration_flags import load_integration_flags
import json
from pathlib import Path


def get_embedder(
    flags_path: str,
    config_path: str = ""
) -> Union[DeterministicEmbedder, WatsonxEmbedder]:
    """
    Get embedder based on integration flags.

    Args:
        flags_path: Path to integration_flags.json
        config_path: Path to watsonx_config.json (if watsonx_enabled=true)

    Returns:
        DeterministicEmbedder or WatsonxEmbedder instance

    Examples:
        >>> embedder = get_embedder("configs/integration_flags.json")
        >>> isinstance(embedder, DeterministicEmbedder)
        True
    """
    flags = load_integration_flags(flags_path)

    if flags["watsonx_enabled"]:
        # Load watsonx config
        if not config_path:
            raise ValueError("config_path required when watsonx_enabled=true")

        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)

        return WatsonxEmbedder(
            api_key=config["api_key"],
            endpoint=config["endpoint"],
            model_id=config["model_id"]
        )
    else:
        # Use deterministic embedder
        return DeterministicEmbedder(dim=128, seed=42)
