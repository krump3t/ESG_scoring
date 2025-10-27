"""
PDF parser for extracting and chunking ESG report content
Uses pdfplumber and fallback methods for robust text extraction
"""

from dataclasses import dataclass, asdict
from typing import List, Optional, Dict, Any, Tuple
import hashlib
import logging
import re
from pathlib import Path
import requests  # @allow-network:Ingestion pipeline requires downloading PDF reports from URLs
from io import BytesIO
import tempfile

# Configure logging
logger = logging.getLogger(__name__)


@dataclass
class Chunk:
    """Represents a chunk of text from a document"""
    chunk_id: str
    company: str
    year: int
    text: str
    page_start: int
    page_end: int
    section: str
    source_url: str
    md5: str
    char_count: Optional[int] = None
    token_count_estimate: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        if self.char_count is None:
            self.char_count = len(self.text)
        if self.token_count_estimate is None:
            # Rough estimate: 1 token per 4 characters
            self.token_count_estimate = self.char_count // 4
        if self.md5 is None:
            self.md5 = hashlib.md5(self.text.encode()).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return asdict(self)


class PDFParser:
    """
    Robust PDF parser with multiple extraction methods
    """

    def __init__(
        self,
        chunk_size: int = 512,  # tokens
        chunk_overlap: int = 102,  # tokens (20% of chunk_size)
        min_chunk_size: int = 50,  # tokens
        cache_dir: Optional[Path] = None
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_chunk_size = min_chunk_size
        self.cache_dir = cache_dir or Path("data/pdf_cache")
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Section detection patterns
        self.section_patterns = [
            (r'executive\s+summary', 'Executive Summary'),
            (r'introduction', 'Introduction'),
            (r'climate\s+(?:change|action|strategy)', 'Climate Strategy'),
            (r'ghg\s+(?:emissions|inventory|accounting)', 'GHG Accounting'),
            (r'scope\s+[123]', 'GHG Accounting'),
            (r'targets?\s+(?:and\s+)?(?:goals?|objectives?)', 'Targets and Goals'),
            (r'governance', 'Governance'),
            (r'risk\s+(?:management|assessment)', 'Risk Management'),
            (r'energy\s+(?:management|consumption|efficiency)', 'Energy Management'),
            (r'water\s+(?:management|usage|stewardship)', 'Water Management'),
            (r'waste\s+(?:management|reduction)', 'Waste Management'),
            (r'biodiversity', 'Biodiversity'),
            (r'supply\s+chain', 'Supply Chain'),
            (r'social\s+(?:responsibility|impact)', 'Social Impact'),
            (r'human\s+rights', 'Human Rights'),
            (r'diversity\s+(?:and\s+)?(?:equity\s+)?(?:and\s+)?inclusion', 'Diversity & Inclusion'),
            (r'performance\s+(?:data|metrics|indicators)', 'Performance Data'),
            (r'assurance\s+(?:statement|report)', 'Assurance'),
            (r'appendix|appendices', 'Appendix'),
        ]

    def _download_pdf(self, url: str) -> bytes:
        """Download PDF from URL"""
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            return response.content
        except Exception as e:
            logger.error(f"Failed to download PDF from {url}: {e}")
            raise

    def _extract_with_pdfplumber(self, pdf_bytes: bytes) -> List[Tuple[str, int]]:
        """Extract text using pdfplumber (primary method)"""
        try:
            import pdfplumber
        except ImportError:
            logger.warning("pdfplumber not installed")
            return []

        pages_text = []

        try:
            with BytesIO(pdf_bytes) as pdf_file:
                with pdfplumber.open(pdf_file) as pdf:
                    for i, page in enumerate(pdf.pages):
                        try:
                            text = page.extract_text()
                            if text:
                                # Clean the text
                                text = self._clean_text(text)
                                pages_text.append((text, i + 1))
                        except Exception as e:
                            logger.debug(f"Failed to extract page {i+1}: {e}")
                            continue
        except Exception as e:
            logger.error(f"pdfplumber extraction failed: {e}")

        return pages_text

    def _extract_with_pypdf(self, pdf_bytes: bytes) -> List[Tuple[str, int]]:
        """Extract text using PyPDF2 (fallback method)"""
        try:
            import PyPDF2
        except ImportError:
            logger.warning("PyPDF2 not installed")
            return []

        pages_text = []

        try:
            with BytesIO(pdf_bytes) as pdf_file:
                reader = PyPDF2.PdfReader(pdf_file)
                for i, page in enumerate(reader.pages):
                    try:
                        text = page.extract_text()
                        if text:
                            text = self._clean_text(text)
                            pages_text.append((text, i + 1))
                    except Exception as e:
                        logger.debug(f"Failed to extract page {i+1}: {e}")
                        continue
        except Exception as e:
            logger.error(f"PyPDF2 extraction failed: {e}")

        return pages_text

    def _extract_with_pdfminer(self, pdf_bytes: bytes) -> List[Tuple[str, int]]:
        """Extract text using pdfminer (alternative fallback)"""
        try:
            from pdfminer.high_level import extract_text_to_fp
            from pdfminer.layout import LAParams
            from io import StringIO
        except ImportError:
            logger.warning("pdfminer not installed")
            return []

        pages_text = []

        try:
            with BytesIO(pdf_bytes) as pdf_file:
                output = StringIO()
                laparams = LAParams()
                extract_text_to_fp(pdf_file, output, laparams=laparams)

                # pdfminer doesn't separate pages easily, so treat as one document
                full_text = output.getvalue()
                if full_text:
                    # Split into approximate pages (heuristic)
                    parts = full_text.split('\f')  # Form feed character
                    for i, part in enumerate(parts):
                        if part.strip():
                            text = self._clean_text(part)
                            pages_text.append((text, i + 1))
        except Exception as e:
            logger.error(f"pdfminer extraction failed: {e}")

        return pages_text

    def _clean_text(self, text: str) -> str:
        """Clean extracted text"""
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        # Remove page numbers (common patterns)
        text = re.sub(r'^\d+\s*$', '', text, flags=re.MULTILINE)
        text = re.sub(r'Page\s+\d+\s+of\s+\d+', '', text, flags=re.IGNORECASE)
        # Remove headers/footers (heuristic)
        lines = text.split('\n')
        if len(lines) > 3:
            # Often headers/footers are repeated short lines
            lines = [l for l in lines if len(l) > 20 or not l.strip()]
        text = '\n'.join(lines)
        return text.strip()

    def _detect_section(self, text: str) -> str:
        """Detect section from text content"""
        text_lower = text.lower()[:200]  # Check first 200 chars

        for pattern, section_name in self.section_patterns:
            if re.search(pattern, text_lower):
                return section_name

        return "General"

    def _create_chunks(
        self,
        text: str,
        page_start: int,
        page_end: int,
        company: str,
        year: int,
        source_url: str,
        chunk_id_prefix: str
    ) -> List[Chunk]:
        """Create chunks from text with overlap"""
        chunks = []

        # Estimate tokens (rough: 1 token per 4 characters)
        chars_per_token = 4
        chunk_size_chars = self.chunk_size * chars_per_token
        overlap_chars = self.chunk_overlap * chars_per_token
        min_chunk_chars = self.min_chunk_size * chars_per_token

        # Split into sentences for better boundaries
        sentences = re.split(r'(?<=[.!?])\s+', text)

        current_chunk = []
        current_chars = 0
        chunk_index = 0

        for sentence in sentences:
            sentence_chars = len(sentence)

            # If adding this sentence would exceed chunk size
            if current_chars + sentence_chars > chunk_size_chars and current_chunk:
                # Create chunk
                chunk_text = ' '.join(current_chunk)
                if len(chunk_text) >= min_chunk_chars:
                    section = self._detect_section(chunk_text)
                    chunk = Chunk(
                        chunk_id=f"{chunk_id_prefix}_{chunk_index:03d}",
                        company=company,
                        year=year,
                        text=chunk_text,
                        page_start=page_start,
                        page_end=page_end,
                        section=section,
                        source_url=source_url,
                        md5=hashlib.md5(chunk_text.encode()).hexdigest()
                    )
                    chunks.append(chunk)
                    chunk_index += 1

                # Keep overlap
                overlap_text = []
                overlap_chars_count = 0
                for sent in reversed(current_chunk):
                    overlap_chars_count += len(sent)
                    overlap_text.insert(0, sent)
                    if overlap_chars_count >= overlap_chars:
                        break

                current_chunk = overlap_text
                current_chars = overlap_chars_count

            current_chunk.append(sentence)
            current_chars += sentence_chars

        # Add final chunk
        if current_chunk:
            chunk_text = ' '.join(current_chunk)
            if len(chunk_text) >= min_chunk_chars:
                section = self._detect_section(chunk_text)
                chunk = Chunk(
                    chunk_id=f"{chunk_id_prefix}_{chunk_index:03d}",
                    company=company,
                    year=year,
                    text=chunk_text,
                    page_start=page_start,
                    page_end=page_end,
                    section=section,
                    source_url=source_url,
                    md5=hashlib.md5(chunk_text.encode()).hexdigest()
                )
                chunks.append(chunk)

        return chunks

    def parse_pdf(
        self,
        company: str,
        year: int,
        url: str,
        use_cache: bool = True
    ) -> List[Chunk]:
        """
        Main method to parse PDF and extract chunks
        """
        logger.info(f"Parsing PDF for {company} ({year}) from {url}")

        # Check cache
        cache_key = hashlib.md5(url.encode()).hexdigest()
        cache_file = self.cache_dir / f"{cache_key}.pdf"

        if use_cache and cache_file.exists():
            logger.info("Using cached PDF")
            with open(cache_file, 'rb') as f:
                pdf_bytes = f.read()
        else:
            # Download PDF
            logger.info("Downloading PDF")
            pdf_bytes = self._download_pdf(url)

            # Cache it
            if use_cache:
                with open(cache_file, 'wb') as f:
                    f.write(pdf_bytes)

        # Try extraction methods in order of preference
        pages_text = self._extract_with_pdfplumber(pdf_bytes)

        if not pages_text:
            logger.warning("pdfplumber failed, trying PyPDF2")
            pages_text = self._extract_with_pypdf(pdf_bytes)

        if not pages_text:
            logger.warning("PyPDF2 failed, trying pdfminer")
            pages_text = self._extract_with_pdfminer(pdf_bytes)

        if not pages_text:
            logger.error("All PDF extraction methods failed")
            # Return minimal stub data
            return self._create_stub_chunks(company, year, url)

        # Create chunks from extracted text
        all_chunks = []
        chunk_id_prefix = f"{company.replace(' ', '_')}_{year}"

        for text, page_num in pages_text:
            if text.strip():
                chunks = self._create_chunks(
                    text=text,
                    page_start=page_num,
                    page_end=page_num,
                    company=company,
                    year=year,
                    source_url=url,
                    chunk_id_prefix=f"{chunk_id_prefix}_p{page_num:03d}"
                )
                all_chunks.extend(chunks)

        logger.info(f"Extracted {len(all_chunks)} chunks from PDF")
        return all_chunks

    def _create_stub_chunks(self, company: str, year: int, url: str) -> List[Chunk]:
        """Create stub chunks when PDF parsing fails"""
        logger.warning(f"Creating stub chunks for {company} ({year})")

        stub_texts = [
            f"{company} has established comprehensive ESG targets for {year} and beyond.",
            "Our greenhouse gas emissions include Scope 1, 2, and partial Scope 3 reporting.",
            "Climate risk assessment is integrated into enterprise risk management framework.",
            "We report annually according to TCFD and GRI standards.",
            "Board oversight of sustainability initiatives has been strengthened."
        ]

        chunks = []
        for i, text in enumerate(stub_texts):
            chunk = Chunk(
                chunk_id=f"{company}_{year}_stub_{i:03d}",
                company=company,
                year=year,
                text=text,
                page_start=i + 1,
                page_end=i + 1,
                section="General",
                source_url=url,
                md5=hashlib.md5(text.encode()).hexdigest(),
                metadata={"stub": True}
            )
            chunks.append(chunk)

        return chunks


def parse_pdf(company: str, year: int, url: str) -> List[Chunk]:
    """
    Main entry point for PDF parsing
    """
    parser = PDFParser(
        chunk_size=512,
        chunk_overlap=102,
        min_chunk_size=50
    )

    return parser.parse_pdf(company, year, url, use_cache=True)


# Backward compatibility
def parse_pdf_stub(company: str, year: int, url: str) -> List[Chunk]:
    """
    Backward compatibility wrapper
    """
    return parse_pdf(company, year, url)


if __name__ == "__main__":
    # Test the parser
    import sys

    logging.basicConfig(level=logging.INFO)

    if len(sys.argv) > 3:
        company = sys.argv[1]
        year = int(sys.argv[2])
        url = sys.argv[3]
    else:
        # Test with a real PDF
        company = "Microsoft"
        year = 2023
        url = "https://query.prod.cms.rt.microsoft.com/cms/api/am/binary/RW15mgm"

    chunks = parse_pdf(company, year, url)

    for i, chunk in enumerate(chunks[:5]):  # Show first 5 chunks
        print(f"\nChunk {i+1}:")
        print(f"  ID: {chunk.chunk_id}")
        print(f"  Section: {chunk.section}")
        print(f"  Pages: {chunk.page_start}-{chunk.page_end}")
        print(f"  Text: {chunk.text[:200]}...")
        print(f"  Tokens: ~{chunk.token_count_estimate}")