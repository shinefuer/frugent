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


@pytest.mark.parametrize("size", [0, 1, 2, 10, 50])
def test_coalescing_preserves_request_identity_exactly_once(size: int) -> None:
    requests = tuple(m.BatchRequest(str(index), bytes([index % 4]), index) for index in range(size))
    flattened = tuple(request.request_id for group in m.coalesce(requests) for request in group)
    assert sorted(flattened) == sorted(request.request_id for request in requests)
    assert len(flattened) == len(set(flattened))


def test_fan_out_preserves_response_bytes_per_subscriber() -> None:
    group = (m.BatchRequest("1", b"x", 0), m.BatchRequest("2", b"x", 1))
    response = b"\x00result\xff"
    assert m.fan_out(group, response) == {"1": response, "2": response}


def test_fan_out_rejects_nonequivalent_group() -> None:
    with pytest.raises(m.BatchingError, match="not equivalent"):
        m.fan_out((m.BatchRequest("1", b"x", 0), m.BatchRequest("2", b"y", 0)), b"r")
