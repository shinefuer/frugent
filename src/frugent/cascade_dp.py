"""Dynamic programming and exhaustive policy checks for synthetic cascade mixtures."""

from __future__ import annotations

from dataclasses import dataclass


class CascadeDPError(ValueError):
    """Raised for invalid synthetic policy optimization inputs."""


@dataclass(frozen=True, slots=True)
class DifficultyMixture:
    weights: tuple[float, ...]

    def __post_init__(self) -> None:
        if not self.weights or any(weight < 0 for weight in self.weights) or sum(self.weights) <= 0:
            raise CascadeDPError(
                "difficulty mixture: weights must be non-negative and sum positive"
            )

    @property
    def normalized(self) -> tuple[float, ...]:
        total = sum(self.weights)
        return tuple(round(weight / total, 6) for weight in self.weights)


@dataclass(frozen=True, slots=True)
class Action:
    model: str
    cost_micros: int
    success: float

    def __post_init__(self) -> None:
        if not self.model or self.cost_micros < 0 or not 0 <= self.success <= 1:
            raise CascadeDPError("cascade action: invalid model, cost, or success")


@dataclass(frozen=True, slots=True)
class Policy:
    actions: tuple[Action, ...]

    @property
    def models(self) -> tuple[str, ...]:
        return tuple(action.model for action in self.actions)


def evaluate(policy: Policy, mixture: DifficultyMixture) -> tuple[float, float]:
    """Return expected fictional micro-cost and scripted success."""
    weights = mixture.normalized
    if len(policy.actions) != len(weights):
        raise CascadeDPError("policy evaluation: difficulty dimensions differ")
    cost = sum(
        action.cost_micros * weight for action, weight in zip(policy.actions, weights, strict=True)
    )
    quality = sum(
        action.success * weight for action, weight in zip(policy.actions, weights, strict=True)
    )
    return round(cost, 6), round(quality, 6)
