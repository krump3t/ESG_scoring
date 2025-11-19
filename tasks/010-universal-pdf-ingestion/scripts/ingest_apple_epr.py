"""
Task 010: Alternative PDF Ingestion - Apple Environmental Progress Report

Fallback when Microsoft URL is unavailable.
Uses Apple's publicly available sustainability report.

Protocol: SCA v13.8-MEA
Date: 2025-11-19
"""
import requests
import logging
import json
from pathlib import Path
import hashlib
import sys

# Add project root to path
project_root = Path(__file__).parents[3]
sys.path.insert(0, str(project_root))

# Apple Environmental Progress Report 2024
# Alternative reliable source for PDF ingestion testing
PDF_URL = "https://www.apple.com/environment/pdf/Apple_Environmental_Progress_Report_2024.pdf"
OUTPUT_PATH = project_root / "data" / "raw" / "pdf" / "AAPL_2024_Environmental.pdf"

logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s: %(message)s'
)
logger = logging.getLogger("PDF_Ingest")


def main():
    """
    Execute PDF ingestion workflow:
    1. Download Apple Environmental Progress Report
    2. Verify file integrity
    3. Calculate SHA256 hash
    4. Generate provenance manifest
    """
    print("=" * 70)
    print("TASK 010: UNIVERSAL PDF INGESTION (Alternative Source)")
    print("=" * 70)
    print()

    # Create output directory
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    # Check if file already exists
    if OUTPUT_PATH.exists():
        logger.info(f"File already exists at {OUTPUT_PATH}")
        logger.info("Skipping download (use existing file)")
        print()
    else:
        # Download file
        logger.info(f"Downloading authentic report from Apple...")
        logger.info(f"URL: {PDF_URL}")
        print()

        try:
            response = requests.get(PDF_URL, stream=True, timeout=30)
            response.raise_for_status()

            logger.info("Download in progress...")
            with open(OUTPUT_PATH, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)

            logger.info("Download complete.")
            print()

        except requests.exceptions.RequestException as e:
            logger.error(f"Download failed: {e}")
            print()
            logger.warning("Both Microsoft and Apple URLs failed.")
            logger.warning("Proceeding with placeholder for extraction testing only.")

            # Use existing placeholder
            placeholder_path = project_root / "data" / "raw" / "pdf" / "MSFT_2024_Environmental.pdf"
            if placeholder_path.exists():
                logger.info(f"Using existing placeholder: {placeholder_path}")
                return 1
            else:
                logger.error("No placeholder available. Manual intervention required.")
                return 1

    # Verify file
    logger.info("Verifying downloaded file...")

    if not OUTPUT_PATH.exists():
        logger.error(f"File not found: {OUTPUT_PATH}")
        return 1

    file_size = OUTPUT_PATH.stat().st_size
    size_mb = file_size / (1024 * 1024)

    logger.info(f"File: {OUTPUT_PATH.name}")
    logger.info(f"Path: {OUTPUT_PATH}")
    logger.info(f"Size: {size_mb:.2f} MB ({file_size:,} bytes)")
    print()

    # Check if file is suspiciously small (likely placeholder)
    if size_mb < 0.1:
        logger.warning("File size < 0.1 MB - likely placeholder/mock data")
        status = "mocked"
    else:
        logger.info("File size looks reasonable for PDF report")
        status = "success"

    # Calculate hash for provenance
    logger.info("Calculating SHA256 hash...")
    file_bytes = OUTPUT_PATH.read_bytes()
    sha256 = hashlib.sha256(file_bytes).hexdigest()

    logger.info(f"SHA256: {sha256}")
    print()

    # Quick validation - check PDF header
    header = file_bytes[:8].decode('latin1', errors='ignore')
    if header.startswith('%PDF'):
        pdf_version = header.strip()
        logger.info(f"PDF Header: {pdf_version}")
        logger.info("File appears to be valid PDF")
    else:
        logger.warning("File does not have standard PDF header")
        logger.warning(f"Header: {header}")

    print()

    # Write manifest
    manifest = {
        "task_id": "010-universal-pdf-ingestion",
        "source": "Apple Inc.",
        "document_type": "Environmental Progress Report",
        "year": 2024,
        "source_url": PDF_URL,
        "local_path": str(OUTPUT_PATH),
        "file_size_bytes": file_size,
        "file_size_mb": round(size_mb, 2),
        "sha256": sha256,
        "status": status,
        "download_timestamp": "2025-11-19",
        "authenticity": "live_download" if status == "success" else "placeholder",
        "notes": "Alternative source (Apple) used due to Microsoft 503 error"
    }

    manifest_path = project_root / "tasks" / "010-universal-pdf-ingestion" / "artifacts" / "ingestion_manifest_apple.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)

    with open(manifest_path, 'w') as f:
        json.dump(manifest, f, indent=2)

    logger.info(f"Manifest saved to: {manifest_path}")
    print()

    # Summary
    print("=" * 70)
    print("INGESTION SUMMARY")
    print("=" * 70)
    print()

    if status == "success":
        print("Status: SUCCESS - Authentic PDF downloaded")
        print()
        print(f"Document: Apple 2024 Environmental Progress Report")
        print(f"Size: {size_mb:.2f} MB")
        print(f"SHA256: {sha256[:16]}...")
        print()
        print("Next Steps:")
        print("  - Validate PDF can be opened")
        print("  - Extract chunks with EnhancedPDFExtractor")
        print("  - Run scoring pipeline")
    else:
        print("Status: DEGRADED - Using placeholder data")
        print()
        print("WARNING: Placeholder PDF created due to download failure")
        print("This file is NOT authentic and should not be used for scoring")
        print()
        print("Recommended Actions:")
        print("  - Check network connectivity")
        print("  - Verify Apple URL is still valid")
        print("  - Manually download and place at:")
        print(f"    {OUTPUT_PATH}")

    print()

    return 0


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print()
        print("Ingestion interrupted by user")
        sys.exit(1)
    except Exception as e:
        print()
        print("=" * 70)
        print(f"UNEXPECTED ERROR: {e}")
        print("=" * 70)
        import traceback
        traceback.print_exc()
        sys.exit(1)
