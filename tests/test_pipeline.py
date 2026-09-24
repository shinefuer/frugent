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


def test_per_task_measurements_conserve_policy_rollups() -> None:
    config = m.PipelineConfig(seed=4, tasks=7)
    baseline = m.baseline_measurements(config)
    stack = m.stack_measurements(config)
    assert tuple(item.task_id for item in baseline) == tuple(item.task_id for item in stack)
    assert len(set(item.task_id for item in stack)) == config.tasks
    assert sum(item.prompt_tokens for item in baseline) == m.baseline_run(config).prompt_tokens
    assert sum(item.cached_tokens for item in stack) == m.stack_run(config).cached_tokens
    assert sum(item.cost_micros for item in stack) == m.stack_run(config).cost_micros


def test_task_measurement_counts_prompt_and_completion_budget() -> None:
    measured = m.TaskMeasurement("t", 10, 4, 3, 8, 2)
    assert measured.total_tokens == 14
    with pytest.raises(m.PipelineError, match="task measurement"):
        m.TaskMeasurement("t", 2, 1, 3, 4, 5)


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


def test_stack_admits_a_deterministic_partial_prefix_under_tight_budgets() -> None:
    base = m.PipelineConfig(seed=3, tasks=8)
    first = m.stack_measurements(base)[0]
    config = m.PipelineConfig(
        seed=3,
        tasks=8,
        token_budget=first.total_tokens,
        cost_budget_micros=first.cost_micros,
    )
    admitted = m.admit_measurements(
        m.stack_measurements(config), config.token_budget, config.cost_budget_micros
    )
    run = m.stack_run(config)
    assert admitted == (first,)
    assert run.completed == 1
    assert sum(item.total_tokens for item in admitted) <= config.token_budget
    assert run.cost_micros <= config.cost_budget_micros


def test_pipeline_reports_zero_completion_without_undefined_percentiles() -> None:
    config = m.PipelineConfig(seed=1, tasks=3, token_budget=1, cost_budget_micros=1)
    artifacts = m.run_pipeline(config)
    assert artifacts.comparison.stack.completed == 0
    stack_row = m.report_rows(artifacts.comparison)[1]
    assert (stack_row.p50_ms, stack_row.p95_ms) == (0.0, 0.0)
    assert "frugent-stack" in artifacts.markdown


def test_random_pipeline_admissions_never_cross_hard_budgets() -> None:
    import random

    generator = random.Random(711)
    for seed in range(40):
        token_budget = generator.randrange(1, 300)
        cost_budget = generator.randrange(1, 2_000)
        config = m.PipelineConfig(seed, 12, token_budget, cost_budget)
        admitted = m.admit_measurements(m.stack_measurements(config), token_budget, cost_budget)
        assert sum(item.total_tokens for item in admitted) <= token_budget
        assert sum(item.cost_micros for item in admitted) <= cost_budget


def test_report_rows_use_net_prompt_tokens_and_measured_latency() -> None:
    comparison = m.compare(m.PipelineConfig(seed=2, tasks=9))
    baseline, stack = m.report_rows(comparison)
    assert baseline.tokens == comparison.baseline.prompt_tokens
    assert stack.tokens == comparison.stack.prompt_tokens - comparison.stack.cached_tokens
    assert stack.p95_ms >= stack.p50_ms


def test_pipeline_trace_roundtrips_with_contiguous_events() -> None:
    from frugent.trace_io import import_trace

    config = m.PipelineConfig(seed=5, tasks=5)
    header, events = import_trace(m.trace_bytes(config, m.compare(config)))
    assert header.seed == 5
    assert tuple(event["sequence"] for event in events) == (0, 1)


def test_pipeline_artifacts_are_byte_deterministic() -> None:
    config = m.PipelineConfig(seed=21, tasks=11)
    first, second = m.run_pipeline(config), m.run_pipeline(config)
    assert first == second


def test_pipeline_artifacts_derive_from_one_comparison() -> None:
    artifacts = m.run_pipeline(m.PipelineConfig(seed=9, tasks=6))
    assert str(artifacts.comparison.stack.cost_micros) in artifacts.markdown
    assert "Offline synthetic measurements" in artifacts.html
    assert artifacts.trace.endswith(b"\n")


def test_report_rows_are_concrete_public_metric_values() -> None:
    from frugent.reports import MetricRow

    rows = m.report_rows(m.compare(m.PipelineConfig(seed=1, tasks=2)))
    assert all(isinstance(row, MetricRow) for row in rows)
