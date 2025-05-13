"""Behavior and invariant tests."""

from __future__ import annotations

import pytest

import frugent.prompt_cache as m


def test_cache_entry_touch_advances_access_and_hits() -> None:
    entry = m.CacheEntry("k", 10, 5, 5)
    assert entry.touch(9) == m.CacheEntry("k", 10, 5, 9, 1)
    assert entry.hits == 0


@pytest.mark.parametrize("values", [("", 1, 0, 0, 0), ("k", -1, 0, 0, 0), ("k", 1, 5, 4, 0)])
def test_cache_entry_rejects_impossible_state(values: tuple[object, ...]) -> None:
    with pytest.raises(m.PromptCacheError, match="cache entry"):
        m.CacheEntry(*values)  # type: ignore[arg-type]


@pytest.mark.parametrize("now", [9, 10, 14])
def test_entry_lives_strictly_before_ttl(now: int) -> None:
    assert not m.is_expired(m.CacheEntry("k", 1, 5, 5), m.CachePolicy(10, 10), now)


@pytest.mark.parametrize("now", [15, 16, 100])
def test_entry_expires_at_or_after_ttl(now: int) -> None:
    assert m.is_expired(m.CacheEntry("k", 1, 5, 5), m.CachePolicy(10, 10), now)


@pytest.mark.parametrize("ttl", [0, 1, 5, 100])
@pytest.mark.parametrize("age", [0, 1, 5, 100])
def test_ttl_boundary_matches_age_comparison(ttl: int, age: int) -> None:
    entry = m.CacheEntry("k", 1, 10, 10)
    assert m.is_expired(entry, m.CachePolicy(10, ttl), 10 + age) is (age >= ttl)


def test_lru_eviction_uses_access_then_creation_then_key() -> None:
    entries = (m.CacheEntry("b", 1, 0, 5), m.CacheEntry("a", 1, 1, 5), m.CacheEntry("old", 1, 0, 4))
    assert m.eviction_order(entries, m.CachePolicy(10, 10, eviction="lru")) == ("old", "b", "a")


def test_lfu_eviction_prefers_fewer_hits() -> None:
    entries = (m.CacheEntry("hot", 1, 0, 9, 3), m.CacheEntry("cold", 1, 0, 8, 0))
    assert m.eviction_order(entries, m.CachePolicy(10, 10, eviction="lfu"))[0] == "cold"
