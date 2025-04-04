"""Behavior and invariant tests."""

from __future__ import annotations

import pytest

import frugent.statistics as m


@pytest.mark.parametrize(
    ("values", "expected"),
    [((0.0,), 0.0), ((1.0, 2.0), 1.5), ((-2.0, 1.0, 4.0), 1.0), ((0.1, 0.2), 0.15)],
)
def test_mean_matches_hand_totals(values: tuple[float, ...], expected: float) -> None:
    assert m.mean(values) == expected


@pytest.mark.parametrize("values", [(), (float("nan"),), (float("inf"),)])
def test_mean_rejects_undefined_inputs(values: tuple[float, ...]) -> None:
    with pytest.raises(m.StatisticsError, match="mean"):
        m.mean(values)


def test_weighted_mean_matches_repeated_observations() -> None:
    assert m.weighted_mean((10.0, 20.0), (3.0, 1.0)) == m.mean((10.0, 10.0, 10.0, 20.0))


@pytest.mark.parametrize(
    ("values", "weights"), [((), ()), ((1.0,), ()), ((1.0,), (0.0,)), ((1.0,), (-1.0,))]
)
def test_weighted_mean_rejects_inconsistent_weights(
    values: tuple[float, ...], weights: tuple[float, ...]
) -> None:
    with pytest.raises(m.StatisticsError, match="weighted mean"):
        m.weighted_mean(values, weights)


@pytest.mark.parametrize("scale", [0.1, 1.0, 7.0, 1000.0])
def test_weighted_mean_is_invariant_to_weight_scale(scale: float) -> None:
    weights = tuple(value * scale for value in (1.0, 2.0, 4.0))
    assert m.weighted_mean((2.0, 5.0, 11.0), weights) == m.weighted_mean(
        (2.0, 5.0, 11.0), (1.0, 2.0, 4.0)
    )


@pytest.mark.parametrize(
    ("probability", "expected"), [(0.0, 0.0), (0.25, 7.5), (0.5, 15.0), (0.95, 28.5), (1.0, 30.0)]
)
def test_quantile_interpolates_known_positions(probability: float, expected: float) -> None:
    assert m.quantile((30.0, 0.0, 20.0, 10.0), probability) == expected


def test_paired_deltas_preserve_task_alignment() -> None:
    assert m.paired_deltas((10.0, 30.0, 20.0), (8.0, 31.0, 15.0)) == (2.0, -1.0, 5.0)


def test_paired_deltas_reject_unpaired_runs() -> None:
    with pytest.raises(m.StatisticsError, match="equal nonzero"):
        m.paired_deltas((1.0,), (1.0, 2.0))


def test_bootstrap_interval_is_seeded_and_contains_constant_mean() -> None:
    assert m.bootstrap_mean_ci((4.0, 4.0, 4.0), seed=7, rounds=50) == (4.0, 4.0)
    first = m.bootstrap_mean_ci((1.0, 2.0, 9.0), seed=19, rounds=200)
    assert first == m.bootstrap_mean_ci((1.0, 2.0, 9.0), seed=19, rounds=200)
    assert first[0] <= m.mean((1.0, 2.0, 9.0)) <= first[1]


@pytest.mark.parametrize("probability", [-0.01, 1.01, float("nan")])
def test_quantile_rejects_probability_outside_closed_interval(probability: float) -> None:
    with pytest.raises(m.StatisticsError, match="quantile"):
        m.quantile((1.0,), probability)


def test_quantile_endpoints_equal_extrema() -> None:
    values = (9.0, -2.0, 4.0)
    assert m.quantile(values, 0.0) == min(values)
    assert m.quantile(values, 1.0) == max(values)


def test_latency_summary_uses_documented_quantiles() -> None:
    values = (1.0, 2.0, 3.0, 100.0)
    assert m.latency_summary(values) == {"p50_ms": 2.5, "p95_ms": 85.45, "max_ms": 100.0}


@pytest.mark.parametrize(
    ("values", "expected"), [((1.0,), 0.0), ((1.0, 2.0, 3.0), 1.0), ((1.0, 1.0, 9.0), 0.0)]
)
def test_median_absolute_deviation_resists_outliers(
    values: tuple[float, ...], expected: float
) -> None:
    assert m.median_absolute_deviation(values) == expected
