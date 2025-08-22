"""Deterministic span trees for offline runtime cost traces."""

from __future__ import annotations

from dataclasses import dataclass, field


class TraceError(ValueError):
    """Raised when trace structure or timing is invalid."""


@dataclass(frozen=True, slots=True)
class Span:
    span_id: str
    name: str
    start_us: int
    end_us: int
    parent_id: str | None = None
    attributes: tuple[tuple[str, str], ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not self.span_id or not self.name or self.start_us < 0 or self.end_us < self.start_us:
            raise TraceError("span: invalid identity, name, or timing")
        if tuple(sorted(self.attributes)) != self.attributes or len(dict(self.attributes)) != len(
            self.attributes
        ):
            raise TraceError("span: attributes must have unique sorted keys")

    @property
    def duration_us(self) -> int:
        return self.end_us - self.start_us
