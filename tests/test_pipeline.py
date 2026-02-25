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
