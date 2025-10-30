"""PDF Parser Backend Protocol - Task 026

This module defines the interface for PDF extraction backends using Protocol (PEP 544).
All backends (default, Docling, future) must implement this interface.

SCA v13.8-MEA Compliance:
- Type hints: 100%
- Docstrings: Complete (module, class, function level)
- Deterministic: _mk_chunk_id is pure function
- No external dependencies: stdlib only
"""
from __future__ import annotations
from typing import List, Dict, Any, Protocol


class PDFParserBackend(Protocol):
    """Protocol defining the interface for PDF extraction backends.

    All implementations must provide deterministic, page-based extraction
    with a standardized output schema. This protocol enables polymorphic
    backend selection without inheritance coupling.

    Implementations:
        - DefaultBackend: PyMuPDF-based text extraction
        - DoclingBackend: Vision model-based structure extraction

    Example:
        >>> backend: PDFParserBackend = DefaultBackend()
        >>> pages = backend.parse_pdf_to_pages("report.pdf", "DOC_001")
        >>> assert all('doc_id' in p for p in pages)
    """

    def parse_pdf_to_pages(self, pdf_path: str, doc_id: str) -> List[Dict[str, Any]]:
        """Extract page-based chunks from PDF.

        Args:
            pdf_path: Absolute path to PDF file (must exist on filesystem)
            doc_id: Unique document identifier (e.g., "LSE_HEAD_2025")

        Returns:
            List of dictionaries with standardized schema:
            [
                {
                    "doc_id": str,      # Same as input doc_id
                    "page": int,        # 1-indexed page number
                    "text": str,        # Extracted text content
                    "chunk_id": str     # Format: {doc_id}_p{page:04d}_{idx:02d}
                },
                ...
            ]

            Returns empty list if PDF not found or extraction fails.

        Raises:
            RuntimeError: If backend initialization failed (e.g., Docling not installed)

        Notes:
            - Implementations must be deterministic (same PDF → same output)
            - Page numbers are 1-indexed (matching PDF viewer conventions)
            - chunk_id must be globally unique and sortable
            - Empty list return on error (logged, not raised)
        """
        ...


def _mk_chunk_id(doc_id: str, page: int, idx: int = 0) -> str:
    """Generate deterministic chunk ID.

    Creates a globally unique, sortable identifier for a PDF chunk.
    Format: {doc_id}_p{page:04d}_{idx:02d}

    Args:
        doc_id: Document identifier (e.g., "LSE_HEAD_2025")
        page: Page number (typically 1-indexed, but not validated)
        idx: Chunk index within page (default: 0 for single chunk per page)

    Returns:
        Chunk ID string (e.g., "LSE_HEAD_2025_p0001_00")

    Examples:
        >>> _mk_chunk_id("LSE_HEAD_2025", 1, 0)
        'LSE_HEAD_2025_p0001_00'

        >>> _mk_chunk_id("AAPL_2023", 42, 5)
        'AAPL_2023_p0042_05'

        >>> # IDs are sortable (lexicographic order = page order)
        >>> id1 = _mk_chunk_id("DOC", 1, 0)
        >>> id2 = _mk_chunk_id("DOC", 2, 0)
        >>> assert id1 < id2

    Notes:
        - Deterministic: Same inputs always produce same output
        - Sortable: Lexicographic sort = page order (zero-padded)
        - No validation: Function formats inputs as-is (caller must validate)
        - page format: 4 digits (allows up to 9999 pages, overflows gracefully)
        - idx format: 2 digits (allows up to 99 chunks per page)
    """
    return f"{doc_id}_p{page:04d}_{idx:02d}"
