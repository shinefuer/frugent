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
