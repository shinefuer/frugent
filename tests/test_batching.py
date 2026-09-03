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


def test_batch_request_rejects_ambiguous_payload_and_arrival_types() -> None:
    with pytest.raises(m.BatchingError, match="batch request"):
        m.BatchRequest("r", "x", 0)  # type: ignore[arg-type]
    with pytest.raises(m.BatchingError, match="batch request"):
        m.BatchRequest("r", b"x", True)


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


def test_batch_metrics_separate_dedup_and_batching() -> None:
    requests = (
        m.BatchRequest("1", b"x", 0),
        m.BatchRequest("2", b"x", 0),
        m.BatchRequest("3", b"y", 0),
    )
    result = m.batch_metrics(requests, (requests,))
    assert result == m.BatchMetrics(3, 2, 1)
    assert result.dedup_ratio == 0.333333
    assert result.mean_batch_size == 2.0


def test_batch_metrics_require_a_complete_ordered_partition() -> None:
    requests = (m.BatchRequest("1", b"x", 0), m.BatchRequest("2", b"y", 1))
    with pytest.raises(m.BatchingError, match="exactly partition"):
        m.batch_metrics(requests, ((requests[0],),))
    with pytest.raises(m.BatchingError, match="exactly partition"):
        m.batch_metrics(requests, ((requests[1], requests[0]),))
    with pytest.raises(m.BatchingError, match="exactly partition"):
        m.batch_metrics(requests, (requests, ()))


def test_single_flight_executes_once_per_equivalent_payload() -> None:
    calls: list[bytes] = []

    def execute(payload: bytes) -> bytes:
        calls.append(payload)
        return payload.upper()

    requests = (
        m.BatchRequest("1", b"x", 0),
        m.BatchRequest("2", b"x", 1),
        m.BatchRequest("3", b"y", 2),
    )
    assert m.execute_single_flights(requests, execute) == {"1": b"X", "2": b"X", "3": b"Y"}
    assert calls == [b"x", b"y"]


def test_batching_rejects_duplicate_subscriber_id_before_execution() -> None:
    requests = (m.BatchRequest("same", b"x", 0), m.BatchRequest("same", b"y", 1))
    calls: list[bytes] = []
    with pytest.raises(m.BatchingError, match="duplicate request id"):
        m.execute_single_flights(requests, lambda payload: calls.append(payload) or payload)
    assert calls == []


@pytest.mark.parametrize("payload", [b"", b"text", b"\x00\xff", bytes(range(32))])
def test_every_equivalent_subscriber_observes_identical_bytes(payload: bytes) -> None:
    requests = tuple(m.BatchRequest(str(index), payload, index) for index in range(8))
    response = payload[::-1]
    results = m.execute_single_flights(requests, lambda _: response)
    assert tuple(results.values()) == (response,) * len(requests)


def test_batch_completion_simulation_amortizes_service() -> None:
    requests = tuple(m.BatchRequest(str(index), b"x", index) for index in range(4))
    batches = m.micro_batches(requests, window_ms=2, max_size=3)
    assert m.simulated_completion_times(batches, 5) == {"0": 7, "1": 7, "2": 7, "3": 12}


def test_coalescing_is_a_stable_complete_partition() -> None:
    import random

    generator = random.Random(18)
    requests = tuple(
        m.BatchRequest(f"r{index}", bytes([generator.randrange(10)]), index) for index in range(300)
    )
    groups = m.coalesce(requests)
    assert tuple(request for group in groups for request in group) != requests
    assert {request.request_id for group in groups for request in group} == {
        request.request_id for request in requests
    }
    assert sum(len(group) for group in groups) == len(requests)
    assert all(len({request.equivalence_key for request in group}) == 1 for group in groups)


def test_single_flight_fanout_is_byte_identical_for_every_subscriber() -> None:
    payloads = tuple(bytes(range(length)) for length in range(1, 40))
    requests = tuple(
        m.BatchRequest(f"{index}-{copy}", payload, index)
        for index, payload in enumerate(payloads)
        for copy in range(4)
    )
    calls: list[bytes] = []

    def execute(payload: bytes) -> bytes:
        calls.append(payload)
        return b"\x00" + payload[::-1] + b"\xff"

    responses = m.execute_single_flights(requests, execute)
    assert len(calls) == len(payloads)
    assert all(
        responses[request.request_id] == b"\x00" + request.payload[::-1] + b"\xff"
        for request in requests
    )


def test_random_micro_batches_respect_size_window_and_order() -> None:
    import random

    generator = random.Random(82)
    arrivals = tuple(sorted(generator.randrange(1000) for _ in range(400)))
    requests = tuple(
        m.BatchRequest(str(index), b"x", arrival) for index, arrival in enumerate(arrivals)
    )
    batches = m.micro_batches(requests, window_ms=7, max_size=9)
    assert tuple(request for batch in batches for request in batch) == requests
    assert all(1 <= len(batch) <= 9 for batch in batches)
    assert all(batch[-1].arrival_ms - batch[0].arrival_ms <= 7 for batch in batches)
