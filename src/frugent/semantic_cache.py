"""Content-addressed semantic result keys with poisoning-safe retrieval."""

from __future__ import annotations

import re
import unicodedata


class SemanticCacheError(ValueError):
    """Raised for invalid semantic cache payloads or state."""


def normalize_text(text: str, *, fold_case: bool = True) -> str:
    """Normalize Unicode and whitespace with an explicit case policy."""
    if not isinstance(text, str):
        raise SemanticCacheError("semantic text: expected string")
    normalized = unicodedata.normalize("NFKC", text)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized.casefold() if fold_case else normalized
