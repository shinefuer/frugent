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
