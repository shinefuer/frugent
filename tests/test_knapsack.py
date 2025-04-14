"""Behavior and invariant tests."""

from __future__ import annotations

import pytest

import frugent.knapsack as m


def test_item_accepts_zero_relevance_but_positive_weight() -> None:
    assert m.Item("background", 3, 0).tokens == 3


@pytest.mark.parametrize("values", [("", 1, 1), ("x", 0, 1), ("x", -1, 1), ("x", 1, -1)])
def test_item_rejects_invalid_identity_weight_or_value(values: tuple[object, ...]) -> None:
    with pytest.raises(m.KnapsackError, match="item"):
        m.Item(*values)  # type: ignore[arg-type]


def test_exact_select_finds_planted_non_greedy_optimum() -> None:
    items = (m.Item("a", 6, 9), m.Item("b", 5, 8), m.Item("c", 5, 8))
    assert tuple(item.key for item in m.exact_select(items, 10)) == ("b", "c")


def test_exact_select_uses_lexical_tie_break() -> None:
    items = (m.Item("z", 2, 3), m.Item("a", 2, 3))
    assert tuple(item.key for item in m.exact_select(items, 2)) == ("a",)
