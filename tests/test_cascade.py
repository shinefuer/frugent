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
