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


@pytest.mark.parametrize(
    ("record", "fragment"),
    [
        ({"content": "x"}, "missing role"),
        ({"role": "user"}, "missing role"),
        ({"role": 1, "content": "x"}, "must be strings"),
        ({"role": "user", "content": []}, "must be strings"),
        ({"role": "user", "content": "x", "metadata": []}, "string mapping"),
        ({"role": "user", "content": "x", "metadata": {"x": 1}}, "string mapping"),
    ],
)
def test_message_reports_precise_record_failures(record: dict[str, object], fragment: str) -> None:
    with pytest.raises(t.RecordError, match=fragment):
        t.Message.from_record(record)


def test_message_rejects_empty_content() -> None:
    with pytest.raises(t.RecordError, match="non-empty"):
        t.Message("user", "")


def test_message_rejects_noncanonical_direct_metadata() -> None:
    with pytest.raises(t.RecordError, match="canonical order"):
        t.Message("user", "x", (("z", "2"), ("a", "1")))
