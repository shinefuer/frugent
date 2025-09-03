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
