"""Golden public facade and import behavior."""

from __future__ import annotations

import frugent


def test_configuration_facade_roundtrips_without_private_imports() -> None:
    config = frugent.RuntimeConfig(seed=4)
    assert frugent.load_config(frugent.dump_config(config)) == config
    assert issubclass(frugent.ConfigError, ValueError)


def test_rate_card_facade_is_explicitly_fictional() -> None:
    card = frugent.demo_rate_card()
    assert "fictional" in card.label
    assert frugent.rate_card_fingerprint(card).startswith("sha256:")


def test_record_types_are_available_from_one_namespace() -> None:
    message = frugent.Message("user", "hello")
    request = frugent.Request("r", (message,), 2)
    assert request.messages == (message,)
    assert frugent.Usage(2, 1).total_tokens == 3


def test_context_facade_preserves_append_only_diffs() -> None:
    base = frugent.MessageStore()
    target = base.append(frugent.Message("user", "x"))
    assert frugent.apply_diff(base, frugent.diff(base, target)) == target


def test_prompt_cache_facade_replays_exact_hits() -> None:
    outcomes = frugent.replay_trace((("x", 2, 0), ("x", 2, 1)), frugent.CachePolicy(4, 10))
    assert outcomes == ((False, 0), (True, 2))


def test_semantic_facade_keeps_fuzzy_discovery_separate() -> None:
    key = frugent.exact_key(" Hello ", "Tool", {"x": 1})
    entry = frugent.SemanticEntry(key, b"ok", 0)
    assert frugent.exact_lookup((entry,), key, 1, 10) == b"ok"
    assert frugent.exact_lookup((entry,), key + "x", 1, 10) is None


def test_mechanics_facade_preserves_response_bytes() -> None:
    requests = (frugent.BatchRequest("a", b"x", 0), frugent.BatchRequest("b", b"x", 1))
    assert frugent.execute_single_flights(requests, lambda payload: payload + b"!") == {
        "a": b"x!",
        "b": b"x!",
    }


def test_cascade_facade_exposes_quality_floor_selection() -> None:
    profiles = (frugent.ModelProfile("a", 1, 1, (0.5,)), frugent.ModelProfile("b", 2, 1, (0.9,)))
    assert frugent.cheapest_profile_at_floor(profiles, (1.0,), 0.8).name == "b"


def test_budget_facade_keeps_reservations_bounded() -> None:
    budget = frugent.Budget(10, 20)
    assert frugent.can_admit(budget, 10, 20)
    assert frugent.reserve(budget, 10, 20).remaining_tokens == 0


def test_trace_facade_roundtrips_checksummed_bytes() -> None:
    header = frugent.TraceHeader("r", 1, "c", "rate")
    encoded = frugent.export_trace(header, ({"kind": "x"},))
    assert frugent.import_trace(encoded)[0] == header
    assert frugent.trace_fingerprint(encoded).startswith("sha256:")


def test_sandbox_facade_returns_precise_denials() -> None:
    policy = frugent.SandboxPolicy((("ok",),), (), frozenset())
    decision = frugent.decide(policy, ("no",))
    assert not decision.allowed and "allowlisted" in decision.reason


def test_runtime_facade_executes_scripted_plan_observe() -> None:
    planner = frugent.ScriptedPlanner(
        (frugent.Action("tool", b"x"), frugent.Action("answer", b"ok"))
    )
    events = frugent.run_loop(planner, lambda payload: payload.upper(), 2)
    assert events[-1].phase == "answer"


def test_pipeline_facade_runs_without_external_dependencies() -> None:
    artifacts = frugent.run_pipeline(frugent.PipelineConfig(seed=2, tasks=3))
    assert artifacts.comparison.stack.completed == 3
    assert "fictional rate card" in artifacts.html


def test_public_symbol_inventory_is_sorted_unique_and_real() -> None:
    assert frugent.__all__ == sorted(set(frugent.__all__))
    assert len(frugent.__all__) >= 75
    assert all(hasattr(frugent, name) for name in frugent.__all__)
