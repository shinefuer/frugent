"""Stable public data types shared by runtime components."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any


class RecordError(ValueError):
    """Raised when a persisted runtime record is invalid."""


@dataclass(frozen=True, slots=True)
class Message:
    """One immutable conversation message with canonical string metadata."""

    role: str
    content: str
    metadata: tuple[tuple[str, str], ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if self.role not in {"system", "user", "assistant", "tool"}:
            raise RecordError(f"message.role: unsupported role {self.role!r}")
        if not isinstance(self.content, str) or not self.content:
            raise RecordError("message.content: expected a non-empty string")
        if tuple(sorted(self.metadata)) != self.metadata:
            raise RecordError("message.metadata: keys must be in canonical order")
        if len({key for key, _ in self.metadata}) != len(self.metadata):
            raise RecordError("message.metadata: duplicate key")

    def to_record(self) -> dict[str, Any]:
        return {
            "role": self.role,
            "content": self.content,
            "metadata": {key: value for key, value in self.metadata},
        }

    @classmethod
    def from_record(cls, record: Mapping[str, Any]) -> Message:
        try:
            role = record["role"]
            content = record["content"]
            raw_metadata = record.get("metadata", {})
        except (KeyError, AttributeError) as error:
            raise RecordError("message: missing role or content") from error
        if not isinstance(role, str) or not isinstance(content, str):
            raise RecordError("message: role and content must be strings")
        if not isinstance(raw_metadata, Mapping) or not all(
            isinstance(key, str) and isinstance(value, str) for key, value in raw_metadata.items()
        ):
            raise RecordError("message.metadata: expected string mapping")
        return cls(role, content, tuple(sorted(raw_metadata.items())))


@dataclass(frozen=True, slots=True)
class Event:
    """A deterministic event in an execution trace."""

    sequence: int
    kind: str
    payload: tuple[tuple[str, str], ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if isinstance(self.sequence, bool) or self.sequence < 0:
            raise RecordError("event.sequence: expected a non-negative integer")
        if not self.kind or not self.kind.replace("_", "").isalnum():
            raise RecordError("event.kind: expected a non-empty identifier")
        if tuple(sorted(self.payload)) != self.payload:
            raise RecordError("event.payload: keys must be in canonical order")

    def to_record(self) -> dict[str, Any]:
        return {
            "sequence": self.sequence,
            "kind": self.kind,
            "payload": dict(self.payload),
        }

    @classmethod
    def from_record(cls, record: Mapping[str, Any]) -> Event:
        sequence = record.get("sequence")
        kind = record.get("kind")
        payload = record.get("payload", {})
        if not isinstance(sequence, int) or not isinstance(kind, str):
            raise RecordError("event: sequence and kind have invalid types")
        if not isinstance(payload, Mapping) or not all(
            isinstance(key, str) and isinstance(value, str) for key, value in payload.items()
        ):
            raise RecordError("event.payload: expected string mapping")
        return cls(sequence, kind, tuple(sorted(payload.items())))


@dataclass(frozen=True, slots=True)
class Decision:
    """A selected candidate and its quantized deterministic score."""

    candidate: str
    reason: str
    score: float

    def __post_init__(self) -> None:
        if not self.candidate:
            raise RecordError("decision.candidate: expected a non-empty identifier")
        if not self.reason:
            raise RecordError("decision.reason: expected a non-empty explanation")
        if not 0.0 <= self.score <= 1.0:
            raise RecordError("decision.score: expected a finite value in [0, 1]")
        object.__setattr__(self, "score", round(self.score, 6))

    def to_record(self) -> dict[str, str | float]:
        return {"candidate": self.candidate, "reason": self.reason, "score": self.score}

    @classmethod
    def from_record(cls, record: Mapping[str, Any]) -> Decision:
        candidate = record.get("candidate")
        reason = record.get("reason")
        score = record.get("score")
        if not isinstance(candidate, str) or not isinstance(reason, str):
            raise RecordError("decision: candidate and reason must be strings")
        if isinstance(score, bool) or not isinstance(score, (int, float)):
            raise RecordError("decision.score: expected a number")
        return cls(candidate, reason, float(score))
