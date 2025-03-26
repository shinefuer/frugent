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
