"""
Task 010: Validate PDF Extraction

Tests EnhancedPDFExtractor on Apple Environmental Progress Report.
Proves pipeline handles non-SEC PDF format.

Protocol: SCA v13.8-MEA
Date: 2025-11-19
"""

import sys
import json
from pathlib import Path
from typing import List, Dict, Any

# Add project root to path
project_root = Path(__file__).parents[3]
sys.path.insert(0, str(project_root))

from agents.extraction.enhanced_pdf_extractor import EnhancedPDFExtractor


def analyze_chunks(chunks: List[Any]) -> Dict[str, Any]:
    """
    Analyze extracted chunks for quality and ESG content.

    Args:
        chunks: List of ExtractedChunk objects

    Returns:
        Dictionary with analysis results
    """
    # ESG keyword vocabulary
    esg_keywords = [
        "climate", "environmental", "carbon", "emissions", "greenhouse",
        "renewable", "energy", "sustainability", "esg", "pollution",
        "water", "waste", "recycling", "biodiversity", "social",
        "supply chain", "materials", "footprint", "net zero", "clean energy"
    ]

    # Collect statistics
    total_chunks = len(chunks)
    total_chars = sum(len(chunk.text) for chunk in chunks)
    avg_chunk_size = total_chars / total_chunks if total_chunks > 0 else 0

    # Count ESG keyword occurrences
    esg_keyword_counts = {kw: 0 for kw in esg_keywords}
    chunks_with_esg_content = 0

    for chunk in chunks:
        text_lower = chunk.text.lower()
        has_esg = False

        for keyword in esg_keywords:
            count = text_lower.count(keyword.lower())
            if count > 0:
                esg_keyword_counts[keyword] += count
                has_esg = True

        if has_esg:
            chunks_with_esg_content += 1

    # Calculate ESG density
    esg_density = chunks_with_esg_content / total_chunks if total_chunks > 0 else 0

    # Find top ESG keywords
    top_keywords = sorted(
        esg_keyword_counts.items(),
        key=lambda x: x[1],
        reverse=True
    )[:10]

    # Find sample chunks with high ESG content
    chunk_esg_scores = []
    for i, chunk in enumerate(chunks[:50]):  # Sample first 50
        text_lower = chunk.text.lower()
        score = sum(text_lower.count(kw.lower()) for kw in esg_keywords)
        chunk_esg_scores.append((i, score, chunk.text[:200]))

    top_chunks = sorted(chunk_esg_scores, key=lambda x: x[1], reverse=True)[:5]

    return {
        "total_chunks": total_chunks,
        "total_characters": total_chars,
        "avg_chunk_size": round(avg_chunk_size, 1),
        "chunks_with_esg_content": chunks_with_esg_content,
        "esg_density_percent": round(esg_density * 100, 1),
        "top_esg_keywords": [{"keyword": kw, "count": count} for kw, count in top_keywords],
        "sample_high_esg_chunks": [
            {
                "chunk_index": idx,
                "esg_keyword_count": score,
                "text_preview": text[:150] + "..."
            }
            for idx, score, text in top_chunks
        ]
    }


def main():
    """
    Execute extraction validation:
    1. Load Apple Environmental Progress Report PDF
    2. Extract chunks using EnhancedPDFExtractor
    3. Analyze chunk quality and ESG content
    4. Generate validation report
    """
    print("=" * 70)
    print("TASK 010: PDF EXTRACTION VALIDATION")
    print("=" * 70)
    print()

    # ==========================================
    # [1/4] LOAD PDF FILE
    # ==========================================
    print("[1/4] Loading PDF file...")

    pdf_file = project_root / "data" / "raw" / "pdf" / "AAPL_2024_Environmental.pdf"

    if not pdf_file.exists():
        print(f"   FAIL - PDF file not found: {pdf_file}")
        return 1

    file_size_mb = pdf_file.stat().st_size / (1024 * 1024)
    print(f"   PASS - Found: {pdf_file.name}")
    print(f"   Size: {file_size_mb:.2f} MB")
    print()

    # ==========================================
    # [2/4] EXTRACT CHUNKS
    # ==========================================
    print("[2/4] Extracting chunks with EnhancedPDFExtractor...")

    try:
        extractor = EnhancedPDFExtractor(
            source_url="https://www.apple.com/environment/pdf/Apple_Environmental_Progress_Report_2024.pdf",
            provider="AppleCorporate"
        )

        chunks = extractor.extract_from_file(
            file_path=str(pdf_file),
            doc_id="AAPL_2024_EPR",
            chunk_size=2000
        )

        print(f"   PASS - Extracted {len(chunks)} chunks")
        print()

    except Exception as e:
        print(f"   FAIL - Extraction error: {e}")
        import traceback
        traceback.print_exc()
        return 1

    # ==========================================
    # [3/4] ANALYZE CHUNKS
    # ==========================================
    print("[3/4] Analyzing chunk quality and ESG content...")

    try:
        analysis = analyze_chunks(chunks)

        print(f"   Total Chunks: {analysis['total_chunks']}")
        print(f"   Total Characters: {analysis['total_characters']:,}")
        print(f"   Avg Chunk Size: {analysis['avg_chunk_size']:.1f} chars")
        print(f"   Chunks with ESG Content: {analysis['chunks_with_esg_content']} ({analysis['esg_density_percent']}%)")
        print()

        print("   Top ESG Keywords:")
        for item in analysis['top_esg_keywords'][:5]:
            print(f"      - {item['keyword']}: {item['count']} occurrences")
        print()

        print("   Sample High-ESG Chunk:")
        if analysis['sample_high_esg_chunks']:
            sample = analysis['sample_high_esg_chunks'][0]
            print(f"      Chunk {sample['chunk_index']}: {sample['esg_keyword_count']} ESG keywords")
            print(f"      Preview: {sample['text_preview']}")
        print()

    except Exception as e:
        print(f"   FAIL - Analysis error: {e}")
        import traceback
        traceback.print_exc()
        return 1

    # ==========================================
    # [4/4] GENERATE VALIDATION REPORT
    # ==========================================
    print("[4/4] Generating validation report...")

    try:
        # Create validation output
        validation_output = {
            "task_id": "010-universal-pdf-ingestion",
            "validation_type": "extraction",
            "source_document": {
                "company": "Apple Inc.",
                "document_type": "Environmental Progress Report",
                "year": 2024,
                "file_path": str(pdf_file),
                "file_size_mb": round(file_size_mb, 2)
            },
            "extraction_results": {
                "extractor": "EnhancedPDFExtractor",
                "total_chunks": analysis['total_chunks'],
                "total_characters": analysis['total_characters'],
                "avg_chunk_size": analysis['avg_chunk_size']
            },
            "esg_content_analysis": {
                "chunks_with_esg_content": analysis['chunks_with_esg_content'],
                "esg_density_percent": analysis['esg_density_percent'],
                "top_keywords": analysis['top_esg_keywords'][:10],
                "sample_chunks": analysis['sample_high_esg_chunks'][:3]
            },
            "validation_status": "PASS",
            "validation_criteria": {
                "chunks_extracted": analysis['total_chunks'] > 0,
                "esg_content_present": analysis['esg_density_percent'] > 50.0,
                "avg_chunk_size_reasonable": 500 < analysis['avg_chunk_size'] < 3000
            }
        }

        # Determine overall validation status
        all_criteria_pass = all(validation_output['validation_criteria'].values())
        validation_output['validation_status'] = "PASS" if all_criteria_pass else "FAIL"

        # Save to artifacts
        output_file = project_root / "tasks" / "010-universal-pdf-ingestion" / "artifacts" / "extraction_validation.json"
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(validation_output, f, indent=2, ensure_ascii=False)

        print(f"   PASS - Report saved to: {output_file.name}")
        print()

    except Exception as e:
        print(f"   FAIL - Report generation error: {e}")
        import traceback
        traceback.print_exc()
        return 1

    # ==========================================
    # SUMMARY
    # ==========================================
    print("=" * 70)
    print("VALIDATION SUMMARY")
    print("=" * 70)
    print()

    if validation_output['validation_status'] == "PASS":
        print("Status: PASS - PDF extraction validated successfully")
        print()
        print("Key Findings:")
        print(f"  - Extracted {analysis['total_chunks']} chunks from 29.35 MB PDF")
        print(f"  - ESG content density: {analysis['esg_density_percent']}%")
        print(f"  - Top keywords: {', '.join([kw['keyword'] for kw in analysis['top_esg_keywords'][:3]])}")
        print()
        print("Validation Criteria:")
        for criterion, passed in validation_output['validation_criteria'].items():
            status = "✓" if passed else "✗"
            print(f"  {status} {criterion}: {passed}")
        print()
        print("Next Steps:")
        print("  - Run scoring pipeline on PDF chunks")
        print("  - Compare PDF vs HTML extraction quality")
        print("  - Document multi-source capability")
    else:
        print("Status: FAIL - Validation criteria not met")
        print()
        print("Failed Criteria:")
        for criterion, passed in validation_output['validation_criteria'].items():
            if not passed:
                print(f"  - {criterion}: {passed}")
        print()

    print()

    return 0 if validation_output['validation_status'] == "PASS" else 1


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print()
        print("Validation interrupted by user")
        sys.exit(1)
    except Exception as e:
        print()
        print("=" * 70)
        print(f"UNEXPECTED ERROR: {e}")
        print("=" * 70)
        import traceback
        traceback.print_exc()
        sys.exit(1)
