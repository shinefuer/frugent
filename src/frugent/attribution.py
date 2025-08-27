"""Conserved span-level fictional cost and optimization attribution."""

from __future__ import annotations

from dataclasses import dataclass


class AttributionError(ValueError):
    """Raised when cost components do not conserve."""


@dataclass(frozen=True, slots=True)
class Cost:
    prompt_micros: int = 0
    completion_micros: int = 0
    cache_saved_micros: int = 0
    batch_saved_micros: int = 0
    adjustment_micros: int = 0

    def __post_init__(self) -> None:
        values = (
            self.prompt_micros,
            self.completion_micros,
            self.cache_saved_micros,
            self.batch_saved_micros,
        )
        if any(
            isinstance(value, bool) or not isinstance(value, int) or value < 0 for value in values
        ) or not isinstance(self.adjustment_micros, int):
            raise AttributionError("cost: components must use valid integer micro-units")

    @property
    def gross_micros(self) -> int:
        return self.prompt_micros + self.completion_micros

    @property
    def net_micros(self) -> int:
        return (
            self.gross_micros
            - self.cache_saved_micros
            - self.batch_saved_micros
            + self.adjustment_micros
        )
