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


def test_scripted_planner_exhaustion_is_explicit() -> None:
    planner = m.ScriptedPlanner(())
    with pytest.raises(m.RuntimeError, match="no action remains"):
        planner.plan(())


def test_loop_runs_plan_act_observe_to_answer() -> None:
    planner = m.ScriptedPlanner((m.Action("tool", b"read"), m.Action("answer", b"done")))
    events = m.run_loop(planner, lambda payload: b"obs:" + payload, 3)
    assert tuple(event.phase for event in events) == ("act", "observe", "act", "answer")
    assert bytes.fromhex(events[1].payload_hex) == b"obs:read"
