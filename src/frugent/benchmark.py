"""Paired metrics for reproducible synthetic coding workloads."""

from __future__ import annotations


class BenchmarkError(ValueError):
    """Raised for unpaired or undefined synthetic metrics."""


def token_savings(baseline_tokens: int, candidate_tokens: int) -> float:
    """Return fractional token reduction against a nonzero synthetic baseline."""
    if baseline_tokens <= 0 or not 0 <= candidate_tokens <= baseline_tokens:
        raise BenchmarkError("token savings: expected 0 <= candidate <= positive baseline")
    return round((baseline_tokens - candidate_tokens) / baseline_tokens, 6)
