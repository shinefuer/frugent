"""Exact and greedy token-budget selection for context blocks."""

from __future__ import annotations

from dataclasses import dataclass


class KnapsackError(ValueError):
    """Raised for malformed items or capacities."""


@dataclass(frozen=True, slots=True)
class Item:
    key: str
    tokens: int
    value: int

    def __post_init__(self) -> None:
        if not self.key or isinstance(self.tokens, bool) or self.tokens <= 0 or self.value < 0:
            raise KnapsackError("item: key must be non-empty, tokens positive, value non-negative")
