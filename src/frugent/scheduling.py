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
        if (
            not isinstance(self.task_id, str)
            or not self.task_id
            or any(
                isinstance(value, bool) or not isinstance(value, int) or value < 0
                for value in values
            )
        ):
            raise SchedulingError("scheduled task: invalid identity or resources")


def task_order(tasks: tuple[Task, ...]) -> tuple[Task, ...]:
    """Order high priority first, then smaller token estimate and stable id."""
    if not isinstance(tasks, tuple) or any(not isinstance(task, Task) for task in tasks):
        raise SchedulingError("task order: expected a task tuple")
    if len({task.task_id for task in tasks}) != len(tasks):
        raise SchedulingError("task order: duplicate task id")
    return tuple(sorted(tasks, key=lambda task: (-task.priority, task.tokens, task.task_id)))


def admit_tasks(
    tasks: tuple[Task, ...], token_limit: int, cost_limit_micros: int
) -> tuple[Task, ...]:
    """Greedily admit deterministic order without overspending either limit."""
    _validate_limits(token_limit, cost_limit_micros, "task admission")
    admitted: list[Task] = []
    remaining_tokens, remaining_cost = token_limit, cost_limit_micros
    for task in task_order(tasks):
        if task.tokens <= remaining_tokens and task.cost_micros <= remaining_cost:
            admitted.append(task)
            remaining_tokens -= task.tokens
            remaining_cost -= task.cost_micros
    return tuple(admitted)


def _validate_limits(token_limit: int, cost_limit_micros: int, operation: str) -> None:
    if any(
        isinstance(value, bool) or not isinstance(value, int) or value < 0
        for value in (token_limit, cost_limit_micros)
    ):
        raise SchedulingError(f"{operation}: limits must be non-negative integers")


def fair_shares(total: int, weights: tuple[int, ...]) -> tuple[int, ...]:
    """Allocate integer units by weight with stable largest remainders."""
    if (
        isinstance(total, bool)
        or not isinstance(total, int)
        or total < 0
        or not isinstance(weights, tuple)
        or not weights
        or any(
            isinstance(weight, bool) or not isinstance(weight, int) or weight <= 0
            for weight in weights
        )
    ):
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
    _validate_limits(token_limit, cost_limit_micros, "task budgets")
    ordered = task_order(tasks)
    if not ordered:
        return {}
    weights = tuple(task.priority + 1 for task in ordered)
    token_shares = fair_shares(token_limit, weights)
    cost_shares = fair_shares(cost_limit_micros, weights)
    return {
        task.task_id: (tokens, cost)
        for task, tokens, cost in zip(ordered, token_shares, cost_shares, strict=True)
    }


def degradation_decision(task: Task, allocation: tuple[int, int]) -> str:
    """Apply downgrade, compression, cache-only, then defer thresholds."""
    if not isinstance(allocation, tuple) or len(allocation) != 2:
        raise SchedulingError("degradation: expected token and cost allocation")
    tokens, cost = allocation
    _validate_limits(tokens, cost, "degradation")
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


def schedule_totals(decisions: tuple[tuple[str, str, int, int], ...]) -> tuple[int, int]:
    """Roll up allocated shares without interpreting unused capacity as spend."""
    if len({task_id for task_id, _, _, _ in decisions}) != len(decisions):
        raise SchedulingError("schedule totals: duplicate task id")
    return sum(tokens for _, _, tokens, _ in decisions), sum(cost for _, _, _, cost in decisions)


def realized_spend(task: Task, decision: tuple[str, str, int, int]) -> tuple[int, int]:
    """Translate one degradation decision into bounded simulated spend."""
    task_id, stage, allocated_tokens, allocated_cost = decision
    if task_id != task.task_id:
        raise SchedulingError("schedule spend: task identity mismatch")
    expected_stage = degradation_decision(task, (allocated_tokens, allocated_cost))
    if stage != expected_stage:
        raise SchedulingError("schedule spend: degradation stage mismatch")
    if stage == "full":
        spend = (task.tokens, task.cost_micros)
    elif stage == "downgrade":
        spend = (task.tokens, (task.cost_micros + 1) // 2)
    elif stage == "compress":
        spend = ((task.tokens + 1) // 2, (task.cost_micros + 1) // 2)
    else:
        spend = (0, 0)
    if spend[0] > allocated_tokens or spend[1] > allocated_cost:
        raise SchedulingError("schedule spend: degradation exceeds allocation")
    return spend


def schedule_spend_totals(
    tasks: tuple[Task, ...], decisions: tuple[tuple[str, str, int, int], ...]
) -> tuple[int, int]:
    """Roll up actual simulated spend while retaining unused allocation."""
    ordered = task_order(tasks)
    if len(ordered) != len(decisions):
        raise SchedulingError("schedule spend: task and decision counts differ")
    spends = tuple(
        realized_spend(task, decision) for task, decision in zip(ordered, decisions, strict=True)
    )
    return sum(tokens for tokens, _ in spends), sum(cost for _, cost in spends)
