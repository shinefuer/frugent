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


def run_loop(planner: ScriptedPlanner, tool: object, max_steps: int) -> tuple[LoopEvent, ...]:
    """Execute planted actions until answer, cancel, or hard step budget."""
    if max_steps <= 0 or not callable(tool):
        raise RuntimeError("agent loop: positive steps and callable tool required")
    events: list[LoopEvent] = []
    observations: list[bytes] = []
    for _ in range(max_steps):
        action = planner.plan(tuple(observations))
        events.append(
            LoopEvent(len(events), "act", action.kind.encode().hex() + ":" + action.payload.hex())
        )
        if action.kind == "answer":
            events.append(LoopEvent(len(events), "answer", action.payload.hex()))
            return tuple(events)
        if action.kind == "cancel":
            events.append(LoopEvent(len(events), "cancel", action.payload.hex()))
            return tuple(events)
        result = tool(action.payload)
        if not isinstance(result, bytes):
            raise RuntimeError("agent loop: tool must return bytes")
        observations.append(result)
        events.append(LoopEvent(len(events), "observe", result.hex()))
    raise RuntimeError("agent loop: step budget exhausted")


def cancelled(events: tuple[LoopEvent, ...]) -> bool:
    """Return whether the terminal event is cancellation."""
    return bool(events) and events[-1].phase == "cancel"


def step_count(events: tuple[LoopEvent, ...]) -> int:
    """Count actions, not observations or terminal annotations."""
    return sum(event.phase == "act" for event in events)


def event_records(events: tuple[LoopEvent, ...]) -> tuple[dict[str, object], ...]:
    """Return schema-stable sequence records."""
    if tuple(event.sequence for event in events) != tuple(range(len(events))):
        raise RuntimeError("loop events: sequence is not contiguous")
    return tuple(
        {
            "schema_version": 1,
            "sequence": event.sequence,
            "phase": event.phase,
            "payload_hex": event.payload_hex,
        }
        for event in events
    )
