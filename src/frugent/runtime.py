"""Deterministic plan-act-observe orchestration over offline adapters and tools."""

from __future__ import annotations

from dataclasses import dataclass


class RuntimeError(ValueError):
    """Raised when the deterministic loop violates protocol or budget."""


@dataclass(frozen=True, slots=True)
class Action:
    kind: str
    payload: bytes

    def __post_init__(self) -> None:
        if self.kind not in {"tool", "answer", "cancel"}:
            raise RuntimeError("runtime action: unsupported kind")


@dataclass(frozen=True, slots=True)
class LoopEvent:
    sequence: int
    phase: str
    payload_hex: str
