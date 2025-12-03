"""Capped deterministic retry schedules with seeded jitter and cancellation."""

from __future__ import annotations

from dataclasses import dataclass


class RetryError(ValueError):
    """Raised for invalid retry policy or attempt state."""


@dataclass(frozen=True, slots=True)
class RetryPolicy:
    max_retries: int = 3
    base_delay_ms: int = 100
    max_delay_ms: int = 2000
    jitter_ppm: int = 100_000

    def __post_init__(self) -> None:
        values = (self.max_retries, self.base_delay_ms, self.max_delay_ms, self.jitter_ppm)
        if any(
            isinstance(value, bool) or not isinstance(value, int) or value < 0 for value in values
        ):
            raise RetryError("retry policy: values must be non-negative integers")
        if self.max_delay_ms < self.base_delay_ms or self.jitter_ppm > 1_000_000:
            raise RetryError("retry policy: invalid cap or jitter")


def base_delay(policy: RetryPolicy, retry_index: int) -> int:
    """Return capped exponential delay before a zero-based retry."""
    if retry_index < 0 or retry_index >= policy.max_retries:
        raise RetryError("retry delay: index outside retry budget")
    return min(policy.max_delay_ms, policy.base_delay_ms * (2**retry_index))
