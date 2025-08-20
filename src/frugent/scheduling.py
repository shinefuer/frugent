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


def fair_shares(total: int, weights: tuple[int, ...]) -> tuple[int, ...]:
    """Allocate integer units by weight with stable largest remainders."""
    if total < 0 or not weights or any(weight <= 0 for weight in weights):
        raise SchedulingError("fair shares: invalid total or weights")
    weight_sum = sum(weights)
    base = [total * weight // weight_sum for weight in weights]
    remainders = [total * weight % weight_sum for weight in weights]
    for index in sorted(range(len(weights)), key=lambda i: (-remainders[i], i))[
        : total - sum(base)
    ]:
        base[index] += 1
    return tuple(base)


def task_budgets(
    tasks: tuple[Task, ...], token_limit: int, cost_limit_micros: int
) -> dict[str, tuple[int, int]]:
    """Allocate token and cost shares using priority+1 as fair weight."""
    ordered = task_order(tasks)
    weights = tuple(task.priority + 1 for task in ordered)
    token_shares = fair_shares(token_limit, weights)
    cost_shares = fair_shares(cost_limit_micros, weights)
    return {
        task.task_id: (tokens, cost)
        for task, tokens, cost in zip(ordered, token_shares, cost_shares, strict=True)
    }


def degradation_decision(task: Task, allocation: tuple[int, int]) -> str:
    """Apply downgrade, compression, cache-only, then defer thresholds."""
    tokens, cost = allocation
    if task.tokens <= tokens and task.cost_micros <= cost:
        return "full"
    if task.tokens <= tokens and task.cost_micros <= cost * 2:
        return "downgrade"
    if task.tokens <= tokens * 2 and task.cost_micros <= cost * 2:
        return "compress"
    if tokens == 0 and cost == 0:
        return "cache_only"
    return "defer"


def schedule(
    tasks: tuple[Task, ...], token_limit: int, cost_limit_micros: int
) -> tuple[tuple[str, str, int, int], ...]:
    """Return task, degradation, token share, and cost share records."""
    allocations = task_budgets(tasks, token_limit, cost_limit_micros)
    return tuple(
        (
            task.task_id,
            degradation_decision(task, allocations[task.task_id]),
            *allocations[task.task_id],
        )
        for task in task_order(tasks)
    )
