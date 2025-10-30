"""PDF to Silver Parquet Converter - Multi-Backend Support (Task 026)

CLI tool for batch PDF extraction with backend selection.

SCA v13.8-MEA Compliance:
- Type hints: 100%
- Docstrings: Complete
- CLI-first design (scriptable)
- Provenance tracking (SHA256, backend metadata)
- Idempotent (safe to run multiple times)
"""
import argparse
import os
import pathlib
import hashlib
import json
from typing import List, Dict, Any
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Backend imports
from libs.extraction.parser_backend import PDFParserBackend
from libs.extraction.backend_default import DefaultBackend

try:
    from libs.extraction.backend_docling import DoclingBackend
    DOCLING_AVAILABLE = True
except ImportError:
    DOCLING_AVAILABLE = False
    logger.warning("Docling backend not available (install: pip install docling)")


def pick_backend(name: str) -> PDFParserBackend:
    """Select PDF parser backend by name.

    Args:
        name: "default" or "docling" (case-insensitive)

    Returns:
        Backend implementation (DefaultBackend or DoclingBackend)

    Raises:
        RuntimeError: If docling requested but not installed

    Example:
        >>> backend = pick_backend("default")
        >>> isinstance(backend, DefaultBackend)
        True
    """
    name = (name or "default").lower()

    if name == "docling":
        if not DOCLING_AVAILABLE:
            raise RuntimeError(
                "Docling backend requested but not available. "
                "Install with: pip install docling"
            )
        return DoclingBackend()

    return DefaultBackend()


def write_parquet(rows: List[Dict[str, Any]], out_path: str) -> None:
    """Write findings to Parquet with standardized schema.

    Args:
        rows: List of dicts with schema {doc_id, page, text, chunk_id}
        out_path: Output path for parquet file

    Notes:
        - Creates parent directories if needed
        - Uses pyarrow engine for consistency
        - Standardized column order
    """
    import pandas as pd

    # Ensure directory exists
    pathlib.Path(out_path).parent.mkdir(parents=True, exist_ok=True)

    # Standardized column order
    df = pd.DataFrame(rows, columns=["doc_id", "page", "text", "chunk_id"])
    df.to_parquet(out_path, index=False, engine="pyarrow")

    logger.info(f"Wrote {len(rows)} rows to {out_path}")


def sha256_file(path: str) -> str:
    """Compute SHA256 hash of file.

    Args:
        path: Path to file

    Returns:
        SHA256 hash as hex string (64 chars)

    Example:
        >>> hash_val = sha256_file("test.pdf")
        >>> len(hash_val)
        64
    """
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):  # 1MB chunks
            h.update(chunk)
    return h.hexdigest()


def main():
    """Main entry point for PDF to silver conversion.

    Command-line interface for converting PDFs to silver-tier Parquet files
    with backend selection and provenance tracking.

    Usage:
        python scripts/pdf_to_silver.py \\
            --org_id LSE_HEAD \\
            --year 2025 \\
            --doc_id LSE_HEAD_2025 \\
            --backend default

    Environment Variables:
        PARSER_BACKEND: Default backend if --backend not specified
    """
    parser = argparse.ArgumentParser(
        description="Convert PDF to silver Parquet with backend selection"
    )
    parser.add_argument("--org_id", required=True, help="Organization ID (e.g., LSE_HEAD)")
    parser.add_argument("--year", type=int, required=True, help="Report year (e.g., 2025)")
    parser.add_argument("--doc_id", required=True, help="Document ID (e.g., LSE_HEAD_2025)")
    parser.add_argument(
        "--backend",
        default=os.getenv("PARSER_BACKEND", "default"),
        help="Backend: 'default' or 'docling' (default: $PARSER_BACKEND or 'default')"
    )
    parser.add_argument("--pdf", help="PDF path (optional, auto-detects from data/raw/)")

    args = parser.parse_args()

    # Locate PDF
    pdf_path = args.pdf
    if not pdf_path:
        candidates = [
            f"data/raw/{args.doc_id}.pdf",
            f"data/silver/org_id={args.org_id}/year={args.year}/{args.doc_id}.pdf"
        ]
        pdf_path = next((p for p in candidates if os.path.exists(p)), "")

    if not pdf_path or not os.path.exists(pdf_path):
        logger.error(f"PDF not found for {args.doc_id}")
        logger.error(f"Searched: {candidates if not args.pdf else [args.pdf]}")
        raise SystemExit(f"PDF not found for {args.doc_id}")

    logger.info(f"Processing {pdf_path} with {args.backend} backend")

    # Extract findings
    try:
        backend = pick_backend(args.backend)
    except RuntimeError as e:
        logger.error(str(e))
        raise SystemExit(1)

    rows = backend.parse_pdf_to_pages(pdf_path, args.doc_id)

    if not rows:
        logger.error(f"No content extracted from {pdf_path}")
        raise SystemExit(f"No content extracted from {pdf_path}")

    logger.info(f"Extracted {len(rows)} pages from {args.doc_id}")

    # Determine output path
    if args.backend.lower() == "docling":
        out_path = f"data/silver_docling/org_id={args.org_id}/year={args.year}/{args.doc_id}_chunks.parquet"
    else:
        out_path = f"data/silver/org_id={args.org_id}/year={args.year}/{args.doc_id}_chunks.parquet"

    # Write Parquet
    write_parquet(rows, out_path)

    # Generate provenance sidecar
    provenance = {
        "doc_id": args.doc_id,
        "org_id": args.org_id,
        "year": args.year,
        "backend": args.backend,
        "source_pdf": pdf_path,
        "source_pdf_sha256": sha256_file(pdf_path),
        "row_count": len(rows),
        "schema_version": "1.0"
    }

    prov_path = out_path + ".prov.json"
    pathlib.Path(prov_path).write_text(json.dumps(provenance, indent=2), encoding="utf-8")

    logger.info(f"Provenance written to {prov_path}")
    print(f"SUCCESS: {out_path} ({len(rows)} rows)")


if __name__ == "__main__":
    main()
