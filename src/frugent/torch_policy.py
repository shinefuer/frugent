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
