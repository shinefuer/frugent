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


@pytest.mark.parametrize(
    ("scores", "threshold", "expected"),
    [((0.9, 0.9, 0.9), 0.8, 0), ((0.2, 0.8, 0.9), 0.8, 1), ((0.1, 0.2, 0.3), 0.8, 2)],
)
def test_confidence_gate_stops_at_first_eligible_profile(
    scores: tuple[float, ...], threshold: float, expected: int
) -> None:
    ladder = tuple(m.ModelProfile(str(i), i + 1, 1, (0.5 + i * 0.1,)) for i in range(3))
    assert m.confidence_route(ladder, scores, threshold) == expected


def test_verifier_can_force_escalation_despite_confidence() -> None:
    ladder = (m.ModelProfile("small", 1, 1, (0.5,)), m.ModelProfile("large", 2, 2, (0.9,)))
    assert m.verified_route(ladder, (0.95, 0.95), (False, True), 0.8) == 1
    assert m.verified_route(ladder, (0.95, 0.95), (True, True), 0.8) == 0
