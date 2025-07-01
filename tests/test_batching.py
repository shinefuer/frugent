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
