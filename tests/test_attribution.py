"""Behavior and invariant tests."""

from __future__ import annotations

import pytest

import frugent.attribution as m


def test_cost_net_reconciles_savings_and_adjustment() -> None:
    cost = m.Cost(100, 50, 20, 10, -5)
    assert cost.gross_micros == 150
    assert cost.net_micros == 115


def test_cost_rejects_negative_savings() -> None:
    with pytest.raises(m.AttributionError, match="integer micro-units"):
        m.Cost(cache_saved_micros=-1)


def test_add_costs_preserves_every_component() -> None:
    costs = (m.Cost(1, 2, 1, 0, 3), m.Cost(4, 5, 0, 2, -1))
    combined = m.add_costs(costs)
    assert combined == m.Cost(5, 7, 1, 2, 2)
    assert combined.net_micros == sum(cost.net_micros for cost in costs)


@pytest.mark.parametrize("size", range(0, 12))
def test_cost_rollup_net_equals_child_net_sum(size: int) -> None:
    costs = tuple(
        m.Cost(index, index * 2, index // 2, index // 3, -index % 2) for index in range(size)
    )
    combined = m.add_costs(costs)
    assert combined.net_micros == sum(cost.net_micros for cost in costs)


def test_cost_conservation_allows_explicit_parent_adjustment() -> None:
    children = (m.Cost(4), m.Cost(5))
    parent = m.Cost(9, adjustment_micros=-1)
    assert m.conserved(parent, children)


def test_cost_conservation_rejects_hidden_difference() -> None:
    with pytest.raises(m.AttributionError, match="conservation"):
        m.require_conserved(m.Cost(10), (m.Cost(4), m.Cost(5)))
