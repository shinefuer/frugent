"""Behavior and invariant tests."""

from __future__ import annotations

import pytest

import frugent.scheduling as m


def test_task_keeps_integer_resource_estimates() -> None:
    assert m.Task("t", 2, 10, 30).cost_micros == 30


@pytest.mark.parametrize("values", [("", 0, 0, 0), ("t", -1, 0, 0), ("t", 1, -1, 0)])
def test_task_rejects_invalid_state(values: tuple[object, ...]) -> None:
    with pytest.raises(m.SchedulingError, match="scheduled task"):
        m.Task(*values)  # type: ignore[arg-type]


def test_scheduler_rejects_ambiguous_resource_types() -> None:
    with pytest.raises(m.SchedulingError, match="scheduled task"):
        m.Task(1, 0, 0, 0)  # type: ignore[arg-type]
    with pytest.raises(m.SchedulingError, match="task admission"):
        m.admit_tasks((), True, 0)
    with pytest.raises(m.SchedulingError, match="fair shares"):
        m.fair_shares(4, (1, True))
    with pytest.raises(m.SchedulingError, match="degradation"):
        m.degradation_decision(m.Task("t", 0, 1, 1), (-1, 1))


def test_task_order_is_priority_aware_and_stable() -> None:
    tasks = (m.Task("low", 0, 1, 1), m.Task("big", 2, 9, 1), m.Task("small", 2, 3, 1))
    assert tuple(task.task_id for task in m.task_order(tasks)) == ("small", "big", "low")


def test_task_order_rejects_duplicate_identity() -> None:
    with pytest.raises(m.SchedulingError, match="duplicate"):
        m.task_order((m.Task("x", 1, 1, 1), m.Task("x", 2, 2, 2)))


@pytest.mark.parametrize("size", [0, 1, 5, 10])
def test_task_order_preserves_identity_and_priority(size: int) -> None:
    tasks = tuple(m.Task(str(index), index % 3, index + 1, 8 + index) for index in range(size))
    ordered = m.task_order(tuple(reversed(tasks)))
    assert {task.task_id for task in ordered} == {task.task_id for task in tasks}
    assert tuple(task.priority for task in ordered) == tuple(
        sorted((task.priority for task in tasks), reverse=True)
    )


def test_task_admission_respects_both_limits() -> None:
    tasks = (m.Task("a", 2, 6, 1), m.Task("b", 1, 4, 9), m.Task("c", 0, 1, 1))
    admitted = m.admit_tasks(tasks, 7, 10)
    assert tuple(task.task_id for task in admitted) == ("a", "c")
    assert sum(task.tokens for task in admitted) <= 7
    assert sum(task.cost_micros for task in admitted) <= 10


@pytest.mark.parametrize(
    ("total", "weights", "expected"),
    [(0, (1, 1), (0, 0)), (5, (1, 1), (3, 2)), (10, (1, 2, 1), (3, 5, 2))],
)
def test_fair_shares_conserve_integer_total(
    total: int, weights: tuple[int, ...], expected: tuple[int, ...]
) -> None:
    assert m.fair_shares(total, weights) == expected
    assert sum(expected) == total


def test_task_budgets_give_higher_priority_no_smaller_share() -> None:
    tasks = (m.Task("low", 0, 1, 1), m.Task("high", 3, 1, 1))
    budgets = m.task_budgets(tasks, 10, 100)
    assert budgets["high"][0] >= budgets["low"][0]
    assert sum(tokens for tokens, _ in budgets.values()) == 10
    assert sum(cost for _, cost in budgets.values()) == 100


def test_empty_scheduler_has_no_allocations_or_spend() -> None:
    assert m.task_budgets((), 10, 20) == {}
    assert m.schedule((), 10, 20) == ()
    assert m.schedule_totals(()) == (0, 0)


@pytest.mark.parametrize("total", range(0, 30))
def test_fair_shares_always_conserve_total(total: int) -> None:
    for weights in ((1,), (1, 1), (1, 2, 3), (9, 1, 4, 2)):
        shares = m.fair_shares(total, weights)
        assert sum(shares) == total
        assert all(share >= 0 for share in shares)


@pytest.mark.parametrize(
    ("allocation", "expected"),
    [
        ((10, 10), "full"),
        ((10, 5), "downgrade"),
        ((5, 5), "compress"),
        ((0, 0), "cache_only"),
        ((2, 9), "defer"),
    ],
)
def test_degradation_decision_follows_declared_order(
    allocation: tuple[int, int], expected: str
) -> None:
    assert m.degradation_decision(m.Task("t", 1, 10, 10), allocation) == expected


def test_schedule_is_deterministic_for_identical_inputs() -> None:
    tasks = (m.Task("b", 1, 5, 7), m.Task("a", 2, 9, 3))
    first = m.schedule(tasks, 10, 10)
    assert first == m.schedule(tasks, 10, 10)
    assert tuple(row[0] for row in first) == ("a", "b")


def test_schedule_record_is_independent_of_input_order() -> None:
    tasks = tuple(m.Task(str(index), index % 4, index + 1, index * 2) for index in range(12))
    assert m.schedule(tasks, 100, 200) == m.schedule(tuple(reversed(tasks)), 100, 200)


def test_schedule_totals_reconcile_allocated_limits() -> None:
    decisions = m.schedule((m.Task("a", 1, 2, 3), m.Task("b", 0, 4, 5)), 11, 17)
    assert m.schedule_totals(decisions) == (11, 17)


def test_fair_shares_conserve_total_with_subunit_rounding_error() -> None:
    import random

    generator = random.Random(44)
    for _ in range(400):
        total = generator.randrange(500)
        weights = tuple(generator.randrange(1, 20) for _ in range(generator.randrange(1, 12)))
        shares = m.fair_shares(total, weights)
        assert sum(shares) == total
        exact = tuple(total * weight / sum(weights) for weight in weights)
        assert all(abs(share - target) < 1 for share, target in zip(shares, exact, strict=True))
