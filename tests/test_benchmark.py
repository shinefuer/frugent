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


def test_cost_per_completed_uses_only_successful_tasks() -> None:
    assert m.cost_per_completed(101, 4) == 25.25
    assert m.cost_per_completed(0, 2) == 0.0


def test_cost_per_completed_rejects_zero_successes() -> None:
    with pytest.raises(m.BenchmarkError, match="completions"):
        m.cost_per_completed(10, 0)


@pytest.mark.parametrize(
    ("outcomes", "expected"), [((True,), 1.0), ((False,), 0.0), ((True, False, True), 0.666667)]
)
def test_completion_rate_counts_scripted_outcomes(
    outcomes: tuple[bool, ...], expected: float
) -> None:
    assert m.completion_rate(outcomes) == expected


def test_quality_preservation_is_pairwise_not_just_average() -> None:
    baseline = (1.0, 0.5)
    assert m.quality_preserved(baseline, (0.9, 0.45), 0.9)
    assert not m.quality_preserved(baseline, (1.0, 0.44), 0.9)


def test_quality_preservation_can_only_get_harder_as_floor_rises() -> None:
    baseline = (0.8, 0.9, 1.0)
    candidate = (0.7, 0.82, 0.91)
    results = [m.quality_preserved(baseline, candidate, floor / 100) for floor in range(0, 101)]
    assert all(not results[index + 1] or results[index] for index in range(len(results) - 1))


def test_latency_simulation_includes_queue_wait() -> None:
    assert m.simulated_latency((0, 2, 20), (5, 5, 3)) == (5, 8, 3)
    assert m.simulated_latency((), ()) == ()


def test_latency_simulation_rejects_unsorted_arrivals() -> None:
    with pytest.raises(m.BenchmarkError, match="sorted"):
        m.simulated_latency((2, 1), (1, 1))


@pytest.mark.parametrize(
    ("completed", "elapsed", "expected"),
    [(0, 100, 0.0), (1, 1000, 1.0), (5, 2000, 2.5), (3, 1, 3000.0)],
)
def test_throughput_uses_simulated_milliseconds(
    completed: int, elapsed: int, expected: float
) -> None:
    assert m.throughput(completed, elapsed) == expected


@pytest.mark.parametrize("service", [(0,), (1, 2, 3), (5, 0, 2, 1)])
def test_back_to_back_fifo_completion_conserves_service(service: tuple[int, ...]) -> None:
    arrivals = (0,) * len(service)
    latencies = m.simulated_latency(arrivals, service)
    assert (latencies[-1] if latencies else 0) == sum(service)


def test_comparison_row_contains_only_derived_measured_fields() -> None:
    assert m.comparison_row(
        baseline_tokens=100,
        candidate_tokens=75,
        baseline_cost=50,
        candidate_cost=35,
        baseline_hits=1,
        candidate_hits=6,
        requests=10,
    ) == {"requests": 10, "token_savings": 0.25, "cache_hit_uplift": 0.5, "cost_savings_micros": 15}


def test_fifo_latency_matches_explicit_completion_clock() -> None:
    import random

    generator = random.Random(6)
    for _ in range(100):
        arrivals = tuple(sorted(generator.randrange(100) for _ in range(20)))
        services = tuple(generator.randrange(10) for _ in arrivals)
        completion = 0
        expected = []
        for arrival, service in zip(arrivals, services, strict=True):
            completion = max(completion, arrival) + service
            expected.append(completion - arrival)
        assert m.simulated_latency(arrivals, services) == tuple(expected)
