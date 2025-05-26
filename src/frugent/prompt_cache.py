"""Prompt-cache entry lifecycle, eviction, and synthetic savings accounting."""

from __future__ import annotations

from dataclasses import dataclass


class PromptCacheError(ValueError):
    """Raised when prompt-cache state or policy is invalid."""


@dataclass(frozen=True, slots=True)
class CacheEntry:
    key: str
    token_count: int
    created_at_ms: int
    last_access_ms: int
    hits: int = 0

    def __post_init__(self) -> None:
        values = (self.token_count, self.created_at_ms, self.last_access_ms, self.hits)
        if not self.key or any(
            isinstance(value, bool) or not isinstance(value, int) or value < 0 for value in values
        ):
            raise PromptCacheError("cache entry: invalid key or non-negative integer field")
        if self.last_access_ms < self.created_at_ms:
            raise PromptCacheError("cache entry: last access precedes creation")

    def touch(self, now_ms: int) -> CacheEntry:
        if now_ms < self.last_access_ms:
            raise PromptCacheError("cache entry: access time moved backwards")
        return CacheEntry(self.key, self.token_count, self.created_at_ms, now_ms, self.hits + 1)


@dataclass(frozen=True, slots=True)
class CachePolicy:
    capacity_tokens: int
    ttl_ms: int
    minimum_admission_tokens: int = 1
    eviction: str = "lru"

    def __post_init__(self) -> None:
        if self.capacity_tokens < 0 or self.ttl_ms < 0 or self.minimum_admission_tokens < 0:
            raise PromptCacheError("cache policy: limits must be non-negative")
        if self.eviction not in {"lru", "lfu"}:
            raise PromptCacheError("cache policy: eviction must be lru or lfu")


def is_expired(entry: CacheEntry, policy: CachePolicy, now_ms: int) -> bool:
    if now_ms < entry.created_at_ms:
        raise PromptCacheError("cache clock: time moved before creation")
    return now_ms - entry.created_at_ms >= policy.ttl_ms


def eviction_order(entries: tuple[CacheEntry, ...], policy: CachePolicy) -> tuple[str, ...]:
    """Return keys in first-to-evict order with stable ties."""
    if policy.eviction == "lru":
        ordered = sorted(
            entries, key=lambda entry: (entry.last_access_ms, entry.created_at_ms, entry.key)
        )
    else:
        ordered = sorted(entries, key=lambda entry: (entry.hits, entry.last_access_ms, entry.key))
    return tuple(entry.key for entry in ordered)


def admitted(entry: CacheEntry, policy: CachePolicy) -> bool:
    """Reject entries too small to matter or too large to ever fit."""
    return policy.minimum_admission_tokens <= entry.token_count <= policy.capacity_tokens


def fit_entries(entries: tuple[CacheEntry, ...], policy: CachePolicy) -> tuple[CacheEntry, ...]:
    """Evict deterministically until total cached tokens fit."""
    kept = {entry.key: entry for entry in entries if admitted(entry, policy)}
    order = eviction_order(tuple(kept.values()), policy)
    total = sum(entry.token_count for entry in kept.values())
    for key in order:
        if total <= policy.capacity_tokens:
            break
        total -= kept.pop(key).token_count
    return tuple(kept[key] for key in sorted(kept))


def purge_expired(
    entries: tuple[CacheEntry, ...], policy: CachePolicy, now_ms: int
) -> tuple[CacheEntry, ...]:
    """Remove every expired entry while preserving stable key order."""
    return tuple(
        sorted(
            (entry for entry in entries if not is_expired(entry, policy, now_ms)),
            key=lambda entry: entry.key,
        )
    )


@dataclass(frozen=True, slots=True)
class CacheMetrics:
    requests: int
    hits: int
    cached_tokens: int

    @property
    def hit_rate(self) -> float:
        return 0.0 if self.requests == 0 else round(self.hits / self.requests, 6)

    @property
    def average_cached_tokens(self) -> float:
        return 0.0 if self.hits == 0 else round(self.cached_tokens / self.hits, 6)


def metrics(outcomes: tuple[tuple[bool, int], ...]) -> CacheMetrics:
    if any(tokens < 0 or (not hit and tokens != 0) for hit, tokens in outcomes):
        raise PromptCacheError("cache metrics: misses cannot report cached tokens")
    return CacheMetrics(
        len(outcomes), sum(hit for hit, _ in outcomes), sum(tokens for _, tokens in outcomes)
    )


def replay_trace(
    requests: tuple[tuple[str, int, int], ...], policy: CachePolicy
) -> tuple[tuple[bool, int], ...]:
    """Replay key/token/time requests through an exact deterministic cache."""
    entries: dict[str, CacheEntry] = {}
    outcomes: list[tuple[bool, int]] = []
    previous_time = 0
    for key, tokens, now_ms in requests:
        if now_ms < previous_time:
            raise PromptCacheError("cache trace: times must be nondecreasing")
        previous_time = now_ms
        entries = {
            entry.key: entry for entry in purge_expired(tuple(entries.values()), policy, now_ms)
        }
        existing = entries.get(key)
        if existing is not None:
            entries[key] = existing.touch(now_ms)
            outcomes.append((True, existing.token_count))
        else:
            candidate = CacheEntry(key, tokens, now_ms, now_ms)
            entries[key] = candidate
            entries = {entry.key: entry for entry in fit_entries(tuple(entries.values()), policy)}
            outcomes.append((False, 0))
    return tuple(outcomes)


def entries_to_record(entries: tuple[CacheEntry, ...]) -> dict[str, object]:
    """Persist logical entry state rather than internal mappings."""
    return {
        "schema_version": 1,
        "entries": [
            {
                "key": entry.key,
                "token_count": entry.token_count,
                "created_at_ms": entry.created_at_ms,
                "last_access_ms": entry.last_access_ms,
                "hits": entry.hits,
            }
            for entry in sorted(entries, key=lambda item: item.key)
        ],
    }
