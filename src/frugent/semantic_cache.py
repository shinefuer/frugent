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


def exact_key(prompt: str, tool_name: str, arguments: dict[str, object]) -> str:
    """Hash the complete normalized payload; retrieval uses this key only."""
    from frugent.codec import payload_digest

    return payload_digest(normalized_payload(prompt, tool_name, arguments))


def shingles(text: str, width: int = 3) -> frozenset[str]:
    """Return character shingles for fuzzy candidate discovery only."""
    if width <= 0:
        raise SemanticCacheError("shingles: width must be positive")
    normalized = normalize_text(text)
    if len(normalized) < width:
        return frozenset({normalized}) if normalized else frozenset()
    return frozenset(
        normalized[index : index + width] for index in range(len(normalized) - width + 1)
    )


def jaccard(left: frozenset[str], right: frozenset[str]) -> float:
    if not left and not right:
        return 1.0
    return round(len(left & right) / len(left | right), 6)


def minhash_signature(
    values: frozenset[str], *, permutations: int = 32, seed: int = 0
) -> tuple[int, ...]:
    """Create a stable SHA-256-based MinHash signature."""
    import hashlib

    if permutations <= 0 or seed < 0:
        raise SemanticCacheError("minhash: permutations positive and seed non-negative")
    if not values:
        return (0,) * permutations
    return tuple(
        min(
            int.from_bytes(hashlib.sha256(f"{seed}:{index}:{value}".encode()).digest()[:8], "big")
            for value in values
        )
        for index in range(permutations)
    )


def minhash_similarity(left: tuple[int, ...], right: tuple[int, ...]) -> float:
    if not left or len(left) != len(right):
        raise SemanticCacheError("minhash similarity: signatures must have equal nonzero length")
    return round(sum(a == b for a, b in zip(left, right, strict=True)) / len(left), 6)
