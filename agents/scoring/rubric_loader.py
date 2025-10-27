"""
Rubric Loader

Parses ESG maturity rubric from markdown format to structured data models.

Per SCA v13.8: Critical Path file - subject to strict quality gates.
"""

from pathlib import Path
import re
from typing import List, Dict, Optional
import logging

from agents.scoring.rubric_models import (
    StageCharacteristic,
    ThemeRubric,
    MaturityRubric
)

logger = logging.getLogger(__name__)


class RubricLoader:
    """
    Load and parse ESG maturity rubric from markdown format.

    Parses rubric markdown with structure:
    - ## Theme N: Theme Name
    - **Theme ID**: `theme_id`
    - ### Stage N: Stage Description
    - - Characteristic 1
    - - Characteristic 2
    """

    def __init__(self) -> None:
        """Initialize rubric loader"""
        self.theme_pattern = re.compile(r'^## Theme \d+: (.+)$', re.MULTILINE)
        self.theme_id_pattern = re.compile(r'^\*\*Theme ID\*\*: `(.+)`$', re.MULTILINE)
        self.stage_pattern = re.compile(r'^### Stage (\d+): .+$', re.MULTILINE)
        self.bullet_pattern = re.compile(r'^- (.+)$', re.MULTILINE)

    def load_from_markdown(self, rubric_path: Path) -> MaturityRubric:
        """
        Load rubric from markdown file.

        Args:
            rubric_path: Path to rubric markdown file

        Returns:
            Parsed MaturityRubric

        Raises:
            FileNotFoundError: If rubric file doesn't exist
            ValueError: If rubric format is invalid
        """
        if not rubric_path.exists():
            raise FileNotFoundError(f"Rubric file not found: {rubric_path}")

        logger.info(f"Loading rubric from {rubric_path}")

        with open(rubric_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Parse version
        version_match = re.search(r'v(\d+\.\d+)', content)
        version = version_match.group(1) if version_match else "1.0"

        # Split into theme sections
        theme_sections = self._split_by_themes(content)

        if len(theme_sections) == 0:
            raise ValueError("Invalid rubric format: No themes found")

        # Parse each theme
        themes = {}
        for theme_section in theme_sections:
            theme = self._parse_theme_section(theme_section)
            if theme:  # Skip themes with no characteristics (e.g., risk_management placeholder)
                themes[theme.theme_id] = theme

        logger.info(f"Loaded {len(themes)} themes from rubric v{version}")

        return MaturityRubric(themes=themes, version=version)

    def _split_by_themes(self, content: str) -> List[str]:
        """Split markdown content by theme sections"""
        # Find all theme headers
        theme_headers = list(self.theme_pattern.finditer(content))

        if not theme_headers:
            return []

        sections = []
        for i, match in enumerate(theme_headers):
            start = match.start()
            end = theme_headers[i + 1].start() if i + 1 < len(theme_headers) else len(content)
            sections.append(content[start:end])

        return sections

    def _parse_theme_section(self, section: str) -> Optional[ThemeRubric]:
        """Parse a single theme section"""
        lines = section.split('\n')

        # Extract theme name
        theme_name = None
        for line in lines:
            match = self.theme_pattern.match(line)
            if match:
                theme_name = match.group(1).strip()
                break

        if not theme_name:
            return None

        # Extract theme ID
        theme_id = None
        for line in lines:
            match = self.theme_id_pattern.match(line.strip())
            if match:
                theme_id = match.group(1).strip()
                break

        if not theme_id:
            # Generate theme_id from theme_name if not found
            theme_id = theme_name.lower().replace(' ', '_').replace(',', '')
            theme_id = re.sub(r'[^a-z0-9_]', '', theme_id)

        # Parse stages
        stages = self._parse_stages(section, theme_id)

        # Skip themes with no characteristics (e.g., placeholders)
        total_chars = sum(len(chars) for chars in stages.values())
        if total_chars == 0:
            logger.warning(f"Skipping theme '{theme_id}' (no characteristics defined)")
            return None

        # Ensure all stages 0-4 exist (fill with empty lists if missing)
        for stage in range(5):
            if stage not in stages:
                stages[stage] = []

        return ThemeRubric(
            theme_name=theme_name,
            theme_id=theme_id,
            stages=stages
        )

    def _parse_stages(self, section: str, theme_id: str) -> Dict[int, List[StageCharacteristic]]:
        """Parse all stages in a theme section"""
        lines = section.split('\n')
        stages = {}
        current_stage = None
        stage_content = []

        for line in lines:
            # Check for stage header
            stage_match = self.stage_pattern.match(line.strip())
            if stage_match:
                # Save previous stage if exists
                if current_stage is not None and stage_content:
                    characteristics = self._parse_characteristics(
                        '\n'.join(stage_content),
                        theme_id,
                        current_stage
                    )
                    stages[current_stage] = characteristics

                # Start new stage
                current_stage = int(stage_match.group(1))
                stage_content = []
            elif current_stage is not None:
                # Accumulate stage content
                stage_content.append(line)

        # Save last stage
        if current_stage is not None and stage_content:
            characteristics = self._parse_characteristics(
                '\n'.join(stage_content),
                theme_id,
                current_stage
            )
            stages[current_stage] = characteristics

        return stages

    def _parse_characteristics(
        self,
        stage_content: str,
        theme_id: str,
        stage: int
    ) -> List[StageCharacteristic]:
        """Parse characteristics from stage content"""
        characteristics = []
        lines = stage_content.split('\n')

        for line in lines:
            match = self.bullet_pattern.match(line.strip())
            if match:
                description = match.group(1).strip()

                # Skip empty or very short descriptions
                if len(description) < 10:
                    continue

                # Extract keywords
                keywords = self._extract_keywords(description)

                characteristic = StageCharacteristic(
                    theme=theme_id,
                    stage=stage,
                    description=description,
                    keywords=keywords
                )

                characteristics.append(characteristic)

        return characteristics

    def _extract_keywords(self, description: str) -> List[str]:
        """
        Extract keywords from characteristic description.

        Extracts:
        - Acronyms (GHG, SBTi, CDP, etc.)
        - Key terms in parentheses
        - Important nouns and verbs
        """
        keywords = []

        # Extract acronyms (2-6 uppercase letters)
        acronyms = re.findall(r'\b[A-Z]{2,6}\b', description)
        keywords.extend(acronyms)

        # Extract terms in parentheses
        parens = re.findall(r'\(([^)]+)\)', description)
        for paren in parens:
            # Split on commas and extract individual terms
            terms = [t.strip() for t in paren.split(',')]
            keywords.extend(terms)

        # Extract key terms (simplified - first few important words)
        # Remove punctuation and split
        cleaned = re.sub(r'[^\w\s]', ' ', description.lower())
        words = cleaned.split()

        # Common important terms
        important_terms = {
            'formal', 'informal', 'systematic', 'evidence', 'comprehensive',
            'targets', 'tracking', 'assurance', 'framework', 'scope', 'methodology',
            'alignment', 'governance', 'integration', 'validation', 'disclosure',
            'automation', 'centralized', 'real-time', 'predictive'
        }

        for word in words:
            if word in important_terms:
                keywords.append(word)

        # Remove duplicates while preserving order
        seen = set()
        unique_keywords = []
        for kw in keywords:
            if kw.lower() not in seen:
                seen.add(kw.lower())
                unique_keywords.append(kw)

        return unique_keywords[:20]  # Limit to 20 keywords

    def _parse_theme_name(self, line: str) -> Optional[str]:
        """Extract theme name from theme header line"""
        match = self.theme_pattern.match(line.strip())
        if match:
            return match.group(1).strip()
        return None

    def _parse_theme_id(self, line: str) -> Optional[str]:
        """Extract theme ID from theme ID line"""
        match = self.theme_id_pattern.match(line.strip())
        if match:
            return match.group(1).strip()
        return None

    def _parse_stage_number(self, line: str) -> Optional[int]:
        """Extract stage number from stage header line"""
        match = self.stage_pattern.match(line.strip())
        if match:
            return int(match.group(1))
        return None

    def cache_rubric(self, rubric: MaturityRubric, cache_path: Path) -> None:
        """
        Cache rubric to JSON file for faster loading.

        Args:
            rubric: Rubric to cache
            cache_path: Path to cache file
        """
        logger.info(f"Caching rubric to {cache_path}")
        rubric.to_parquet(cache_path)

    def load_from_cache(self, cache_path: Path) -> MaturityRubric:
        """
        Load rubric from cached JSON file.

        Args:
            cache_path: Path to cache file

        Returns:
            Loaded MaturityRubric

        Raises:
            FileNotFoundError: If cache file doesn't exist
        """
        if not cache_path.exists():
            raise FileNotFoundError(f"Cache file not found: {cache_path}")

        logger.info(f"Loading rubric from cache {cache_path}")
        return MaturityRubric.from_json(cache_path)
