"""Behavior and invariant tests."""

from __future__ import annotations

import pytest

import frugent.trace_io as m


def test_trace_header_record_includes_reproducibility_metadata() -> None:
    header = m.TraceHeader("run", 7, "cfg", "rate")
    assert header.to_record() == {
        "run_id": "run",
        "seed": 7,
        "config_hash": "cfg",
        "rate_card_hash": "rate",
        "schema_version": 2,
    }


def test_trace_header_rejects_empty_fingerprint() -> None:
    with pytest.raises(m.TraceIOError, match="trace header"):
        m.TraceHeader("run", 0, "", "rate")


def test_trace_event_roundtrip_preserves_payload() -> None:
    encoded = m.encode_event(3, {"kind": "route", "model": "small"})
    assert m.decode_event(encoded) == {"sequence": 3, "kind": "route", "model": "small"}


def test_trace_event_rejects_duplicate_sequence_field() -> None:
    with pytest.raises(m.TraceIOError, match="duplicate sequence"):
        m.encode_event(1, {"sequence": 2})
