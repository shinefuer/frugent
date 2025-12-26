"""Behavior and invariant tests."""

from __future__ import annotations

import pytest

import frugent.workloads as m


def test_synthetic_task_requires_planted_ground_truth() -> None:
    task = m.SyntheticTask("t1", "single_edit", "easy", "edit x", ("inspect", "patch"), 11, "g0")
    assert task.solution_path == ("inspect", "patch")
    with pytest.raises(m.WorkloadError, match="planted"):
        m.SyntheticTask("t2", "docs", "easy", "write", (), 4, "g0")
