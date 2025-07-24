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


def validate_ladder(profiles: tuple[ModelProfile, ...]) -> None:
    """Require increasing fictional cost and nondecreasing scripted success."""
    if not profiles or len({profile.name for profile in profiles}) != len(profiles):
        raise CascadeError("model ladder: unique profiles required")
    width = len(profiles[0].success_by_difficulty)
    if any(len(profile.success_by_difficulty) != width for profile in profiles):
        raise CascadeError("model ladder: difficulty curves must align")
    for index in range(len(profiles) - 1):
        left, right = profiles[index], profiles[index + 1]
        if right.cost_micros < left.cost_micros:
            raise CascadeError("model ladder: costs must be nondecreasing")
        if any(
            b < a
            for a, b in zip(left.success_by_difficulty, right.success_by_difficulty, strict=True)
        ):
            raise CascadeError("model ladder: success must be nondecreasing")
