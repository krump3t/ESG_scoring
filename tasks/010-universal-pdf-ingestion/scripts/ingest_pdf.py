"""
Task 010: Live PDF Ingestion

Downloads Microsoft Environmental Sustainability Report for authenticity testing.
Validates multi-source ingestion capability (PDF vs HTML).

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

# Microsoft 2024 Environmental Sustainability Report (Stable Link)
# If this 404s, we will need to provide a manual override path
PDF_URL = "https://query.prod.cms.rt.microsoft.com/cms/api/am/binary/RW1l7s"
OUTPUT_PATH = project_root / "data" / "raw" / "pdf" / "MSFT_2024_Environmental.pdf"

logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s: %(message)s'
)
logger = logging.getLogger("PDF_Ingest")


def main():
    """
    Execute PDF ingestion workflow:
    1. Download Microsoft Environmental Sustainability Report
    2. Verify file integrity
    3. Calculate SHA256 hash
    4. Generate provenance manifest
    """
    print("=" * 70)
    print("TASK 010: UNIVERSAL PDF INGESTION")
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
        logger.info(f"Downloading authentic report from Microsoft...")
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
            logger.warning("Creating placeholder file for connectivity testing...")
            logger.warning("NOTE: This is NOT authentic data - for dev/testing only")

            # Create minimal valid PDF structure
            # In production, this would be Fail-Closed (exit with error)
            placeholder_content = """%PDF-1.4
1 0 obj
<<
/Type /Catalog
/Pages 2 0 R
>>
endobj
2 0 obj
<<
/Type /Pages
/Kids [3 0 R]
/Count 1
>>
endobj
3 0 obj
<<
/Type /Page
/Parent 2 0 R
/MediaBox [0 0 612 792]
/Contents 4 0 R
>>
endobj
4 0 obj
<<
/Length 44
>>
stream
BT
/F1 12 Tf
100 700 Td
(Mock PDF - Download Failed) Tj
ET
endstream
endobj
xref
0 5
0000000000 65535 f
0000000009 00000 n
0000000058 00000 n
0000000115 00000 n
0000000214 00000 n
trailer
<<
/Size 5
/Root 1 0 R
>>
startxref
306
%%EOF
"""
            OUTPUT_PATH.write_text(placeholder_content)
            print()

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
        "source": "Microsoft Corporation",
        "document_type": "Environmental Sustainability Report",
        "year": 2024,
        "source_url": PDF_URL,
        "local_path": str(OUTPUT_PATH),
        "file_size_bytes": file_size,
        "file_size_mb": round(size_mb, 2),
        "sha256": sha256,
        "status": status,
        "download_timestamp": "2025-11-19",
        "authenticity": "live_download" if status == "success" else "placeholder"
    }

    manifest_path = project_root / "tasks" / "010-universal-pdf-ingestion" / "artifacts" / "ingestion_manifest.json"
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
        print(f"Document: Microsoft 2024 Environmental Sustainability Report")
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
        print("  - Verify Microsoft URL is still valid")
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
