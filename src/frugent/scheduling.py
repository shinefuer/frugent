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


def admit_tasks(
    tasks: tuple[Task, ...], token_limit: int, cost_limit_micros: int
) -> tuple[Task, ...]:
    """Greedily admit deterministic order without overspending either limit."""
    if token_limit < 0 or cost_limit_micros < 0:
        raise SchedulingError("task admission: limits must be non-negative")
    admitted: list[Task] = []
    remaining_tokens, remaining_cost = token_limit, cost_limit_micros
    for task in task_order(tasks):
        if task.tokens <= remaining_tokens and task.cost_micros <= remaining_cost:
            admitted.append(task)
            remaining_tokens -= task.tokens
            remaining_cost -= task.cost_micros
    return tuple(admitted)
