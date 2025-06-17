"""Behavior and invariant tests."""

from __future__ import annotations

import pytest

import frugent.compression as m


def test_block_keeps_explicit_synthetic_relevance() -> None:
    block = m.Block("b", "needle", 3, 7, 500_000, 10)
    assert block.planted_relevance == 10


@pytest.mark.parametrize("values", [("", "x", 1, 0), ("x", "x", 0, 0), ("x", "x", 1, -1)])
def test_block_rejects_invalid_identity_weight_or_recency(values: tuple[object, ...]) -> None:
    with pytest.raises(m.CompressionError, match="block"):
        m.Block(*values)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("budget", "keys"), [(0, ()), (2, ("c",)), (4, ("b", "c")), (9, ("a", "b", "c"))]
)
def test_sliding_window_keeps_newest_contiguous_suffix(budget: int, keys: tuple[str, ...]) -> None:
    blocks = (m.Block("a", "a", 5, 0), m.Block("b", "b", 2, 1), m.Block("c", "c", 2, 2))
    assert tuple(block.key for block in m.sliding_window(blocks, budget)) == keys


@pytest.mark.parametrize("budget", range(0, 20))
def test_sliding_window_never_exceeds_budget(budget: int) -> None:
    blocks = tuple(m.Block(str(index), "x", index % 4 + 1, index) for index in range(10))
    selected = m.sliding_window(blocks, budget)
    assert sum(block.tokens for block in selected) <= budget
    assert blocks[-len(selected) :] == selected if selected else True
