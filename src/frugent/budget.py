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
    if any(
        isinstance(value, bool) or not isinstance(value, int) or value < 0
        for value in (tokens, cost_micros)
    ):
        raise BudgetError("admission: estimates must be non-negative integers")
    return tokens <= budget.remaining_tokens and cost_micros <= budget.remaining_cost_micros


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


def release(budget: Budget, tokens: int, cost_micros: int) -> Budget:
    """Return unused reserved resources without crossing zero spend."""
    if any(value < 0 for value in (tokens, cost_micros)):
        raise BudgetError("release: values must be non-negative")
    if tokens > budget.tokens_spent or cost_micros > budget.cost_spent_micros:
        raise BudgetError("release: cannot release more than spent")
    return Budget(
        budget.token_limit,
        budget.cost_limit_micros,
        budget.tokens_spent - tokens,
        budget.cost_spent_micros - cost_micros,
    )


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
