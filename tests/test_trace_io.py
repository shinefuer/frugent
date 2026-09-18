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


def test_trace_header_rejects_ambiguous_runtime_types() -> None:
    with pytest.raises(m.TraceIOError, match="trace header"):
        m.TraceHeader("run", True, "cfg", "rate")
    with pytest.raises(m.TraceIOError, match="trace header"):
        m.TraceHeader(1, 0, "cfg", "rate")  # type: ignore[arg-type]


def test_trace_event_roundtrip_preserves_payload() -> None:
    encoded = m.encode_event(3, {"kind": "route", "model": "small"})
    assert m.decode_event(encoded) == {"sequence": 3, "kind": "route", "model": "small"}


def test_trace_event_rejects_duplicate_sequence_field() -> None:
    with pytest.raises(m.TraceIOError, match="duplicate sequence"):
        m.encode_event(1, {"sequence": 2})


def test_trace_event_rejects_boolean_sequence() -> None:
    with pytest.raises(m.TraceIOError, match="invalid"):
        m.encode_event(True, {"kind": "x"})


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


def test_trace_import_checks_payload_schema_version_not_only_envelope() -> None:
    from frugent.codec import encode_envelope

    header = m.TraceHeader("r", 1, "c", "p").to_record()
    header["schema_version"] = 1
    encoded = encode_envelope("frugent.trace.header", 2, header) + b"\n"
    with pytest.raises(m.TraceIOError, match="schema version"):
        m.import_trace(encoded)


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


def test_same_header_and_events_export_identical_bytes() -> None:
    header = m.TraceHeader("run", 42, "config", "rate")
    events = tuple({"kind": "step", "value": index} for index in range(20))
    assert m.export_trace(header, events) == m.export_trace(header, events)


def test_event_diff_reports_change_and_addition() -> None:
    header = m.TraceHeader("r", 1, "c", "p")
    left = m.export_trace(header, ({"kind": "a"},))
    right = m.export_trace(header, ({"kind": "b"}, {"kind": "c"}))
    changes = m.event_diff(left, right)
    assert tuple(change["sequence"] for change in changes) == (0, 1)
    assert changes[1]["before"] is None


def test_trace_diff_includes_reproducibility_header_changes() -> None:
    left = m.export_trace(m.TraceHeader("left", 1, "c", "p"), ({"kind": "same"},))
    right = m.export_trace(m.TraceHeader("right", 2, "c", "p"), ({"kind": "same"},))
    difference = m.trace_diff(left, right)
    assert difference.changed
    assert difference.header == (
        m.TraceHeader("left", 1, "c", "p"),
        m.TraceHeader("right", 2, "c", "p"),
    )
    assert difference.events == ()


def test_trace_diff_is_empty_only_for_logically_identical_runs() -> None:
    header = m.TraceHeader("r", 1, "c", "p")
    left = m.export_trace(header, ({"kind": "a"},))
    same = m.export_trace(header, ({"kind": "a"},))
    changed = m.export_trace(header, ({"kind": "b"},))
    assert m.trace_diff(left, same) == m.TraceDiff(None, ())
    assert not m.trace_diff(left, same).changed
    assert tuple(item["sequence"] for item in m.trace_diff(left, changed).events) == (0,)


def test_trace_migration_rejects_boolean_seed() -> None:
    record = {"schema_version": 1, "run": "r", "seed": True, "config": "c", "rate": "x"}
    with pytest.raises(m.TraceIOError, match="seed"):
        m.migrate_header(record)


def test_trace_migration_rejects_boolean_schema_version() -> None:
    record = {"schema_version": True, "run": "r", "seed": 1, "config": "c", "rate": "x"}
    with pytest.raises(m.TraceIOError, match="unsupported"):
        m.migrate_header(record)


def test_trace_stream_roundtrips_hostile_but_valid_event_text() -> None:
    header = m.TraceHeader("run", 9, "cfg", "rate")
    events = tuple(
        {"kind": f"event-{index}", "text": text}
        for index, text in enumerate(
            ("<script>alert(1)</script>", "line1\nline2", "零成本", "quotes: \" ' ", "\u0000")
        )
    )
    encoded = m.export_trace(header, events)
    restored_header, restored = m.import_trace(encoded)
    assert restored_header == header
    assert (
        tuple(
            {key: value for key, value in event.items() if key != "sequence"} for event in restored
        )
        == events
    )


def test_each_trace_line_is_independently_checksummed() -> None:
    data = m.export_trace(
        m.TraceHeader("r", 0, "c", "x"), tuple({"value": index} for index in range(8))
    )
    lines = data.splitlines()
    for index in range(len(lines)):
        mutated = list(lines)
        marker = b'"checksum":"'
        position = mutated[index].index(marker) + len(marker)
        changed = bytearray(mutated[index])
        changed[position] = ord("0") if changed[position] != ord("0") else ord("1")
        mutated[index] = bytes(changed)
        assert not m.verify_trace(b"\n".join(mutated) + b"\n")


def test_event_diff_is_empty_for_reencoding_and_precise_for_change() -> None:
    header = m.TraceHeader("r", 1, "c", "x")
    left = m.export_trace(header, ({"x": 1}, {"x": 2}, {"x": 3}))
    same = m.export_trace(header, ({"x": 1}, {"x": 2}, {"x": 3}))
    right = m.export_trace(header, ({"x": 1}, {"x": 9}, {"x": 3}, {"x": 4}))
    assert m.event_diff(left, same) == ()
    assert tuple(change["sequence"] for change in m.event_diff(left, right)) == (1, 3)
