"""Canonical serialization and checksum tests."""

from __future__ import annotations

import pytest

from frugent.codec import CodecError, canonical_json, payload_digest


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
