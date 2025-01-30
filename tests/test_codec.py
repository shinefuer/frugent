"""Canonical serialization and checksum tests."""

from __future__ import annotations

import pytest

import frugent.codec as c
from frugent.codec import CodecError, canonical_json, decode_json, payload_digest


def test_canonical_json_ignores_mapping_insertion_order() -> None:
    left = {"模型": "tiny", "usage": {"output": 2, "input": 5}}
    right = {"usage": {"input": 5, "output": 2}, "模型": "tiny"}
    assert canonical_json(left) == canonical_json(right)
    assert (
        canonical_json(left)
        == b'{"usage":{"input":5,"output":2},"\xe6\xa8\xa1\xe5\x9e\x8b":"tiny"}'
    )


def test_payload_digest_is_namespaced_and_repeatable() -> None:
    first = payload_digest({"a": [1, 2, 3]})
    assert first == payload_digest({"a": [1, 2, 3]})
    assert first.startswith("sha256:")
    assert len(first) == len("sha256:") + 64


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_canonical_json_rejects_non_finite_root(value: float) -> None:
    with pytest.raises(CodecError, match="non-finite"):
        canonical_json(value)


@pytest.mark.parametrize(
    ("value", "path"),
    [
        ({"score": float("nan")}, r"\$.score"),
        ({"scores": [0.5, float("inf")]}, r"\$.scores\[1\]"),
        ([{"nested": float("-inf")}], r"\$\[0\].nested"),
    ],
)
def test_canonical_json_identifies_nested_non_finite_path(value: object, path: str) -> None:
    with pytest.raises(CodecError, match=path):
        canonical_json(value)


def test_canonical_json_rejects_non_string_object_keys() -> None:
    with pytest.raises(CodecError, match="keys must be strings"):
        canonical_json({1: "value"})


def test_canonical_json_rejects_unhandled_objects() -> None:
    with pytest.raises(CodecError, match="not JSON-compatible"):
        canonical_json({"value": object()})


def test_decode_json_inverts_canonical_encoding() -> None:
    value = {"seed": 7, "labels": ["easy", "hard"], "enabled": True}
    assert decode_json(canonical_json(value)) == value


@pytest.mark.parametrize("payload", [b"{", b"[] trailing", b'"\xff"'])
def test_decode_json_rejects_malformed_bytes(payload: bytes) -> None:
    with pytest.raises(CodecError, match="invalid JSON"):
        decode_json(payload)


@pytest.mark.parametrize(
    "payload",
    [
        '{"seed":1,"seed":2}',
        '{"outer":{"x":1,"x":2}}',
        '[{"kind":"a","kind":"b"}]',
    ],
)
def test_decode_json_never_silently_overwrites_duplicate_keys(payload: str) -> None:
    with pytest.raises(CodecError, match="duplicate object key"):
        decode_json(payload)


@pytest.mark.parametrize("constant", ["NaN", "Infinity", "-Infinity"])
def test_decode_json_rejects_non_finite_constants(constant: str) -> None:
    with pytest.raises(CodecError, match="non-finite JSON constant"):
        decode_json(f'{{"value":{constant}}}')


def test_checksum_envelope_roundtrip() -> None:
    encoded = c.encode_envelope("frugent.trace", 2, {"events": [1, 2]})
    assert c.decode_envelope(encoded, "frugent.trace") == (2, {"events": [1, 2]})


def test_checksum_envelope_rejects_payload_tampering() -> None:
    encoded = c.encode_envelope("frugent.trace", 1, {"cost": 10})
    tampered = encoded.replace(b'"cost":10', b'"cost":11')
    with pytest.raises(CodecError, match="checksum mismatch"):
        c.decode_envelope(tampered, "frugent.trace")


@pytest.mark.parametrize(
    ("schema", "version"), [("", 1), ("trace", 0), ("trace", -1), ("trace", True)]
)
def test_encode_envelope_requires_schema_identity(schema: str, version: int) -> None:
    with pytest.raises(CodecError, match="envelope"):
        c.encode_envelope(schema, version, {})


def test_decode_envelope_rejects_wrong_schema() -> None:
    encoded = c.encode_envelope("frugent.config", 1, {})
    with pytest.raises(CodecError, match="expected schema"):
        c.decode_envelope(encoded, "frugent.trace")


def test_decode_envelope_rejects_extra_fields_even_with_valid_json() -> None:
    with pytest.raises(CodecError, match="unexpected shape"):
        c.decode_envelope(b'{"schema":"x","version":1,"payload":{},"checksum":"x","extra":0}', "x")
