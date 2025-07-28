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
