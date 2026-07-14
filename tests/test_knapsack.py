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


@pytest.mark.parametrize("capacity", range(0, 8))
def test_exact_selection_never_exceeds_capacity(capacity: int) -> None:
    items = tuple(m.Item(chr(97 + index), index + 1, (index * 3) % 7) for index in range(6))
    selected = m.exact_select(items, capacity)
    assert sum(item.tokens for item in selected) <= capacity
    assert len({item.key for item in selected}) == len(selected)


def test_greedy_select_respects_capacity_and_stable_order() -> None:
    items = (m.Item("c", 4, 4), m.Item("a", 2, 5), m.Item("b", 3, 6))
    selected = m.greedy_select(items, 5)
    assert tuple(item.key for item in selected) == ("a", "b")
    assert sum(item.tokens for item in selected) <= 5


def test_selection_totals_reconcile_items() -> None:
    items = (m.Item("a", 2, 7), m.Item("b", 5, 3))
    assert m.selection_totals(items) == (7, 10)
    assert m.selection_totals(()) == (0, 0)


def test_approximation_ratio_uses_same_item_set() -> None:
    items = (m.Item("a", 6, 12), m.Item("b", 5, 9), m.Item("c", 5, 9))
    assert m.approximation_ratio(items, 10) == 0.666667
    assert m.approximation_ratio((m.Item("x", 2, 0),), 2) == 1.0


def test_exact_solver_matches_enumerated_subset_oracle() -> None:
    import itertools

    items = (m.Item("a", 1, 2), m.Item("b", 2, 5), m.Item("c", 3, 6), m.Item("d", 4, 8))
    for capacity in range(8):
        feasible_values = [
            sum(item.value for item in subset)
            for size in range(len(items) + 1)
            for subset in itertools.combinations(items, size)
            if sum(item.tokens for item in subset) <= capacity
        ]
        assert m.selection_totals(m.exact_select(items, capacity))[1] == max(feasible_values)


def test_capacity_curve_is_monotonic() -> None:
    items = (m.Item("a", 2, 3), m.Item("b", 3, 7))
    curve = m.capacity_curve(items, 5)
    assert curve == (0, 0, 3, 7, 7, 10)
    assert all(curve[index] <= curve[index + 1] for index in range(len(curve) - 1))


def test_pareto_items_remove_strictly_dominated_blocks() -> None:
    items = (
        m.Item("keep", 2, 5),
        m.Item("heavy", 3, 5),
        m.Item("weak", 2, 4),
        m.Item("trade", 1, 2),
    )
    assert tuple(item.key for item in m.pareto_items(items)) == ("keep", "trade")


@pytest.mark.parametrize("capacity", range(0, 16))
def test_approximation_ratio_stays_in_unit_interval(capacity: int) -> None:
    items = tuple(m.Item(str(index), index + 1, index * index + 1) for index in range(8))
    assert 0.0 <= m.approximation_ratio(items, capacity) <= 1.0


@pytest.mark.parametrize("capacity", range(0, 11))
def test_reduced_solver_preserves_exact_planted_value(capacity: int) -> None:
    items = (m.Item("a", 2, 5), m.Item("b", 3, 5), m.Item("c", 4, 9), m.Item("d", 1, 1))
    assert (
        m.selection_totals(m.reduced_exact_select(items, capacity))[1]
        == m.selection_totals(m.exact_select(items, capacity))[1]
    )


def test_exact_selection_matches_exhaustive_small_instances() -> None:
    import itertools
    import random

    generator = random.Random(71)
    for size in range(1, 8):
        for case in range(20):
            items = tuple(
                m.Item(f"{case}-{index}", generator.randrange(1, 8), generator.randrange(1, 15))
                for index in range(size)
            )
            budget = generator.randrange(0, 18)
            chosen = m.exact_select(items, budget)
            feasible = tuple(
                subset
                for count in range(size + 1)
                for subset in itertools.combinations(items, count)
                if sum(item.tokens for item in subset) <= budget
            )
            optimum = max(sum(item.value for item in subset) for subset in feasible)
            assert sum(item.value for item in chosen) == optimum
