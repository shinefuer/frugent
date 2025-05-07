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
