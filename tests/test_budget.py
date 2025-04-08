"""Behavior and invariant tests."""

from __future__ import annotations

import pytest

import frugent.budget as m


def test_budget_reports_exact_remaining_resources() -> None:
    budget = m.Budget(100, 500, 30, 120)
    assert budget.remaining_tokens == 70
    assert budget.remaining_cost_micros == 380


@pytest.mark.parametrize("values", [(-1, 0, 0, 0), (1, 1, 2, 0), (1, 1, 0, 2), (True, 1, 0, 0)])
def test_budget_rejects_invalid_state(values: tuple[int, int, int, int]) -> None:
    with pytest.raises(m.BudgetError, match="budget"):
        m.Budget(*values)
