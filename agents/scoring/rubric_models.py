"""
Rubric Data Models

Core data structures for ESG maturity rubric representation.

Per SCA v13.8: Critical Path file - subject to strict quality gates.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any
from pathlib import Path
import json
import pandas as pd


@dataclass(frozen=True)
class StageCharacteristic:
    """
    A single characteristic that defines maturity at a specific stage.

    Attributes:
        theme: Theme identifier (e.g., "ghg_accounting")
        stage: Maturity stage (0-4)
        description: Full text description of the characteristic
        keywords: Key terms extracted from description for matching
    """

    theme: str
    stage: int
    description: str
    keywords: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Validate characteristic fields"""
        if not self.theme or len(self.theme.strip()) == 0:
            raise ValueError("Theme cannot be empty")

        if not (0 <= self.stage <= 4):
            raise ValueError(f"Stage must be between 0 and 4, got {self.stage}")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "theme": self.theme,
            "stage": self.stage,
            "description": self.description,
            "keywords": self.keywords
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StageCharacteristic":
        """Create from dictionary"""
        return cls(
            theme=data["theme"],
            stage=data["stage"],
            description=data["description"],
            keywords=data.get("keywords", [])
        )


@dataclass
class ThemeRubric:
    """
    Rubric for a single ESG theme with all stages defined.

    Attributes:
        theme_name: Human-readable theme name
        theme_id: Theme identifier (lowercase with underscores)
        stages: Dictionary mapping stage (0-4) to list of characteristics
    """

    theme_name: str
    theme_id: str
    stages: Dict[int, List[StageCharacteristic]]

    def __post_init__(self) -> None:
        """Validate theme rubric"""
        # Ensure all stages 0-4 are defined
        required_stages = set(range(5))
        defined_stages = set(self.stages.keys())

        if defined_stages != required_stages:
            missing = required_stages - defined_stages
            raise ValueError(
                f"All stages 0-4 must be defined. Missing: {sorted(missing)}"
            )

    def get_stage_characteristics(self, stage: int) -> List[StageCharacteristic]:
        """Get characteristics for a specific stage"""
        if stage not in self.stages:
            raise ValueError(f"Stage {stage} not found in theme {self.theme_id}")

        return self.stages[stage]

    def get_all_characteristics(self) -> List[StageCharacteristic]:
        """Get all characteristics across all stages"""
        all_chars = []
        for stage in sorted(self.stages.keys()):
            all_chars.extend(self.stages[stage])
        return all_chars

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "theme_name": self.theme_name,
            "theme_id": self.theme_id,
            "stages": {
                str(stage): [char.to_dict() for char in chars]
                for stage, chars in self.stages.items()
            }
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ThemeRubric":
        """Create from dictionary"""
        stages = {}
        for stage_str, chars_data in data["stages"].items():
            stage = int(stage_str)
            stages[stage] = [
                StageCharacteristic.from_dict(char_data)
                for char_data in chars_data
            ]

        return cls(
            theme_name=data["theme_name"],
            theme_id=data["theme_id"],
            stages=stages
        )


@dataclass
class MaturityRubric:
    """
    Complete ESG maturity rubric with all themes.

    Attributes:
        themes: Dictionary mapping theme_id to ThemeRubric
        version: Rubric version (e.g., "1.0")
    """

    themes: Dict[str, ThemeRubric]
    version: str

    def __post_init__(self) -> None:
        """Validate rubric"""
        if len(self.themes) == 0:
            raise ValueError("Rubric must contain at least one theme")

    def get_theme(self, theme_id: str) -> ThemeRubric:
        """Get rubric for a specific theme"""
        if theme_id not in self.themes:
            raise KeyError(f"Theme '{theme_id}' not found in rubric")

        return self.themes[theme_id]

    def get_theme_characteristics(self, theme_id: str) -> List[StageCharacteristic]:
        """Get all characteristics for a theme"""
        theme = self.get_theme(theme_id)
        return theme.get_all_characteristics()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "version": self.version,
            "themes": {
                theme_id: theme.to_dict()
                for theme_id, theme in self.themes.items()
            }
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MaturityRubric":
        """Create from dictionary"""
        themes = {}
        for theme_id, theme_data in data["themes"].items():
            themes[theme_id] = ThemeRubric.from_dict(theme_data)

        return cls(
            themes=themes,
            version=data["version"]
        )

    def to_json(self, output_path: Path) -> None:
        """Save rubric to JSON file"""
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)

    def to_parquet(self, output_path: Path) -> None:
        """Save rubric to Parquet file (Phase 5: JSON->Parquet)"""
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Convert rubric to DataFrame format
        rows = []
        for theme_id, theme in sorted(self.themes.items()):
            for stage, chars in sorted(theme.stages.items()):
                for char in chars:
                    rows.append({
                        'version': self.version,
                        'theme_id': theme_id,
                        'theme_name': theme.theme_name,
                        'stage': stage,
                        'description': char.description,
                        'keywords': '|'.join(char.keywords) if char.keywords else ''
                    })

        df = pd.DataFrame(rows)
        df.to_parquet(str(output_path), index=False)

    @classmethod
    def from_json(cls, json_path: Path) -> "MaturityRubric":
        """Load rubric from JSON file"""
        if not json_path.exists():
            raise FileNotFoundError(f"JSON file not found: {json_path}")

        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        return cls.from_dict(data)

    @classmethod
    def from_parquet(cls, parquet_path: Path) -> "MaturityRubric":
        """Load rubric from Parquet file (Phase 5: JSON->Parquet)"""
        if not parquet_path.exists():
            raise FileNotFoundError(f"Parquet file not found: {parquet_path}")

        df = pd.read_parquet(str(parquet_path))

        # Reconstruct rubric from DataFrame
        themes_dict = {}
        for _, row in df.iterrows():
            theme_id = row['theme_id']
            if theme_id not in themes_dict:
                themes_dict[theme_id] = {
                    'theme_name': row['theme_name'],
                    'stages': {}
                }

            stage = int(row['stage'])
            if stage not in themes_dict[theme_id]['stages']:
                themes_dict[theme_id]['stages'][stage] = []

            keywords = [k.strip() for k in row['keywords'].split('|')] if row['keywords'] else []
            char = StageCharacteristic(
                theme=theme_id,
                stage=stage,
                description=row['description'],
                keywords=keywords
            )
            themes_dict[theme_id]['stages'][stage].append(char)

        # Convert back to ThemeRubric objects
        themes = {}
        for theme_id, theme_data in themes_dict.items():
            themes[theme_id] = ThemeRubric(
                theme_name=theme_data['theme_name'],
                theme_id=theme_id,
                stages=theme_data['stages']
            )

        return cls(themes=themes, version=df['version'].iloc[0] if len(df) > 0 else '1.0')
