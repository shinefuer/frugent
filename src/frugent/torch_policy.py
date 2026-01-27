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
