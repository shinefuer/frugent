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
