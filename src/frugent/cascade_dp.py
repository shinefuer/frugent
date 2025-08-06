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


def enumerate_policies(options: tuple[tuple[Action, ...], ...]) -> tuple[Policy, ...]:
    """Enumerate one action per difficulty in lexical model order."""
    import itertools

    if not options or any(not actions for actions in options):
        raise CascadeDPError("policy enumeration: options required for every difficulty")
    normalized = tuple(
        tuple(sorted(actions, key=lambda action: action.model)) for actions in options
    )
    return tuple(Policy(tuple(actions)) for actions in itertools.product(*normalized))


def optimal_policy(
    options: tuple[tuple[Action, ...], ...], mixture: DifficultyMixture, quality_floor: float
) -> Policy:
    """Choose least expected cost among policies meeting quality floor."""
    if not 0 <= quality_floor <= 1:
        raise CascadeDPError("policy optimization: quality floor must be in [0, 1]")
    feasible = [
        policy
        for policy in enumerate_policies(options)
        if evaluate(policy, mixture)[1] >= quality_floor
    ]
    if not feasible:
        raise CascadeDPError("policy optimization: quality floor is infeasible")
    return min(feasible, key=lambda policy: (evaluate(policy, mixture)[0], policy.models))


def pareto_frontier(policies: tuple[Policy, ...], mixture: DifficultyMixture) -> tuple[Policy, ...]:
    """Keep policies not dominated in expected cost and quality."""
    scored = {policy: evaluate(policy, mixture) for policy in policies}
    return tuple(
        sorted(
            (
                policy
                for policy, (cost, quality) in scored.items()
                if not any(
                    other_cost <= cost
                    and other_quality >= quality
                    and (other_cost < cost or other_quality > quality)
                    for other, (other_cost, other_quality) in scored.items()
                    if other != policy
                )
            ),
            key=lambda policy: (scored[policy][0], -scored[policy][1], policy.models),
        )
    )
