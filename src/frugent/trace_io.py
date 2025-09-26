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
