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
