"""Immutable append-only message history with versioned snapshots."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from frugent.types import Message


class ContextError(ValueError):
    """Raised when a context history violates append-only invariants."""


@dataclass(frozen=True, slots=True)
class MessageStore:
    """A persistent value whose version equals its message count."""

    messages: tuple[Message, ...] = ()

    @property
    def version(self) -> int:
        return len(self.messages)

    def append(self, message: Message) -> MessageStore:
        if not isinstance(message, Message):
            raise ContextError("store.append: expected Message")
        return MessageStore((*self.messages, message))

    def extend(self, messages: tuple[Message, ...]) -> MessageStore:
        result = self
        for message in messages:
            result = result.append(message)
        return result

    def summary(self) -> Mapping[str, Any]:
        """Return cheap metadata without serializing message contents."""
        return {"version": self.version, "roles": tuple(message.role for message in self.messages)}


@dataclass(frozen=True, slots=True)
class Snapshot:
    """A named prefix view into one message store."""

    name: str
    version: int
    messages: tuple[Message, ...]

    def __post_init__(self) -> None:
        if not self.name:
            raise ContextError("snapshot.name: expected non-empty")
        if self.version != len(self.messages):
            raise ContextError("snapshot.version: must equal message count")


def snapshot(store: MessageStore, name: str) -> Snapshot:
    return Snapshot(name, store.version, store.messages)
