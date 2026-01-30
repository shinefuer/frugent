"""Optional CPU PyTorch confidence and cache-admission training on synthetic labels."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


class TorchPolicyError(ValueError):
    """Raised for malformed optional policy-training inputs."""


@dataclass(frozen=True, slots=True)
class TrainingExample:
    features: tuple[float, ...]
    label: float

    def __post_init__(self) -> None:
        if not self.features or any(not np.isfinite(value) for value in self.features):
            raise TorchPolicyError("example: finite features are required")
        if self.label not in {0.0, 1.0}:
            raise TorchPolicyError("example: binary label is required")


def torch_available() -> bool:
    import importlib.util

    return importlib.util.find_spec("torch") is not None


def tensor_dataset(examples: tuple[TrainingExample, ...]) -> tuple[object, object]:
    import torch

    if not examples or len({len(example.features) for example in examples}) != 1:
        raise TorchPolicyError("tensor dataset: examples need one feature width")
    features = torch.tensor([example.features for example in examples], dtype=torch.float32)
    labels = torch.tensor([[example.label] for example in examples], dtype=torch.float32)
    return features, labels


def build_confidence_head(width: int, *, seed: int) -> object:
    import torch

    if width < 1 or seed < 0:
        raise TorchPolicyError("confidence head: positive width and seed required")
    torch.manual_seed(seed)
    return torch.nn.Sequential(torch.nn.Linear(width, 1), torch.nn.Sigmoid())


def train_head(
    model: object, examples: tuple[TrainingExample, ...], *, epochs: int, learning_rate: float
) -> tuple[float, ...]:
    import torch

    if epochs < 1 or not 0 < learning_rate <= 1:
        raise TorchPolicyError("training: invalid epochs or learning rate")
    if not isinstance(model, torch.nn.Module):
        raise TorchPolicyError("training: expected torch module")
    features, labels = tensor_dataset(examples)
    optimizer = torch.optim.SGD(model.parameters(), lr=learning_rate)
    loss_function = torch.nn.BCELoss()
    losses: list[float] = []
    for _ in range(epochs):
        optimizer.zero_grad()
        loss = loss_function(model(features), labels)
        loss.backward()
        optimizer.step()
        losses.append(round(float(loss.detach()), 6))
    return tuple(losses)


def predict_confidence(model: object, features: tuple[float, ...]) -> float:
    import torch

    if not isinstance(model, torch.nn.Module) or not features:
        raise TorchPolicyError("prediction: model and features are required")
    model.eval()
    with torch.no_grad():
        output = model(torch.tensor([features], dtype=torch.float32))
    return round(float(output[0, 0]), 6)


def admission_examples(
    reuse_counts: tuple[int, ...], token_sizes: tuple[int, ...]
) -> tuple[TrainingExample, ...]:
    if len(reuse_counts) != len(token_sizes) or not reuse_counts:
        raise TorchPolicyError("admission examples: paired non-empty inputs required")
    if any(
        reuse < 0 or tokens <= 0 for reuse, tokens in zip(reuse_counts, token_sizes, strict=True)
    ):
        raise TorchPolicyError("admission examples: invalid reuse or token count")
    return tuple(
        TrainingExample((float(reuse), float(tokens) / 100.0), float(reuse * tokens >= 80))
        for reuse, tokens in zip(reuse_counts, token_sizes, strict=True)
    )
