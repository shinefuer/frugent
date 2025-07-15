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
