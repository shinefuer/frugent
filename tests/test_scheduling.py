"""Behavior and invariant tests."""

from __future__ import annotations

import pytest

import frugent.scheduling as m


def test_task_keeps_integer_resource_estimates() -> None:
    assert m.Task("t", 2, 10, 30).cost_micros == 30


@pytest.mark.parametrize("values", [("", 0, 0, 0), ("t", -1, 0, 0), ("t", 1, -1, 0)])
def test_task_rejects_invalid_state(values: tuple[object, ...]) -> None:
    with pytest.raises(m.SchedulingError, match="scheduled task"):
        m.Task(*values)  # type: ignore[arg-type]
