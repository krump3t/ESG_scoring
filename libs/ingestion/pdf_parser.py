"""
libs/ingestion/pdf_parser.py - Production PDF Parser

Handles actual PDF binary processing using Docling backend for enhanced extraction.

Author: SCA v13.8-MEA
Task: 031-ingestion-authenticity (updated Task 037 for Docling migration)
Protocol: Real PDF parsing with enhanced table extraction, no golden text substitution
"""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from libs.extraction.backend_docling import DoclingBackend


@dataclass
class PDFParseResult:
    """
    Result of PDF parsing operation

    Fields:
        success: Whether parsing succeeded
        text: Extracted text from PDF (None if failed)
        page_count: Number of pages in PDF
        metadata: PDF metadata dict
        error_message: Error message if parsing failed
    """
    success: bool
    text: str | None
    page_count: int
    metadata: dict[str, Any] | None
    error_message: str | None


class PDFParser:
    """
    Production PDF parser using Docling backend

    Extracts text and metadata from PDF files with enhanced table preservation.
    """

    def __init__(self):
        """Initialize PDF parser with Docling backend"""
        self._backend = DoclingBackend()

    def parse(self, pdf_path: Path) -> PDFParseResult:
        """
        Parse a PDF file and extract text and metadata

        Args:
            pdf_path: Path to PDF file

        Returns:
            PDFParseResult with extraction results
        """
        pdf_path = Path(pdf_path)

        # Check if file exists
        if not pdf_path.exists():
            return PDFParseResult(
                success=False,
                text=None,
                page_count=0,
                metadata=None,
                error_message=f"File not found: {pdf_path}"
            )

        # Respect ALLOW_NETWORK environment variable
        allow_network = os.getenv("ALLOW_NETWORK", "").strip()
        if allow_network:
            # Network is allowed, but we don't need it for local PDFs
            pass

        try:
            # Use Docling backend for extraction
            doc_id = f"DOC_{pdf_path.stem}"
            pages = self._backend.parse_pdf_to_pages(str(pdf_path), doc_id)

            if not pages:
                return PDFParseResult(
                    success=False,
                    text=None,
                    page_count=0,
                    metadata=None,
                    error_message="No content extracted from PDF"
                )

            # Extract text from all pages
            text_parts = []
            for page in pages:
                text_parts.append(page.get("text", ""))

            # Combine all text
            full_text = "\n".join(text_parts)

            # Extract metadata (Docling provides limited metadata)
            # For now, use basic info from extraction results
            metadata = {
                "title": "",  # Docling doesn't extract PDF metadata
                "author": "",
                "subject": "",
                "creator": "",
                "producer": "Docling",
                "creationDate": "",
                "modDate": "",
                "backend": "docling",
                "pages_extracted": len(pages)
            }

            page_count = len(pages)

            return PDFParseResult(
                success=True,
                text=full_text,
                page_count=page_count,
                metadata=metadata,
                error_message=None
            )

        except Exception as e:
            # Handle parsing errors gracefully
            return PDFParseResult(
                success=False,
                text=None,
                page_count=0,
                metadata=None,
                error_message=f"PDF parsing error: {str(e)}"
            )
