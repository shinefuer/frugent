"""Deterministic statistics for paired synthetic experiments."""

from __future__ import annotations


class StatisticsError(ValueError):
    """Raised for undefined or inconsistent statistics."""


def mean(values: tuple[float, ...]) -> float:
    """Return a six-decimal arithmetic mean."""
    if not values:
        raise StatisticsError("mean: expected at least one value")
    if not all(float("-inf") < value < float("inf") for value in values):
        raise StatisticsError("mean: values must be finite")
    return round(sum(values) / len(values), 6)


def weighted_mean(values: tuple[float, ...], weights: tuple[float, ...]) -> float:
    """Return a finite non-negative weighted mean."""
    if len(values) != len(weights) or not values:
        raise StatisticsError("weighted mean: values and weights must have equal nonzero length")
    if any(weight < 0 or not float("-inf") < weight < float("inf") for weight in weights):
        raise StatisticsError("weighted mean: weights must be finite and non-negative")
    total_weight = sum(weights)
    if total_weight == 0:
        raise StatisticsError("weighted mean: total weight must be positive")
    if not all(float("-inf") < value < float("inf") for value in values):
        raise StatisticsError("weighted mean: values must be finite")
    return round(
        sum(value * weight for value, weight in zip(values, weights, strict=True)) / total_weight, 6
    )


def quantile(values: tuple[float, ...], probability: float) -> float:
    """Compute a linearly interpolated quantile over sorted finite values."""
    if not values or not 0.0 <= probability <= 1.0:
        raise StatisticsError("quantile: requires values and probability in [0, 1]")
    ordered = sorted(values)
    if not all(float("-inf") < value < float("inf") for value in ordered):
        raise StatisticsError("quantile: values must be finite")
    position = (len(ordered) - 1) * probability
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = position - lower
    return round(ordered[lower] * (1 - fraction) + ordered[upper] * fraction, 6)
