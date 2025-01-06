"""Behavior contracts for public runtime records."""

from __future__ import annotations

import pytest

import frugent.types as t


def test_message_roundtrip_canonicalizes_metadata() -> None:
    message = t.Message.from_record(
        {"role": "user", "content": "fix it", "metadata": {"z": "2", "a": "1"}}
    )
    assert message.metadata == (("a", "1"), ("z", "2"))
    assert t.Message.from_record(message.to_record()) == message


@pytest.mark.parametrize("role", ["system", "user", "assistant", "tool"])
def test_message_accepts_each_protocol_role(role: str) -> None:
    assert t.Message(role, "payload").role == role


@pytest.mark.parametrize("role", ["", "developer", "USER", " tool"])
def test_message_rejects_roles_outside_protocol(role: str) -> None:
    with pytest.raises(t.RecordError, match=r"message\.role"):
        t.Message(role, "payload")
