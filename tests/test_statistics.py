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
