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
