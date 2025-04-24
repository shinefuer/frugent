"""Paired metrics for reproducible synthetic coding workloads."""

from __future__ import annotations


class BenchmarkError(ValueError):
    """Raised for unpaired or undefined synthetic metrics."""


def token_savings(baseline_tokens: int, candidate_tokens: int) -> float:
    """Return fractional token reduction against a nonzero synthetic baseline."""
    if baseline_tokens <= 0 or not 0 <= candidate_tokens <= baseline_tokens:
        raise BenchmarkError("token savings: expected 0 <= candidate <= positive baseline")
    return round((baseline_tokens - candidate_tokens) / baseline_tokens, 6)


def cache_hit_uplift(baseline_hits: int, candidate_hits: int, requests: int) -> float:
    """Return absolute hit-rate uplift over identical requests."""
    if requests <= 0 or not 0 <= baseline_hits <= requests or not 0 <= candidate_hits <= requests:
        raise BenchmarkError("cache uplift: hits must fit positive request count")
    return round((candidate_hits - baseline_hits) / requests, 6)


def cost_per_completed(total_cost_micros: int, completed: int) -> float:
    """Return fictional micro-cost per completed synthetic task."""
    if total_cost_micros < 0 or completed <= 0:
        raise BenchmarkError("cost per completed: requires non-negative cost and completions")
    return round(total_cost_micros / completed, 6)


def completion_rate(outcomes: tuple[bool, ...]) -> float:
    """Return successful scripted tasks divided by generated tasks."""
    if not outcomes:
        raise BenchmarkError("completion rate: expected outcomes")
    return round(sum(outcomes) / len(outcomes), 6)
