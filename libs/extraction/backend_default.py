"""Default PDF Backend - PyMuPDF Extraction (Task 026)

This module implements the default PDF extraction backend using PyMuPDF (fitz).
Maintains existing extraction behavior for backward compatibility.

SCA v13.8-MEA Compliance:
- Type hints: 100%
- Docstrings: Complete
- Deterministic: Same PDF → same output
- Error handling: Fail gracefully (returns empty list, logs errors)
- No mocks: Real PyMuPDF library calls
"""
from typing import List, Dict, Any
from .parser_backend import PDFParserBackend, _mk_chunk_id
import os
import logging

logger = logging.getLogger(__name__)


class DefaultBackend(PDFParserBackend):
    """Default PDF extraction backend using PyMuPDF.

    Provides fast, text-only extraction with no structure preservation.
    Maintains existing pipeline behavior for backward compatibility.

    Features:
        - Text-only extraction (no tables, layout, or OCR)
        - Fast (~1-2 seconds per document)
        - Deterministic (same PDF → same output)
        - Graceful error handling (returns empty list on failure)

    Limitations:
        - Tables converted to narrative text (structure lost)
        - No layout analysis
        - No OCR for scanned PDFs
        - No multi-modal content

    Example:
        >>> backend = DefaultBackend()
        >>> pages = backend.parse_pdf_to_pages("report.pdf", "DOC_001")
        >>> print(f"Extracted {len(pages)} pages")
    """

    def parse_pdf_to_pages(self, pdf_path: str, doc_id: str) -> List[Dict[str, Any]]:
        """Extract page-based chunks using PyMuPDF.

        Args:
            pdf_path: Absolute path to PDF file
            doc_id: Unique document identifier

        Returns:
            List of dicts with schema:
            [
                {
                    "doc_id": str,
                    "page": int,  # 1-indexed
                    "text": str,
                    "chunk_id": str,
                    "source": "default"
                },
                ...
            ]

            Returns empty list if PDF not found or extraction fails.

        Example:
            >>> backend = DefaultBackend()
            >>> result = backend.parse_pdf_to_pages("data/raw/report.pdf", "RPT_001")
            >>> assert len(result) > 0
            >>> assert result[0]["source"] == "default"
        """
        # Validate PDF exists
        if not os.path.exists(pdf_path):
            logger.error(f"PDF not found: {pdf_path}")
            return []

        rows: List[Dict[str, Any]] = []

        try:
            import fitz  # PyMuPDF

            # Open PDF
            doc = fitz.open(pdf_path)
            logger.info(f"Opened PDF: {pdf_path} ({doc.page_count} pages)")

            # Extract text from each page
            for i in range(doc.page_count):
                page_num = i + 1  # 1-indexed (matching PDF viewer conventions)
                page = doc.load_page(i)

                # Extract text
                text = page.get_text("text") or ""

                # Create standardized row
                rows.append({
                    "doc_id": doc_id,
                    "page": page_num,
                    "text": text,
                    "chunk_id": _mk_chunk_id(doc_id, page_num, 0),
                    "source": "default"
                })

            doc.close()
            logger.info(f"Extracted {len(rows)} pages from {doc_id}")

        except ImportError:
            logger.error("PyMuPDF (fitz) not installed. Install: pip install pymupdf")
            return []

        except Exception as e:
            logger.error(f"Failed to extract from {pdf_path}: {e}")
            return []

        return rows
