"""Behavior and invariant tests."""

from __future__ import annotations

import pytest

import frugent.runtime as m


@pytest.mark.parametrize("kind", ["tool", "answer", "cancel"])
def test_action_accepts_protocol_kinds(kind: str) -> None:
    assert m.Action(kind, b"x").kind == kind


def test_action_rejects_unknown_kind() -> None:
    with pytest.raises(m.RuntimeError, match="unsupported kind"):
        m.Action("think", b"x")


def test_scripted_planner_yields_planted_order() -> None:
    planner = m.ScriptedPlanner((m.Action("tool", b"read"), m.Action("answer", b"done")))
    assert planner.plan(()) == m.Action("tool", b"read")
    assert planner.plan((b"observation",)) == m.Action("answer", b"done")
