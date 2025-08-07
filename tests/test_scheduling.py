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
