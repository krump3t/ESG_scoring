"""
Integration Verification: Clean Real Apple 10-K
Protocol: SCA v13.8-MEA

Applies SecHtmlCleaner to authentic Apple 2024 10-K and validates output quality.
"""
import re
from pathlib import Path
import sys


# Copy the cleaner class here or import if we moved it to a library file
# For simplicity in this verification script, we include the logic
class SecHtmlCleaner:
    """Surgical cleaner for SEC EDGAR HTML/XBRL files."""

    def clean(self, raw_html: str) -> str:
        """
        Remove XBRL/XML metadata while preserving disclosure narrative.

        Args:
            raw_html: Raw SEC EDGAR HTML with inline XBRL

        Returns:
            Cleaned text with XBRL artifacts removed
        """
        if not raw_html:
            return ""

        # 1. Remove the hidden XBRL header (contains massive metadata blocks)
        # Target: <ix:header> ... </ix:header>
        # Using dotall regex to span newlines
        text = re.sub(r'<ix:header>.*?</ix:header>', '', raw_html, flags=re.DOTALL | re.IGNORECASE)

        # 2. Remove specific XBRL tags but KEEP content if it's narrative
        # <ix:nonNumeric ...> Actual Text </ix:nonNumeric> -> Actual Text
        text = re.sub(r'</?ix:\w+[^>]*>', ' ', text)

        # 3. Remove XML style tags <xbrldi:...>
        text = re.sub(r'</?xbrldi:\w+[^>]*>', ' ', text)

        # 4. Standard HTML cleanup (scripts, styles)
        text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL | re.IGNORECASE)

        # 5. Aggressive Tag Strip (The nuclear option for remaining tags)
        text = re.sub(r'<[^>]+>', ' ', text)

        # 6. Whitespace normalization
        text = re.sub(r'\s+', ' ', text).strip()

        return text


def main():
    """
    Execute live cleaning verification workflow:
    1. Load raw Apple 10-K HTML
    2. Apply SecHtmlCleaner
    3. Validate output quality
    4. Save preview for inspection
    """
    print("=" * 70)
    print("LIVE CLEANING VERIFICATION: Apple 2024 10-K")
    print("=" * 70)
    print()

    # Load raw file
    raw_path = Path("data/raw/sec_edgar/AAPL_2024_10K.htm")

    if not raw_path.exists():
        print(f"   FAIL - {raw_path} not found")
        sys.exit(1)

    file_size_mb = raw_path.stat().st_size / (1024 * 1024)
    print(f"[1/4] Loading {raw_path.name} ({file_size_mb:.2f} MB)...")

    try:
        raw_content = raw_path.read_text(encoding='utf-8')
        print(f"   PASS - Loaded {len(raw_content):,} characters")
        print()
    except Exception as e:
        print(f"   FAIL - Error loading file: {e}")
        sys.exit(1)

    # Apply cleaner
    print("[2/4] Applying SecHtmlCleaner...")

    cleaner = SecHtmlCleaner()
    clean_text = cleaner.clean(raw_content)

    reduction_pct = 100 * (1 - len(clean_text) / len(raw_content))

    print(f"   Original Length: {len(raw_content):,} chars")
    print(f"   Cleaned Length:  {len(clean_text):,} chars")
    print(f"   Reduction:       {reduction_pct:.1f}%")
    print()

    # Quality Checks
    print("[3/4] Validating output quality...")

    validation_errors = []

    # Check for XBRL leaks
    if "us-gaap" in clean_text:
        count = clean_text.count("us-gaap")
        validation_errors.append(f"Found 'us-gaap' {count} times (XBRL Leak)")

    if "ix:header" in clean_text:
        validation_errors.append("Found 'ix:header' (XBRL Leak)")

    if "<xml" in clean_text.lower():
        validation_errors.append("Found XML tags")

    # Check for common XBRL patterns
    xbrl_patterns = ["contextRef=", "xmlns:", "xbrldi:", "dei:"]
    for pattern in xbrl_patterns:
        if pattern in clean_text:
            count = clean_text.count(pattern)
            validation_errors.append(f"Found '{pattern}' {count} times (XBRL Leak)")

    if validation_errors:
        print("   [FAIL] Cleaning incomplete:")
        for err in validation_errors:
            print(f"      - {err}")

        # Show context of first failure
        if "us-gaap" in clean_text:
            idx = clean_text.find("us-gaap")
            context_start = max(0, idx - 100)
            context_end = min(len(clean_text), idx + 100)
            print()
            print("   Context of 'us-gaap' leak:")
            print(f"   ...{clean_text[context_start:context_end]}...")
        print()

    else:
        print("   [SUCCESS] XBRL artifacts successfully removed")
        print()

    # Check for disclosure text preservation
    print("[4/4] Checking disclosure text preservation...")

    # Common SEC 10-K disclosure phrases (should be preserved)
    expected_phrases = [
        "risk factors",
        "business",
        "company",
        "fiscal year",
        "financial",
        "market",
        "operations"
    ]

    found_phrases = []
    for phrase in expected_phrases:
        if phrase.lower() in clean_text.lower():
            found_phrases.append(phrase)

    if found_phrases:
        print(f"   [PASS] Found {len(found_phrases)}/{len(expected_phrases)} expected disclosure phrases:")
        for phrase in found_phrases[:5]:  # Show first 5
            print(f"      - '{phrase}'")
        print()
    else:
        print(f"   [WARN] No expected disclosure phrases found")
        print(f"   File may have been over-cleaned")
        print()

    # Save preview
    artifacts_dir = Path("tasks/008-sec-content-filtering/artifacts")
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    preview_path = artifacts_dir / "clean_preview.txt"
    preview_length = 5000

    try:
        preview_path.write_text(clean_text[:preview_length], encoding='utf-8')
        print(f"   Preview saved to: {preview_path}")
        print(f"   Preview length: {preview_length} characters")
        print()
    except Exception as e:
        print(f"   WARN - Could not save preview: {e}")
        print()

    # Summary
    print("=" * 70)
    print("VERIFICATION SUMMARY")
    print("=" * 70)
    print()

    if validation_errors:
        print("Status: FAIL - XBRL contamination still present")
        print()
        print("Issues:")
        for err in validation_errors:
            print(f"  - {err}")
        print()
        print("Next Steps:")
        print("  - Review cleaner regex patterns")
        print("  - Add more aggressive XBRL removal")
        print("  - Re-run verification")
        return 1

    else:
        print("Status: SUCCESS - Cleaning verified")
        print()
        print("Results:")
        print(f"  - Original size: {len(raw_content):,} chars ({file_size_mb:.2f} MB)")
        print(f"  - Cleaned size: {len(clean_text):,} chars")
        print(f"  - Reduction: {reduction_pct:.1f}%")
        print(f"  - Disclosure phrases preserved: {len(found_phrases)}/{len(expected_phrases)}")
        print()
        print("Next Steps:")
        print("  - Integrate cleaner into Task 007 pipeline")
        print("  - Re-run orchestration with cleaned text")
        print("  - Expect score improvement: 0.29 -> 1.5+")
        print()
        return 0


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print()
        print("Verification interrupted by user")
        sys.exit(1)
    except Exception as e:
        print()
        print("=" * 70)
        print(f"UNEXPECTED ERROR: {e}")
        print("=" * 70)
        import traceback
        traceback.print_exc()
        sys.exit(1)
