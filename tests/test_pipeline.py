"""Behavior and invariant tests."""

from __future__ import annotations

import pytest

import frugent.pipeline as m


def test_pipeline_config_enforces_offline_run_limits() -> None:
    assert m.PipelineConfig(seed=3, tasks=4).tasks == 4
    with pytest.raises(m.PipelineError, match="positive"):
        m.PipelineConfig(tasks=0)
