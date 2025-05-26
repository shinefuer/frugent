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


def test_fit_entries_enforces_capacity() -> None:
    policy = m.CachePolicy(10, 100, eviction="lru")
    entries = (m.CacheEntry("old", 6, 0, 0), m.CacheEntry("new", 6, 1, 5))
    assert m.fit_entries(entries, policy) == (entries[1],)


@pytest.mark.parametrize("tokens", [0, 1, 2, 10, 11])
def test_admission_uses_closed_policy_interval(tokens: int) -> None:
    assert m.admitted(m.CacheEntry("k", tokens, 0, 0), m.CachePolicy(10, 10, 2)) is (
        2 <= tokens <= 10
    )


def test_purge_expired_keeps_only_live_entries() -> None:
    entries = (m.CacheEntry("old", 1, 0, 0), m.CacheEntry("live", 1, 6, 6))
    assert m.purge_expired(entries, m.CachePolicy(10, 10), 10) == (entries[1],)


def test_zero_ttl_expires_immediately() -> None:
    entry = m.CacheEntry("k", 1, 3, 3)
    assert m.purge_expired((entry,), m.CachePolicy(10, 0), 3) == ()


@pytest.mark.parametrize("capacity", range(0, 12))
def test_fitted_entries_never_exceed_token_capacity(capacity: int) -> None:
    entries = tuple(m.CacheEntry(str(index), index + 1, index, index) for index in range(6))
    kept = m.fit_entries(entries, m.CachePolicy(capacity, 100, 0))
    assert sum(entry.token_count for entry in kept) <= capacity
    assert len({entry.key for entry in kept}) == len(kept)


def test_cache_metrics_match_trace_counts() -> None:
    result = m.metrics(((True, 10), (False, 0), (True, 4)))
    assert result == m.CacheMetrics(3, 2, 14)
    assert result.hit_rate == 0.666667
    assert result.average_cached_tokens == 7.0


def test_cache_metrics_reject_tokens_on_miss() -> None:
    with pytest.raises(m.PromptCacheError, match="misses"):
        m.metrics(((False, 1),))


def test_trace_replay_observes_hits_eviction_and_ttl() -> None:
    policy = m.CachePolicy(8, 10)
    trace = (("a", 4, 0), ("a", 4, 1), ("b", 6, 2), ("a", 4, 3), ("b", 6, 12))
    assert m.replay_trace(trace, policy) == (
        (False, 0),
        (True, 4),
        (False, 0),
        (False, 0),
        (False, 0),
    )
