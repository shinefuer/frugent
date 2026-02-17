"""End-to-end offline synthesis, runtime measurement, tracing, and reporting."""

from __future__ import annotations

from dataclasses import dataclass


class PipelineError(ValueError):
    """Raised for invalid offline pipeline requests."""


@dataclass(frozen=True, slots=True)
class PipelineConfig:
    seed: int = 0
    tasks: int = 24
    token_budget: int = 4096
    cost_budget_micros: int = 100_000

    def __post_init__(self) -> None:
        values = (self.seed, self.tasks, self.token_budget, self.cost_budget_micros)
        if any(isinstance(value, bool) or not isinstance(value, int) for value in values):
            raise PipelineError("pipeline config: integer fields required")
        if self.seed < 0 or self.tasks < 1 or self.token_budget < 1 or self.cost_budget_micros < 1:
            raise PipelineError("pipeline config: positive limits and non-negative seed required")
