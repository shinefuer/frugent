"""Behavior and invariant tests."""

from __future__ import annotations

import pytest

import frugent.pipeline as m


def test_pipeline_config_enforces_offline_run_limits() -> None:
    assert m.PipelineConfig(seed=3, tasks=4).tasks == 4
    with pytest.raises(m.PipelineError, match="positive"):
        m.PipelineConfig(tasks=0)


def test_policy_run_rejects_impossible_cache_measurements() -> None:
    with pytest.raises(m.PipelineError, match="inconsistent"):
        m.PolicyRun("x", 1, 4, 5, 2, (1,))


def test_policy_run_accepts_empty_latency_only_for_empty_completion() -> None:
    empty = m.PolicyRun("empty", 0, 0, 0, 0, ())
    assert empty.completed == 0


def test_baseline_measures_every_generated_task() -> None:
    run = m.baseline_run(m.PipelineConfig(seed=4, tasks=7))
    assert run.completed == 7
    assert run.prompt_tokens > 0 and run.cached_tokens == 0
    assert len(run.latencies_ms) == 7


def test_stack_accounts_only_observed_cache_hits() -> None:
    run = m.stack_run(m.PipelineConfig(seed=8, tasks=20))
    assert 0 < run.cached_tokens < run.prompt_tokens
    assert run.completed == 20


def test_comparison_uses_identical_completion_denominator() -> None:
    comparison = m.compare(m.PipelineConfig(seed=14, tasks=16))
    assert comparison.baseline.completed == comparison.stack.completed == 16
    assert 0 < comparison.token_savings < 1
    assert comparison.cost_savings_micros > 0


def test_stack_never_exceeds_generated_task_count() -> None:
    for seed in range(12):
        config = m.PipelineConfig(seed=seed, tasks=5)
        assert m.stack_run(config).completed <= config.tasks


def test_report_rows_use_net_prompt_tokens_and_measured_latency() -> None:
    comparison = m.compare(m.PipelineConfig(seed=2, tasks=9))
    baseline, stack = m.report_rows(comparison)
    assert baseline.tokens == comparison.baseline.prompt_tokens
    assert stack.tokens == comparison.stack.prompt_tokens - comparison.stack.cached_tokens
    assert stack.p95_ms >= stack.p50_ms
