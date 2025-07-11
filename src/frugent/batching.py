"""Request equivalence, single-flight fan-out, and deterministic micro-batches."""

from __future__ import annotations

from dataclasses import dataclass

from frugent.codec import payload_digest


class BatchingError(ValueError):
    """Raised for malformed batching inputs or schedules."""


@dataclass(frozen=True, slots=True)
class BatchRequest:
    request_id: str
    payload: bytes
    arrival_ms: int

    def __post_init__(self) -> None:
        if not self.request_id or self.arrival_ms < 0:
            raise BatchingError("batch request: invalid identity or arrival")

    @property
    def equivalence_key(self) -> str:
        return payload_digest({"payload_hex": self.payload.hex()})


def coalesce(requests: tuple[BatchRequest, ...]) -> tuple[tuple[BatchRequest, ...], ...]:
    """Group exact payload equivalents in first-arrival key order."""
    groups: dict[str, list[BatchRequest]] = {}
    order: list[str] = []
    for request in requests:
        key = request.equivalence_key
        if key not in groups:
            groups[key] = []
            order.append(key)
        groups[key].append(request)
    return tuple(tuple(groups[key]) for key in order)


def fan_out(group: tuple[BatchRequest, ...], response: bytes) -> dict[str, bytes]:
    """Give every subscriber the exact same immutable response bytes."""
    if not group:
        raise BatchingError("fan out: expected subscribers")
    if len({request.equivalence_key for request in group}) != 1:
        raise BatchingError("fan out: subscribers are not equivalent")
    if len({request.request_id for request in group}) != len(group):
        raise BatchingError("fan out: duplicate request id")
    return {request.request_id: response for request in group}


def micro_batches(
    requests: tuple[BatchRequest, ...], *, window_ms: int, max_size: int
) -> tuple[tuple[BatchRequest, ...], ...]:
    """Batch ordered arrivals without exceeding size or first-item wait window."""
    if (
        window_ms < 0
        or max_size <= 0
        or tuple(sorted(r.arrival_ms for r in requests)) != tuple(r.arrival_ms for r in requests)
    ):
        raise BatchingError("micro batch: invalid window, size, or arrival order")
    batches: list[list[BatchRequest]] = []
    for request in requests:
        if (
            not batches
            or len(batches[-1]) >= max_size
            or request.arrival_ms - batches[-1][0].arrival_ms > window_ms
        ):
            batches.append([request])
        else:
            batches[-1].append(request)
    return tuple(tuple(batch) for batch in batches)


def wait_times(batch: tuple[BatchRequest, ...], dispatch_ms: int) -> tuple[int, ...]:
    """Return non-negative wait per subscriber in batch order."""
    if any(dispatch_ms < request.arrival_ms for request in batch):
        raise BatchingError("batch wait: dispatch precedes arrival")
    return tuple(dispatch_ms - request.arrival_ms for request in batch)
