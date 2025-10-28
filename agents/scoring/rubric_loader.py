"""Loader for compiled ESG maturity rubric JSON files."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List

from agents.scoring.rubric_models import (
    MaturityRubric,
    StageCharacteristic,
    ThemeRubric,
)


class RubricLoader:
    """Load rubric data from compiled JSON artifacts."""

    def __init__(self, compiled_path: Path | None = None) -> None:
        self.compiled_path = compiled_path or Path("rubrics/maturity_v3.json")

    def load(self) -> MaturityRubric:
        """Load the rubric from the configured compiled JSON path."""
        return load_from_compiled_json(self.compiled_path)


def load_from_compiled_json(json_path: Path) -> MaturityRubric:
    """Load rubric definitions from a compiled JSON file."""
    if not json_path.exists():
        raise FileNotFoundError(f"Compiled rubric not found at {json_path}")

    with json_path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)

    version = str(payload.get("version", "3.0"))
    themes_payload = payload.get("themes", [])

    theme_order: List[str] = []
    themes: Dict[str, ThemeRubric] = {}

    for theme_entry in themes_payload:
        code = str(theme_entry["code"])
        name = str(theme_entry.get("name", code))
        intent = str(theme_entry.get("intent", ""))
        stages_payload = theme_entry.get("stages", {})

        stage_map: Dict[int, StageCharacteristic] = {}
        for stage_key, stage_data in stages_payload.items():
            stage = int(stage_key)
            label = str(stage_data.get("label", f"Stage {stage}"))
            descriptor = str(stage_data.get("descriptor", ""))
            examples_payload = stage_data.get("evidence_examples", [])
            evidence_examples = tuple(str(item) for item in examples_payload)

            stage_map[stage] = StageCharacteristic(
                stage=stage,
                label=label,
                descriptor=descriptor,
                evidence_examples=evidence_examples,
            )

        theme_order.append(code)
        themes[code] = ThemeRubric(
            code=code,
            name=name,
            intent=intent,
            stages=stage_map,
        )

    return MaturityRubric(version=version, themes=themes, theme_order=tuple(theme_order))
