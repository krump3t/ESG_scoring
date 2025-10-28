"""Deterministic provenance helpers used across the scoring pipeline."""

from __future__ import annotations

import hashlib
import re


_WHITESPACE = re.compile(r"\s+")


def sha256_text(text: str) -> str:
    """Return the hexadecimal SHA256 digest for the provided text."""
    digest = hashlib.sha256()
    digest.update(text.encode("utf-8"))
    return digest.hexdigest()


def trim_to_words(text: str, max_words: int) -> str:
    """Return ``text`` trimmed to at most ``max_words`` words."""
    if max_words <= 0:
        return ""
    normalized = _WHITESPACE.sub(" ", text.strip())
    words = normalized.split(" ")
    limited = words[:max_words]
    return " ".join(word for word in limited if word)
