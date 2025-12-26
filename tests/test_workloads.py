"""Behavior and invariant tests."""

from __future__ import annotations

import pytest

import frugent.workloads as m


def test_synthetic_task_requires_planted_ground_truth() -> None:
    task = m.SyntheticTask("t1", "single_edit", "easy", "edit x", ("inspect", "patch"), 11, "g0")
    assert task.solution_path == ("inspect", "patch")
    with pytest.raises(m.WorkloadError, match="planted"):
        m.SyntheticTask("t2", "docs", "easy", "write", (), 4, "g0")


def test_generate_corpus_is_seeded_and_varied() -> None:
    first = m.generate_corpus(19, 12)
    assert first == m.generate_corpus(19, 12)
    assert first != m.generate_corpus(20, 12)
    assert len({task.kind for task in first}) > 1


@pytest.mark.parametrize(("seed", "size"), [(-1, 1), (0, 0), (True, 2)])
def test_generate_corpus_rejects_invalid_shape(seed: int, size: int) -> None:
    with pytest.raises(m.WorkloadError, match="corpus"):
        m.generate_corpus(seed, size)


def test_generated_task_identities_are_unique() -> None:
    tasks = m.generate_corpus(0, 100)
    assert len({task.task_id for task in tasks}) == len(tasks)


def test_affinity_sessions_preserve_every_request_once() -> None:
    tasks = m.generate_corpus(7, 17)
    sessions = m.affinity_sessions(tasks)
    assert sum(map(len, sessions)) == len(tasks)
    assert all(len({prompt.splitlines()[0] for prompt in session}) == 1 for session in sessions)


def test_manifest_explicitly_labels_synthetic_data() -> None:
    record = m.manifest_record(4, m.generate_corpus(4, 2))
    assert record["schema_version"] == 1
    assert record["synthetic"] is True
    assert len(record["tasks"]) == 2


def test_manifest_fingerprint_changes_with_content() -> None:
    tasks = m.generate_corpus(3, 4)
    assert m.manifest_fingerprint(3, tasks) == m.manifest_fingerprint(3, tasks)
    assert m.manifest_fingerprint(3, tasks) != m.manifest_fingerprint(3, tasks[:-1])
