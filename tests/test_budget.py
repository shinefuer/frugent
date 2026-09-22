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


def test_group_reservation_is_atomic_and_release_is_its_inverse() -> None:
    original = m.Budget(20, 30)
    group = ((3, 4), (5, 6), (0, 2))
    reserved = m.reserve_many(original, group)
    assert reserved == m.Budget(20, 30, 8, 12)
    assert m.release_many(reserved, group) == original


def test_group_reservation_rejects_whole_overspend() -> None:
    original = m.Budget(10, 10, 2, 1)
    with pytest.raises(m.BudgetError, match="exceeds remaining"):
        m.reserve_many(original, ((4, 2), (5, 2)))
    assert original == m.Budget(10, 10, 2, 1)


def test_group_reservation_validates_every_pair_before_accounting() -> None:
    with pytest.raises(m.BudgetError, match="group reservation"):
        m.reserve_many(m.Budget(10, 10), ((1, 1), (True, 2)))


def test_release_inverts_matching_reservation() -> None:
    base = m.Budget(100, 100)
    reserved = m.reserve(base, 30, 40)
    assert m.release(reserved, 30, 40) == base


def test_budget_operations_reject_boolean_and_noninteger_amounts() -> None:
    budget = m.Budget(10, 20, 3, 4)
    with pytest.raises(m.BudgetError, match="admission"):
        m.can_admit(budget, True, 1)
    with pytest.raises(m.BudgetError, match="release"):
        m.release(budget, 1.5, 1)  # type: ignore[arg-type]
    with pytest.raises(m.BudgetError, match="estimate cap"):
        m.capped_estimate(budget, 1, False)


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


def test_partition_conserves_remaining_limits() -> None:
    parts = m.partition(m.Budget(10, 20, 1, 2), (1, 2, 1))
    assert sum(part.token_limit for part in parts) == 9
    assert sum(part.cost_limit_micros for part in parts) == 18
    assert max(part.token_limit for part in parts) - min(part.token_limit for part in parts) <= 2


@pytest.mark.parametrize(
    ("tokens", "cost", "expected"), [(0, 0, (0, 0)), (10, 20, (7, 14)), (2, 30, (2, 14))]
)
def test_estimate_cap_never_exceeds_remaining_resources(
    tokens: int, cost: int, expected: tuple[int, int]
) -> None:
    assert m.capped_estimate(m.Budget(10, 20, 3, 6), tokens, cost) == expected


@pytest.mark.parametrize("tokens", range(0, 12))
@pytest.mark.parametrize("cost", range(0, 8))
def test_partition_conserves_small_integer_remainders(tokens: int, cost: int) -> None:
    parts = m.partition(m.Budget(tokens, cost), (1, 3, 2))
    assert sum(part.token_limit for part in parts) == tokens
    assert sum(part.cost_limit_micros for part in parts) == cost


def test_rollup_charges_only_child_spend() -> None:
    children = (m.Budget(10, 20, 3, 4), m.Budget(5, 9, 2, 7))
    assert m.rollup(m.Budget(100, 100), children) == m.Budget(100, 100, 5, 11)


def test_rollup_cannot_hide_parent_overspend() -> None:
    with pytest.raises(m.BudgetError, match="reservation"):
        m.rollup(m.Budget(4, 100), (m.Budget(10, 10, 5, 1),))


def test_rollup_rejects_nonbudget_children_before_accounting() -> None:
    with pytest.raises(m.BudgetError, match="children"):
        m.rollup(m.Budget(10, 10), (object(),))  # type: ignore[arg-type]


def test_random_reservations_release_to_identical_budget() -> None:
    import random

    generator = random.Random(13)
    for _ in range(500):
        token_limit, cost_limit = generator.randrange(1000), generator.randrange(1000)
        tokens, cost = generator.randrange(token_limit + 1), generator.randrange(cost_limit + 1)
        initial = m.Budget(token_limit, cost_limit)
        assert m.release(m.reserve(initial, tokens, cost), tokens, cost) == initial
