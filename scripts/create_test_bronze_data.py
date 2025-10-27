"""
Create test bronze data with synthetic ESG report
For demonstration and validation purposes
"""
import sys
from pathlib import Path
import tempfile
from datetime import datetime
import uuid
import os

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.crawler.extractors.pdf_extractor import PDFExtractor
from agents.crawler.writers.parquet_writer import ParquetWriter


def create_test_pdf() -> str:
    """Create a test PDF with ESG-like content"""
    try:
        import fitz  # PyMuPDF

        # Create temporary PDF
        temp_dir = tempfile.gettempdir()
        pdf_path = os.path.join(temp_dir, 'test_esg_report_2024.pdf')

        doc = fitz.open()

        # Page 1: Title and Executive Summary
        page1 = doc.new_page()
        text1 = """Environmental, Social, and Governance Report 2024

Test Corporation Environmental Sustainability Report

Executive Summary:
Test Corporation is committed to achieving net-zero emissions by 2030.
We have set science-based targets (SBTi) approved in Q1 2024.

Our comprehensive GHG Protocol-compliant emissions reporting covers:
- Scope 1: Direct emissions from owned facilities
- Scope 2: Indirect emissions from purchased energy
- Scope 3: Value chain emissions (15 categories)

Key Achievements 2024:
- 45% reduction in Scope 1 & 2 emissions vs 2020 baseline
- 100% renewable energy procurement for all operations
- TCFD-aligned climate risk disclosure
- ISO 14001 certified environmental management system
        """
        page1.insert_text((72, 72), text1, fontsize=11)

        # Page 2: Targets and Metrics
        page2 = doc.new_page()
        text2 = """Climate Targets and Performance Metrics

Science-Based Targets (SBTi Approved):
- Near-term: 50% absolute reduction in Scope 1+2 by 2030 (vs 2020)
- Long-term: Net-zero across value chain by 2050
- Scope 3: 30% reduction per unit revenue by 2030

Greenhouse Gas Inventory (tCO2e):
                    2020      2023      2024      Target 2030
Scope 1:           50,000    35,000    27,500    25,000
Scope 2 (loc):     80,000    20,000     5,000         0
Scope 2 (mkt):     80,000    10,000         0         0
Scope 3:          450,000   420,000   400,000   315,000

Third-party Assurance: Limited assurance provided by EY (2024)

Data Quality and Governance:
- Automated data collection via centralized EMS platform
- Real-time validation and lineage tracking
- Quarterly audits by ESG Steering Committee
        """
        page2.insert_text((72, 72), text2, fontsize=10)

        # Page 3: Frameworks and Compliance
        page3 = doc.new_page()
        text3 = """Reporting Frameworks and Compliance

Our ESG reporting aligns with multiple frameworks:

ISSB/TCFD:
- Full climate-related financial disclosure
- Scenario analysis (1.5C, 2C, 3C pathways)
- Climate risk integration into enterprise risk management

GHG Protocol:
- Corporate Accounting Standard compliant
- Comprehensive Scope 1, 2, 3 inventory
- Recalculation policy for base year adjustments

CSRD/ESRS:
- Dual materiality assessment conducted
- Digital tagging (XBRL) in preparation
- Supply chain due diligence programs

External Validation:
- CDP Climate: A rating (2024)
- MSCI ESG Rating: AA
- Sustainalytics ESG Risk: Low (15.2)

Data Systems:
- Apache Iceberg-based data lake architecture
- Automated ETL pipelines with Parquet storage
- Real-time dashboards for KPI monitoring
        """
        page3.insert_text((72, 72), text3, fontsize=10)

        doc.save(pdf_path)
        doc.close()

        return pdf_path

    except ImportError:
        print("ERROR: PyMuPDF not installed - cannot create test PDF")
        return None


def main():
    print("="*60)
    print("CREATE TEST BRONZE DATA")
    print("="*60)

    # Create test PDF
    print(f"\n1. Creating test ESG report PDF...")
    pdf_path = create_test_pdf()

    if not pdf_path:
        print("   FAILED - PyMuPDF not available")
        return False

    print(f"   Created: {pdf_path}")

    # Extract PDF
    print(f"\n2. Extracting PDF content...")
    try:
        extractor = PDFExtractor()
        result = extractor.extract(pdf_path)

        print(f"   Pages: {result['page_count']}")
        print(f"   Text length: {len(result['text'])} characters")
        print(f"   Tables: {len(result['tables'])}")
        print(f"   Figures: {len(result['figures'])}")
        print(f"   SHA256: {result['sha256'][:16]}...")

        # Check for framework mentions
        text_lower = result['text'].lower()
        frameworks = []
        if 'sbti' in text_lower or 'science-based' in text_lower:
            frameworks.append('SBTi')
        if 'tcfd' in text_lower or 'issb' in text_lower:
            frameworks.append('TCFD/ISSB')
        if 'ghg protocol' in text_lower:
            frameworks.append('GHG Protocol')
        if 'csrd' in text_lower or 'esrs' in text_lower:
            frameworks.append('CSRD/ESRS')

        print(f"   Detected frameworks: {', '.join(frameworks)}")

    except Exception as e:
        print(f"   ERROR extracting: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Prepare data for bronze layer
    print(f"\n3. Preparing data for bronze layer...")
    doc_id = str(uuid.uuid4())
    company = "test_corporation"
    year = 2024

    data = {
        'org_id': company,
        'year': year,
        'doc_id': doc_id,
        'source_url': f'file://{pdf_path}',
        'doc_type': 'pdf',
        'extraction_timestamp': datetime.now(),
        'sha256': result['sha256'],
        'page_count': result['page_count'],
        'raw_text': result['text'],
        'tables': result.get('tables', []),
        'figures': result.get('figures', []),
        'metadata': result.get('metadata', {})
    }

    print(f"   org_id: {company}")
    print(f"   year: {year}")
    print(f"   doc_id: {doc_id}")

    # Write to bronze layer
    print(f"\n4. Writing to bronze layer (MinIO)...")
    try:
        writer = ParquetWriter(
            minio_endpoint='localhost:9000',
            access_key='minioadmin',
            secret_key='minioadmin',
            bucket='esg-lake'
        )

        success = writer.write(data, atomic=True)

        if success:
            s3_path = writer.generate_path(company, year, doc_id)
            print(f"   SUCCESS!")
            print(f"   Path: s3://esg-lake/{s3_path}")
        else:
            print(f"   FAILED to write")
            return False

    except Exception as e:
        print(f"   ERROR writing: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Verify in MinIO
    print(f"\n5. Verifying in MinIO...")
    try:
        from minio import Minio

        client = Minio(
            'localhost:9000',
            access_key='minioadmin',
            secret_key='minioadmin',
            secure=False
        )

        # Check if object exists
        stat = client.stat_object('esg-lake', s3_path)
        print(f"   File size: {stat.size} bytes")
        print(f"   Last modified: {stat.last_modified}")
        print(f"   Content type: {stat.content_type}")
        print(f"   VERIFIED!")

    except Exception as e:
        print(f"   ERROR verifying: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "="*60)
    print("TEST BRONZE DATA CREATED SUCCESSFULLY")
    print("="*60)
    print(f"\nBronze layer path: s3://esg-lake/{s3_path}")
    print(f"Organization: {company}")
    print(f"Year: {year}")
    print(f"Document ID: {doc_id}")
    print(f"SHA256: {result['sha256']}")
    print(f"\nFrameworks detected: {', '.join(frameworks)}")
    print("\nNext: Query with Trino to validate Parquet schema")

    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
