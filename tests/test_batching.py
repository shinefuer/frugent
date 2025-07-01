"""Behavior and invariant tests."""

from __future__ import annotations

import pytest

import frugent.batching as m


def test_equivalence_key_uses_exact_payload_bytes() -> None:
    left = m.BatchRequest("a", b"same", 0)
    right = m.BatchRequest("b", b"same", 9)
    changed = m.BatchRequest("c", b"Same", 0)
    assert left.equivalence_key == right.equivalence_key
    assert left.equivalence_key != changed.equivalence_key


def test_batch_request_requires_identity() -> None:
    with pytest.raises(m.BatchingError, match="batch request"):
        m.BatchRequest("", b"x", 0)


def test_coalesce_groups_only_byte_equivalent_payloads() -> None:
    requests = (
        m.BatchRequest("1", b"a", 0),
        m.BatchRequest("2", b"b", 1),
        m.BatchRequest("3", b"a", 2),
    )
    groups = m.coalesce(requests)
    assert tuple(tuple(request.request_id for request in group) for group in groups) == (
        ("1", "3"),
        ("2",),
    )
