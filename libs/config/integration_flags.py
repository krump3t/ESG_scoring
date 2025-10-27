"""
Integration Flags Loader

Loads feature flags from configs/integration_flags.json to toggle:
- semantic_enabled: Enable semantic retrieval
- watsonx_enabled: Use watsonx embeddings (vs deterministic)
- astradb_enabled: Use AstraDB backend (vs in-memory)

SCA v13.8 Compliance:
- Type safety: 100% annotated
- Fail-safe defaults: All disabled if file missing
- Determinism: Loaded once at startup
"""

import json
from typing import Dict, Any
from pathlib import Path


def load_integration_flags(flags_path: str) -> Dict[str, bool]:
    """
    Load integration flags from JSON file.

    Args:
        flags_path: Path to integration_flags.json

    Returns:
        Dict with semantic_enabled, watsonx_enabled, astradb_enabled

    Raises:
        ValueError: If JSON invalid
        KeyError: If required keys missing

    Examples:
        >>> flags = load_integration_flags("configs/integration_flags.json")
        >>> flags["semantic_enabled"]
        False
    """
    path = Path(flags_path)

    # If file missing, return safe defaults (all disabled)
    if not path.exists():
        return {
            "semantic_enabled": False,
            "watsonx_enabled": False,
            "astradb_enabled": False
        }

    # Load and validate
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in {flags_path}: {e}")

    # Validate required keys
    required_keys = ["semantic_enabled", "watsonx_enabled", "astradb_enabled"]
    for key in required_keys:
        if key not in data:
            raise KeyError(f"Missing required key '{key}' in {flags_path}")

    return {
        "semantic_enabled": data["semantic_enabled"],
        "watsonx_enabled": data["watsonx_enabled"],
        "astradb_enabled": data["astradb_enabled"]
    }
