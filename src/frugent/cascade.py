"""Quality-gated model ladders over fictional cost and scripted success profiles."""

from __future__ import annotations

from dataclasses import dataclass


class CascadeError(ValueError):
    """Raised for invalid model ladders or escalation outcomes."""


@dataclass(frozen=True, slots=True)
class ModelProfile:
    name: str
    cost_micros: int
    latency_ms: int
    success_by_difficulty: tuple[float, ...]

    def __post_init__(self) -> None:
        if (
            not self.name
            or self.cost_micros < 0
            or self.latency_ms < 0
            or not self.success_by_difficulty
        ):
            raise CascadeError("model profile: invalid identity, cost, latency, or curve")
        if any(not 0 <= value <= 1 for value in self.success_by_difficulty):
            raise CascadeError("model profile: success values must be in [0, 1]")
