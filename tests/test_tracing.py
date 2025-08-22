"""Behavior and invariant tests."""

from __future__ import annotations

import pytest

import frugent.tracing as m


def test_span_duration_uses_half_open_timestamps() -> None:
    span = m.Span("s", "route", 10, 17, attributes=(("model", "small"),))
    assert span.duration_us == 7


@pytest.mark.parametrize(
    "values", [("", "n", 0, 0), ("s", "", 0, 0), ("s", "n", -1, 0), ("s", "n", 2, 1)]
)
def test_span_rejects_invalid_identity_or_timing(values: tuple[object, ...]) -> None:
    with pytest.raises(m.TraceError, match="span"):
        m.Span(*values)  # type: ignore[arg-type]
