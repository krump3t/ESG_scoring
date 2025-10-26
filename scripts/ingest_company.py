logger = logging.getLogger(__name__)

import logging

"""
Company Data Ingestion CLI

Ingests company ESG data from PDF or Parquet sources.
Creates stub bronze Parquet and updates companies.json manifest.

SCA v13.8 Compliance:
- Determinism: Stable file operations, sorted JSON keys
- Type safety: 100% annotated
- No network: Offline file operations only
- Exit codes: 0=success, 1=validation error, 2=file not found
"""

logger = logging.getLogger(__name__)

import argparse
logger = logging.getLogger(__name__)

import sys
logger = logging.getLogger(__name__)

import json
logger = logging.getLogger(__name__)

import shutil
from pathlib import Path
from typing import Dict, Any, Optional
logger = logging.getLogger(__name__)

import re

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def slugify(text: str) -> str:
    """
    Convert company name to filesystem-safe slug.

    Args:
        text: Company name

    Returns:
        Lowercase slug with underscores
    """
    # Remove special chars, convert to lowercase, replace spaces with underscores
    slug = re.sub(r'[^\w\s-]', '', text.lower())
    slug = re.sub(r'[-\s]+', '_', slug)
    return slug.strip('_')


def validate_year(year: int) -> None:
    """
    Validate year is in acceptable range.

    Args:
        year: Year to validate

    Raises:
        ValueError: If year out of range
    """
    if not (2000 <= year <= 2100):
        raise ValueError(f"Year must be between 2000 and 2100, got {year}")


def ensure_directories() -> None:
    """Create required artifact directories."""
    Path("artifacts/raw").mkdir(parents=True, exist_ok=True)
    Path("artifacts/bronze").mkdir(parents=True, exist_ok=True)
    Path("artifacts/demo").mkdir(parents=True, exist_ok=True)


def ingest_pdf(
    company: str,
    year: int,
    pdf_path: Path
) -> Dict[str, Any]:
    """
    Ingest PDF file.

    Args:
        company: Company name
        year: Reporting year
        pdf_path: Path to source PDF

    Returns:
        Manifest dict with paths
    """
    # Copy PDF to artifacts/raw
    dest_pdf = Path("artifacts/raw") / pdf_path.name
    shutil.copy2(pdf_path, dest_pdf)

    slug = slugify(company)
    bronze_path = Path(f"artifacts/bronze/{slug}_{year}.parquet")

    # Write true Parquet file using pandas
    import pandas as pd
    stub_data = {
        "doc_id": [f"doc_0001"],
        "company": [company],
        "year": [year],
        "source": ["pdf"],
        "path": [str(dest_pdf)],
        "text": [f"PDF stub: {pdf_path.name}"]
    }

    # Write as true Parquet format
    df = pd.DataFrame(stub_data)
    df.to_parquet(bronze_path, index=False)

    # Increment metric
    try:
        from apps.api.metrics import esg_demo_ingest_total
        esg_demo_ingest_total.labels(source="pdf").inc()
    except ImportError as e:
        logger.warning(f"Optional import failed: {e}")  # Metrics not available in test environment

    return {
        "company": company,
        "year": year,
        "slug": slug,
        "sources": {"pdf": str(dest_pdf)},
        "bronze": str(bronze_path)
    }


def ingest_parquet(
    company: str,
    year: int,
    parquet_path: Path
) -> Dict[str, Any]:
    """
    Ingest existing Parquet file.

    Args:
        company: Company name
        year: Reporting year
        parquet_path: Path to source Parquet

    Returns:
        Manifest dict with paths
    """
    slug = slugify(company)
    bronze_path = Path(f"artifacts/bronze/{slug}_{year}.parquet")

    # Copy to bronze
    shutil.copy2(parquet_path, bronze_path)

    # Increment metric
    try:
        from apps.api.metrics import esg_demo_ingest_total
        esg_demo_ingest_total.labels(source="parquet").inc()
    except ImportError as e:
        logger.warning(f"Optional import failed: {e}")  # Metrics not available in test environment

    return {
        "company": company,
        "year": year,
        "slug": slug,
        "sources": {"parquet": str(parquet_path)},
        "bronze": str(bronze_path)
    }


def update_companies_manifest(record: Dict[str, Any]) -> None:
    """
    Update or append to companies.json.

    Args:
        record: Company record to add/update
    """
    companies_path = Path("artifacts/demo/companies.json")

    # Load existing or create new
    if companies_path.exists():
        companies = json.loads(companies_path.read_text())
    else:
        companies = []

    # Update existing or append
    updated = False
    for i, comp in enumerate(companies):
        if comp["company"] == record["company"] and comp["year"] == record["year"]:
            companies[i] = record
            updated = True
            break

    if not updated:
        companies.append(record)

    # Write with sorted keys for determinism
    companies_path.write_text(json.dumps(companies, indent=2, sort_keys=True))


def main() -> int:
    """
    Main CLI entry point.

    Returns:
        Exit code: 0=success, 1=validation error, 2=file not found
    """
    parser = argparse.ArgumentParser(
        description="Ingest company ESG data from PDF or Parquet"
    )
    parser.add_argument("--company", required=True, help="Company name")
    parser.add_argument("--year", required=True, type=int, help="Reporting year")

    # Source group (one required)
    source_group = parser.add_mutually_exclusive_group(required=True)
    source_group.add_argument("--pdf", type=Path, help="Path to PDF file")
    source_group.add_argument("--parquet", type=Path, help="Path to Parquet file")

    args = parser.parse_args()

    try:
        # Validate year
        validate_year(args.year)

        # Ensure directories exist
        ensure_directories()

        # Determine source and check existence
        if args.pdf:
            if not args.pdf.exists():
                print(f"Error: PDF not found: {args.pdf}", file=sys.stderr)
                return 2

            record = ingest_pdf(args.company, args.year, args.pdf)
            print(f"[OK] Ingested PDF: {args.company} ({args.year})")

        elif args.parquet:
            if not args.parquet.exists():
                print(f"Error: Parquet not found: {args.parquet}", file=sys.stderr)
                return 2

            record = ingest_parquet(args.company, args.year, args.parquet)
            print(f"[OK] Ingested Parquet: {args.company} ({args.year})")

        # Update manifest
        update_companies_manifest(record)
        print(f"[OK] Updated companies manifest: {record['slug']}")

        return 0

    except ValueError as e:
        print(f"Validation error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
