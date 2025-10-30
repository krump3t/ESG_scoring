"""
Enhanced PDF/HTML Text Extraction for ESG Reports

Extracts text with provenance tracking:
- Page numbers, section headers
- Source URL, provider, document hash
- Chunk metadata (offset, confidence)
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from pathlib import Path
import hashlib
import json
import os
from datetime import datetime


@dataclass
class ExtractedChunk:
    """Extracted text chunk with full provenance."""
    text: str
    page: int
    section: Optional[str] = None
    source_url: Optional[str] = None
    provider: Optional[str] = None
    doc_hash: Optional[str] = None
    chunk_id: Optional[str] = None
    confidence: float = 1.0
    timestamp: Optional[str] = None


class EnhancedPDFExtractor:
    """Extract text from PDF/HTML with provenance tracking."""

    def __init__(self, source_url: str = "", provider: str = "unknown"):
        """Initialize extractor with source context."""
        self.source_url = source_url
        self.provider = provider
        self.chunks: List[ExtractedChunk] = []

    def extract_from_file(
        self,
        file_path: str,
        doc_id: str = "",
        chunk_size: int = 1000
    ) -> List[ExtractedChunk]:
        """
        Extract text from PDF or HTML file with provenance.

        Args:
            file_path: Path to PDF or HTML file
            doc_id: Document identifier for chunk IDs
            chunk_size: Target chunk size in characters

        Returns:
            List of ExtractedChunk objects with metadata
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        # Calculate document hash
        doc_hash = self._hash_file(file_path)

        # Route by file type
        if path.suffix.lower() == '.pdf':
            text = self._extract_pdf_text(file_path)
        elif path.suffix.lower() in ['.html', '.htm']:
            text = self._extract_html_text(file_path)
        else:
            raise ValueError(f"Unsupported file type: {path.suffix}")

        # Split into chunks with metadata
        self.chunks = self._chunk_text(
            text,
            chunk_size=chunk_size,
            doc_id=doc_id,
            doc_hash=doc_hash
        )

        return self.chunks

    def _extract_pdf_text(self, file_path: str) -> str:
        """Extract text from PDF (fallback for when PyPDF2 not available)."""
        # Placeholder: in production, use PyPDF2 or pdfplumber
        # For now, return file content as-is if text file
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read()
        except Exception:
            return ""

    def _extract_html_text(self, file_path: str) -> str:
        """Extract text from HTML with structure preservation."""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                html_content = f.read()

            # Simple HTML text extraction (remove tags)
            import re
            text = re.sub(r'<[^>]+>', ' ', html_content)
            text = re.sub(r'\s+', ' ', text)
            return text.strip()
        except Exception:
            return ""

    def _hash_file(self, file_path: str) -> str:
        """Calculate SHA256 hash of file."""
        sha256_hash = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256_hash.update(chunk)
        return sha256_hash.hexdigest()[:16]  # Use first 16 chars

    def _chunk_text(
        self,
        text: str,
        chunk_size: int = 1000,
        doc_id: str = "",
        doc_hash: str = ""
    ) -> List[ExtractedChunk]:
        """Split text into overlapping chunks with metadata."""
        chunks = []
        overlap = 200

        for i in range(0, len(text), chunk_size - overlap):
            chunk_text = text[i:i + chunk_size]

            # Estimate page number (assume ~3000 chars per page)
            page_num = (i // 3000) + 1

            # Use deterministic timestamp in offline/replay mode
            if os.environ.get("WX_OFFLINE_REPLAY") == "true" or os.environ.get("FIXED_TIME"):
                timestamp = "2025-10-28T06:00:00Z"  # Fixed timestamp for determinism
            else:
                timestamp = datetime.utcnow().isoformat() + "Z"

            chunk = ExtractedChunk(
                text=chunk_text,
                page=page_num,
                section=None,
                source_url=self.source_url,
                provider=self.provider,
                doc_hash=doc_hash,
                chunk_id=f"{doc_id}_p{page_num}_c{len(chunks)}",
                confidence=1.0,
                timestamp=timestamp
            )
            chunks.append(chunk)

        return chunks

    def to_dict(self, chunk: ExtractedChunk) -> Dict[str, Any]:
        """Convert chunk to dictionary for JSON serialization."""
        return {
            "text": chunk.text,
            "page": chunk.page,
            "section": chunk.section,
            "source_url": chunk.source_url,
            "provider": chunk.provider,
            "doc_hash": chunk.doc_hash,
            "chunk_id": chunk.chunk_id,
            "confidence": chunk.confidence,
            "timestamp": chunk.timestamp
        }


def extract_document(
    file_path: str,
    source_url: str = "",
    provider: str = "unknown",
    chunk_size: int = 1000
) -> List[Dict[str, Any]]:
    """
    Convenience function to extract document with full provenance.

    Args:
        file_path: Path to PDF or HTML file
        source_url: Source URL for provenance
        provider: Data provider (SEC, CDP, GRI, SASB, IR)
        chunk_size: Chunk size in characters

    Returns:
        List of chunk dictionaries with metadata
    """
    extractor = EnhancedPDFExtractor(source_url=source_url, provider=provider)
    chunks = extractor.extract_from_file(file_path, chunk_size=chunk_size)
    return [extractor.to_dict(chunk) for chunk in chunks]


def extract_pdf_chunks(
    pdf_path: str,
    chunk_size: int = 1000,
    chunk_overlap: int = 200
) -> List[Dict[str, Any]]:
    """
    Extract PDF with chunking (compatibility wrapper for ingestion scripts).

    This function provides compatibility with scripts that expect the
    extract_pdf_chunks() signature. It delegates to extract_document()
    which uses the EnhancedPDFExtractor class.

    Args:
        pdf_path: Path to PDF file
        chunk_size: Target chunk size in characters (default 1000)
        chunk_overlap: Overlap between chunks (default 200, currently not used)

    Returns:
        List of chunk dictionaries with keys:
        - text: Chunk text content
        - page: Page number
        - section: Section name (optional)
        - source_url: Source URL
        - provider: Data provider
        - doc_hash: Document SHA256 hash (truncated)
        - chunk_id: Unique chunk identifier
        - confidence: Extraction confidence (1.0)
        - timestamp: ISO timestamp
    """
    # Note: chunk_overlap parameter is accepted for compatibility but
    # the current implementation uses a fixed 200-character overlap
    # internally in the _chunk_text method
    return extract_document(
        file_path=pdf_path,
        source_url=f"file://{Path(pdf_path).resolve()}",
        provider="local",
        chunk_size=chunk_size
    )
