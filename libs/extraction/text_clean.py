"""
Text Cleaning & Binary Detection Utilities

SCA v13.8-MEA Compliance:
- Detect binary/corrupted PDF data in text fields
- Clean text while preserving meaningful content
- Flag suspect text for downstream handling
"""

import re
import unicodedata
from typing import Tuple


def is_binaryish(text: str, threshold: float = 0.15) -> bool:
    """
    Detect if text contains excessive binary/control characters.

    Args:
        text: Input text to analyze
        threshold: Fraction of binary chars to trigger detection (default: 15%)

    Returns:
        True if text appears to be binary/corrupted data

    Examples:
        >>> is_binaryish("Hello world")
        False
        >>> is_binaryish("\\x00\\x01\\x02ABC")
        True
    """
    if not text:
        return False

    # Count control characters (exclude whitespace like \n, \t, \r)
    control_chars = sum(
        1 for c in text
        if unicodedata.category(c).startswith('C') and c not in ('\n', '\t', '\r', ' ')
    )

    # Count null bytes (strong binary indicator)
    null_bytes = text.count('\x00')

    # Count non-printable characters
    non_printable = sum(
        1 for c in text
        if ord(c) < 32 and c not in ('\n', '\t', '\r')
    )

    total_chars = len(text)
    if total_chars == 0:
        return False

    # Binary if >threshold control chars OR any null bytes
    control_ratio = (control_chars + non_printable) / total_chars
    return control_ratio > threshold or null_bytes > 0


def clean_text(text: str, preserve_newlines: bool = True) -> str:
    """
    Clean text by removing control characters and normalizing whitespace.

    Args:
        text: Input text to clean
        preserve_newlines: Keep newline characters (default: True)

    Returns:
        Cleaned text with normalized whitespace

    Examples:
        >>> clean_text("Hello\\x00\\x01world")
        'Helloworld'
        >>> clean_text("Too   many    spaces")
        'Too many spaces'
    """
    if not text:
        return ""

    # Remove null bytes
    text = text.replace('\x00', '')

    # Remove control characters (keep newlines if preserve_newlines=True)
    if preserve_newlines:
        # Keep \n, \r, \t
        text = ''.join(
            c for c in text
            if not (unicodedata.category(c).startswith('C') and c not in ('\n', '\r', '\t'))
        )
    else:
        # Remove all control characters
        text = ''.join(
            c for c in text
            if not unicodedata.category(c).startswith('C')
        )

    # Normalize whitespace (collapse multiple spaces)
    text = re.sub(r' +', ' ', text)

    # Normalize newlines (remove excessive blank lines)
    text = re.sub(r'\n{3,}', '\n\n', text)

    # Strip leading/trailing whitespace
    text = text.strip()

    return text


def validate_and_clean(text: str) -> Tuple[str, str]:
    """
    Validate text quality and clean if needed.

    Args:
        text: Input text to validate and clean

    Returns:
        Tuple of (cleaned_text, status)
        - status: "ok", "cleaned", "suspect", or "empty"

    Examples:
        >>> validate_and_clean("Hello world")
        ('Hello world', 'ok')
        >>> validate_and_clean("\\x00Binary\\x01data")
        ('Binarydata', 'suspect')
    """
    if not text:
        return ("", "empty")

    # Check if binary
    if is_binaryish(text):
        cleaned = clean_text(text)
        # If cleaning helped significantly, mark as cleaned
        if cleaned and not is_binaryish(cleaned):
            return (cleaned, "cleaned")
        else:
            # Still looks binary after cleaning
            return (cleaned if cleaned else text, "suspect")

    # Clean normal text (remove extra whitespace, etc.)
    cleaned = clean_text(text)

    # If cleaning didn't change much, it's ok
    if len(cleaned) > 0.8 * len(text):
        return (cleaned, "ok")
    else:
        # Significant content lost during cleaning
        return (cleaned, "cleaned")


def get_text_quality_score(text: str) -> float:
    """
    Compute text quality score (0.0 = binary, 1.0 = clean text).

    Args:
        text: Input text to score

    Returns:
        Quality score between 0.0 and 1.0

    Examples:
        >>> get_text_quality_score("Hello world")
        1.0
        >>> get_text_quality_score("\\x00\\x01\\x02") < 0.2
        True
    """
    if not text:
        return 0.0

    # Count printable vs total
    printable = sum(1 for c in text if c.isprintable() or c in ('\n', '\t', '\r'))
    total = len(text)

    # Base quality on printable ratio
    quality = printable / total if total > 0 else 0.0

    # Penalize if detected as binary
    if is_binaryish(text):
        quality *= 0.5

    return min(1.0, quality)


# Aliases for Task 026 compatibility
def is_binary_like(text: str) -> bool:
    """Alias for is_binaryish (Task 026 naming convention).

    Returns True for None or empty text (treated as binary/invalid).
    """
    if text is None or text == "":
        return True
    return is_binaryish(text)


def quality_score(text: str) -> float:
    """Alias for get_text_quality_score (Task 026 naming convention)."""
    return get_text_quality_score(text)


def extract_clean_quote(text: str, max_length: int = 500) -> Tuple[str, float]:
    """Extract and clean a quote from text with quality assessment.

    Args:
        text: Source text
        max_length: Maximum quote length

    Returns:
        (cleaned_quote, quality_score)

    Example:
        >>> extract_clean_quote("  Too   many    spaces  ", 100)
        ('Too many spaces', 1.0)
    """
    # Score BEFORE cleaning (to detect binary in original)
    original_score = quality_score(text)

    cleaned = clean_text(text)

    # Use lower of original and cleaned score (penalize binary input)
    final_score = min(original_score, quality_score(cleaned))

    # Truncate if needed
    if len(cleaned) > max_length:
        cleaned = cleaned[:max_length] + "..."

    return cleaned, final_score
