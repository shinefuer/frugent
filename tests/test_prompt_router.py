"""Behavior and invariant tests."""

from __future__ import annotations

import pytest

import frugent.prompt_router as m


def test_instance_keeps_explicit_queue_load() -> None:
    instance = m.Instance("worker-a", m.PrefixTrie(), 17)
    assert instance.name == "worker-a"
    assert instance.queued_tokens == 17


@pytest.mark.parametrize("values", [("", 0), ("a", -1)])
def test_instance_rejects_invalid_identity_or_queue(values: tuple[object, int]) -> None:
    with pytest.raises(m.PromptRouterError, match="router instance"):
        m.Instance(values[0], m.PrefixTrie(), values[1])  # type: ignore[arg-type]


def test_choose_instance_prefers_longest_cached_prefix() -> None:
    left, right = m.Instance("left", m.PrefixTrie()), m.Instance("right", m.PrefixTrie())
    left.cache.insert(("a",))
    right.cache.insert(("a", "b"))
    assert m.choose_instance((left, right), ("a", "b", "c")).name == "right"


def test_choose_instance_uses_stable_name_tie_break() -> None:
    assert (
        m.choose_instance(
            (m.Instance("z", m.PrefixTrie()), m.Instance("a", m.PrefixTrie())), ("x",)
        ).name
        == "a"
    )


def test_load_penalty_can_move_only_low_affinity_work() -> None:
    high = m.Instance("high", m.PrefixTrie(), queued_tokens=100)
    idle = m.Instance("idle", m.PrefixTrie(), queued_tokens=0)
    high.cache.insert(("a", "b", "c"))
    idle.cache.insert(("a",))
    assert m.choose_instance((high, idle), ("a", "b", "c"), load_penalty_ppm=1_000).name == "high"
    assert m.choose_instance((high, idle), ("a",), load_penalty_ppm=20_000).name == "idle"
