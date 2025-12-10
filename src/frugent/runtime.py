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


class ScriptedPlanner:
    """Yield planted actions in order for offline mechanics tests."""

    def __init__(self, actions: tuple[Action, ...]) -> None:
        self.actions = actions
        self.cursor = 0

    def plan(self, observations: tuple[bytes, ...]) -> Action:
        if self.cursor >= len(self.actions):
            raise RuntimeError("scripted planner: no action remains")
        action = self.actions[self.cursor]
        self.cursor += 1
        return action
