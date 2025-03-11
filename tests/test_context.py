"""Append-only context snapshots, diffs, and persistence tests."""

from __future__ import annotations

import frugent.context as ctx
from frugent.types import Message


def test_append_returns_new_version_without_mutating_parent() -> None:
    empty = ctx.MessageStore()
    first = empty.append(Message("user", "task"))
    second = first.append(Message("assistant", "plan"))
    assert empty.version == 0
    assert first.version == 1
    assert second.version == 2
    assert first.messages == (Message("user", "task"),)


def test_extend_is_equivalent_to_ordered_appends() -> None:
    messages = (Message("user", "one"), Message("tool", "two"))
    assert ctx.MessageStore().extend(messages) == ctx.MessageStore().append(messages[0]).append(
        messages[1]
    )


def test_store_summary_omits_message_content() -> None:
    store = ctx.MessageStore((Message("user", "private synthetic fixture"),))
    assert store.summary() == {"version": 1, "roles": ("user",)}
