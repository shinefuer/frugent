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
            not self.run_id
            or self.seed < 0
            or not self.config_hash
            or not self.rate_card_hash
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
    if sequence < 0 or "sequence" in event:
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
    try:
        header = TraceHeader(**header_record)
    except TypeError as error:
        raise TraceIOError(f"trace header: invalid shape: {error}") from error
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


def migrate_header(record: dict[str, object]) -> dict[str, object]:
    """Migrate v1 run/config/rate fields to explicit v2 names."""
    version = record.get("schema_version")
    if version == 2:
        return TraceHeader(**record).to_record()
    expected = {"schema_version", "run", "seed", "config", "rate"}
    if version != 1 or set(record) != expected:
        raise TraceIOError("trace migration: unsupported legacy header")
    return TraceHeader(
        str(record["run"]), int(record["seed"]), str(record["config"]), str(record["rate"])
    ).to_record()


def trace_fingerprint(data: bytes | str) -> str:
    """Hash exact verified bytes for report metadata."""
    import hashlib

    raw = data.encode() if isinstance(data, str) else data
    if not verify_trace(raw):
        raise TraceIOError("trace fingerprint: stream is invalid")
    return "sha256:" + hashlib.sha256(raw).hexdigest()
