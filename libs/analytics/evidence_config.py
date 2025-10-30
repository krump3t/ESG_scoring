"""
Evidence Configuration & Validation - Phase F Enhancement

Centralizes evidence quality thresholds with document-length-aware span requirements.
Implements Option A: Adaptive span (≥5 for docs ≥10 pages, ≥3 for shorter docs).

Key Features:
- Document-length-aware minimum span calculation
- Evidence quality validation (distinct pages, span, per-page cap)
- Per-page evidence capping to prevent concentration
"""

from typing import List, Dict, Any, Set
from collections import defaultdict

# Phase F Evidence Constants
EVIDENCE_PAGE_MIN_DISTINCT = 3  # Minimum distinct pages per theme (up from 2)
EVIDENCE_PER_PAGE_CAP = 5  # Maximum evidence items per page
DOC_LENGTH_THRESHOLD = 10  # Page count threshold for span calculation
MIN_SPAN_SHORT_DOCS = 3  # Minimum span for documents < 10 pages
MIN_SPAN_LONG_DOCS = 5  # Minimum span for documents ≥ 10 pages


def get_min_span_for_doc(total_pages: int) -> int:
    """
    Calculate minimum page span based on document length.

    Option A: Adaptive span requirement
    - Documents ≥10 pages: require span ≥5 (evidence spread across document)
    - Documents <10 pages: require span ≥3 (relaxed for shorter docs)

    Args:
        total_pages: Total page count of document

    Returns:
        Minimum required page span for evidence validation

    Example:
        >>> get_min_span_for_doc(25)  # Long document
        5
        >>> get_min_span_for_doc(8)   # Short document
        3
    """
    if total_pages >= DOC_LENGTH_THRESHOLD:
        return MIN_SPAN_LONG_DOCS
    else:
        return MIN_SPAN_SHORT_DOCS


def evidence_ok(pages: List[Any], total_pages: int) -> Dict[str, Any]:
    """
    Validate evidence meets Phase F quality gates.

    Gates:
    1. Minimum distinct pages: ≥3 unique pages
    2. Minimum page span: ≥ get_min_span_for_doc(total_pages)
    3. Page span calculation: max(pages) - min(pages)

    Args:
        pages: List of page numbers (can be int or str)
        total_pages: Total page count of document

    Returns:
        Dict with validation results:
        - passed: bool - True if all gates pass
        - distinct_pages: int - Count of unique pages
        - page_span: int - Difference between max and min page
        - min_span_required: int - Threshold based on document length
        - unique_pages: Set[int] - Set of unique page numbers
        - gates: Dict[str, bool] - Individual gate results

    Example:
        >>> evidence_ok([2, 3, 7, 8, 12], total_pages=25)
        {
            "passed": True,
            "distinct_pages": 5,
            "page_span": 10,
            "min_span_required": 5,
            "unique_pages": {2, 3, 7, 8, 12},
            "gates": {"min_distinct": True, "min_span": True}
        }
    """
    # Normalize pages to integers, filter invalid
    page_nums: List[int] = []
    for p in pages:
        try:
            if isinstance(p, str):
                page_num = int(p)
            elif isinstance(p, int):
                page_num = p
            else:
                continue

            # Exclude default/invalid page numbers
            if page_num > 0:
                page_nums.append(page_num)
        except (ValueError, TypeError):
            continue

    unique_pages: Set[int] = set(page_nums)
    distinct_count = len(unique_pages)

    # Calculate span
    if distinct_count >= 2:
        page_span = max(unique_pages) - min(unique_pages)
    else:
        page_span = 0

    # Get minimum span requirement for this document
    min_span_required = get_min_span_for_doc(total_pages)

    # Gate checks
    gate_min_distinct = distinct_count >= EVIDENCE_PAGE_MIN_DISTINCT
    gate_min_span = page_span >= min_span_required

    return {
        "passed": gate_min_distinct and gate_min_span,
        "distinct_pages": distinct_count,
        "page_span": page_span,
        "min_span_required": min_span_required,
        "unique_pages": unique_pages,
        "gates": {
            "min_distinct": gate_min_distinct,
            "min_span": gate_min_span
        }
    }


def cap_per_page(items: List[Dict[str, Any]], max_per_page: int = EVIDENCE_PER_PAGE_CAP) -> List[Dict[str, Any]]:
    """
    Limit evidence items per page to prevent concentration.

    Strategy:
    - Group items by page number
    - Take first N items from each page (preserves retrieval ranking)
    - Return flattened list

    Args:
        items: List of evidence items with 'page' or 'page_no' field
        max_per_page: Maximum items per page (default: 5)

    Returns:
        Capped list of evidence items

    Example:
        >>> items = [
        ...     {"page": 1, "quote": "A"},
        ...     {"page": 1, "quote": "B"},
        ...     {"page": 1, "quote": "C"},
        ...     # ... 10 more items from page 1
        ...     {"page": 2, "quote": "D"}
        ... ]
        >>> capped = cap_per_page(items, max_per_page=5)
        >>> len([x for x in capped if x["page"] == 1])
        5  # Limited to 5 items from page 1
    """
    by_page: Dict[Any, List[Dict[str, Any]]] = defaultdict(list)

    for item in items:
        page = item.get("page") or item.get("page_no")
        by_page[page].append(item)

    # Cap each page and flatten
    capped_items: List[Dict[str, Any]] = []
    for page, page_items in by_page.items():
        capped_items.extend(page_items[:max_per_page])

    return capped_items


def get_evidence_summary(items: List[Dict[str, Any]], total_pages: int) -> Dict[str, Any]:
    """
    Generate comprehensive evidence quality summary.

    Args:
        items: List of evidence items with page information
        total_pages: Total page count of document

    Returns:
        Summary dict with:
        - total_items: int
        - unique_pages: int
        - page_span: int
        - validation: Dict from evidence_ok()
        - per_page_distribution: Dict[page, count]
        - max_items_on_single_page: int
        - concentration_warning: bool (True if any page has >CAP items)
    """
    pages = [item.get("page") or item.get("page_no") for item in items]
    validation = evidence_ok(pages, total_pages)

    # Per-page distribution
    by_page: Dict[Any, int] = defaultdict(int)
    for p in pages:
        if p is not None and p != 0:
            by_page[p] += 1

    max_on_single = max(by_page.values()) if by_page else 0

    return {
        "total_items": len(items),
        "unique_pages": validation["distinct_pages"],
        "page_span": validation["page_span"],
        "validation": validation,
        "per_page_distribution": dict(by_page),
        "max_items_on_single_page": max_on_single,
        "concentration_warning": max_on_single > EVIDENCE_PER_PAGE_CAP
    }
