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


@dataclass(frozen=True, slots=True)
class ContextDiff:
    base_version: int
    appended: tuple[Message, ...]

    @property
    def target_version(self) -> int:
        return self.base_version + len(self.appended)


def diff(base: MessageStore, target: MessageStore) -> ContextDiff:
    """Return the suffix when target extends base exactly."""
    if target.messages[: base.version] != base.messages:
        raise ContextError("context diff: target does not extend base")
    return ContextDiff(base.version, target.messages[base.version :])


def apply_diff(base: MessageStore, change: ContextDiff) -> MessageStore:
    if base.version != change.base_version:
        raise ContextError("context diff: base version mismatch")
    return base.extend(change.appended)


def store_to_record(store: MessageStore) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "version": store.version,
        "messages": [message.to_record() for message in store.messages],
    }


def store_from_record(record: Mapping[str, Any]) -> MessageStore:
    if set(record) != {"schema_version", "version", "messages"} or record["schema_version"] != 1:
        raise ContextError("context record: unexpected schema")
    raw = record["messages"]
    if not isinstance(raw, list):
        raise ContextError("context record: messages must be a list")
    try:
        store = MessageStore(tuple(Message.from_record(item) for item in raw))
    except (TypeError, ValueError) as error:
        raise ContextError(f"context record: invalid message: {error}") from error
    if record["version"] != store.version:
        raise ContextError("context record: version mismatch")
    return store
