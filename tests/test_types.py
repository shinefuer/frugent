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


def test_event_roundtrip_preserves_sequence_and_payload() -> None:
    event = t.Event.from_record({"sequence": 3, "kind": "tool_result", "payload": {"b": "2"}})
    assert event.to_record() == {
        "sequence": 3,
        "kind": "tool_result",
        "payload": {"b": "2"},
    }
    assert t.Event.from_record(event.to_record()) == event


@pytest.mark.parametrize("sequence", [-1, -100, True])
def test_event_rejects_invalid_sequence(sequence: int) -> None:
    with pytest.raises(t.RecordError, match=r"event\.sequence"):
        t.Event(sequence, "step")


def test_decision_quantizes_score_at_production() -> None:
    decision = t.Decision("local-small", "prefix affinity", 0.123456789)
    assert decision.score == 0.123457
    assert t.Decision.from_record(decision.to_record()) == decision


@pytest.mark.parametrize("score", [-0.001, 1.001, float("nan")])
def test_decision_rejects_scores_outside_unit_interval(score: float) -> None:
    with pytest.raises(t.RecordError, match=r"decision\.score"):
        t.Decision("candidate", "reason", score)


@pytest.mark.parametrize("kind", ["step", "tool_result", "CACHE_HIT", "x9"])
def test_event_accepts_protocol_identifiers(kind: str) -> None:
    assert t.Event(0, kind).kind == kind


@pytest.mark.parametrize("kind", ["", "tool result", "path/name", "!"])
def test_event_rejects_ambiguous_kind(kind: str) -> None:
    with pytest.raises(t.RecordError, match=r"event\.kind"):
        t.Event(0, kind)


def test_event_wire_shape_is_stable() -> None:
    assert t.Event(7, "cache_hit", (("model", "tiny"),)).to_record() == {
        "sequence": 7,
        "kind": "cache_hit",
        "payload": {"model": "tiny"},
    }


def test_decision_wire_shape_is_stable() -> None:
    assert t.Decision("tiny", "lowest eligible cost", 0.75).to_record() == {
        "candidate": "tiny",
        "reason": "lowest eligible cost",
        "score": 0.75,
    }


def test_usage_addition_preserves_categories() -> None:
    left = t.Usage(100, 20, 80)
    right = t.Usage(40, 10, 10)
    assert left + right == t.Usage(140, 30, 90)
    assert (left + right).total_tokens == 170


def test_usage_rejects_impossible_cached_total() -> None:
    with pytest.raises(t.RecordError, match="cannot exceed"):
        t.Usage(3, 1, 4)
