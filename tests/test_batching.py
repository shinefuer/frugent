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


def test_micro_batches_honor_window_and_size() -> None:
    requests = tuple(
        m.BatchRequest(str(index), bytes([index]), arrival)
        for index, arrival in enumerate((0, 2, 4, 9, 10))
    )
    assert tuple(len(batch) for batch in m.micro_batches(requests, window_ms=5, max_size=2)) == (
        2,
        2,
        1,
    )


def test_micro_batches_reject_unsorted_arrivals() -> None:
    with pytest.raises(m.BatchingError, match="arrival order"):
        m.micro_batches(
            (m.BatchRequest("a", b"x", 2), m.BatchRequest("b", b"y", 1)), window_ms=1, max_size=2
        )


def test_wait_times_preserve_subscriber_order() -> None:
    batch = (m.BatchRequest("a", b"x", 2), m.BatchRequest("b", b"y", 5))
    assert m.wait_times(batch, 7) == (5, 2)


def test_wait_times_reject_early_dispatch() -> None:
    with pytest.raises(m.BatchingError, match="precedes arrival"):
        m.wait_times((m.BatchRequest("a", b"x", 3),), 2)


@pytest.mark.parametrize("window", [0, 1, 5, 20])
def test_each_micro_batch_stays_inside_first_arrival_window(window: int) -> None:
    requests = tuple(m.BatchRequest(str(index), b"x", index * 2) for index in range(20))
    for batch in m.micro_batches(requests, window_ms=window, max_size=7):
        assert batch[-1].arrival_ms - batch[0].arrival_ms <= window
        assert len(batch) <= 7
