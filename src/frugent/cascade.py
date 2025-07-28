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


def confidence_route(
    profiles: tuple[ModelProfile, ...], confidences: tuple[float, ...], threshold: float
) -> int:
    """Return index of first profile meeting confidence, else final profile."""
    validate_ladder(profiles)
    if len(confidences) != len(profiles) or not 0 <= threshold <= 1:
        raise CascadeError("confidence gate: invalid scores or threshold")
    if any(not 0 <= score <= 1 for score in confidences):
        raise CascadeError("confidence gate: scores must be in [0, 1]")
    return next(
        (index for index, score in enumerate(confidences) if score >= threshold), len(profiles) - 1
    )


def verified_route(
    profiles: tuple[ModelProfile, ...],
    confidences: tuple[float, ...],
    verified: tuple[bool, ...],
    threshold: float,
) -> int:
    """Stop only when both the confidence and local verifier accept."""
    if len(verified) != len(profiles):
        raise CascadeError("verifier gate: result length mismatch")
    validate_ladder(profiles)
    if len(confidences) != len(profiles):
        raise CascadeError("verifier gate: confidence length mismatch")
    for index, (score, passed) in enumerate(zip(confidences, verified, strict=True)):
        if score >= threshold and passed:
            return index
    return len(profiles) - 1


def attempted_profiles(
    selected_index: int, retry_budget: int, profile_count: int
) -> tuple[int, ...]:
    """Return bounded forward attempts beginning at selected profile."""
    if not 0 <= selected_index < profile_count or retry_budget < 0:
        raise CascadeError("cascade retries: invalid index, budget, or count")
    stop = min(profile_count, selected_index + retry_budget + 1)
    return tuple(range(selected_index, stop))


def expected_quality(profile: ModelProfile, difficulty_weights: tuple[float, ...]) -> float:
    """Weight scripted success by an explicit synthetic difficulty mixture."""
    if len(difficulty_weights) != len(profile.success_by_difficulty) or any(
        weight < 0 for weight in difficulty_weights
    ):
        raise CascadeError("expected quality: invalid difficulty weights")
    total = sum(difficulty_weights)
    if total <= 0:
        raise CascadeError("expected quality: weights must sum positive")
    return round(
        sum(
            success * weight
            for success, weight in zip(
                profile.success_by_difficulty, difficulty_weights, strict=True
            )
        )
        / total,
        6,
    )
