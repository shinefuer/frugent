"""Behavior and invariant tests."""

from __future__ import annotations

import pytest

import frugent.cascade_dp as m


def test_difficulty_mixture_normalizes_weights() -> None:
    assert m.DifficultyMixture((1.0, 2.0, 1.0)).normalized == (0.25, 0.5, 0.25)


@pytest.mark.parametrize("weights", [(), (-1.0,), (0.0, 0.0)])
def test_difficulty_mixture_rejects_invalid_weights(weights: tuple[float, ...]) -> None:
    with pytest.raises(m.CascadeDPError, match="difficulty mixture"):
        m.DifficultyMixture(weights)
