"""Versioned checksummed JSONL trace persistence and migration."""

from __future__ import annotations

from dataclasses import dataclass

from frugent.codec import decode_envelope, encode_envelope


class TraceIOError(ValueError):
    """Raised for corrupted or unsupported trace streams."""


@dataclass(frozen=True, slots=True)
class TraceHeader:
    run_id: str
    seed: int
    config_hash: str
    rate_card_hash: str
    schema_version: int = 2

    def __post_init__(self) -> None:
        if (
            not isinstance(self.run_id, str)
            or not self.run_id
            or isinstance(self.seed, bool)
            or not isinstance(self.seed, int)
            or self.seed < 0
            or not isinstance(self.config_hash, str)
            or not self.config_hash
            or not isinstance(self.rate_card_hash, str)
            or not self.rate_card_hash
            or isinstance(self.schema_version, bool)
            or not isinstance(self.schema_version, int)
            or self.schema_version != 2
        ):
            raise TraceIOError("trace header: invalid field")

    def to_record(self) -> dict[str, object]:
        return {
            "run_id": self.run_id,
            "seed": self.seed,
            "config_hash": self.config_hash,
            "rate_card_hash": self.rate_card_hash,
            "schema_version": self.schema_version,
        }


def encode_event(sequence: int, event: dict[str, object]) -> bytes:
    """Encode one sequence-bearing event with the shared checksum codec."""
    if (
        isinstance(sequence, bool)
        or not isinstance(sequence, int)
        or sequence < 0
        or not isinstance(event, dict)
        or "sequence" in event
    ):
        raise TraceIOError("trace event: invalid or duplicate sequence")
    return encode_envelope("frugent.trace.event", 2, {"sequence": sequence, **event})


def decode_event(data: bytes | str) -> dict[str, object]:
    try:
        version, payload = decode_envelope(data, "frugent.trace.event")
    except ValueError as error:
        raise TraceIOError(f"trace event: {error}") from error
    if (
        version != 2
        or not isinstance(payload, dict)
        or not isinstance(payload.get("sequence"), int)
        or isinstance(payload.get("sequence"), bool)
        or payload["sequence"] < 0
    ):
        raise TraceIOError("trace event: unsupported version or payload")
    return payload


def export_trace(header: TraceHeader, events: tuple[dict[str, object], ...]) -> bytes:
    """Write header then ordered events as independently checksummed lines."""
    lines = [encode_envelope("frugent.trace.header", 2, header.to_record())]
    lines.extend(encode_event(index, event) for index, event in enumerate(events))
    return b"\n".join(lines) + b"\n"


def import_trace(data: bytes | str) -> tuple[TraceHeader, tuple[dict[str, object], ...]]:
    """Verify every line, schema, and contiguous sequence."""
    raw = data.encode() if isinstance(data, str) else data
    if not raw.endswith(b"\n") or not raw:
        raise TraceIOError("trace stream: expected complete newline-terminated data")
    lines = raw.splitlines()
    try:
        version, header_record = decode_envelope(lines[0], "frugent.trace.header")
    except ValueError as error:
        raise TraceIOError(f"trace header: {error}") from error
    if version != 2 or not isinstance(header_record, dict):
        raise TraceIOError("trace header: unsupported schema")
    header = _header_from_record(header_record)
    events = tuple(decode_event(line) for line in lines[1:])
    if tuple(event["sequence"] for event in events) != tuple(range(len(events))):
        raise TraceIOError("trace stream: event sequence is not contiguous")
    return header, events


def verify_trace(data: bytes | str) -> bool:
    """Return true only when the complete trace can be imported."""
    try:
        import_trace(data)
    except TraceIOError:
        return False
    return True


def _header_from_record(record: dict[str, object]) -> TraceHeader:
    expected = {"run_id", "seed", "config_hash", "rate_card_hash", "schema_version"}
    if set(record) != expected:
        raise TraceIOError("trace header record: unexpected fields")
    run_id, seed = record["run_id"], record["seed"]
    config_hash, rate_hash = record["config_hash"], record["rate_card_hash"]
    schema_version = record["schema_version"]
    if not isinstance(run_id, str) or not isinstance(seed, int) or isinstance(seed, bool):
        raise TraceIOError("trace header record: invalid run id or seed")
    if not isinstance(config_hash, str) or not isinstance(rate_hash, str):
        raise TraceIOError("trace header record: invalid fingerprints")
    if (
        isinstance(schema_version, bool)
        or not isinstance(schema_version, int)
        or schema_version != 2
    ):
        raise TraceIOError("trace header record: unsupported schema version")
    return TraceHeader(run_id, seed, config_hash, rate_hash, schema_version)


def migrate_header(record: dict[str, object]) -> dict[str, object]:
    """Migrate v1 run/config/rate fields to explicit v2 names."""
    version = record.get("schema_version")
    if isinstance(version, bool):
        raise TraceIOError("trace migration: unsupported legacy header")
    if version == 2:
        return _header_from_record(record).to_record()
    expected = {"schema_version", "run", "seed", "config", "rate"}
    if version != 1 or set(record) != expected:
        raise TraceIOError("trace migration: unsupported legacy header")
    seed = record["seed"]
    if not isinstance(seed, int) or isinstance(seed, bool):
        raise TraceIOError("trace migration: seed must be an integer")
    return TraceHeader(
        str(record["run"]), seed, str(record["config"]), str(record["rate"])
    ).to_record()


def trace_fingerprint(data: bytes | str) -> str:
    """Hash exact verified bytes for report metadata."""
    import hashlib

    raw = data.encode() if isinstance(data, str) else data
    if not verify_trace(raw):
        raise TraceIOError("trace fingerprint: stream is invalid")
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def event_diff(left: bytes, right: bytes) -> tuple[dict[str, object], ...]:
    """Return paired sequence records whose logical payload changed."""
    _, left_events = import_trace(left)
    _, right_events = import_trace(right)
    return _event_changes(left_events, right_events)


def _event_changes(
    left_events: tuple[dict[str, object], ...],
    right_events: tuple[dict[str, object], ...],
) -> tuple[dict[str, object], ...]:
    length = max(len(left_events), len(right_events))
    changes: list[dict[str, object]] = []
    for index in range(length):
        before = left_events[index] if index < len(left_events) else None
        after = right_events[index] if index < len(right_events) else None
        if before != after:
            changes.append({"sequence": index, "before": before, "after": after})
    return tuple(changes)


@dataclass(frozen=True, slots=True)
class TraceDiff:
    """Logical header and event changes between two verified streams."""

    header: tuple[TraceHeader, TraceHeader] | None
    events: tuple[dict[str, object], ...]

    @property
    def changed(self) -> bool:
        return self.header is not None or bool(self.events)


def trace_diff(left: bytes, right: bytes) -> TraceDiff:
    """Compare complete traces, including reproducibility metadata."""
    left_header, left_events = import_trace(left)
    right_header, right_events = import_trace(right)
    header_change = None if left_header == right_header else (left_header, right_header)
    return TraceDiff(header_change, _event_changes(left_events, right_events))
