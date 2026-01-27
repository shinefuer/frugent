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


def test_tensor_dataset_rejects_mixed_feature_widths() -> None:
    examples = (m.TrainingExample((1,), 0), m.TrainingExample((1, 2), 1))
    with pytest.raises(m.TorchPolicyError, match="feature width"):
        m.tensor_dataset(examples)


def test_tensor_dataset_preserves_example_order_and_shape() -> None:
    features, labels = m.tensor_dataset(
        (m.TrainingExample((1, 2), 0), m.TrainingExample((3, 4), 1))
    )
    assert tuple(features.shape) == (2, 2)
    assert labels.tolist() == [[0.0], [1.0]]


def test_confidence_head_initialization_is_seeded() -> None:
    left = m.build_confidence_head(2, seed=8)
    right = m.build_confidence_head(2, seed=8)
    assert all(
        torch.equal(a, b) for a, b in zip(left.parameters(), right.parameters(), strict=True)
    )
