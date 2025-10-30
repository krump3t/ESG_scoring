"""
PDF Text Extractor - Phase 3B + Phase E Page Tracking

Extracts text from born-digital PDF files using PyMuPDF (fitz).
Phase E Enhancement: Page-aware extraction for evidence provenance.

Author: Scientific Coding Agent v13.8-MEA
Date: 2025-10-24 (Phase 3B), 2025-10-29 (Phase E)
"""

import os
from typing import Any, Dict, List, Optional
import fitz  # PyMuPDF


class PDFTextExtractor:
    """Extracts text from PDF files using PyMuPDF.

    Handles multi-page PDFs, preserves text structure, and provides
    page-level extraction capabilities.
    """

    def __init__(self, min_text_length: int = 100):
        """Initialize PDF text extractor.

        Args:
            min_text_length: Minimum expected text length (chars) for valid PDF
        """
        self.min_text_length = min_text_length

    def extract_text(self, pdf_path: str) -> str:
        """Extract all text from PDF file.

        Args:
            pdf_path: Path to PDF file

        Returns:
            Extracted text (all pages concatenated with double newlines)

        Raises:
            FileNotFoundError: If PDF file doesn't exist
            ValueError: If PDF is empty or text extraction fails
        """
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF not found: {pdf_path}")

        try:
            doc = fitz.open(pdf_path)
            text_parts = []

            # Extract text from each page
            for page_num in range(len(doc)):
                page = doc[page_num]
                text = page.get_text()
                text_parts.append(text)

            doc.close()

            # Concatenate with page breaks
            full_text = "\n\n".join(text_parts)

            # Validate minimum length
            if len(full_text.strip()) < self.min_text_length:
                raise ValueError(
                    f"PDF text too short: {len(full_text)} chars "
                    f"(expected ≥{self.min_text_length})"
                )

            return full_text

        except Exception as e:
            if isinstance(e, (FileNotFoundError, ValueError)):
                raise
            raise ValueError(f"Failed to extract text from PDF: {e}")

    def extract_page(self, pdf_path: str, page_num: int) -> str:
        """Extract text from specific page (0-indexed).

        Args:
            pdf_path: Path to PDF file
            page_num: Page number (0-indexed)

        Returns:
            Extracted text from page

        Raises:
            ValueError: If page number invalid
            FileNotFoundError: If PDF doesn't exist
        """
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF not found: {pdf_path}")

        try:
            doc = fitz.open(pdf_path)
            page_count = len(doc)

            # Validate page number
            if page_num < 0 or page_num >= page_count:
                doc.close()
                raise ValueError(
                    f"Invalid page number: {page_num} "
                    f"(PDF has {page_count} pages)"
                )

            page = doc[page_num]
            text = page.get_text()
            doc.close()

            return text

        except Exception as e:
            if isinstance(e, (ValueError, FileNotFoundError)):
                raise
            raise ValueError(f"Failed to extract page {page_num}: {e}")

    def get_page_count(self, pdf_path: str) -> int:
        """Get number of pages in PDF.

        Args:
            pdf_path: Path to PDF file

        Returns:
            Number of pages

        Raises:
            FileNotFoundError: If PDF doesn't exist
        """
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF not found: {pdf_path}")

        doc = fitz.open(pdf_path)
        count = len(doc)
        doc.close()
        return count

    def extract_with_page_metadata(self, pdf_path: str, min_chunk_chars: int = 100) -> List[Dict[str, Any]]:
        """Extract text with page number metadata for evidence provenance (Phase E).

        Creates page-aware chunks suitable for evidence tracking. Each chunk
        includes page number, text content, and character offsets within the PDF.

        Args:
            pdf_path: Path to PDF file
            min_chunk_chars: Minimum characters per chunk (skip smaller fragments)

        Returns:
            List of dicts with keys:
                - page_num (int): 1-indexed page number
                - text (str): Extracted text chunk
                - char_start (int): Character offset start
                - char_end (int): Character offset end
                - pdf_path (str): Source PDF path

        Raises:
            FileNotFoundError: If PDF doesn't exist
            ValueError: If PDF is empty or extraction fails

        Example:
            >>> extractor = PDFTextExtractor()
            >>> chunks = extractor.extract_with_page_metadata("report.pdf")
            >>> chunks[0]
            {
                'page_num': 1,
                'text': 'Executive Summary\\n\\nOur company...',
                'char_start': 0,
                'char_end': 245,
                'pdf_path': 'report.pdf'
            }
        """
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF not found: {pdf_path}")

        try:
            doc = fitz.open(pdf_path)
            chunks = []
            global_char_offset = 0

            for page_num in range(len(doc)):
                page = doc[page_num]
                page_text = page.get_text()

                # Split page text by double newlines (paragraphs)
                paragraphs = page_text.split('\n\n')
                page_char_offset = 0

                for para in paragraphs:
                    para_stripped = para.strip()

                    # Skip tiny fragments (likely headers/footers/artifacts)
                    if len(para_stripped) < min_chunk_chars:
                        page_char_offset += len(para) + 2  # +2 for newlines
                        continue

                    chunk = {
                        "page_num": page_num + 1,  # 1-indexed for human readability
                        "text": para_stripped,
                        "char_start": global_char_offset + page_char_offset,
                        "char_end": global_char_offset + page_char_offset + len(para),
                        "pdf_path": str(pdf_path)
                    }
                    chunks.append(chunk)

                    page_char_offset += len(para) + 2

                # Update global offset for next page
                global_char_offset += len(page_text) + 2  # +2 for page break

            doc.close()

            # Validate we extracted something
            if not chunks:
                raise ValueError(
                    f"No valid chunks extracted from PDF (min_chunk_chars={min_chunk_chars}). "
                    f"PDF may be empty or contain only short fragments."
                )

            return chunks

        except Exception as e:
            if isinstance(e, (FileNotFoundError, ValueError)):
                raise
            raise ValueError(f"Failed to extract page metadata from PDF: {e}")
