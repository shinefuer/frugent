"""Versioned runtime configuration with explicit migrations."""

from __future__ import annotations

from dataclasses import dataclass

CURRENT_SCHEMA_VERSION = 2


class ConfigError(ValueError):
    """Raised when runtime configuration is invalid or ambiguous."""


@dataclass(frozen=True, slots=True)
class RuntimeConfig:
    """Hard runtime limits expressed with deterministic integer budgets."""

    seed: int = 0
    max_steps: int = 8
    token_budget: int = 4096
    cost_budget_micros: int = 100_000
    quality_floor: float = 0.8
    schema_version: int = CURRENT_SCHEMA_VERSION

    def __post_init__(self) -> None:
        integers = {
            "seed": self.seed,
            "max_steps": self.max_steps,
            "token_budget": self.token_budget,
            "cost_budget_micros": self.cost_budget_micros,
        }
        for name, value in integers.items():
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ConfigError(f"config.{name}: expected a non-negative integer")
        if self.max_steps == 0 or self.token_budget == 0:
            raise ConfigError("config: max_steps and token_budget must be positive")
        if not 0.0 <= self.quality_floor <= 1.0:
            raise ConfigError("config.quality_floor: expected a value in [0, 1]")
        if self.schema_version != CURRENT_SCHEMA_VERSION:
            raise ConfigError(f"config.schema_version: expected {CURRENT_SCHEMA_VERSION}")
        object.__setattr__(self, "quality_floor", round(self.quality_floor, 6))

    def to_record(self) -> dict[str, int | float]:
        return {
            "schema_version": self.schema_version,
            "seed": self.seed,
            "max_steps": self.max_steps,
            "token_budget": self.token_budget,
            "cost_budget_micros": self.cost_budget_micros,
            "quality_floor": self.quality_floor,
        }
