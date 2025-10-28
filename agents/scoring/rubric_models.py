"""Typed data structures for ESG rubric v3 artifacts."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Mapping, Sequence, Tuple


_TOKEN_PATTERN = re.compile(r"[a-z0-9]{3,}")


def _dedupe(sequence: Iterable[str]) -> Tuple[str, ...]:
    seen = set()
    ordered: List[str] = []
    for item in sequence:
        if item not in seen:
            seen.add(item)
            ordered.append(item)
    return tuple(ordered)


def _extract_keywords(*texts: str) -> Tuple[str, ...]:
    keywords: List[str] = []
    for text in texts:
        if not text:
            continue
        cleaned = text.lower()
        keywords.extend(_TOKEN_PATTERN.findall(cleaned))
    return _dedupe(keywords)


@dataclass(frozen=True)
class StageCharacteristic:
    """Metadata describing a single rubric stage."""

    stage: int
    label: str
    descriptor: str
    evidence_examples: Tuple[str, ...] = field(default_factory=tuple)
    keywords: Tuple[str, ...] = field(init=False)

    def __post_init__(self) -> None:
        if not 0 <= self.stage <= 4:
            raise ValueError(f"stage must be in [0, 4], got {self.stage}")
        object.__setattr__(
            self,
            "keywords",
            _extract_keywords(self.label, self.descriptor, *self.evidence_examples),
        )


@dataclass(frozen=True)
class ThemeRubric:
    """Rubric definition for a single ESG theme."""

    code: str
    name: str
    intent: str
    stages: Mapping[int, StageCharacteristic]

    def __post_init__(self) -> None:
        required = {0, 1, 2, 3, 4}
        if set(self.stages.keys()) != required:
            missing = sorted(required - set(self.stages.keys()))
            raise ValueError(f"Theme {self.code} missing stages {missing}")

    def get_stage(self, stage: int) -> StageCharacteristic:
        if stage not in self.stages:
            raise KeyError(f"Stage {stage} not found for theme {self.code}")
        return self.stages[stage]

    @property
    def ordered_stages(self) -> Sequence[StageCharacteristic]:
        return tuple(self.stages[index] for index in sorted(self.stages))


@dataclass(frozen=True)
class MaturityRubric:
    """Complete rubric asset with deterministic theme ordering."""

    version: str
    themes: Mapping[str, ThemeRubric]
    theme_order: Tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.theme_order:
            raise ValueError("theme_order cannot be empty")
        missing = set(self.theme_order) ^ set(self.themes.keys())
        if missing:
            raise ValueError(f"theme_order mismatch for themes: {sorted(missing)}")

    def get_theme(self, code: str) -> ThemeRubric:
        if code not in self.themes:
            raise KeyError(f"Theme '{code}' not found in rubric")
        return self.themes[code]

    @property
    def themes_in_order(self) -> Sequence[ThemeRubric]:
        return tuple(self.themes[code] for code in self.theme_order)
