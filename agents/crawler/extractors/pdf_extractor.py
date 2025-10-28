"""Minimal PDF text extraction with deterministic chunk ids."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, List, Sequence

try:
    from PyPDF2 import PdfReader  # type: ignore
except ImportError:  # pragma: no cover - PyPDF2 may be optional
    PdfReader = None  # type: ignore

logger = logging.getLogger(__name__)


def extract_text(pdf_path: str | Path) -> List[Dict[str, object]]:
    """Return list of page-level chunks with doc_id, page, text, chunk_id."""
    path = Path(pdf_path)
    if PdfReader is None:
        raise ImportError("PyPDF2 not installed. Install to enable PDF extraction.")

    reader = PdfReader(str(path))
    doc_id = path.stem
    chunks: List[Dict[str, object]] = []

    for index, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        chunk_id = f"{doc_id}:{index:04d}"
        chunks.append(
            {
                "doc_id": doc_id,
                "chunk_id": chunk_id,
                "page": index,
                "text": text.strip(),
            }
        )

    logger.info("Extracted %s chunks from %s", len(chunks), path)
    chunks.sort(key=lambda chunk: chunk["page"])
    return chunks
