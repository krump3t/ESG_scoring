"""
PDF Text Extractor - Phase 3B

Extracts text from born-digital PDF files using PyMuPDF (fitz).

Author: Scientific Coding Agent v13.8-MEA
Date: 2025-10-24
"""

import os
from typing import Optional
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
