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


@pytest.mark.parametrize("field", ["run_id", "config_hash", "rate_card_hash"])
def test_header_requires_each_identity_field(field: str) -> None:
    values = {"run_id": "r", "seed": 1, "config_hash": "c", "rate_card_hash": "p"}
    values[field] = ""
    with pytest.raises(m.TraceIOError, match="trace header"):
        m.TraceHeader(**values)


def test_trace_export_has_header_and_one_line_per_event() -> None:
    data = m.export_trace(m.TraceHeader("r", 1, "c", "p"), ({"kind": "a"}, {"kind": "b"}))
    assert data.count(b"\n") == 3
    assert data.endswith(b"\n")


def test_trace_import_inverts_export() -> None:
    header = m.TraceHeader("r", 1, "c", "p")
    data = m.export_trace(header, ({"kind": "a"}, {"kind": "b"}))
    restored_header, events = m.import_trace(data)
    assert restored_header == header
    assert events == ({"sequence": 0, "kind": "a"}, {"sequence": 1, "kind": "b"})


def test_verify_trace_detects_single_byte_tampering() -> None:
    data = m.export_trace(m.TraceHeader("r", 1, "c", "p"), ({"kind": "alpha"},))
    assert m.verify_trace(data)
    assert not m.verify_trace(data.replace(b"alpha", b"omega"))


def test_verify_trace_rejects_truncated_tail() -> None:
    data = m.export_trace(m.TraceHeader("r", 1, "c", "p"), ())
    assert not m.verify_trace(data.rstrip(b"\n"))


@pytest.mark.parametrize("index", range(5))
def test_tampering_any_event_line_invalidates_stream(index: int) -> None:
    data = m.export_trace(
        m.TraceHeader("r", 1, "c", "p"), tuple({"kind": f"event-{i}"} for i in range(5))
    )
    changed = data.replace(f"event-{index}".encode(), f"event-X{index}".encode())
    assert not m.verify_trace(changed)


def test_v1_header_migration_renames_reproducibility_fields() -> None:
    legacy = {"schema_version": 1, "run": "r", "seed": 3, "config": "c", "rate": "p"}
    assert m.migrate_header(legacy) == m.TraceHeader("r", 3, "c", "p").to_record()


def test_current_header_migration_is_idempotent() -> None:
    record = m.TraceHeader("r", 3, "c", "p").to_record()
    assert m.migrate_header(m.migrate_header(record)) == record


def test_trace_fingerprint_is_exact_byte_digest() -> None:
    data = m.export_trace(m.TraceHeader("r", 1, "c", "p"), ({"kind": "x"},))
    assert m.trace_fingerprint(data) == m.trace_fingerprint(data)
    changed = m.export_trace(m.TraceHeader("r", 1, "c", "p"), ({"kind": "y"},))
    assert m.trace_fingerprint(data) != m.trace_fingerprint(changed)
