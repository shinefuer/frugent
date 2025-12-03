"""Behavior and invariant tests."""

from __future__ import annotations

import pytest

import frugent.retry as m


def test_retry_policy_accepts_zero_retries_and_jitter() -> None:
    assert m.RetryPolicy(0, 0, 0, 0).max_retries == 0


@pytest.mark.parametrize("values", [(-1, 1, 1, 0), (1, 2, 1, 0), (1, 1, 1, 1_000_001)])
def test_retry_policy_rejects_invalid_bounds(values: tuple[int, ...]) -> None:
    with pytest.raises(m.RetryError, match="retry policy"):
        m.RetryPolicy(*values)


@pytest.mark.parametrize(("index", "expected"), [(0, 100), (1, 200), (2, 400), (3, 500)])
def test_base_delay_doubles_then_caps(index: int, expected: int) -> None:
    assert m.base_delay(m.RetryPolicy(4, 100, 500, 0), index) == expected


def test_delay_rejects_index_at_retry_budget() -> None:
    policy = m.RetryPolicy(2)
    with pytest.raises(m.RetryError, match="outside retry budget"):
        m.base_delay(policy, 2)
