"""
Query Parser (User Query → QueryIntent)

Parses natural language queries to extract structured intent:
- Company (ticker symbol)
- Year (fiscal year)
- Theme (ESG theme: GHG, TSP, etc.)
- Question type (Scope 1 emissions, targets, assurance, etc.)

Uses pattern matching + fuzzy matching for robustness.
Part of Task 008 - ESG Data Extraction vertical slice (Option 1).
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Dict, Any
import re
from difflib import get_close_matches


class QuestionType(Enum):
    """Types of questions the system can answer"""
    SCOPE_1_EMISSIONS = "scope_1_emissions"
    SCOPE_2_EMISSIONS = "scope_2_emissions"
    SCOPE_3_DISCLOSURE = "scope_3_disclosure"
    SCOPE_12_EMISSIONS = "scope_12_emissions"
    SCOPE_123_COMPREHENSIVE = "scope_123_comprehensive"
    EMISSIONS_TARGET = "emissions_target"
    ASSURANCE_LEVEL = "assurance_level"
    GENERAL = "general"


@dataclass
class QueryIntent:
    """
    Structured representation of user query intent.

    Attributes:
        company: Company ticker symbol (e.g., "MSFT")
        year: Fiscal year (e.g., 2023) or None
        theme: ESG theme (e.g., "GHG")
        question_type: Type of question being asked
        raw_query: Original user query
        confidence: Confidence score (0.0 - 1.0)
        metadata: Additional metadata from parsing
    """
    company: str
    year: Optional[int]
    theme: str
    question_type: QuestionType
    raw_query: str
    confidence: float
    metadata: Dict[str, Any] = field(default_factory=dict)


class QueryParser:
    """
    Parse natural language queries to structured QueryIntent.

    Uses pattern matching to extract company, year, theme, and question type.
    Handles variations in query format and company names.
    """

    # Company name to ticker mapping (for common variations)
    COMPANY_MAP = {
        "microsoft": "MSFT",
        "microsoft corporation": "MSFT",
        "msft": "MSFT",

        "apple": "AAPL",
        "apple inc": "AAPL",
        "apple inc.": "AAPL",
        "aapl": "AAPL",

        "tesla": "TSLA",
        "tsla": "TSLA",

        "exxon": "XOM",
        "exxonmobil": "XOM",
        "exxon mobil": "XOM",
        "exxon mobil corporation": "XOM",
        "xom": "XOM",

        "target": "TGT",
        "target corp": "TGT",
        "target corporation": "TGT",
        "tgt": "TGT",

        # Typo variations for fuzzy matching
        "microsft": "MSFT",  # Common typo
        "microsof": "MSFT"
    }

    # Question type patterns (ordered by specificity - most specific first)
    QUESTION_PATTERNS = [
        # Assurance (check before targets, as queries may contain both keywords)
        (r"assurance|verification|audit|third[- ]party", QuestionType.ASSURANCE_LEVEL),

        # Scope 1, 2, 3 comprehensive
        (r"scope\s+1,?\s*2,?\s*(and|&)?\s*3", QuestionType.SCOPE_123_COMPREHENSIVE),

        # Scope 1 and 2 combined
        (r"scope\s+1\s+and\s+(?:scope\s+)?2", QuestionType.SCOPE_12_EMISSIONS),

        # Scope 3 specific
        (r"scope\s+3", QuestionType.SCOPE_3_DISCLOSURE),

        # Scope 2 specific
        (r"scope\s+2", QuestionType.SCOPE_2_EMISSIONS),

        # Scope 1 specific
        (r"scope\s+1", QuestionType.SCOPE_1_EMISSIONS),

        # Targets and goals
        (r"target|goal|commitment|reduction.*(?:by|for)\s+\d{4}", QuestionType.EMISSIONS_TARGET),
        (r"carbon.*target|emission.*target", QuestionType.EMISSIONS_TARGET),
    ]

    def __init__(self):
        """Initialize query parser with compiled patterns."""
        self.company_map_lower = {k.lower(): v for k, v in self.COMPANY_MAP.items()}
        self.question_patterns_compiled = [
            (re.compile(pattern, re.IGNORECASE), qtype)
            for pattern, qtype in self.QUESTION_PATTERNS
        ]

    def parse(self, query: str) -> QueryIntent:
        """
        Parse user query to structured QueryIntent.

        Args:
            query: Natural language user query

        Returns:
            QueryIntent with extracted company, year, theme, question type

        Raises:
            ValueError: If company cannot be identified
        """
        query_lower = query.lower()
        parsed_patterns = []

        # Extract company
        company = self._extract_company(query_lower)
        if not company:
            raise ValueError(f"Could not identify company in query: {query}")

        # Extract year (optional)
        year = self._extract_year(query_lower)

        # Extract theme (default to GHG for now)
        theme = self._extract_theme(query_lower)

        # Extract question type
        question_type = self._extract_question_type(query_lower, parsed_patterns)

        # Calculate confidence based on how many patterns matched
        confidence = self._calculate_confidence(company, year, question_type, parsed_patterns)

        return QueryIntent(
            company=company,
            year=year,
            theme=theme,
            question_type=question_type,
            raw_query=query,
            confidence=confidence,
            metadata={"parsed_patterns": parsed_patterns}
        )

    def _extract_company(self, query_lower: str) -> Optional[str]:
        """
        Extract company ticker from query.

        Uses exact matching first, then fuzzy matching for typos.

        Args:
            query_lower: Lowercased query string

        Returns:
            Company ticker (e.g., "MSFT") or None
        """
        # Try exact matching first
        for company_name, ticker in self.company_map_lower.items():
            # Use word boundaries to avoid false matches
            pattern = r'\b' + re.escape(company_name) + r'(?:\'s|\')?'
            if re.search(pattern, query_lower):
                return ticker

        # Try fuzzy matching for typos
        words = query_lower.split()
        for word in words:
            # Remove possessive and punctuation
            clean_word = word.rstrip("'s.,!?")
            matches = get_close_matches(clean_word, self.company_map_lower.keys(), n=1, cutoff=0.8)
            if matches:
                return self.company_map_lower[matches[0]]

        return None

    def _extract_year(self, query_lower: str) -> Optional[int]:
        """
        Extract fiscal year from query.

        Supports formats: 2023, FY2023, fiscal year 2023, etc.

        Args:
            query_lower: Lowercased query string

        Returns:
            Year (e.g., 2023) or None
        """
        # Pattern for year (2020-2030 range for recent filings)
        year_patterns = [
            r'\b(202[0-9])\b',  # 2020-2029
            r'\bfy\s*(\d{4})\b',  # FY2023
            r'fiscal\s+year\s+(\d{4})',  # fiscal year 2023
        ]

        for pattern in year_patterns:
            match = re.search(pattern, query_lower)
            if match:
                year = int(match.group(1))
                if 2020 <= year <= 2030:
                    return year

        return None

    def _extract_theme(self, query_lower: str) -> str:
        """
        Extract ESG theme from query.

        For now, defaults to GHG (vertical slice focus).
        Future: Support TSP, OSP, DM, RD, EI, RMM.

        Args:
            query_lower: Lowercased query string

        Returns:
            Theme string (e.g., "GHG")
        """
        # Check for GHG-related keywords
        ghg_keywords = [
            "ghg", "greenhouse gas", "emissions?", "carbon", "co2", "scope"
        ]

        for keyword in ghg_keywords:
            if re.search(r'\b' + keyword + r'\b', query_lower):
                return "GHG"

        # Default to GHG (vertical slice focus)
        return "GHG"

    def _extract_question_type(
        self,
        query_lower: str,
        parsed_patterns: list
    ) -> QuestionType:
        """
        Extract question type from query.

        Uses pattern matching ordered by specificity.

        Args:
            query_lower: Lowercased query string
            parsed_patterns: List to append matched pattern names

        Returns:
            QuestionType enum value
        """
        for pattern, qtype in self.question_patterns_compiled:
            if pattern.search(query_lower):
                parsed_patterns.append(qtype.value)
                return qtype

        # Default to GENERAL if no specific pattern matched
        return QuestionType.GENERAL

    def _calculate_confidence(
        self,
        company: Optional[str],
        year: Optional[int],
        question_type: QuestionType,
        parsed_patterns: list
    ) -> float:
        """
        Calculate confidence score for parsed intent.

        Args:
            company: Extracted company ticker
            year: Extracted year
            question_type: Extracted question type
            parsed_patterns: List of matched patterns

        Returns:
            Confidence score (0.0 - 1.0)
        """
        confidence = 0.0

        # Company identified: +0.4
        if company:
            confidence += 0.4

        # Year identified: +0.2 (optional for some queries)
        if year:
            confidence += 0.2

        # Specific question type (not GENERAL): +0.3
        if question_type != QuestionType.GENERAL:
            confidence += 0.3
        else:
            confidence += 0.1  # General questions still get some credit

        # Pattern matched: +0.1
        if parsed_patterns:
            confidence += 0.1

        return min(1.0, confidence)
