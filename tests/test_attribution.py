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


def test_group_costs_sorts_labels_and_sums_records() -> None:
    grouped = m.group_costs(
        (("tool:read", m.Cost(2)), ("model:small", m.Cost(3)), ("tool:read", m.Cost(5)))
    )
    assert tuple(grouped) == ("model:small", "tool:read")
    assert grouped["tool:read"].net_micros == 7


def test_rate_breakdown_conversion_reconciles_actual_cost() -> None:
    from frugent.ratecard import CostBreakdown

    breakdown = CostBreakdown(60, 10, 20, 5)
    cost = m.from_rate_breakdown(breakdown, baseline_micros=120)
    assert cost == m.Cost(100, 20, 30, 5)
    assert cost.net_micros == breakdown.total_micros


@pytest.mark.parametrize("cached", [0, 10, 50, 100])
def test_rate_attribution_matches_priced_usage(cached: int) -> None:
    from frugent.ratecard import ModelRate, attribute_savings, price_usage
    from frugent.types import Usage

    rate, usage = ModelRate("m", 1000, 2000, 250_000, 800_000), Usage(100, 10, cached)
    breakdown = price_usage(rate, usage, batched=True)
    savings = attribute_savings(rate, usage, batched=True)
    assert (
        m.from_rate_breakdown(breakdown, savings.baseline_micros).net_micros
        == savings.actual_micros
    )


def test_net_shares_use_grouped_actual_cost() -> None:
    assert m.net_shares({"a": m.Cost(1), "b": m.Cost(3)}) == {"a": 0.25, "b": 0.75}
    assert m.net_shares({"a": m.Cost()}) == {"a": 0.0}


def test_cost_delta_includes_added_and_removed_labels() -> None:
    left = {"same": m.Cost(3), "removed": m.Cost(2)}
    right = {"same": m.Cost(5), "added": m.Cost(7)}
    assert m.cost_delta(left, right) == {"added": 7, "removed": -2, "same": 2}
