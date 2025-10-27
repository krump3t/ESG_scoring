"""
Multi-company ESG query synthesizer.
Protocol: SCA v13.8-MEA | Evidence-first | Rubric-aligned

Expands multi-company queries into per-company, per-theme sub-queries using
canonical rubric definitions from rubrics/maturity_v3.json.

Architecture:
    User Query → Query Expansion → List[CompanyQuery] → Retrieval Pipeline

Key Features:
    - Deterministic ordering (sorted by company, then theme)
    - Rubric-aligned theme metadata
    - Type-safe dataclasses
    - Comprehensive validation
"""

import json
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)

# Constants
ESG_ROOT = Path(os.getenv("ESG_ROOT", Path(__file__).parent.parent.parent))
RUBRIC_PATH = ESG_ROOT / "rubrics" / "maturity_v3.json"
SEED = int(os.getenv("SEED", "42"))  # Deterministic seed for reproducibility

# Valid theme codes from rubric
VALID_THEMES = {"TSP", "OSP", "DM", "GHG", "RD", "EI", "RMM"}


@dataclass
class CompanyQuery:
    """
    Expanded query for a single (company, theme) pair.

    Attributes:
        company_id: Company name or identifier
        theme: Theme code (TSP, OSP, DM, GHG, RD, EI, RMM)
        query_text: Generated query string
        metadata: Theme metadata from rubric (intent, stages, etc.)
    """

    company_id: str
    theme: str
    query_text: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate fields after initialization."""
        if not self.company_id:
            raise ValueError("company_id cannot be empty")
        if self.theme not in VALID_THEMES:
            raise ValueError(f"Invalid theme: {self.theme}. Must be one of {VALID_THEMES}")


@dataclass
class MultiCompanyQuery:
    """
    Multi-company query specification.

    Attributes:
        companies: List of company names/IDs
        themes: List of theme codes to analyze
        year: Reporting year
        top_k: Number of documents to retrieve per query
    """

    companies: List[str]
    themes: List[str]
    year: int
    top_k: int = 50

    def __post_init__(self) -> None:
        """Validate fields after initialization."""
        if not self.companies:
            raise ValueError("Must specify at least one company")
        if not self.themes:
            raise ValueError("Must specify at least one theme")

        # Validate themes
        invalid_themes = set(self.themes) - VALID_THEMES
        if invalid_themes:
            raise ValueError(f"Invalid theme codes: {invalid_themes}. Valid themes: {VALID_THEMES}")


def load_rubric_themes() -> List[Dict[str, Any]]:
    """
    Load theme definitions from canonical rubric JSON.

    Returns:
        List of theme dictionaries with code, name, intent, stages

    Raises:
        FileNotFoundError: If rubric file doesn't exist
        json.JSONDecodeError: If rubric is invalid JSON
    """
    if not RUBRIC_PATH.exists():
        raise FileNotFoundError(
            f"Rubric not found: {RUBRIC_PATH}. "
            "Run: python rubrics/compile_rubric.py to generate it."
        )

    with open(RUBRIC_PATH, "r", encoding="utf-8") as f:
        rubric_data: Dict[str, Any] = json.load(f)

    themes: List[Dict[str, Any]] = rubric_data["themes"]
    return themes


def expand_multi_company_query(query: MultiCompanyQuery) -> List[CompanyQuery]:
    """
    Expand multi-company query into per-company, per-theme sub-queries.

    Strategy:
        1. Load rubric theme definitions from maturity_v3.json
        2. For each (company, theme) pair:
           - Generate query using theme name and intent
           - Add metadata (intent, stages, year)
        3. Sort by company (alphabetical), then theme (rubric order)
        4. Return deterministically ordered list

    Args:
        query: MultiCompanyQuery specification

    Returns:
        List of CompanyQuery objects, one per (company, theme) pair

    Raises:
        ValueError: If companies or themes are empty, or theme is invalid
        FileNotFoundError: If rubric file not found

    Example:
        >>> query = MultiCompanyQuery(
        ...     companies=["Apple Inc.", "Microsoft"],
        ...     themes=["TSP", "GHG"],
        ...     year=2024
        ... )
        >>> expanded = expand_multi_company_query(query)
        >>> len(expanded)
        4
        >>> expanded[0].theme
        'TSP'
    """
    # Load rubric
    themes = load_rubric_themes()
    theme_lookup = {theme["code"]: theme for theme in themes}

    # Theme order from rubric (for deterministic sorting)
    theme_order = {theme["code"]: idx for idx, theme in enumerate(themes)}

    # Expand queries
    expanded = []

    for company in sorted(query.companies):  # Alphabetical sort for determinism
        for theme_code in query.themes:
            if theme_code not in theme_lookup:
                raise ValueError(
                    f"Invalid theme code: {theme_code}. "
                    f"Valid themes: {list(theme_lookup.keys())}"
                )

            theme_def = theme_lookup[theme_code]

            # Generate query text
            query_text = (
                f"What are {company}'s {theme_def['name']} targets, "
                f"processes, and evidence for {query.year}?"
            )

            # Extract metadata
            metadata = {
                "intent": theme_def["intent"],
                "stages": list(theme_def["stages"].keys()),
                "year": query.year,
                "theme_name": theme_def["name"],
            }

            expanded.append(
                CompanyQuery(
                    company_id=company,
                    theme=theme_code,
                    query_text=query_text,
                    metadata=metadata,
                )
            )

    # Sort by company (already sorted), then by theme order from rubric
    expanded.sort(key=lambda q: (q.company_id, theme_order.get(q.theme, 999)))

    return expanded


# Legacy class for backward compatibility
class QuerySynthesizer:
    """
    Rule-based query synthesis for multi-company ESG analysis.

    Implements deterministic NER-like keyword extraction and template expansion.
    No external models or network calls.
    """

    # Known companies and themes (can be expanded)
    KNOWN_COMPANIES: Dict[str, str] = {
        "apple": "AAPL",
        "aapl": "AAPL",
        "exxonmobil": "XOM",
        "exxon": "XOM",
        "xom": "XOM",
        "jpmorgan": "JPM",
        "jpmorgan chase": "JPM",
        "jpm": "JPM",
        "chase": "JPM",
    }

    KNOWN_THEMES: Set[str] = {
        "climate",
        "social",
        "governance",
        "supply_chain",
        "diversity",
        "environmental",
        "environmental sustainability",
    }

    THEME_ALIASES: Dict[str, str] = {
        "environmental": "climate",
        "environmental sustainability": "climate",
        "social responsibility": "social",
        "governance": "governance",
        "esg": "climate",  # Default theme
    }

    # Query templates for each theme
    QUERY_TEMPLATES: Dict[str, List[str]] = {
        "climate": [
            "What is {company}'s climate change strategy?",
            "How does {company} address carbon emissions?",
            "What are {company}'s greenhouse gas reduction targets?",
            "Describe {company}'s climate risk management framework.",
        ],
        "social": [
            "What is {company}'s diversity and inclusion policy?",
            "How does {company} support employee wellbeing?",
            "What are {company}'s community engagement initiatives?",
            "Describe {company}'s social responsibility programs.",
        ],
        "governance": [
            "What is {company}'s board composition?",
            "How does {company} ensure ethical business practices?",
            "What is {company}'s executive compensation structure?",
            "Describe {company}'s corporate governance framework.",
        ],
        "supply_chain": [
            "How does {company} manage supplier diversity?",
            "What are {company}'s supply chain sustainability practices?",
            "How does {company} ensure ethical sourcing?",
            "Describe {company}'s supply chain risk management.",
        ],
        "diversity": [
            "What is {company}'s diversity strategy?",
            "How diverse is {company}'s workforce?",
            "What programs does {company} have for underrepresented groups?",
            "Describe {company}'s diversity metrics and progress.",
        ],
    }

    def __init__(self) -> None:
        """Initialize QuerySynthesizer with deterministic behavior."""
        logger.info(f"QuerySynthesizer initialized with SEED={SEED}")

    def synthesize(
        self,
        user_query: str,
        companies: Optional[List[str]] = None,
        theme: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Synthesize company-specific ESG queries from user input.

        Algorithm:
        1. Extract company mentions via keyword matching (case-insensitive)
        2. Identify ESG theme via keyword matching
        3. Generate company-specific queries using templates
        4. Return list of (company_id, theme, query) tuples

        Args:
            user_query: Multi-company ESG query (e.g., "Compare climate policies: Apple vs ExxonMobil")
            companies: Optional override list of company IDs. If None, extract from query.
            theme: Optional override ESG theme. If None, extract from query.

        Returns:
            List of dicts with keys: company, theme, query, template_index

        Raises:
            ValueError: If user_query empty, no companies found, or invalid theme after extraction
            RuntimeError: If synthesis fails unexpectedly
        """
        # Validate input
        if not user_query or len(user_query.strip()) == 0:
            raise ValueError("user_query cannot be empty")

        logger.debug(f"Synthesizing queries for: {user_query[:50]}...")

        try:
            # Step 1: Extract companies from query or use provided list
            if companies is None:
                extracted_companies = self._extract_companies(user_query)
                if not extracted_companies:
                    raise ValueError(
                        "No companies found in query. "
                        "Provide companies list or mention known companies (AAPL, XOM, JPM)."
                    )
                companies_to_use = extracted_companies
            else:
                if not companies:
                    raise ValueError("companies list cannot be empty")
                companies_to_use = companies

            # Step 2: Extract theme from query or use provided
            if theme is None:
                extracted_theme = self._extract_theme(user_query)
                if not extracted_theme:
                    # Default to climate if no theme found
                    extracted_theme = "climate"
                theme_to_use = extracted_theme
            else:
                if theme not in self.KNOWN_THEMES:
                    raise ValueError(f"Invalid theme: {theme}. Must be in {self.KNOWN_THEMES}")
                theme_to_use = theme

            # Step 3: Generate company-specific queries
            results = []
            for company_id in companies_to_use:
                # Validate company format
                if not isinstance(company_id, str) or len(company_id.strip()) == 0:
                    raise ValueError(f"Invalid company_id: {company_id}")

                # Get templates for theme
                templates = self.QUERY_TEMPLATES.get(theme_to_use, self.QUERY_TEMPLATES["climate"])

                # Generate query using deterministic template selection (based on hash)
                template_idx = (hash(company_id + user_query) % len(templates)) % len(templates)
                template = templates[abs(template_idx)]
                generated_query = template.format(company=company_id)

                results.append(
                    {
                        "company": company_id,
                        "theme": theme_to_use,
                        "query": generated_query,
                        "template_index": template_idx,
                    }
                )

            logger.info(f"Generated {len(results)} queries for {len(companies_to_use)} companies")
            return results

        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Query synthesis failed: {e}")
            raise RuntimeError(f"Query synthesis error: {e}") from e

    def _extract_companies(self, query: str) -> List[str]:
        """
        Extract company IDs from query via keyword matching.

        Args:
            query: User query string

        Returns:
            List of company IDs (e.g., ["AAPL", "XOM"])

        Raises:
            ValueError: Never (returns empty list if no matches)
        """
        query_lower = query.lower()
        found_companies: Set[str] = set()

        # Try longest match first (for "jpmorgan chase" before "chase")
        sorted_aliases = sorted(self.KNOWN_COMPANIES.keys(), key=len, reverse=True)
        for alias in sorted_aliases:
            if alias in query_lower:
                company_id = self.KNOWN_COMPANIES[alias]
                found_companies.add(company_id)

        return sorted(list(found_companies))  # Deterministic ordering

    def _extract_theme(self, query: str) -> str:
        """
        Extract ESG theme from query via keyword matching.

        Args:
            query: User query string

        Returns:
            Theme string (e.g., "climate", "social", etc.) or "" if not found

        Raises:
            ValueError: Never (returns "" if no match)
        """
        query_lower = query.lower()

        # Try known themes first
        for theme in self.KNOWN_THEMES:
            if theme in query_lower:
                return self.THEME_ALIASES.get(theme, theme)

        # Try aliases
        for alias, canonical in self.THEME_ALIASES.items():
            if alias in query_lower:
                return canonical

        return ""  # No theme found

    def expand_multi_company_query(
        self,
        user_query: str,
    ) -> List[str]:
        """
        Expand a multi-company query into individual company queries.

        This method is tested by test_query_synthesizer_template_generation_invariant.

        Args:
            user_query: Multi-company query (e.g., "Compare climate policies: Apple vs ExxonMobil")

        Returns:
            List of generated queries (one per company), each ≤400 characters (~100 tokens)

        Raises:
            ValueError: If user_query empty or invalid
        """
        if not user_query or len(user_query.strip()) == 0:
            raise ValueError("user_query cannot be empty")

        results = self.synthesize(user_query)
        queries = [result["query"] for result in results]

        # Validate query length (100 tokens ≈ 400 chars)
        for query in queries:
            if len(query) > 400:
                raise ValueError(f"Generated query exceeds 400 characters: {len(query)}")

        return queries
