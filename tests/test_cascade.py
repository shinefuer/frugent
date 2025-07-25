"""Behavior and invariant tests."""

from __future__ import annotations

import pytest

import frugent.cascade as m


def test_model_profile_keeps_scripted_success_curve() -> None:
    profile = m.ModelProfile("small", 10, 3, (0.9, 0.5, 0.1))
    assert profile.success_by_difficulty[1] == 0.5


@pytest.mark.parametrize("curve", [(), (-0.1,), (1.1,), (float("nan"),)])
def test_model_profile_rejects_invalid_success_curve(curve: tuple[float, ...]) -> None:
    with pytest.raises(m.CascadeError, match="model profile"):
        m.ModelProfile("m", 1, 1, curve)


def test_valid_ladder_accepts_more_capable_expensive_profiles() -> None:
    ladder = (m.ModelProfile("small", 1, 1, (0.8, 0.3)), m.ModelProfile("large", 5, 3, (0.9, 0.8)))
    assert m.validate_ladder(ladder) is None


def test_ladder_rejects_quality_regression() -> None:
    ladder = (m.ModelProfile("a", 1, 1, (0.8,)), m.ModelProfile("b", 2, 1, (0.7,)))
    with pytest.raises(m.CascadeError, match="success must"):
        m.validate_ladder(ladder)


def test_ladder_rejects_different_difficulty_dimensions() -> None:
    profiles = (m.ModelProfile("a", 1, 1, (0.5,)), m.ModelProfile("b", 2, 1, (0.6, 0.7)))
    with pytest.raises(m.CascadeError, match="align"):
        m.validate_ladder(profiles)
