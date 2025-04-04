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


def paired_deltas(baseline: tuple[float, ...], candidate: tuple[float, ...]) -> tuple[float, ...]:
    """Subtract paired candidate values from baselines in task order."""
    if len(baseline) != len(candidate) or not baseline:
        raise StatisticsError("paired deltas: runs must have equal nonzero length")
    return tuple(round(left - right, 6) for left, right in zip(baseline, candidate, strict=True))


def bootstrap_mean_ci(
    values: tuple[float, ...], *, seed: int, rounds: int = 1000, confidence: float = 0.95
) -> tuple[float, float]:
    """Return a seeded percentile interval for the sample mean."""
    import random

    if not values or isinstance(seed, bool) or seed < 0 or rounds < 1 or not 0 < confidence < 1:
        raise StatisticsError("bootstrap: invalid values, seed, rounds, or confidence")
    generator = random.Random(seed)
    samples = tuple(
        mean(tuple(values[generator.randrange(len(values))] for _ in values)) for _ in range(rounds)
    )
    tail = (1.0 - confidence) / 2.0
    return quantile(samples, tail), quantile(samples, 1.0 - tail)


def latency_summary(values_ms: tuple[float, ...]) -> dict[str, float]:
    """Return deterministic P50/P95/max values for simulated latency only."""
    return {
        "p50_ms": quantile(values_ms, 0.5),
        "p95_ms": quantile(values_ms, 0.95),
        "max_ms": quantile(values_ms, 1.0),
    }


def median_absolute_deviation(values: tuple[float, ...]) -> float:
    """Return the median distance from the sample median."""
    center = quantile(values, 0.5)
    return quantile(tuple(abs(value - center) for value in values), 0.5)
