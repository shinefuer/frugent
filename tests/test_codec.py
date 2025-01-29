"""Canonical serialization and checksum tests."""

from __future__ import annotations

from frugent.codec import canonical_json, payload_digest


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
