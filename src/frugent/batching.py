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
