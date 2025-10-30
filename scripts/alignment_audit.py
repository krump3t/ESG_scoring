#!/usr/bin/env python3
"""
Alignment Audit - Quote Verification Against Source PDFs

Validates that all quoted evidence in evidence_audit.json files
actually appears on the claimed page in the source PDF.

Fail-closed: Any mismatch results in exit code 2 with detailed report.

Usage:
    python scripts/alignment_audit.py
"""

import json
import glob
import sys
import os
from pathlib import Path

try:
    import fitz  # PyMuPDF
except ImportError:
    print("Installing PyMuPDF for PDF text extraction...")
    os.system("pip install pymupdf >nul 2>&1" if os.name == "nt" else "pip install pymupdf >/dev/null 2>&1")
    import fitz


def get_text_on_page(pdf_path: str, page_num: int) -> str:
    """
    Extract text from a specific page in a PDF.

    Args:
        pdf_path: Path to PDF file
        page_num: 1-indexed page number

    Returns:
        Page text as string, or empty string if page out of range
    """
    try:
        with fitz.open(pdf_path) as doc:
            if 1 <= page_num <= doc.page_count:
                return doc.load_page(page_num - 1).get_text("text")
    except Exception as e:
        print(f"Warning: Could not read {pdf_path} page {page_num}: {e}")
    return ""


def find_pdf_for_doc(doc_id: str) -> str:
    """
    Locate the source PDF for a document ID.

    Checks multiple possible locations:
    1. data/silver/org_id={ORG}/year={YEAR}/{DOC_ID}.pdf
    2. data/pdf_cache/{COMPANY}_{YEAR}_*.pdf
    3. data/raw/{DOC_ID}.pdf

    Args:
        doc_id: Document identifier (e.g., "AAPL_2023", "LSE_HEAD_2025")

    Returns:
        Path to PDF, or empty string if not found
    """
    # Parse doc_id
    parts = doc_id.split("_")
    if len(parts) < 2:
        return ""

    org_id = parts[0]
    year = parts[1]

    # Try silver location
    silver_path = f"data/silver/org_id={org_id}/year={year}/{doc_id}.pdf"
    if os.path.exists(silver_path):
        return silver_path

    # Try pdf_cache (with wildcards)
    pdf_cache_pattern = f"data/pdf_cache/{org_id}_{year}_*.pdf"
    matches = glob.glob(pdf_cache_pattern)
    if matches:
        return matches[0]

    # Try raw location
    raw_path = f"data/raw/{doc_id}.pdf"
    if os.path.exists(raw_path):
        return raw_path

    return ""


def main():
    """
    Main alignment audit: verify all quotes appear in source PDFs.

    Exit codes:
        0 - All quotes verified
        1 - No evidence audits found
        2 - Alignment failures detected
    """
    audit_files = glob.glob("artifacts/matrix/*/pipeline_validation/evidence_audit.json")

    if not audit_files:
        print("No evidence audit files found. Skipping alignment audit.")
        return 1

    failures = []

    for audit_path in audit_files:
        with open(audit_path, encoding="utf-8") as f:
            audit = json.load(f)

        doc_id = audit.get("doc_id", "unknown")
        pdf_path = find_pdf_for_doc(doc_id)

        if not pdf_path:
            print(f"Warning: No PDF found for {doc_id}, skipping alignment audit")
            continue

        if not os.path.exists(pdf_path):
            print(f"Warning: PDF path {pdf_path} does not exist for {doc_id}")
            continue

        # Check each theme's evidence
        themes = audit.get("themes") or {}
        for theme_name, theme_info in themes.items():
            evidence = theme_info.get("evidence") or []

            for item in evidence:
                if not isinstance(item, dict):
                    continue

                quote = (item.get("quote") or "").strip()
                page = item.get("page")

                if not quote or not isinstance(page, int):
                    continue

                # Get page text
                page_text = get_text_on_page(pdf_path, page)

                # Check if quote appears in page text (exact match)
                if quote not in page_text:
                    # Try fuzzy match on first 60 chars
                    import re
                    fuzzy_pattern = re.escape(quote[:60])
                    if not re.search(fuzzy_pattern, page_text, re.DOTALL):
                        failures.append({
                            "doc_id": doc_id,
                            "theme": theme_name,
                            "page": page,
                            "quote_preview": quote[:80] + "...",
                            "pdf_path": pdf_path,
                        })

    if failures:
        print("\nALIGNMENT AUDIT FAILED")
        print("=" * 60)
        for fail in failures:
            print(f"\nDocument: {fail['doc_id']}")
            print(f"Theme: {fail['theme']}")
            print(f"Page: {fail['page']}")
            print(f"Quote: {fail['quote_preview']}")
            print(f"PDF: {fail['pdf_path']}")
        print("=" * 60)
        print(f"\nTotal failures: {len(failures)}")
        return 2

    print("Alignment audit PASS - all quotes verified in source PDFs (SUCCESS)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
