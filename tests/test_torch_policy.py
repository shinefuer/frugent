"""Behavior and invariant tests."""

from __future__ import annotations

import pytest

import frugent.torch_policy as m

pytestmark = pytest.mark.model
torch = pytest.importorskip("torch")


def test_training_example_validates_binary_synthetic_labels() -> None:
    assert m.TrainingExample((1.0, 2.0), 1.0).label == 1.0
    with pytest.raises(m.TorchPolicyError, match="binary"):
        m.TrainingExample((1.0,), 0.5)


def test_torch_extra_is_available_for_model_suite() -> None:
    assert m.torch_available()
