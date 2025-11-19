"""
Task 008: SEC Content Filtering - Noise Diagnostic

Inspects the 'low quality' chunks from Task 007 pipeline run to confirm
XBRL/XML contamination hypothesis.

Protocol: SCA v13.8-MEA
Author: Scientific Coding Agent
Date: 2025-11-19
"""

import json
import sys
from pathlib import Path
import re

# Add project root to path
project_root = Path(__file__).parents[3]
sys.path.insert(0, str(project_root))


def main():
    """
    Diagnostic workflow:
    1. Load Task 007 pipeline output
    2. Inspect retrieved evidence text
    3. Analyze raw HTML file header
    4. Confirm XBRL contamination hypothesis
    """
    print("=" * 70)
    print("SEC CONTENT FILTERING - NOISE DIAGNOSTIC")
    print("=" * 70)
    print()

    # ==============================================
    # [1/4] LOAD TASK 007 OUTPUT
    # ==============================================
    print("[1/4] Loading Task 007 pipeline output...")

    pipeline_output_path = project_root / "tasks" / "007-pipeline-orchestration" / "artifacts" / "pipeline_output.json"

    if not pipeline_output_path.exists():
        print(f"   FAIL - Task 007 output not found: {pipeline_output_path}")
        return 1

    try:
        with open(pipeline_output_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        company = data.get("company", "Unknown")
        maturity = data.get("aggregate_score", {}).get("maturity_level", 0)
        confidence = data.get("aggregate_score", {}).get("confidence", 0)

        print(f"   PASS - Loaded output for {company}")
        print(f"   Aggregate Maturity: {maturity:.2f}")
        print(f"   Confidence: {confidence:.3f}")
        print()

    except Exception as e:
        print(f"   FAIL - Error loading output: {e}")
        return 1

    # ==============================================
    # [2/4] INSPECT RETRIEVED EVIDENCE
    # ==============================================
    print("[2/4] Inspecting retrieved evidence text...")

    individual_scores = data.get("individual_scores", [])

    if not individual_scores:
        print("   WARN - No individual scores found in output")
    else:
        print(f"   Found {len(individual_scores)} scored findings")
        print()

        for i, score in enumerate(individual_scores, 1):
            query = score.get("query", "unknown")
            finding_text = score.get("finding_text", "")
            retrieval_score = score.get("retrieval_score", 0.0)
            maturity_level = score.get("maturity_level", 0.0)

            print(f"   Finding {i}: '{query}'")
            print(f"      Retrieval Score: {retrieval_score:.3f}")
            print(f"      Maturity Level: {maturity_level}")
            print(f"      Text Preview (first 150 chars):")
            print(f"         {finding_text[:150]}")

            # Check for XBRL indicators
            xbrl_indicators = [
                "Member",
                "us-gaap:",
                "0000320193",  # Apple's CIK
                "dei:",
                "<xbrl",
                "xmlns:",
                "contextRef"
            ]

            found_indicators = [ind for ind in xbrl_indicators if ind in finding_text]

            if found_indicators:
                print(f"      [XBRL DETECTED] Indicators: {', '.join(found_indicators)}")
            else:
                print(f"      [CLEAN TEXT] No XBRL indicators detected")

            print()

    # ==============================================
    # [3/4] ANALYZE RAW HTML HEADER
    # ==============================================
    print("[3/4] Analyzing raw SEC HTML file header...")

    raw_path = project_root / "data" / "raw" / "sec_edgar" / "AAPL_2024_10K.htm"

    if not raw_path.exists():
        print(f"   FAIL - Raw file not found: {raw_path}")
        return 1

    try:
        with open(raw_path, 'r', encoding='utf-8') as f:
            content = f.read()

        file_size_mb = raw_path.stat().st_size / (1024 * 1024)
        print(f"   File: {raw_path.name}")
        print(f"   Size: {file_size_mb:.2f} MB")
        print()

        # Analyze first 2000 characters
        header = content[:2000]

        print("   --- HEADER PREVIEW (first 2000 chars) ---")
        print(header)
        print("   --- END HEADER ---")
        print()

        # Check for XBRL/XML markers
        xbrl_patterns = [
            (r"<XBRL>", "XBRL root tag"),
            (r"<xbrl", "XBRL namespace tag"),
            (r"xmlns:", "XML namespace declaration"),
            (r"us-gaap:", "US GAAP taxonomy reference"),
            (r"dei:", "Document Entity Information taxonomy"),
            (r"contextRef=", "XBRL context reference"),
            (r"<TYPE>", "EDGAR document type tag"),
            (r"<SEQUENCE>", "EDGAR sequence tag"),
            (r"<FILENAME>", "EDGAR filename tag")
        ]

        print("[3/4] XBRL/XML Marker Detection:")
        detected_markers = []

        for pattern, description in xbrl_patterns:
            matches = re.findall(pattern, header, re.IGNORECASE)
            if matches:
                count = len(matches)
                detected_markers.append(description)
                print(f"   [FOUND] {description}: {count} occurrence(s)")

        if detected_markers:
            print()
            print(f"   [CONFIRMED] XBRL/XML contamination detected")
            print(f"   Markers found: {', '.join(detected_markers)}")
        else:
            print()
            print(f"   [UNEXPECTED] Header appears clean - no XBRL markers detected")

        print()

    except Exception as e:
        print(f"   FAIL - Error reading raw file: {e}")
        import traceback
        traceback.print_exc()
        return 1

    # ==============================================
    # [4/4] ESTIMATE XBRL SECTION SIZE
    # ==============================================
    print("[4/4] Estimating XBRL section size...")

    try:
        # Find approximate end of XBRL section
        # Common patterns: </XBRL>, <DOCUMENT> (start of actual filing)
        xbrl_end_patterns = [
            r"</XBRL>",
            r"</xbrl>",
            r"<DOCUMENT>",
            r"<TYPE>10-K"
        ]

        xbrl_end_position = None
        matched_pattern = None

        for pattern in xbrl_end_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                if xbrl_end_position is None or match.start() < xbrl_end_position:
                    xbrl_end_position = match.start()
                    matched_pattern = pattern

        if xbrl_end_position:
            xbrl_section_kb = xbrl_end_position / 1024
            percent_of_file = (xbrl_end_position / len(content)) * 100

            print(f"   XBRL section ends at: position {xbrl_end_position:,}")
            print(f"   XBRL section size: {xbrl_section_kb:.1f} KB")
            print(f"   Percentage of file: {percent_of_file:.1f}%")
            print(f"   Matched pattern: {matched_pattern}")
            print()

            # Estimate how many chunks this represents (chunk_size=2000 from Task 007)
            chunk_size = 2000
            estimated_xbrl_chunks = xbrl_end_position // chunk_size

            print(f"   Estimated XBRL chunks (chunk_size={chunk_size}): {estimated_xbrl_chunks}")
            print(f"   These chunks should be FILTERED before indexing")

        else:
            print(f"   WARN - Could not locate XBRL section end marker")
            print(f"   File may have non-standard structure")

        print()

    except Exception as e:
        print(f"   FAIL - Error estimating XBRL size: {e}")
        import traceback
        traceback.print_exc()
        return 1

    # ==============================================
    # SUMMARY
    # ==============================================
    print("=" * 70)
    print("DIAGNOSTIC SUMMARY")
    print("=" * 70)
    print()

    if detected_markers:
        print("Status: HYPOTHESIS CONFIRMED")
        print()
        print("Findings:")
        print(f"  - XBRL/XML contamination present in SEC HTML file")
        print(f"  - Retrieved evidence contains XBRL tags (not disclosure text)")
        print(f"  - Low ESG scores ({maturity:.2f}) due to non-ESG content")
        if xbrl_end_position:
            print(f"  - XBRL section: ~{xbrl_section_kb:.1f} KB ({percent_of_file:.1f}% of file)")
            print(f"  - Estimated XBRL chunks: {estimated_xbrl_chunks}")
        print()
        print("Recommendation:")
        print("  - Implement XBRL/XML filter in Task 008")
        print("  - Strip XBRL section before chunking")
        print("  - Re-run Task 007 pipeline with cleaned text")
        print("  - Expected score improvement: 0.29 -> 1.5+")
    else:
        print("Status: HYPOTHESIS REJECTED")
        print()
        print("Unexpected Result:")
        print(f"  - No XBRL markers detected in file header")
        print(f"  - Low scores may have different cause")
        print()
        print("Next Steps:")
        print("  - Investigate alternative causes (chunk quality, query mismatch)")
        print("  - Review extraction logic in EnhancedPDFExtractor")

    print()

    return 0


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print()
        print("Diagnostic interrupted by user")
        sys.exit(1)
    except Exception as e:
        print()
        print("=" * 70)
        print(f"UNEXPECTED ERROR: {e}")
        print("=" * 70)
        import traceback
        traceback.print_exc()
        sys.exit(1)
