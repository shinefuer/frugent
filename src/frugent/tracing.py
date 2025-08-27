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


def validate_forest(spans: tuple[Span, ...]) -> None:
    """Check unique ids, parent existence, containment, and acyclicity."""
    by_id = {span.span_id: span for span in spans}
    if len(by_id) != len(spans):
        raise TraceError("span forest: duplicate span id")
    for span in spans:
        if span.parent_id is None:
            continue
        parent = by_id.get(span.parent_id)
        if parent is None:
            raise TraceError("span forest: missing parent")
        if not parent.start_us <= span.start_us <= span.end_us <= parent.end_us:
            raise TraceError("span forest: child is outside parent timing")
        seen = {span.span_id}
        cursor = parent
        while cursor.parent_id is not None:
            if cursor.span_id in seen:
                raise TraceError("span forest: parent cycle")
            seen.add(cursor.span_id)
            cursor = by_id.get(cursor.parent_id)  # type: ignore[assignment]
            if cursor is None:
                raise TraceError("span forest: missing parent")


def child_index(spans: tuple[Span, ...]) -> dict[str | None, tuple[Span, ...]]:
    """Group direct children by parent and sort by time then id."""
    validate_forest(spans)
    groups: dict[str | None, list[Span]] = {}
    for span in spans:
        groups.setdefault(span.parent_id, []).append(span)
    return {
        parent: tuple(sorted(children, key=lambda span: (span.start_us, span.span_id)))
        for parent, children in groups.items()
    }


def preorder(spans: tuple[Span, ...]) -> tuple[Span, ...]:
    """Return roots and descendants in stable depth-first order."""
    index = child_index(spans)
    ordered: list[Span] = []

    def visit(span: Span) -> None:
        ordered.append(span)
        for child in index.get(span.span_id, ()):
            visit(child)

    for root in index.get(None, ()):
        visit(root)
    return tuple(ordered)


def exclusive_duration(span: Span, spans: tuple[Span, ...]) -> int:
    """Subtract direct-child wall time, rejecting overlapping siblings."""
    children = child_index(spans).get(span.span_id, ())
    previous_end = span.start_us
    total = 0
    for child in children:
        if child.start_us < previous_end:
            raise TraceError("exclusive duration: sibling spans overlap")
        total += child.duration_us
        previous_end = child.end_us
    return span.duration_us - total


def span_id(seed: int, sequence: int, name: str) -> str:
    """Create a compact content-derived id without wall-clock entropy."""
    from frugent.codec import payload_digest

    if seed < 0 or sequence < 0 or not name:
        raise TraceError("span id: invalid seed, sequence, or name")
    return payload_digest({"seed": seed, "sequence": sequence, "name": name})[7:23]


def span_record(span: Span) -> dict[str, object]:
    return {
        "span_id": span.span_id,
        "parent_id": span.parent_id,
        "name": span.name,
        "start_us": span.start_us,
        "end_us": span.end_us,
        "attributes": dict(span.attributes),
    }


def span_from_record(record: dict[str, object]) -> Span:
    expected = {"span_id", "parent_id", "name", "start_us", "end_us", "attributes"}
    if set(record) != expected or not isinstance(record["attributes"], dict):
        raise TraceError("span record: unexpected shape")
    attributes = record["attributes"]
    if not all(
        isinstance(key, str) and isinstance(value, str) for key, value in attributes.items()
    ):
        raise TraceError("span record: attributes must be strings")
    try:
        return Span(
            record["span_id"],
            record["name"],
            record["start_us"],
            record["end_us"],
            record["parent_id"],
            tuple(sorted(attributes.items())),
        )
    except TypeError as error:
        raise TraceError(f"span record: invalid scalar type: {error}") from error


def span_diff(left: tuple[Span, ...], right: tuple[Span, ...]) -> dict[str, tuple[str, ...]]:
    """Compare logical span records without depending on input order."""
    left_map, right_map = (
        {span.span_id: span for span in left},
        {span.span_id: span for span in right},
    )
    return {
        "added": tuple(sorted(right_map.keys() - left_map.keys())),
        "removed": tuple(sorted(left_map.keys() - right_map.keys())),
        "changed": tuple(
            sorted(
                key for key in left_map.keys() & right_map.keys() if left_map[key] != right_map[key]
            )
        ),
    }
