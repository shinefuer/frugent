"""Versioned runtime configuration with explicit migrations."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

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

    @property
    def fingerprint(self) -> str:
        """Return a content fingerprint suitable for report metadata."""
        from frugent.codec import payload_digest

        return payload_digest(self.to_record())

    @classmethod
    def from_record(cls, record: Mapping[str, Any]) -> RuntimeConfig:
        """Parse the current schema while rejecting missing or unknown fields."""
        expected = {
            "schema_version",
            "seed",
            "max_steps",
            "token_budget",
            "cost_budget_micros",
            "quality_floor",
        }
        actual = set(record)
        if actual != expected:
            missing = sorted(expected - actual)
            unknown = sorted(actual - expected)
            raise ConfigError(f"config fields: missing={missing}, unknown={unknown}")
        try:
            return cls(
                schema_version=record["schema_version"],
                seed=record["seed"],
                max_steps=record["max_steps"],
                token_budget=record["token_budget"],
                cost_budget_micros=record["cost_budget_micros"],
                quality_floor=record["quality_floor"],
            )
        except TypeError as error:
            raise ConfigError(f"config value types: {error}") from error


def migrate_config(record: Mapping[str, Any]) -> dict[str, int | float]:
    """Migrate a supported historical record to the current schema."""
    version = record.get("schema_version")
    if isinstance(version, bool):
        raise ConfigError(f"config migration: unsupported schema_version {version!r}")
    if version == CURRENT_SCHEMA_VERSION:
        return RuntimeConfig.from_record(record).to_record()
    if version != 1:
        raise ConfigError(f"config migration: unsupported schema_version {version!r}")
    expected = {"schema_version", "seed", "steps", "tokens", "cost_micros"}
    if set(record) != expected:
        raise ConfigError("config migration v1: unexpected fields")
    return RuntimeConfig(
        seed=record["seed"],
        max_steps=record["steps"],
        token_budget=record["tokens"],
        cost_budget_micros=record["cost_micros"],
        quality_floor=0.8,
    ).to_record()


def dump_config(config: RuntimeConfig) -> bytes:
    """Render the exact current schema as canonical UTF-8 JSON."""
    from frugent.codec import canonical_json

    return canonical_json(config.to_record()) + b"\n"
