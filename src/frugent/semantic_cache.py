"""Content-addressed semantic result keys with poisoning-safe retrieval."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass


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


@dataclass(frozen=True, slots=True)
class SemanticEntry:
    key: str
    response: bytes
    created_at_ms: int


def exact_lookup(
    entries: tuple[SemanticEntry, ...], key: str, now_ms: int, ttl_ms: int
) -> bytes | None:
    """Return only an exact content-addressed hit that has not expired."""
    if now_ms < 0 or ttl_ms < 0:
        raise SemanticCacheError("semantic lookup: times must be non-negative")
    for entry in entries:
        if entry.key == key and now_ms - entry.created_at_ms < ttl_ms:
            return entry.response
    return None


def fuzzy_candidates(
    query: str, prompts: dict[str, str], threshold: float
) -> tuple[tuple[str, float], ...]:
    """Rank suggestions; callers must still verify exact equivalence before retrieval."""
    if not 0 <= threshold <= 1:
        raise SemanticCacheError("fuzzy threshold: expected [0, 1]")
    query_shingles = shingles(query)
    candidates = [
        (key, jaccard(query_shingles, shingles(prompt))) for key, prompt in prompts.items()
    ]
    return tuple(
        sorted(
            (item for item in candidates if item[1] >= threshold),
            key=lambda item: (-item[1], item[0]),
        )
    )


@dataclass(frozen=True, slots=True)
class SemanticMetrics:
    hits: int
    misses: int
    evictions: int

    @property
    def hit_rate(self) -> float:
        total = self.hits + self.misses
        return 0.0 if total == 0 else round(self.hits / total, 6)


def semantic_metrics(outcomes: tuple[str, ...]) -> SemanticMetrics:
    allowed = {"hit", "miss", "eviction"}
    if any(outcome not in allowed for outcome in outcomes):
        raise SemanticCacheError("semantic metrics: unknown outcome")
    return SemanticMetrics(
        outcomes.count("hit"), outcomes.count("miss"), outcomes.count("eviction")
    )


@dataclass(frozen=True, slots=True)
class SemanticPolicy:
    capacity: int
    ttl_ms: int

    def __post_init__(self) -> None:
        if self.capacity < 0 or self.ttl_ms < 0:
            raise SemanticCacheError("semantic policy: limits must be non-negative")


@dataclass(frozen=True, slots=True)
class SemanticState:
    entries: tuple[SemanticEntry, ...] = ()
    outcomes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if len({entry.key for entry in self.entries}) != len(self.entries):
            raise SemanticCacheError("semantic state: duplicate exact key")
        if tuple(sorted(self.entries, key=lambda entry: entry.key)) != self.entries:
            raise SemanticCacheError("semantic state: entries must use key order")
        if any(outcome not in {"hit", "miss", "eviction"} for outcome in self.outcomes):
            raise SemanticCacheError("semantic state: unknown outcome")


def state_lookup(
    state: SemanticState, key: str, now_ms: int, policy: SemanticPolicy
) -> tuple[bytes | None, SemanticState]:
    """Purge expired entries and return only an exact unexpired hit."""
    if now_ms < 0:
        raise SemanticCacheError("semantic state lookup: time must be non-negative")
    live = tuple(entry for entry in state.entries if now_ms - entry.created_at_ms < policy.ttl_ms)
    response = exact_lookup(live, key, now_ms, policy.ttl_ms)
    outcome = "hit" if response is not None else "miss"
    return response, SemanticState(live, (*state.outcomes, outcome))


def state_put(state: SemanticState, entry: SemanticEntry, policy: SemanticPolicy) -> SemanticState:
    """Replace the same exact key, then evict oldest/key order to capacity."""
    retained = [item for item in state.entries if item.key != entry.key]
    retained.append(entry)
    retained.sort(key=lambda item: item.key)
    outcomes = state.outcomes
    while len(retained) > policy.capacity:
        victim = min(retained, key=lambda item: (item.created_at_ms, item.key))
        retained.remove(victim)
        outcomes = (*outcomes, "eviction")
    return SemanticState(tuple(retained), outcomes)


def state_metrics(state: SemanticState) -> SemanticMetrics:
    return semantic_metrics(state.outcomes)


def state_record(state: SemanticState) -> dict[str, object]:
    return {
        "schema_version": 1,
        "entries": [
            {
                "key": entry.key,
                "response_hex": entry.response.hex(),
                "created_at_ms": entry.created_at_ms,
            }
            for entry in state.entries
        ],
        "outcomes": list(state.outcomes),
    }


def state_from_record(record: dict[str, object]) -> SemanticState:
    if set(record) != {"schema_version", "entries", "outcomes"} or record["schema_version"] != 1:
        raise SemanticCacheError("semantic state record: unexpected schema")
    entries, outcomes = record["entries"], record["outcomes"]
    if (
        not isinstance(entries, list)
        or not isinstance(outcomes, list)
        or not all(isinstance(value, str) for value in outcomes)
    ):
        raise SemanticCacheError("semantic state record: invalid containers")
    try:
        parsed = tuple(
            SemanticEntry(
                str(item["key"]), bytes.fromhex(str(item["response_hex"])), item["created_at_ms"]
            )
            for item in entries
            if isinstance(item, dict)
        )
    except (KeyError, TypeError, ValueError) as error:
        raise SemanticCacheError(f"semantic state record: invalid entry: {error}") from error
    if len(parsed) != len(entries) or any(
        not isinstance(entry.created_at_ms, int) or isinstance(entry.created_at_ms, bool)
        for entry in parsed
    ):
        raise SemanticCacheError("semantic state record: invalid entry type")
    return SemanticState(parsed, tuple(outcomes))
