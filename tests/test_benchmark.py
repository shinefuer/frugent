"""Behavior and invariant tests."""

from __future__ import annotations

import pytest

import frugent.benchmark as m


@pytest.mark.parametrize(
    ("baseline", "candidate", "expected"),
    [(100, 100, 0.0), (100, 75, 0.25), (3, 1, 0.666667), (9, 0, 1.0)],
)
def test_token_savings_uses_fractional_reduction(
    baseline: int, candidate: int, expected: float
) -> None:
    assert m.token_savings(baseline, candidate) == expected


@pytest.mark.parametrize("values", [(0, 0), (10, 11), (10, -1)])
def test_token_savings_rejects_invalid_comparison(values: tuple[int, int]) -> None:
    with pytest.raises(m.BenchmarkError, match="token savings"):
        m.token_savings(*values)


@pytest.mark.parametrize(
    ("base", "candidate", "requests", "expected"),
    [(0, 5, 10, 0.5), (8, 8, 10, 0.0), (9, 4, 10, -0.5)],
)
def test_cache_uplift_preserves_direction(
    base: int, candidate: int, requests: int, expected: float
) -> None:
    assert m.cache_hit_uplift(base, candidate, requests) == expected


@pytest.mark.parametrize("requests", [1, 2, 7, 100])
def test_cache_uplift_stays_between_minus_and_plus_one(requests: int) -> None:
    for baseline in range(requests + 1):
        for candidate in range(requests + 1):
            assert -1.0 <= m.cache_hit_uplift(baseline, candidate, requests) <= 1.0
