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


def normalized_payload(
    prompt: str, tool_name: str, arguments: dict[str, object], *, fold_case: bool = True
) -> dict[str, object]:
    """Build the exact normalized payload used for content addressing."""
    from frugent.codec import canonical_json, decode_json

    if not tool_name or not isinstance(arguments, dict):
        raise SemanticCacheError("semantic payload: tool name and argument object required")
    canonical_arguments = decode_json(canonical_json(arguments))
    return {
        "prompt": normalize_text(prompt, fold_case=fold_case),
        "tool_name": tool_name.casefold() if fold_case else tool_name,
        "arguments": canonical_arguments,
        "fold_case": fold_case,
    }
