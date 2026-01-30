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


@pytest.mark.slow
def test_confidence_training_reduces_real_loss_on_synthetic_data() -> None:
    examples = tuple(m.TrainingExample((float(x),), float(x > 0)) for x in (-2, -1, 1, 2))
    model = m.build_confidence_head(1, seed=4)
    losses = m.train_head(model, examples, epochs=80, learning_rate=0.2)
    assert losses[-1] < losses[0] * 0.55


def test_prediction_does_not_change_model_parameters() -> None:
    model = m.build_confidence_head(1, seed=9)
    before = tuple(parameter.detach().clone() for parameter in model.parameters())
    m.predict_confidence(model, (1.0,))
    assert all(torch.equal(a, b) for a, b in zip(before, model.parameters(), strict=True))


def test_confidence_prediction_is_bounded_and_quantized() -> None:
    model = m.build_confidence_head(2, seed=2)
    value = m.predict_confidence(model, (0.25, -0.5))
    assert 0 <= value <= 1
    assert value == round(value, 6)


def test_admission_examples_use_declared_planted_threshold() -> None:
    examples = m.admission_examples((0, 2, 4), (100, 30, 20))
    assert tuple(example.label for example in examples) == (0.0, 0.0, 1.0)
    assert examples[1].features == (2.0, 0.3)


@pytest.mark.parametrize(("reuse", "tokens", "threshold"), [(-1, 2, 0.5), (1, 0, 0.5), (1, 2, 1.1)])
def test_admission_decision_rejects_invalid_boundaries(
    reuse: int, tokens: int, threshold: float
) -> None:
    with pytest.raises(m.TorchPolicyError, match="admission decision"):
        m.admission_decision(
            m.build_confidence_head(2, seed=0),
            reuse_count=reuse,
            token_size=tokens,
            threshold=threshold,
        )


def test_admission_decision_matches_exposed_confidence() -> None:
    model = m.build_confidence_head(2, seed=12)
    confidence = m.predict_confidence(model, (3.0, 0.5))
    assert m.admission_decision(model, reuse_count=3, token_size=50, threshold=confidence)
    if confidence < 1:
        assert not m.admission_decision(
            model, reuse_count=3, token_size=50, threshold=confidence + 1e-6
        )
