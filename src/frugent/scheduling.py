"""Priority-aware deterministic scheduling with fair shares and degradation."""

from __future__ import annotations

from dataclasses import dataclass


class SchedulingError(ValueError):
    """Raised for invalid tasks or allocations."""


@dataclass(frozen=True, slots=True)
class Task:
    task_id: str
    priority: int
    tokens: int
    cost_micros: int

    def __post_init__(self) -> None:
        values = (self.priority, self.tokens, self.cost_micros)
        if not self.task_id or any(
            isinstance(value, bool) or not isinstance(value, int) or value < 0 for value in values
        ):
            raise SchedulingError("scheduled task: invalid identity or resources")


def task_order(tasks: tuple[Task, ...]) -> tuple[Task, ...]:
    """Order high priority first, then smaller token estimate and stable id."""
    if len({task.task_id for task in tasks}) != len(tasks):
        raise SchedulingError("task order: duplicate task id")
    return tuple(sorted(tasks, key=lambda task: (-task.priority, task.tokens, task.task_id)))
