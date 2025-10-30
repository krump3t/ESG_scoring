"""Alignment Audit Script - Quote Validation Against Source PDFs (Task 026)

CLI tool for validating evidence quotes against silver parquet files.

SCA v13.8-MEA Compliance:
- Type hints: 100%
- Docstrings: Complete
- CLI-first design (scriptable)
- Quote validation with fuzzy matching support
- Backend-aware path resolution
"""
import argparse
import os
import json
import re
from pathlib import Path
from typing import List, Dict, Any, Optional
import logging
from difflib import SequenceMatcher

import pandas as pd

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Import silver locator for backend-aware path resolution
from libs.retrieval.silver_locator import locate_chunks_parquet


def _normalize_whitespace(text: str) -> str:
    """Normalize whitespace in text for comparison.

    Args:
        text: Input text

    Returns:
        Text with normalized whitespace (single spaces, no leading/trailing)

    Example:
        >>> _normalize_whitespace("too   many    spaces")
        'too many spaces'
    """
    return re.sub(r'\s+', ' ', text).strip()


def find_quote_in_text(
    quote: str,
    text: str,
    case_sensitive: bool = False,
    normalize_whitespace: bool = False,
    fuzzy: bool = False,
    fuzzy_threshold: float = 0.85
) -> Dict[str, Any]:
    """Find quote within text and return location information.

    Args:
        quote: Quote to search for
        text: Text to search within
        case_sensitive: Whether to match case exactly (default: False)
        normalize_whitespace: Whether to normalize whitespace before matching
        fuzzy: Enable fuzzy matching for approximate matches
        fuzzy_threshold: Minimum similarity ratio for fuzzy matches (0.0-1.0)

    Returns:
        Dict with keys:
        - found: bool (True if quote found)
        - start_idx: int (start position in text, -1 if not found)
        - end_idx: int (end position in text)
        - fuzzy_score: float (similarity ratio if fuzzy matching used)

    Example:
        >>> result = find_quote_in_text("test", "This is a test string")
        >>> result['found']
        True
        >>> result['start_idx'] >= 0
        True
    """
    # Normalize whitespace if requested
    search_quote = _normalize_whitespace(quote) if normalize_whitespace else quote
    search_text = _normalize_whitespace(text) if normalize_whitespace else text

    # Case insensitive search
    if not case_sensitive:
        search_quote = search_quote.lower()
        search_text = search_text.lower()

    # Try exact match first
    start_idx = search_text.find(search_quote)
    if start_idx != -1:
        return {
            "found": True,
            "start_idx": start_idx,
            "end_idx": start_idx + len(search_quote),
            "match_type": "exact"
        }

    # Try fuzzy matching if enabled
    if fuzzy:
        # Use sliding window approach for fuzzy matching
        quote_len = len(search_quote)
        best_score = 0.0
        best_start = -1

        # Try windows of similar length
        for window_size in [quote_len, int(quote_len * 0.9), int(quote_len * 1.1)]:
            for i in range(len(search_text) - window_size + 1):
                window = search_text[i:i + window_size]
                score = SequenceMatcher(None, search_quote, window).ratio()
                if score > best_score:
                    best_score = score
                    best_start = i

        if best_score >= fuzzy_threshold:
            return {
                "found": True,
                "start_idx": best_start,
                "end_idx": best_start + window_size,
                "fuzzy_score": best_score,
                "match_type": "fuzzy"
            }

    # Not found
    return {
        "found": False,
        "start_idx": -1
    }


def compute_alignment_score(quote: str, found_text: str) -> float:
    """Compute alignment quality score between quote and found text.

    Uses SequenceMatcher to compute similarity ratio (0.0-1.0).

    Args:
        quote: Original quote text
        found_text: Text found in source

    Returns:
        Similarity score (1.0 = exact match, 0.0 = no match)

    Example:
        >>> compute_alignment_score("test", "test")
        1.0
        >>> compute_alignment_score("test", "tent") < 1.0
        True
    """
    # Normalize for comparison
    norm_quote = _normalize_whitespace(quote.lower())
    norm_found = _normalize_whitespace(found_text.lower())

    # Use SequenceMatcher for similarity
    score = SequenceMatcher(None, norm_quote, norm_found).ratio()
    return round(score, 3)


def load_parquet_file(parquet_path: str) -> pd.DataFrame:
    """Load parquet file with validation.

    Args:
        parquet_path: Path to parquet file

    Returns:
        DataFrame with columns: doc_id, page, text, chunk_id

    Raises:
        FileNotFoundError: If parquet file doesn't exist
        ValueError: If parquet schema invalid

    Example:
        >>> df = load_parquet_file("data.parquet")
        >>> list(df.columns)
        ['doc_id', 'page', 'text', 'chunk_id']
    """
    if not os.path.exists(parquet_path):
        raise FileNotFoundError(f"Parquet file not found: {parquet_path}")

    df = pd.read_parquet(parquet_path)

    # Validate schema
    required_cols = {"doc_id", "page", "text", "chunk_id"}
    if not required_cols.issubset(df.columns):
        raise ValueError(f"Invalid parquet schema. Required: {required_cols}, Got: {set(df.columns)}")

    return df


def audit_quote_against_parquet(
    quote: str,
    parquet_path: str,
    fuzzy: bool = True,
    fuzzy_threshold: float = 0.85
) -> Dict[str, Any]:
    """Audit single quote against parquet file.

    Args:
        quote: Quote text to validate
        parquet_path: Path to silver parquet file
        fuzzy: Enable fuzzy matching
        fuzzy_threshold: Minimum similarity for fuzzy matches

    Returns:
        Dict with keys:
        - found: bool
        - page: int (page number if found)
        - chunk_id: str (chunk identifier if found)
        - alignment_score: float (quality score)
        - match_type: str ("exact" or "fuzzy")

    Example:
        >>> result = audit_quote_against_parquet("test", "data.parquet")
        >>> result['found']
        True
    """
    df = load_parquet_file(parquet_path)

    # Search through all pages
    for _, row in df.iterrows():
        text = row['text']
        result = find_quote_in_text(
            quote,
            text,
            case_sensitive=False,
            normalize_whitespace=True,
            fuzzy=fuzzy,
            fuzzy_threshold=fuzzy_threshold
        )

        if result['found']:
            # Extract matched text for scoring
            found_text = text[result['start_idx']:result['end_idx']]
            alignment_score = compute_alignment_score(quote, found_text)

            return {
                "found": True,
                "page": int(row['page']),
                "chunk_id": row['chunk_id'],
                "alignment_score": alignment_score,
                "match_type": result.get('match_type', 'exact'),
                "fuzzy_score": result.get('fuzzy_score'),
                "start_idx": result['start_idx'],
                "end_idx": result['end_idx']
            }

    # Not found in any page
    return {
        "found": False
    }


def batch_audit_quotes(quotes: List[str], parquet_path: str) -> List[Dict[str, Any]]:
    """Audit multiple quotes against parquet file.

    Args:
        quotes: List of quote strings
        parquet_path: Path to silver parquet file

    Returns:
        List of audit results (one per quote)

    Example:
        >>> results = batch_audit_quotes(["quote1", "quote2"], "data.parquet")
        >>> len(results) == 2
        True
    """
    results = []
    for quote in quotes:
        result = audit_quote_against_parquet(quote, parquet_path)
        result['quote'] = quote
        results.append(result)
    return results


def generate_audit_report(audit_results: List[Dict[str, Any]], output_path: str) -> None:
    """Generate JSON audit report.

    Args:
        audit_results: List of audit result dicts
        output_path: Path for output JSON file

    Example:
        >>> generate_audit_report(results, "audit_report.json")
    """
    found_count = sum(1 for r in audit_results if r['found'])
    not_found_count = len(audit_results) - found_count

    report = {
        "total_quotes": len(audit_results),
        "found_count": found_count,
        "not_found_count": not_found_count,
        "pass_rate": round(found_count / len(audit_results), 3) if audit_results else 0.0,
        "results": audit_results
    }

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    Path(output_path).write_text(json.dumps(report, indent=2), encoding='utf-8')

    logger.info(f"Audit report written to {output_path}")


def locate_parquet_for_audit(doc_id: str, org_id: str, year: int) -> str:
    """Locate parquet file for audit using backend-aware resolution.

    Args:
        doc_id: Document ID
        org_id: Organization ID
        year: Report year

    Returns:
        Path to parquet file or empty string if not found

    Example:
        >>> path = locate_parquet_for_audit("LSE_HEAD_2025", "LSE_HEAD", 2025)
        >>> path != ""
        True
    """
    return locate_chunks_parquet(doc_id, org_id, year)


def main():
    """Main entry point for alignment audit.

    Command-line interface for validating quotes against silver parquet files.

    Usage:
        python scripts/alignment_audit.py \\
            --org_id LSE_HEAD \\
            --year 2025 \\
            --doc_id LSE_HEAD_2025 \\
            --quote "Sample quote text"

        # Batch mode
        python scripts/alignment_audit.py \\
            --org_id LSE_HEAD \\
            --year 2025 \\
            --doc_id LSE_HEAD_2025 \\
            --quotes_file evidence_quotes.json \\
            --report_out audit_report.json

    Environment Variables:
        PARSER_BACKEND: Backend to use (default or docling)
    """
    parser = argparse.ArgumentParser(
        description="Validate evidence quotes against silver parquet files"
    )
    parser.add_argument("--org_id", required=True, help="Organization ID")
    parser.add_argument("--year", type=int, required=True, help="Report year")
    parser.add_argument("--doc_id", required=True, help="Document ID")
    parser.add_argument("--quote", help="Single quote to validate")
    parser.add_argument("--quotes_file", help="JSON file with list of quotes")
    parser.add_argument("--report_out", help="Output path for audit report JSON")
    parser.add_argument("--fuzzy", action="store_true", default=True, help="Enable fuzzy matching")
    parser.add_argument("--fuzzy_threshold", type=float, default=0.85, help="Fuzzy match threshold")

    args = parser.parse_args()

    # Locate parquet file
    parquet_path = locate_parquet_for_audit(args.doc_id, args.org_id, args.year)

    if not parquet_path or not os.path.exists(parquet_path):
        logger.error(f"Parquet file not found for {args.doc_id}")
        raise SystemExit(f"Parquet file not found for {args.doc_id}")

    logger.info(f"Using parquet: {parquet_path}")

    # Collect quotes
    quotes = []
    if args.quote:
        quotes.append(args.quote)
    if args.quotes_file:
        quotes_data = json.loads(Path(args.quotes_file).read_text())
        if isinstance(quotes_data, list):
            quotes.extend(quotes_data)
        elif isinstance(quotes_data, dict) and 'quotes' in quotes_data:
            quotes.extend(quotes_data['quotes'])

    if not quotes:
        logger.error("No quotes provided (use --quote or --quotes_file)")
        raise SystemExit("No quotes provided")

    logger.info(f"Auditing {len(quotes)} quote(s)")

    # Audit quotes
    results = batch_audit_quotes(quotes, parquet_path)

    # Print summary
    found_count = sum(1 for r in results if r['found'])
    print(f"\n=== Alignment Audit Results ===")
    print(f"Total Quotes: {len(results)}")
    print(f"Found: {found_count}")
    print(f"Not Found: {len(results) - found_count}")
    print(f"Pass Rate: {found_count / len(results) * 100:.1f}%")

    # Print details
    for i, result in enumerate(results, 1):
        if result['found']:
            print(f"\n[{i}] ✓ FOUND - Page {result['page']}")
            print(f"    Quote: {result['quote'][:80]}...")
            print(f"    Alignment: {result['alignment_score']:.3f} ({result['match_type']})")
        else:
            print(f"\n[{i}] ✗ NOT FOUND")
            print(f"    Quote: {result['quote'][:80]}...")

    # Generate report if requested
    if args.report_out:
        generate_audit_report(results, args.report_out)
        print(f"\nDetailed report: {args.report_out}")

    # Exit with non-zero if any quotes not found
    if found_count < len(results):
        raise SystemExit(1)

    print("\n✓ All quotes validated successfully")


if __name__ == "__main__":
    main()
