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
