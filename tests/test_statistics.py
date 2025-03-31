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
