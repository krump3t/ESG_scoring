"""
HTML Parser for SEC 10-K Filings

Parses SEC EDGAR HTML filings and provides page offset tracking for evidence citation.
Designed to work with the evidence extraction matchers in agents/parser/matchers/.

Key features:
- Extracts clean text from HTML sections
- Tracks approximate page numbers for citation purposes
- Handles SEC-specific HTML structure (tables, exhibits, etc.)
- Provides text chunking for matcher processing
"""

from dataclasses import dataclass
from typing import Optional, List, Dict, Tuple
from pathlib import Path
import re
import hashlib

from bs4 import BeautifulSoup, Tag


@dataclass
class HTMLSection:
    """Represents a section of an HTML document with page offset tracking"""
    section_name: str
    text: str
    start_offset: int  # Character offset from document start
    end_offset: int
    page_no: int  # Approximate page number (for 8.5x11 paper at ~3000 chars/page)
    html_tag: Optional[str] = None
    metadata: Optional[Dict] = None


class SECHTMLParser:
    """
    Parser for SEC EDGAR HTML filings (10-K, 20-F, etc.)

    Handles SEC-specific HTML structure and provides text extraction
    with page offset tracking for evidence citation.
    """

    # SEC 10-K standard sections
    STANDARD_SECTIONS = {
        "item_1a": ["Item 1A", "Risk Factors"],
        "item_1": ["Item 1", "Business"],
        "item_7": ["Item 7", "Management's Discussion"],
        "item_8": ["Item 8", "Financial Statements"],
        "item_7a": ["Item 7A", "Quantitative and Qualitative Disclosures"]
    }

    # Approximate characters per page (8.5x11 paper, 12pt font, single-spaced)
    CHARS_PER_PAGE = 3000

    def __init__(self):
        """Initialize SEC HTML parser"""
        self.document_text: str = ""
        self.sections: List[HTMLSection] = []
        self.page_offsets: Dict[int, int] = {}  # page_no -> char_offset

    def parse_filing(self, html_content: str, filing_url: str = "") -> Tuple[str, Dict[int, int]]:
        """
        Parse SEC HTML filing and extract clean text with page offsets.

        Args:
            html_content: Raw HTML content from SEC EDGAR
            filing_url: Optional URL for traceability

        Returns:
            Tuple of (full_text, page_offsets_dict)
            page_offsets_dict maps page_no -> character offset
        """
        soup = BeautifulSoup(html_content, 'lxml')

        # Remove script and style tags
        for tag in soup(['script', 'style', 'meta', 'link']):
            tag.decompose()

        # Extract text from body
        body = soup.find('body')
        if not body:
            # Fallback: use entire document
            body = soup

        # Get clean text
        self.document_text = self._clean_text(body.get_text())

        # Calculate page offsets
        self.page_offsets = self._calculate_page_offsets(self.document_text)

        # Extract sections
        self.sections = self._extract_sections(soup)

        return self.document_text, self.page_offsets

    def _clean_text(self, text: str) -> str:
        """
        Clean extracted text by:
        - Normalizing whitespace
        - Removing excessive line breaks
        - Preserving paragraph structure
        """
        # Replace multiple spaces with single space
        text = re.sub(r'[ \t]+', ' ', text)

        # Replace 3+ newlines with 2 (preserve paragraph breaks)
        text = re.sub(r'\n{3,}', '\n\n', text)

        # Remove leading/trailing whitespace from each line
        lines = [line.strip() for line in text.split('\n')]
        text = '\n'.join(lines)

        return text.strip()

    def _calculate_page_offsets(self, text: str) -> Dict[int, int]:
        """
        Calculate approximate page numbers based on character count.

        Assumes standard 8.5x11 page with ~3000 characters.
        Used for evidence citation (e.g., "found on page 42").

        Returns:
            Dict mapping page_no -> character_offset
        """
        page_offsets = {}
        total_chars = len(text)
        page_no = 1

        # Always have at least page 1, even for empty documents
        if total_chars == 0:
            page_offsets[1] = 0
            return page_offsets

        for offset in range(0, total_chars, self.CHARS_PER_PAGE):
            page_offsets[page_no] = offset
            page_no += 1

        return page_offsets

    def get_page_number(self, char_offset: int) -> int:
        """
        Get approximate page number for a given character offset.

        Args:
            char_offset: Character position in document

        Returns:
            Approximate page number (1-indexed)
        """
        return (char_offset // self.CHARS_PER_PAGE) + 1

    def _extract_sections(self, soup: BeautifulSoup) -> List[HTMLSection]:
        """
        Extract standard SEC 10-K sections.

        Looks for Item 1, Item 1A, Item 7, etc.
        """
        sections = []

        # Simple approach: find headers containing "Item X"
        # More sophisticated extraction could use SEC XML tags

        # For now, return the full document as one section
        # TODO: Implement proper section detection
        full_section = HTMLSection(
            section_name="Full Document",
            text=self.document_text,
            start_offset=0,
            end_offset=len(self.document_text),
            page_no=1,
            html_tag="body"
        )
        sections.append(full_section)

        return sections

    def get_context_window(
        self,
        match_start: int,
        match_end: int,
        words_before: int = 15,
        words_after: int = 15
    ) -> Tuple[str, str, str]:
        """
        Get context window around a match for evidence extraction.

        Args:
            match_start: Character offset of match start
            match_end: Character offset of match end
            words_before: Number of words before match to include
            words_after: Number of words after match to include

        Returns:
            Tuple of (context_before, match_text, context_after)
        """
        # Get text before match
        text_before = self.document_text[:match_start]
        words_b = text_before.split()[-words_before:]
        context_before = ' '.join(words_b)

        # Get match text
        match_text = self.document_text[match_start:match_end]

        # Get text after match
        text_after = self.document_text[match_end:]
        words_a = text_after.split()[:words_after]
        context_after = ' '.join(words_a)

        return context_before, match_text, context_after

    def extract_30_word_context(self, match_start: int, match_end: int) -> str:
        """
        Extract 30-word context (15 before + match + 15 after) as specified
        in ESG Maturity Rubric v3.0 evidence requirements.

        Args:
            match_start: Character offset of match start
            match_end: Character offset of match end

        Returns:
            30-word context string for evidence storage
        """
        context_before, match_text, context_after = self.get_context_window(
            match_start, match_end, words_before=15, words_after=15
        )

        # Combine with ellipsis markers
        full_context = f"...{context_before} {match_text} {context_after}..."
        return full_context.strip()
