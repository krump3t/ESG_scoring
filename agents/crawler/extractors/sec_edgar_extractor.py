"""
SEC EDGAR Cached Data Extractor

Extracts findings from cached SEC EDGAR 10-K data (Item 1A Risk Factors)

Input: JSON file with SEC EDGAR API response structure
Output: Normalized findings list (compatible with evidence_aggregator)

Author: SCA v13.8-MEA
Task: DEMO-001 Multi-Source E2E Demo
Protocol: No mocks, reads real cached API data
"""
import json
from typing import List, Dict, Any
from pathlib import Path


class SECEdgarExtractor:
    """
    Extract findings from cached SEC EDGAR 10-K data

    Focuses on Item 1A Risk Factors (climate-related risks)
    """

    def __init__(self) -> None:
        """Initialize SEC EDGAR extractor"""
        self.name = "SECEdgarExtractor"

    def extract(self, cache_path: str) -> Dict[str, Any]:
        """
        Extract findings from cached SEC EDGAR JSON

        Args:
            cache_path: Path to cached SEC EDGAR JSON file

        Returns:
            {
                "findings": List[Dict],  # Normalized finding records
                "metadata": Dict  # Source metadata
            }
        """
        # Read cached data
        with open(cache_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Extract Item 1A text
        item_1a = data.get("item_1a_risk_factors", {})
        risk_text = item_1a.get("text", "")
        themes_detected = item_1a.get("themes_detected", [])

        if not risk_text:
            return {"findings": [], "metadata": data.get("metadata", {})}

        # Split risk text into sections (by paragraph)
        sections = self._split_into_sections(risk_text)

        # Create findings for each section
        findings = []
        char_offset = 0
        for idx, section_text in enumerate(sections):
            # Skip very short sections (<50 chars)
            if len(section_text.strip()) < 50:
                char_offset += len(section_text)
                continue

            # Determine theme from section text
            theme = self._detect_theme(section_text, themes_detected)

            finding = {
                "finding_id": f"sec-{idx+1:03d}",
                "text": section_text.strip(),
                "theme": theme,
                "source_id": "sec_edgar",
                "source_type": "10-K",
                "doc_id": data.get("source_id", "sec-edgar-unknown"),
                "page_no": None,  # SEC filings don't have page numbers
                "char_start": char_offset,
                "char_end": char_offset + len(section_text),
                "entities": self._extract_entities(section_text),
                "frameworks": item_1a.get("entities", {}).get("frameworks", []),
                "org_id": data.get("company_name", "Unknown"),
                "year": data.get("year", None)
            }
            findings.append(finding)
            char_offset += len(section_text)

        return {
            "findings": findings,
            "metadata": {
                "source": "SEC EDGAR",
                "company": data.get("company_name"),
                "ticker": data.get("ticker"),
                "year": data.get("year"),
                "report_type": data.get("report_type"),
                "sha256": data.get("metadata", {}).get("sha256")
            }
        }

    def _split_into_sections(self, text: str) -> List[str]:
        """
        Split risk factors text into sections

        Uses double newlines as section boundaries
        """
        # Split by double newline (paragraph boundaries)
        sections = text.split('\n\n')
        return [s.strip() for s in sections if s.strip()]

    def _detect_theme(self, text: str, suggested_themes: List[str]) -> str:
        """
        Detect theme from section text

        Uses keyword matching to map to rubric themes
        """
        text_lower = text.lower()

        # Theme keywords (rubric-aligned)
        theme_keywords = {
            "Climate": ["climate", "carbon", "emissions", "greenhouse gas", "ghg", "warming"],
            "Risk": ["risk", "vulnerability", "exposure", "uncertain"],
            "Governance": ["board", "committee", "oversight", "governance", "audit"],
            "Operations": ["supply chain", "operations", "manufacturing", "facilities", "logistics"],
            "GHG": ["scope 1", "scope 2", "scope 3", "emissions inventory", "carbon footprint"],
            "TSP": ["target", "goal", "commitment", "2030", "net zero", "carbon neutral"],
            "RD": ["disclosure", "reporting", "transparency", "stakeholder"]
        }

        # Count matches for each theme
        theme_scores = {}
        for theme, keywords in theme_keywords.items():
            score = sum(1 for kw in keywords if kw in text_lower)
            if score > 0:
                theme_scores[theme] = score

        # Return highest scoring theme
        if theme_scores:
            return max(theme_scores, key=theme_scores.get)

        # Fallback to suggested themes
        if suggested_themes:
            return suggested_themes[0]

        return "Risk"  # Default for SEC Item 1A

    def _extract_entities(self, text: str) -> List[str]:
        """
        Extract entities from text (simple keyword extraction)

        Looks for years, percentages, and key terms
        """
        entities = []

        # Extract years (2020-2050)
        import re
        years = re.findall(r'\b(20[2-5]\d)\b', text)
        entities.extend(years)

        # Extract percentages
        percentages = re.findall(r'\b\d+%\b', text)
        entities.extend(percentages)

        # Extract key terms
        key_terms = [
            "Board of Directors", "Audit Committee", "carbon neutral",
            "renewable energy", "climate change", "supply chain"
        ]
        for term in key_terms:
            if term.lower() in text.lower():
                entities.append(term)

        return list(set(entities))  # Deduplicate
