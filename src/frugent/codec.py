"""Canonical codecs for deterministic persisted artifacts."""

from __future__ import annotations

import hashlib
import json
import math
from typing import Any


class CodecError(ValueError):
    """Raised when a payload cannot be represented canonically."""


def _reject_non_finite(value: Any, path: str = "$") -> None:
    if isinstance(value, float) and not math.isfinite(value):
        raise CodecError(f"{path}: non-finite float is not canonical")
    if isinstance(value, dict):
        for key, child in value.items():
            if not isinstance(key, str):
                raise CodecError(f"{path}: object keys must be strings")
            _reject_non_finite(child, f"{path}.{key}")
    elif isinstance(value, (list, tuple)):
        for index, child in enumerate(value):
            _reject_non_finite(child, f"{path}[{index}]")


def canonical_json(value: Any) -> bytes:
    """Encode JSON with stable ordering and no insignificant whitespace."""
    _reject_non_finite(value)
    try:
        rendered = json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
    except (TypeError, ValueError) as error:
        raise CodecError(f"payload is not JSON-compatible: {error}") from error
    return rendered.encode("utf-8")


def payload_digest(value: Any) -> str:
    """Return a namespaced SHA-256 digest of the canonical bytes."""
    return "sha256:" + hashlib.sha256(canonical_json(value)).hexdigest()


def decode_json(payload: bytes | str) -> Any:
    """Decode a JSON document while rejecting duplicate keys and non-finite numbers."""

    def pairs(values: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in values:
            if key in result:
                raise CodecError(f"duplicate object key: {key}")
            result[key] = value
        return result

    def invalid_constant(value: str) -> None:
        raise CodecError(f"non-finite JSON constant: {value}")

    try:
        decoded = json.loads(payload, object_pairs_hook=pairs, parse_constant=invalid_constant)
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        raise CodecError(f"invalid JSON: {error}") from error
    _reject_non_finite(decoded)
    return decoded


def encode_envelope(schema: str, version: int, payload: Any) -> bytes:
    """Encode a versioned payload with a digest over its exact content."""
    if not schema or isinstance(version, bool) or version < 1:
        raise CodecError("envelope: schema must be non-empty and version must be positive")
    body = {"schema": schema, "version": version, "payload": payload}
    return canonical_json({**body, "checksum": payload_digest(body)})


def decode_envelope(data: bytes | str, expected_schema: str) -> tuple[int, Any]:
    """Verify and decode a versioned checksum envelope."""
    decoded = decode_json(data)
    if not isinstance(decoded, dict) or set(decoded) != {
        "schema",
        "version",
        "payload",
        "checksum",
    }:
        raise CodecError("envelope: unexpected shape")
    if decoded["schema"] != expected_schema:
        raise CodecError(f"envelope: expected schema {expected_schema!r}")
    version = decoded["version"]
    checksum = decoded["checksum"]
    if isinstance(version, bool) or not isinstance(version, int) or version < 1:
        raise CodecError("envelope.version: expected a positive integer")
    body = {"schema": decoded["schema"], "version": version, "payload": decoded["payload"]}
    if not isinstance(checksum, str) or checksum != payload_digest(body):
        raise CodecError("envelope: checksum mismatch")
    return version, decoded["payload"]


def encode_jsonl(records: list[Any]) -> bytes:
    """Encode records as independently checksummed canonical JSON lines."""
    lines = [encode_envelope("frugent.jsonl.record", 1, record) for record in records]
    return b"\n".join(lines) + (b"\n" if lines else b"")


def decode_jsonl(data: bytes | str) -> list[Any]:
    """Decode complete nonblank JSON lines and verify each checksum."""
    raw = data.encode("utf-8") if isinstance(data, str) else data
    if raw and not raw.endswith(b"\n"):
        raise CodecError("jsonl: final record is incomplete")
    result: list[Any] = []
    for line_number, line in enumerate(raw.splitlines(), start=1):
        if not line.strip():
            raise CodecError(f"jsonl: blank line at {line_number}")
        try:
            _, payload = decode_envelope(line, "frugent.jsonl.record")
        except CodecError as error:
            raise CodecError(f"jsonl line {line_number}: {error}") from error
        result.append(payload)
    return result
