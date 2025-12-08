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


def test_jittered_delay_is_seeded_and_bounded() -> None:
    policy = m.RetryPolicy(4, 100, 1000, 250_000)
    first = tuple(m.jittered_delay(policy, index, 7) for index in range(4))
    assert first == tuple(m.jittered_delay(policy, index, 7) for index in range(4))
    assert all(0 <= delay <= policy.max_delay_ms for delay in first)


def test_retry_schedule_length_equals_budget() -> None:
    for retries in range(6):
        policy = m.RetryPolicy(retries, 10, 100, 0)
        assert len(m.retry_schedule(policy, 1)) == retries


@pytest.mark.parametrize("code", [75, 124, 429, 500, 502, 503, 504])
def test_transient_codes_retry_inside_budget(code: int) -> None:
    assert m.should_retry(code, 0, m.RetryPolicy())


@pytest.mark.parametrize("code", [0, 1, 2, 126, 127, 130, 400, 401, 403])
def test_terminal_codes_do_not_retry(code: int) -> None:
    assert not m.should_retry(code, 0, m.RetryPolicy())


@pytest.mark.parametrize("seed", range(20))
def test_jitter_stays_inside_configured_radius(seed: int) -> None:
    policy = m.RetryPolicy(3, 100, 1000, 100_000)
    for index in range(3):
        base = m.base_delay(policy, index)
        actual = m.jittered_delay(policy, index, seed)
        assert base - base // 10 <= actual <= base + base // 10


def test_attempt_records_stop_on_success() -> None:
    records = m.attempt_records((500, 503, 0, 500), m.RetryPolicy(3, 10, 100, 0), 1)
    assert tuple(record.exit_code for record in records) == (500, 503, 0)
    assert tuple(record.delay_before_ms for record in records) == (0, 10, 20)


def test_total_delay_sums_executed_retries_only() -> None:
    records = m.attempt_records((500, 500, 0), m.RetryPolicy(3, 10, 100, 0), 1)
    assert m.total_delay(records) == 30
