"""Deterministic plan-act-observe orchestration over offline adapters and tools."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from frugent.adapters import Adapter, AdapterRequest, AdapterResponse


class RuntimeError(ValueError):
    """Raised when the deterministic loop violates protocol or budget."""


@dataclass(frozen=True, slots=True)
class Action:
    kind: str
    payload: bytes

    def __post_init__(self) -> None:
        if not isinstance(self.kind, str) or self.kind not in {"tool", "answer", "cancel"}:
            raise RuntimeError("runtime action: unsupported kind")
        if not isinstance(self.payload, bytes):
            raise RuntimeError("runtime action: payload must be bytes")


@dataclass(frozen=True, slots=True)
class LoopEvent:
    sequence: int
    phase: str
    payload_hex: str

    def __post_init__(self) -> None:
        if (
            isinstance(self.sequence, bool)
            or not isinstance(self.sequence, int)
            or self.sequence < 0
            or not isinstance(self.phase, str)
            or self.phase not in {"act", "observe", "answer", "cancel"}
            or not isinstance(self.payload_hex, str)
        ):
            raise RuntimeError("loop event: invalid sequence, phase, or payload")
        try:
            decoded = bytes.fromhex(self.payload_hex)
        except ValueError as error:
            raise RuntimeError("loop event: payload is not canonical hex") from error
        if decoded.hex() != self.payload_hex:
            raise RuntimeError("loop event: payload is not canonical hex")


@runtime_checkable
class Planner(Protocol):
    """Produce the next action from immutable observation bytes."""

    def plan(self, observations: tuple[bytes, ...]) -> Action: ...


class ScriptedPlanner:
    """Yield planted actions in order for offline mechanics tests."""

    def __init__(self, actions: tuple[Action, ...]) -> None:
        if not isinstance(actions, tuple) or any(
            not isinstance(action, Action) for action in actions
        ):
            raise RuntimeError("scripted planner: actions must be an action tuple")
        self.actions = actions
        self.cursor = 0

    def plan(self, observations: tuple[bytes, ...]) -> Action:
        if not isinstance(observations, tuple) or any(
            not isinstance(observation, bytes) for observation in observations
        ):
            raise RuntimeError("scripted planner: observations must be a byte tuple")
        if self.cursor >= len(self.actions):
            raise RuntimeError("scripted planner: no action remains")
        action = self.actions[self.cursor]
        self.cursor += 1
        return action


def action_record(action: Action) -> bytes:
    """Encode one adapter action with a single stable kind separator."""
    return action.kind.encode("ascii") + b"\0" + action.payload


def action_from_record(data: bytes) -> Action:
    """Decode an adapter response into a validated runtime action."""
    if not isinstance(data, bytes) or b"\0" not in data:
        raise RuntimeError("adapter action: expected kind and payload bytes")
    raw_kind, _, payload = data.partition(b"\0")
    try:
        kind = raw_kind.decode("ascii")
    except UnicodeDecodeError as error:
        raise RuntimeError("adapter action: kind must be ASCII") from error
    return Action(kind, payload)


class AdapterPlanner:
    """Turn exact offline adapter responses into plan-act-observe actions."""

    def __init__(self, adapter: Adapter, requests: tuple[AdapterRequest, ...]) -> None:
        if not isinstance(adapter, Adapter) or not isinstance(requests, tuple):
            raise RuntimeError("adapter planner: adapter and request tuple required")
        self.adapter = adapter
        self.requests = requests
        self.cursor = 0
        self.responses: list[AdapterResponse] = []

    def plan(self, observations: tuple[bytes, ...]) -> Action:
        if not isinstance(observations, tuple) or any(
            not isinstance(observation, bytes) for observation in observations
        ):
            raise RuntimeError("adapter planner: observations must be a byte tuple")
        if self.cursor >= len(self.requests):
            raise RuntimeError("adapter planner: no request remains")
        request = self.requests[self.cursor]
        response = self.adapter.complete(request)
        if response.request_id != request.request_id:
            raise RuntimeError("adapter planner: response id mismatch")
        self.cursor += 1
        self.responses.append(response)
        return action_from_record(response.content)


def run_loop(planner: Planner, tool: object, max_steps: int) -> tuple[LoopEvent, ...]:
    """Execute planted actions until answer, cancel, or hard step budget."""
    if (
        isinstance(max_steps, bool)
        or not isinstance(max_steps, int)
        or max_steps <= 0
        or not callable(tool)
    ):
        raise RuntimeError("agent loop: positive steps and callable tool required")
    events: list[LoopEvent] = []
    observations: list[bytes] = []
    for _ in range(max_steps):
        action = planner.plan(tuple(observations))
        events.append(LoopEvent(len(events), "act", action_record(action).hex()))
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


def trace_fingerprint(events: tuple[LoopEvent, ...]) -> str:
    from frugent.codec import payload_digest

    return payload_digest(list(event_records(events)))


def terminal_outcome(events: tuple[LoopEvent, ...]) -> tuple[str, bytes]:
    """Return answer/cancel phase and decoded terminal bytes."""
    if not events or events[-1].phase not in {"answer", "cancel"}:
        raise RuntimeError("loop terminal: trace is incomplete")
    return events[-1].phase, bytes.fromhex(events[-1].payload_hex)
