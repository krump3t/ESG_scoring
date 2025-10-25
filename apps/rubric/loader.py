"""
Rubric Loader - JSON Schema Source of Truth

Loads ESG maturity rubric from esg_rubric_schema_v3.json.
This is the ONLY authoritative source for theme definitions and scoring rules.

SCA v13.8 Compliance:
- Type safety: 100% annotated with dataclasses
- Single source: JSON schema only (no markdown parsing)
- Determinism: Immutable frozen dataclasses
"""

from __future__ import annotations
import json
import pathlib
import dataclasses
from typing import Any, Dict, List

SCHEMA_PATH = pathlib.Path("rubrics/esg_rubric_schema_v3.json")


@dataclasses.dataclass(frozen=True)
class Theme:
    """ESG maturity theme with stages."""
    code: str
    name: str
    stages: Dict[str, Any]


@dataclasses.dataclass(frozen=True)
class Rubric:
    """Complete rubric with themes and scoring rules."""
    version: str
    themes: List[Theme]
    scoring_rules: Dict[str, Any]


def load_rubric(path: pathlib.Path = SCHEMA_PATH) -> Rubric:
    """
    Load rubric from JSON schema.

    Args:
        path: Path to JSON schema (default: rubrics/esg_rubric_schema_v3.json)

    Returns:
        Rubric instance with themes and scoring rules

    Raises:
        FileNotFoundError: If schema file doesn't exist
        json.JSONDecodeError: If schema is invalid JSON
    """
    data = json.loads(path.read_text(encoding="utf-8"))

    themes = [
        Theme(
            code=t["code"],
            name=t["name"],
            stages=t["stages"]
        )
        for t in data["themes"]
    ]

    return Rubric(
        version=str(data.get("version", "v3")),
        themes=themes,
        scoring_rules=data.get("scoring_rules", {})
    )
