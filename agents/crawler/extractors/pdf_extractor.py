"""
PDF Extractor using PyMuPDF
Critical Path: Extracts text, tables, and metadata from PDF documents
"""
from typing import Dict, List, Any, Optional
from pathlib import Path
import hashlib
import logging

logger = logging.getLogger(__name__)


class PDFExtractor:
    """
    Extract text, tables, and metadata from PDF documents

    Uses PyMuPDF (fitz) for text extraction and layout preservation
    """

    def __init__(self) -> None:
        """Initialize PDF extractor"""
        self.name = "PDFExtractor"
        logger.info("Initialized PDF Extractor")

    def extract(self, pdf_path: str, extract_tables: bool = True,
                extract_images: bool = True) -> Dict[str, Any]:
        """
        Extract content from PDF document

        Args:
            pdf_path: Path to PDF file
            extract_tables: Whether to extract tables
            extract_images: Whether to extract image metadata

        Returns:
            Dictionary with extracted content:
            - text: Full text content
            - tables: List of extracted tables
            - figures: List of image metadata
            - page_count: Number of pages
            - metadata: Document metadata
            - sha256: Document hash for deduplication
        """
        try:
            import fitz  # type: ignore # PyMuPDF

            # Calculate SHA256 hash first
            sha256_hash = self._calculate_sha256(pdf_path)

            # Open PDF
            with fitz.open(pdf_path) as doc:
                # Extract text with layout preservation
                text_parts = []
                for page in doc:
                    text_parts.append(page.get_text("text"))

                full_text = "\n\n".join(text_parts)

                # Extract tables if requested
                tables = []
                if extract_tables:
                    tables = self._extract_tables(pdf_path)

                # Extract figure metadata if requested
                figures = []
                if extract_images:
                    figures = self._extract_figures(doc)

                # Extract metadata
                metadata = {
                    'title': doc.metadata.get('title', ''),
                    'author': doc.metadata.get('author', ''),
                    'subject': doc.metadata.get('subject', ''),
                    'creator': doc.metadata.get('creator', ''),
                    'producer': doc.metadata.get('producer', ''),
                    'creation_date': doc.metadata.get('creationDate', ''),
                }

                return {
                    'text': full_text,
                    'tables': tables,
                    'figures': figures,
                    'page_count': len(doc),
                    'metadata': metadata,
                    'sha256': sha256_hash
                }

        except ImportError:
            logger.warning("PyMuPDF not installed, using fallback extraction")
            return self._fallback_extract(pdf_path)
        except Exception as e:
            logger.error(f"Error extracting PDF {pdf_path}: {e}")
            raise

    def _calculate_sha256(self, file_path: str) -> str:
        """Calculate SHA256 hash of file"""
        sha256 = hashlib.sha256()

        with open(file_path, 'rb') as f:
            while chunk := f.read(8192):
                sha256.update(chunk)

        return sha256.hexdigest()

    def _extract_tables(self, pdf_path: str) -> List[Dict[str, Any]]:
        """Extract tables from PDF using pdfplumber"""
        tables = []

        try:
            import pdfplumber

            with pdfplumber.open(pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages):
                    page_tables = page.extract_tables()
                    if page_tables:
                        for table_idx, table in enumerate(page_tables):
                            tables.append({
                                'page': page_num + 1,
                                'table_index': table_idx,
                                'data': table,
                                'row_count': len(table) if table else 0,
                                'col_count': len(table[0]) if table and table[0] else 0
                            })

        except ImportError:
            logger.warning("pdfplumber not installed, skipping table extraction")
        except Exception as e:
            logger.warning(f"Error extracting tables: {e}")

        return tables

    def _extract_figures(self, doc: Any) -> List[Dict[str, Any]]:
        """Extract figure/image metadata from PDF"""
        figures = []

        try:
            for page_num, page in enumerate(doc):
                image_list = page.get_images()

                for img_idx, img_info in enumerate(image_list):
                    # img_info is a tuple: (xref, smask, width, height, ...)
                    xref = img_info[0]

                    figures.append({
                        'page': page_num + 1,
                        'image_index': img_idx,
                        'xref': xref,
                        'width': img_info[2] if len(img_info) > 2 else None,
                        'height': img_info[3] if len(img_info) > 3 else None
                    })

        except Exception as e:
            logger.warning(f"Error extracting figures: {e}")

        return figures

    def _fallback_extract(self, pdf_path: str) -> Dict[str, Any]:
        """Fallback extraction when PyMuPDF not available"""
        sha256_hash = self._calculate_sha256(pdf_path)

        # Try to read as text (won't work for binary PDFs)
        try:
            with open(pdf_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
        except Exception:
            content = "Error: Unable to extract PDF content"

        return {
            'text': content,
            'tables': [],
            'figures': [],
            'page_count': 1,
            'metadata': {},
            'sha256': sha256_hash
        }
