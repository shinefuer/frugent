"""Hard token and integer micro-cost budgets with explicit degradation."""

from __future__ import annotations

from dataclasses import dataclass


class BudgetError(ValueError):
    """Raised when a budget operation could overspend or become ambiguous."""


@dataclass(frozen=True, slots=True)
class Budget:
    token_limit: int
    cost_limit_micros: int
    tokens_spent: int = 0
    cost_spent_micros: int = 0

    def __post_init__(self) -> None:
        values = (
            self.token_limit,
            self.cost_limit_micros,
            self.tokens_spent,
            self.cost_spent_micros,
        )
        if any(
            isinstance(value, bool) or not isinstance(value, int) or value < 0 for value in values
        ):
            raise BudgetError("budget: values must be non-negative integers")
        if self.tokens_spent > self.token_limit or self.cost_spent_micros > self.cost_limit_micros:
            raise BudgetError("budget: spent resources exceed limit")

    @property
    def remaining_tokens(self) -> int:
        return self.token_limit - self.tokens_spent

    @property
    def remaining_cost_micros(self) -> int:
        return self.cost_limit_micros - self.cost_spent_micros


def can_admit(budget: Budget, tokens: int, cost_micros: int) -> bool:
    """Return whether a reservation fits both hard limits."""
    _validate_amounts(tokens, cost_micros, "admission")
    return tokens <= budget.remaining_tokens and cost_micros <= budget.remaining_cost_micros


def _validate_amounts(tokens: int, cost_micros: int, operation: str) -> None:
    if any(
        isinstance(value, bool) or not isinstance(value, int) or value < 0
        for value in (tokens, cost_micros)
    ):
        raise BudgetError(f"{operation}: values must be non-negative integers")


def reserve(budget: Budget, tokens: int, cost_micros: int) -> Budget:
    """Return updated immutable state or reject the whole reservation."""
    if not can_admit(budget, tokens, cost_micros):
        raise BudgetError("reservation: request exceeds remaining budget")
    return Budget(
        budget.token_limit,
        budget.cost_limit_micros,
        budget.tokens_spent + tokens,
        budget.cost_spent_micros + cost_micros,
    )


def _reservation_total(
    reservations: tuple[tuple[int, int], ...], operation: str
) -> tuple[int, int]:
    if not isinstance(reservations, tuple) or any(
        not isinstance(item, tuple) or len(item) != 2 for item in reservations
    ):
        raise BudgetError(f"{operation}: expected a tuple of token and cost pairs")
    for tokens, cost in reservations:
        _validate_amounts(tokens, cost, operation)
    return (
        sum(tokens for tokens, _ in reservations),
        sum(cost for _, cost in reservations),
    )


def reserve_many(budget: Budget, reservations: tuple[tuple[int, int], ...]) -> Budget:
    """Atomically reserve a measured group or reject it without partial spend."""
    tokens, cost = _reservation_total(reservations, "group reservation")
    return reserve(budget, tokens, cost)


def release(budget: Budget, tokens: int, cost_micros: int) -> Budget:
    """Return unused reserved resources without crossing zero spend."""
    _validate_amounts(tokens, cost_micros, "release")
    if tokens > budget.tokens_spent or cost_micros > budget.cost_spent_micros:
        raise BudgetError("release: cannot release more than spent")
    return Budget(
        budget.token_limit,
        budget.cost_limit_micros,
        budget.tokens_spent - tokens,
        budget.cost_spent_micros - cost_micros,
    )


def release_many(budget: Budget, reservations: tuple[tuple[int, int], ...]) -> Budget:
    """Atomically release the exact aggregate of a reservation group."""
    tokens, cost = _reservation_total(reservations, "group release")
    return release(budget, tokens, cost)


DEGRADATION_LADDER = ("full", "downgrade", "compress", "cache_only", "defer")


def degradation_stage(budget: Budget, estimates: tuple[tuple[str, int, int], ...]) -> str:
    """Select the first declared stage whose estimate fits."""
    names = tuple(name for name, _, _ in estimates)
    if names != DEGRADATION_LADDER[:-1]:
        raise BudgetError("degradation: estimates must follow the declared ladder")
    for name, tokens, cost in estimates:
        if can_admit(budget, tokens, cost):
            return name
    return "defer"


def partition(budget: Budget, shares: tuple[int, ...]) -> tuple[Budget, ...]:
    """Partition unspent limits with exact remainder distribution."""
    if not shares or any(
        isinstance(share, bool) or not isinstance(share, int) or share <= 0 for share in shares
    ):
        raise BudgetError("partition: shares must be positive integers")
    total = sum(shares)
    token_parts = [budget.remaining_tokens * share // total for share in shares]
    cost_parts = [budget.remaining_cost_micros * share // total for share in shares]
    for index in range(budget.remaining_tokens - sum(token_parts)):
        token_parts[index % len(token_parts)] += 1
    for index in range(budget.remaining_cost_micros - sum(cost_parts)):
        cost_parts[index % len(cost_parts)] += 1
    return tuple(Budget(tokens, cost) for tokens, cost in zip(token_parts, cost_parts, strict=True))


def capped_estimate(budget: Budget, tokens: int, cost_micros: int) -> tuple[int, int]:
    """Clamp optimistic work estimates to resources that remain."""
    _validate_amounts(tokens, cost_micros, "estimate cap")
    return min(tokens, budget.remaining_tokens), min(cost_micros, budget.remaining_cost_micros)


def rollup(parent: Budget, children: tuple[Budget, ...]) -> Budget:
    """Charge a parent for child spends while enforcing parent limits."""
    if not isinstance(children, tuple) or any(not isinstance(child, Budget) for child in children):
        raise BudgetError("budget rollup: children must be a budget tuple")
    tokens = sum(child.tokens_spent for child in children)
    cost = sum(child.cost_spent_micros for child in children)
    return reserve(parent, tokens, cost)
