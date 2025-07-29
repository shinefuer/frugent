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


def test_policy_preserves_difficulty_action_order() -> None:
    policy = m.Policy((m.Action("small", 1, 0.8), m.Action("large", 5, 0.9)))
    assert policy.models == ("small", "large")


def test_action_rejects_success_above_one() -> None:
    with pytest.raises(m.CascadeDPError, match="cascade action"):
        m.Action("m", 1, 1.1)


@pytest.mark.parametrize("scale", [0.1, 1.0, 10.0, 1000.0])
def test_mixture_normalization_is_scale_invariant(scale: float) -> None:
    weights = tuple(scale * value for value in (1.0, 2.0, 3.0))
    assert (
        m.DifficultyMixture(weights).normalized == m.DifficultyMixture((1.0, 2.0, 3.0)).normalized
    )


def test_policy_evaluation_matches_hand_weighted_values() -> None:
    policy = m.Policy((m.Action("s", 1, 0.5), m.Action("l", 9, 1.0)))
    assert m.evaluate(policy, m.DifficultyMixture((3.0, 1.0))) == (3.0, 0.625)


def test_policy_enumeration_covers_cartesian_choices() -> None:
    option = (m.Action("a", 1, 0.5), m.Action("b", 2, 0.8))
    policies = m.enumerate_policies((option, option, option))
    assert len(policies) == 8
    assert policies[0].models == ("a", "a", "a")
    assert policies[-1].models == ("b", "b", "b")
