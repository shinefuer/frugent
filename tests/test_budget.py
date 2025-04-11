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


@pytest.mark.parametrize(
    ("tokens", "cost", "expected"), [(0, 0, True), (70, 380, True), (71, 1, False), (1, 381, False)]
)
def test_admission_checks_both_remaining_limits(tokens: int, cost: int, expected: bool) -> None:
    assert m.can_admit(m.Budget(100, 500, 30, 120), tokens, cost) is expected


@pytest.mark.parametrize("token_limit", [0, 1, 7, 31])
@pytest.mark.parametrize("cost_limit", [0, 1, 11, 47])
def test_all_admissions_fit_remaining_limits(token_limit: int, cost_limit: int) -> None:
    budget = m.Budget(token_limit, cost_limit)
    for tokens in range(token_limit + 2):
        for cost in range(cost_limit + 2):
            if m.can_admit(budget, tokens, cost):
                assert tokens <= budget.remaining_tokens
                assert cost <= budget.remaining_cost_micros


def test_reserve_is_atomic_and_immutable() -> None:
    original = m.Budget(10, 20)
    updated = m.reserve(original, 4, 7)
    assert updated == m.Budget(10, 20, 4, 7)
    assert original == m.Budget(10, 20)


def test_reserve_rejects_without_partial_spend() -> None:
    original = m.Budget(10, 20, 9, 5)
    with pytest.raises(m.BudgetError, match="exceeds remaining"):
        m.reserve(original, 2, 1)
    assert original.tokens_spent == 9


def test_release_inverts_matching_reservation() -> None:
    base = m.Budget(100, 100)
    reserved = m.reserve(base, 30, 40)
    assert m.release(reserved, 30, 40) == base


@pytest.mark.parametrize("amounts", [(31, 0), (0, 41), (-1, 0)])
def test_release_rejects_impossible_refund(amounts: tuple[int, int]) -> None:
    with pytest.raises(m.BudgetError, match="release"):
        m.release(m.Budget(100, 100, 30, 40), *amounts)


def test_degradation_selects_first_affordable_stage() -> None:
    estimates = (
        ("full", 100, 100),
        ("downgrade", 80, 40),
        ("compress", 20, 30),
        ("cache_only", 0, 0),
    )
    assert m.degradation_stage(m.Budget(50, 50), estimates) == "compress"
    assert m.degradation_stage(m.Budget(0, 0), estimates) == "cache_only"


def test_degradation_never_skips_an_affordable_earlier_stage() -> None:
    estimates = (("full", 8, 8), ("downgrade", 6, 6), ("compress", 4, 4), ("cache_only", 0, 0))
    for limit in range(0, 10):
        selected = m.degradation_stage(m.Budget(limit, limit), estimates)
        selected_index = m.DEGRADATION_LADDER.index(selected)
        assert all(
            not m.can_admit(m.Budget(limit, limit), tokens, cost)
            for _, tokens, cost in estimates[:selected_index]
        )
