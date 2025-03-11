"""Append-only context snapshots, diffs, and persistence tests."""

from __future__ import annotations

import pytest

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


@pytest.mark.parametrize("value", [None, "message", {"role": "user"}, 1])
def test_store_append_rejects_non_messages(value: object) -> None:
    with pytest.raises(ctx.ContextError, match="expected Message"):
        ctx.MessageStore().append(value)  # type: ignore[arg-type]


def test_extending_empty_tuple_preserves_value() -> None:
    store = ctx.MessageStore((Message("system", "rules"),))
    assert store.extend(()) == store


def test_snapshot_freezes_current_prefix() -> None:
    store = ctx.MessageStore().append(Message("user", "one"))
    snap = ctx.snapshot(store, "before-tool")
    later = store.append(Message("tool", "two"))
    assert snap.version == 1
    assert snap.messages == store.messages
    assert snap.messages != later.messages


def test_snapshot_rejects_empty_name() -> None:
    with pytest.raises(ctx.ContextError, match=r"snapshot\.name"):
        ctx.snapshot(ctx.MessageStore(), "")
