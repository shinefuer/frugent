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


def test_action_and_event_records_reject_ambiguous_runtime_values() -> None:
    with pytest.raises(m.RuntimeError, match="payload must be bytes"):
        m.Action("tool", "x")  # type: ignore[arg-type]
    with pytest.raises(m.RuntimeError, match="loop event"):
        m.LoopEvent(True, "act", "00")
    with pytest.raises(m.RuntimeError, match="canonical hex"):
        m.LoopEvent(0, "observe", "0A")


def test_scripted_planner_yields_planted_order() -> None:
    planner = m.ScriptedPlanner((m.Action("tool", b"read"), m.Action("answer", b"done")))
    assert planner.plan(()) == m.Action("tool", b"read")
    assert planner.plan((b"observation",)) == m.Action("answer", b"done")


def test_scripted_planner_exhaustion_is_explicit() -> None:
    planner = m.ScriptedPlanner(())
    with pytest.raises(m.RuntimeError, match="no action remains"):
        planner.plan(())


def test_scripted_planner_validates_actions_and_observations() -> None:
    with pytest.raises(m.RuntimeError, match="action tuple"):
        m.ScriptedPlanner(("tool",))  # type: ignore[arg-type]
    planner = m.ScriptedPlanner((m.Action("answer", b"ok"),))
    with pytest.raises(m.RuntimeError, match="byte tuple"):
        planner.plan(("observation",))  # type: ignore[arg-type]


def test_action_adapter_record_roundtrips_binary_payload() -> None:
    action = m.Action("tool", b"\x00read\xff")
    assert m.action_from_record(m.action_record(action)) == action
    with pytest.raises(m.RuntimeError, match="kind and payload"):
        m.action_from_record(b"answer")


def test_adapter_planner_drives_the_same_plan_act_observe_loop() -> None:
    from frugent.adapters import AdapterRequest, ScriptedAdapter

    requests = (AdapterRequest("1", b"plan", 4), AdapterRequest("2", b"finish", 4))
    adapter = ScriptedAdapter(
        "scripted-small",
        {b"plan": m.action_record(m.Action("tool", b"read")), b"finish": b"answer\0done"},
    )
    planner = m.AdapterPlanner(adapter, requests)
    events = m.run_loop(planner, lambda payload: b"observed:" + payload, 2)
    assert tuple(event.phase for event in events) == ("act", "observe", "act", "answer")
    assert m.terminal_outcome(events) == ("answer", b"done")
    assert tuple(response.request_id for response in planner.responses) == ("1", "2")


def test_adapter_planner_rejects_response_identity_drift() -> None:
    from frugent.adapters import AdapterRequest, AdapterResponse

    class WrongIdentityAdapter:
        def complete(self, request: AdapterRequest) -> AdapterResponse:
            return AdapterResponse("other", b"answer\0done", "mock", 1, 1)

    planner = m.AdapterPlanner(WrongIdentityAdapter(), (AdapterRequest("expected", b"p", 0),))
    with pytest.raises(m.RuntimeError, match="response id mismatch"):
        planner.plan(())


def test_loop_runs_plan_act_observe_to_answer() -> None:
    planner = m.ScriptedPlanner((m.Action("tool", b"read"), m.Action("answer", b"done")))
    events = m.run_loop(planner, lambda payload: b"obs:" + payload, 3)
    assert tuple(event.phase for event in events) == ("act", "observe", "act", "answer")
    assert bytes.fromhex(events[1].payload_hex) == b"obs:read"
    assert all(bytes.fromhex(event.payload_hex).hex() == event.payload_hex for event in events)


def test_loop_rejects_boolean_step_budget_before_planning() -> None:
    planner = m.ScriptedPlanner((m.Action("answer", b"ok"),))
    with pytest.raises(m.RuntimeError, match="positive steps"):
        m.run_loop(planner, lambda _: b"", True)
    assert planner.cursor == 0


def test_cancel_action_stops_before_tool_execution() -> None:
    called = False

    def tool(_: bytes) -> bytes:
        nonlocal called
        called = True
        return b"x"

    events = m.run_loop(m.ScriptedPlanner((m.Action("cancel", b"user"),)), tool, 2)
    assert m.cancelled(events)
    assert not called


def test_step_count_ignores_observations_and_terminal_event() -> None:
    events = m.run_loop(
        m.ScriptedPlanner((m.Action("tool", b"x"), m.Action("answer", b"y"))), lambda _: b"o", 2
    )
    assert m.step_count(events) == 2


def test_loop_raises_when_step_budget_exhausts() -> None:
    with pytest.raises(m.RuntimeError, match="step budget exhausted"):
        m.run_loop(m.ScriptedPlanner((m.Action("tool", b"x"),)), lambda _: b"o", 1)


@pytest.mark.parametrize("payload", [b"", b"text", b"\x00\xff", bytes(range(32))])
def test_loop_observation_roundtrips_binary_bytes(payload: bytes) -> None:
    events = m.run_loop(
        m.ScriptedPlanner((m.Action("tool", b"x"), m.Action("answer", b"ok"))), lambda _: payload, 2
    )
    observation = next(event for event in events if event.phase == "observe")
    assert bytes.fromhex(observation.payload_hex) == payload


def test_loop_event_records_have_contiguous_sequence() -> None:
    events = m.run_loop(m.ScriptedPlanner((m.Action("answer", b"ok"),)), lambda _: b"", 1)
    records = m.event_records(events)
    assert tuple(record["sequence"] for record in records) == tuple(range(len(records)))
    assert records[-1]["payload_hex"] == "6f6b"


def test_loop_trace_fingerprint_is_byte_deterministic() -> None:
    actions = (m.Action("tool", b"x"), m.Action("answer", b"done"))
    first = m.run_loop(m.ScriptedPlanner(actions), lambda _: b"obs", 3)
    second = m.run_loop(m.ScriptedPlanner(actions), lambda _: b"obs", 3)
    assert first == second
    assert m.trace_fingerprint(first) == m.trace_fingerprint(second)


@pytest.mark.parametrize("seed", range(12))
def test_same_seed_derived_actions_produce_identical_trace(seed: int) -> None:
    payload = seed.to_bytes(2, "big")
    actions = (m.Action("tool", payload), m.Action("answer", payload[::-1]))
    first = m.run_loop(m.ScriptedPlanner(actions), lambda value: value + b"!", 2)
    second = m.run_loop(m.ScriptedPlanner(actions), lambda value: value + b"!", 2)
    assert m.event_records(first) == m.event_records(second)


def test_terminal_outcome_decodes_answer_bytes() -> None:
    events = m.run_loop(m.ScriptedPlanner((m.Action("answer", b"\x00ok"),)), lambda _: b"", 1)
    assert m.terminal_outcome(events) == ("answer", b"\x00ok")


def test_terminal_outcome_rejects_incomplete_trace() -> None:
    with pytest.raises(m.RuntimeError, match="incomplete"):
        m.terminal_outcome((m.LoopEvent(0, "act", "00"),))


def test_loop_trace_bytes_repeat_for_many_seed_derived_payloads() -> None:
    for seed in range(100):
        payload = seed.to_bytes(2, "big")
        actions = (
            m.Action("tool", payload),
            m.Action("tool", payload[::-1]),
            m.Action("answer", b"done"),
        )
        left = m.run_loop(m.ScriptedPlanner(actions), lambda value: b"obs:" + value, 3)
        right = m.run_loop(m.ScriptedPlanner(actions), lambda value: b"obs:" + value, 3)
        assert m.event_records(left) == m.event_records(right)
        assert m.trace_fingerprint(left) == m.trace_fingerprint(right)
