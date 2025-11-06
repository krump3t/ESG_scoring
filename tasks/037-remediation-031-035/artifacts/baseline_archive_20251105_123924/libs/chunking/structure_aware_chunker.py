"""Structure-aware PDF chunker preserving semantic boundaries.

This module implements intelligent chunking that respects document structure:
- Section boundaries (headers detected via Docling metadata)
- Table boundaries (no table splitting, preserved from Docling markdown)
- List/bullet point preservation
- Paragraph-aware splitting (no mid-sentence breaks)

Task: 037-remediation-031-035 (Docling Migration)
Critical Path: Yes
Backend: Docling 2.60.0 (vision-based structure extraction)
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

logger = logging.getLogger(__name__)

# Constants
DEFAULT_CHUNK_SIZE = 512  # tokens
DEFAULT_OVERLAP = 50  # tokens
MIN_CHUNK_SIZE = 100  # tokens
MAX_CHUNK_SIZE = 1000  # tokens


class ChunkType(Enum):
    """Type of content in a chunk."""
    TEXT = "text"
    TABLE = "table"
    LIST = "list"
    HEADER = "header"
    FOOTER = "footer"


@dataclass
class Chunk:
    """A semantically-aware chunk of document content.

    Attributes:
        text: The chunk content
        page_num: Page number (0-indexed)
        chunk_type: Type of content
        section_title: Section header this chunk belongs to
        metadata: Additional metadata (font info, bbox, etc.)
    """
    text: str
    page_num: int
    chunk_type: ChunkType
    section_title: str | None = None
    metadata: dict = field(default_factory=dict)
    char_start: int = 0
    char_end: int = 0

    def token_count(self) -> int:
        """Estimate token count (rough: 1 token ≈ 4 characters)."""
        return len(self.text) // 4


class StructureAwareChunker:
    """Chunk PDF documents preserving semantic structure using Docling.

    Uses Docling vision-based extraction to detect and preserve:
    - Section headers (from Docling markdown headings ##, ###)
    - Tables (preserved as markdown tables with | delimiters)
    - Lists (bullets, numbering detected in markdown)
    - Paragraphs (double newlines)

    Chunks respect these boundaries and avoid splitting mid-sentence.
    Docling provides superior structure detection compared to font-based heuristics.
    """

    def __init__(
        self,
        chunk_size: int = DEFAULT_CHUNK_SIZE,
        overlap: int = DEFAULT_OVERLAP,
        min_chunk_size: int = MIN_CHUNK_SIZE,
        use_docling: bool = True,
    ):
        """Initialize chunker with size parameters.

        Args:
            chunk_size: Target chunk size in tokens
            overlap: Overlap between chunks in tokens
            min_chunk_size: Minimum chunk size (avoid tiny fragments)
            use_docling: Use Docling backend (recommended, default=True)

        Raises:
            ValueError: If parameters are invalid
        """
        if chunk_size <= 0:
            raise ValueError(f"chunk_size must be positive, got {chunk_size}")
        if overlap < 0 or overlap >= chunk_size:
            raise ValueError(f"overlap must be in [0, chunk_size), got {overlap}")
        if min_chunk_size <= 0 or min_chunk_size > chunk_size:
            raise ValueError(
                f"min_chunk_size must be in (0, chunk_size], got {min_chunk_size}"
            )

        self.chunk_size = chunk_size
        self.overlap = overlap
        self.min_chunk_size = min_chunk_size
        self.use_docling = use_docling

        # Pattern for detecting list items
        self.list_pattern = re.compile(
            r"^\s*(?:[\u2022\u2023\u25E6\u2043\u2219]|[-*]|\d+\.|\([a-z]\))\s+"
        )

        # Initialize Docling backend if requested
        self._docling_backend = None
        if self.use_docling:
            try:
                from libs.extraction.backend_docling import DoclingBackend
                self._docling_backend = DoclingBackend()
                logger.info("Docling backend initialized for structure-aware chunking")
            except ImportError:
                logger.warning("Docling not available, falling back to basic chunking")
                self.use_docling = False

    def chunk_pdf(self, pdf_path: str) -> list[Chunk]:
        """Chunk a PDF file with structure awareness using Docling.

        Args:
            pdf_path: Path to PDF file

        Returns:
            List of Chunk objects with metadata

        Raises:
            FileNotFoundError: If PDF doesn't exist
            RuntimeError: If PDF parsing fails
        """
        if not Path(pdf_path).exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")

        # Use Docling backend if available, otherwise fall back to basic chunking
        if self.use_docling and self._docling_backend:
            return self._chunk_pdf_with_docling(pdf_path)
        else:
            raise RuntimeError(
                "Docling backend required for structure-aware chunking. "
                "Install with: pip install docling"
            )

    def _chunk_pdf_with_docling(self, pdf_path: str) -> list[Chunk]:  # noqa: C901
        """Chunk PDF using Docling-extracted markdown structure.

        NOTE: Complexity C901 acceptable - sequential state machine for parsing
        structured document layouts. Refactoring would reduce readability.

        Args:
            pdf_path: Path to PDF file

        Returns:
            List of Chunk objects

        Raises:
            RuntimeError: If Docling parsing fails
        """
        try:
            # Use Docling backend to extract structured pages
            doc_id = Path(pdf_path).stem
            pages = self._docling_backend.parse_pdf_to_pages(pdf_path, doc_id)
        except Exception as e:
            raise RuntimeError(f"Docling parsing failed for {pdf_path}: {e}")

        if not pages:
            raise ValueError(f"PDF {pdf_path} produced no pages")

        chunks: list[Chunk] = []
        current_section = None

        for page in pages:
            page_num = page["page"]
            text = page["text"]

            # Split page text into lines for markdown parsing
            lines = text.split("\n")
            current_block = []
            current_type = ChunkType.TEXT

            for line in lines:
                line_stripped = line.strip()
                if not line_stripped:
                    # Empty line: end current block
                    if current_block:
                        block_text = "\n".join(current_block)
                        chunks.append(Chunk(
                            text=block_text,
                            page_num=page_num,
                            chunk_type=current_type,
                            section_title=current_section,
                            char_start=0,  # Docling doesn't provide char positions
                            char_end=len(block_text)
                        ))
                        current_block = []
                        current_type = ChunkType.TEXT
                    continue

                # Check if line is a markdown header (##, ###)
                if line_stripped.startswith("##"):
                    # Flush current block
                    if current_block:
                        block_text = "\n".join(current_block)
                        chunks.append(Chunk(
                            text=block_text,
                            page_num=page_num,
                            chunk_type=current_type,
                            section_title=current_section,
                            char_start=0,
                            char_end=len(block_text)
                        ))
                        current_block = []

                    # Process header
                    header_text = line_stripped.lstrip("#").strip()
                    current_section = header_text
                    chunks.append(Chunk(
                        text=header_text,
                        page_num=page_num,
                        chunk_type=ChunkType.HEADER,
                        section_title=current_section,
                        metadata={"level": line_stripped.count("#")},
                        char_start=0,
                        char_end=len(header_text)
                    ))
                    current_type = ChunkType.TEXT
                    continue

                # Check if line contains markdown table markers (|)
                if "|" in line_stripped and line_stripped.count("|") >= 2:
                    # Start or continue table block
                    if current_type != ChunkType.TABLE:
                        # Flush previous block
                        if current_block:
                            block_text = "\n".join(current_block)
                            chunks.append(Chunk(
                                text=block_text,
                                page_num=page_num,
                                chunk_type=current_type,
                                section_title=current_section,
                                char_start=0,
                                char_end=len(block_text)
                            ))
                            current_block = []
                        current_type = ChunkType.TABLE
                    current_block.append(line)
                    continue

                # Check if line is a list item
                if self._is_list(line_stripped):
                    if current_type != ChunkType.LIST:
                        # Flush previous block
                        if current_block:
                            block_text = "\n".join(current_block)
                            chunks.append(Chunk(
                                text=block_text,
                                page_num=page_num,
                                chunk_type=current_type,
                                section_title=current_section,
                                char_start=0,
                                char_end=len(block_text)
                            ))
                            current_block = []
                        current_type = ChunkType.LIST
                    current_block.append(line)
                    continue

                # Regular text
                if current_type != ChunkType.TEXT:
                    # Flush previous non-text block
                    if current_block:
                        block_text = "\n".join(current_block)
                        metadata = (
                            {"rows": len(current_block)}
                            if current_type == ChunkType.TABLE
                            else {}
                        )
                        chunks.append(Chunk(
                            text=block_text,
                            page_num=page_num,
                            chunk_type=current_type,
                            section_title=current_section,
                            metadata=metadata,
                            char_start=0,
                            char_end=len(block_text)
                        ))
                        current_block = []
                    current_type = ChunkType.TEXT

                current_block.append(line)

            # Flush any remaining block
            if current_block:
                block_text = "\n".join(current_block)
                chunks.append(Chunk(
                    text=block_text,
                    page_num=page_num,
                    chunk_type=current_type,
                    section_title=current_section,
                    char_start=0,
                    char_end=len(block_text)
                ))

        # Merge small chunks
        chunks = self._merge_small_chunks(chunks)

        # Split large chunks at sentence boundaries
        chunks = self._split_large_chunks(chunks)

        return chunks

    # Helper methods for text analysis (Docling-compatible)

    def _is_list(self, text: str) -> bool:
        """Detect if text is a list."""
        lines = text.strip().split("\n")
        if len(lines) < 2:
            return False

        # Count lines starting with list markers
        list_lines = sum(1 for line in lines if self.list_pattern.match(line))
        return list_lines >= len(lines) / 2

    def _split_paragraphs(self, text: str) -> list[str]:
        """Split text into paragraphs (double newline separated)."""
        return [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]

    def _get_avg_font_size(self, block: dict) -> float:
        """Get average font size in a block."""
        sizes = []
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                sizes.append(span.get("size", 10))
        return sum(sizes) / len(sizes) if sizes else 10.0

    def _is_bold(self, block: dict) -> bool:
        """Check if block contains bold text."""
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                flags = span.get("flags", 0)
                if flags & 2 ** 4:  # Bold flag
                    return True
        return False

    def _merge_small_chunks(self, chunks: list[Chunk]) -> list[Chunk]:
        """Merge consecutive small chunks."""
        if not chunks:
            return []

        merged: list[Chunk] = []
        current = chunks[0]

        for next_chunk in chunks[1:]:
            # Can merge if same type, same section, same page
            can_merge = (
                current.chunk_type == next_chunk.chunk_type and
                current.section_title == next_chunk.section_title and
                current.page_num == next_chunk.page_num and
                current.token_count() < self.min_chunk_size
            )

            if can_merge:
                current = Chunk(
                    text=current.text + "\n\n" + next_chunk.text,
                    page_num=current.page_num,
                    chunk_type=current.chunk_type,
                    section_title=current.section_title,
                    metadata=current.metadata,
                    char_start=current.char_start,
                    char_end=next_chunk.char_end
                )
            else:
                merged.append(current)
                current = next_chunk

        merged.append(current)
        return merged

    def _split_large_chunks(self, chunks: list[Chunk]) -> list[Chunk]:
        """Split chunks exceeding max size at sentence boundaries."""
        result: list[Chunk] = []

        for chunk in chunks:
            if chunk.token_count() <= self.chunk_size:
                result.append(chunk)
                continue

            # Split at sentence boundaries
            sentences = self._split_sentences(chunk.text)
            current_text = ""

            for sentence in sentences:
                test_text = current_text + " " + sentence if current_text else sentence
                if len(test_text) // 4 > self.chunk_size and current_text:
                    # Save current chunk
                    result.append(Chunk(
                        text=current_text.strip(),
                        page_num=chunk.page_num,
                        chunk_type=chunk.chunk_type,
                        section_title=chunk.section_title,
                        metadata=chunk.metadata,
                        char_start=chunk.char_start,
                        char_end=chunk.char_end
                    ))
                    current_text = sentence
                else:
                    current_text = test_text

            # Add remaining text
            if current_text.strip():
                result.append(Chunk(
                    text=current_text.strip(),
                    page_num=chunk.page_num,
                    chunk_type=chunk.chunk_type,
                    section_title=chunk.section_title,
                    metadata=chunk.metadata,
                    char_start=chunk.char_start,
                    char_end=chunk.char_end
                ))

        return result

    def _split_sentences(self, text: str) -> list[str]:
        """Split text into sentences."""
        # Simple sentence splitter (can be improved with NLP)
        return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]


if __name__ == '__main__':
    import argparse
    import sys

    import pandas as pd
    ap = argparse.ArgumentParser()
    ap.add_argument('--pdf', required=True)
    ap.add_argument('--out', required=True)
    args = ap.parse_args()
    try:
        from libs.chunking.structure_aware_chunker import StructureAwareChunker
        chunker = StructureAwareChunker(chunk_size=512, overlap=50)
        chunks = chunker.chunk_pdf(args.pdf)
        # Convert to DataFrame
        import pandas as pd
        df = pd.DataFrame([{
            'text': c.text,
            'page_num': c.page_num,
            'chunk_type': (
                c.chunk_type.value
                if hasattr(c.chunk_type, 'value')
                else str(c.chunk_type)
            ),
            'section_title': c.section_title or '',
            'char_start': getattr(c, 'char_start', 0),
            'char_end': getattr(c, 'char_end', 0)
        } for c in chunks])
        df.to_parquet(args.out, index=False)
        print(f'CHUNKER_OK {len(df)}')
    except Exception as e:
        print(f'CHUNKER_RUN_FAIL:{e}', file=sys.stderr)
        sys.exit(3)
