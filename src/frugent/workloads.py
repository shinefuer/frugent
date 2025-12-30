"""Seeded synthetic coding-workload generation with planted solution paths."""

from __future__ import annotations

from dataclasses import dataclass


class WorkloadError(ValueError):
    """Raised for invalid synthetic workload definitions."""


TASK_KINDS = ("single_edit", "refactor", "test_fix", "docs")
DIFFICULTIES = ("easy", "medium", "hard")


@dataclass(frozen=True, slots=True)
class SyntheticTask:
    task_id: str
    kind: str
    difficulty: str
    prompt: str
    solution_path: tuple[str, ...]
    optimal_cost_micros: int
    prefix_group: str

    def __post_init__(self) -> None:
        if not self.task_id or self.kind not in TASK_KINDS or self.difficulty not in DIFFICULTIES:
            raise WorkloadError("task: invalid identity, kind, or difficulty")
        if (
            not self.prompt
            or not self.solution_path
            or any(not step for step in self.solution_path)
        ):
            raise WorkloadError("task: prompt and planted solution path are required")
        if self.optimal_cost_micros <= 0 or not self.prefix_group:
            raise WorkloadError("task: positive planted cost and prefix group are required")


def generate_corpus(seed: int, size: int) -> tuple[SyntheticTask, ...]:
    """Generate reproducible offline tasks with explicit planted optima."""
    import random

    if isinstance(seed, bool) or seed < 0 or size < 1:
        raise WorkloadError("corpus: seed must be non-negative and size positive")
    randomizer = random.Random(seed)
    tasks: list[SyntheticTask] = []
    for index in range(size):
        kind = TASK_KINDS[randomizer.randrange(len(TASK_KINDS))]
        difficulty = DIFFICULTIES[randomizer.randrange(len(DIFFICULTIES))]
        depth = DIFFICULTIES.index(difficulty) + 2
        path = ("inspect", *(f"apply-{kind}-{step}" for step in range(depth - 1)))
        group = f"repo-{randomizer.randrange(max(1, min(size, 4)))}"
        tasks.append(
            SyntheticTask(
                f"synthetic-{seed}-{index}",
                kind,
                difficulty,
                f"[{group}] {kind.replace('_', ' ')} task {index}",
                path,
                (depth * 17 + TASK_KINDS.index(kind) * 3),
                group,
            )
        )
    return tuple(tasks)


def affinity_sessions(tasks: tuple[SyntheticTask, ...]) -> tuple[tuple[str, ...], ...]:
    """Group rendered prompts by shared synthetic repository prefix."""
    if not tasks:
        raise WorkloadError("sessions: expected generated tasks")
    grouped: dict[str, list[str]] = {}
    for task in tasks:
        grouped.setdefault(task.prefix_group, []).append(
            f"workspace:{task.prefix_group}\npolicy:offline\nrequest:{task.prompt}"
        )
    return tuple(tuple(grouped[key]) for key in sorted(grouped))


def task_record(task: SyntheticTask) -> dict[str, object]:
    return {
        "task_id": task.task_id,
        "kind": task.kind,
        "difficulty": task.difficulty,
        "prompt": task.prompt,
        "solution_path": list(task.solution_path),
        "optimal_cost_micros": task.optimal_cost_micros,
        "prefix_group": task.prefix_group,
    }


def manifest_record(seed: int, tasks: tuple[SyntheticTask, ...]) -> dict[str, object]:
    if not tasks:
        raise WorkloadError("manifest: expected tasks")
    return {
        "schema_version": 1,
        "seed": seed,
        "synthetic": True,
        "tasks": [task_record(task) for task in tasks],
    }


def manifest_fingerprint(seed: int, tasks: tuple[SyntheticTask, ...]) -> str:
    from frugent.codec import payload_digest

    return payload_digest(manifest_record(seed, tasks))


def manifest_from_record(record: dict[str, object]) -> tuple[int, tuple[SyntheticTask, ...]]:
    expected = {"schema_version", "seed", "synthetic", "tasks"}
    if set(record) != expected or record["schema_version"] != 1 or record["synthetic"] is not True:
        raise WorkloadError("manifest: unsupported or non-synthetic record")
    try:
        seed = int(record["seed"])
        raw_tasks = record["tasks"]
        if not isinstance(raw_tasks, list):
            raise TypeError("tasks must be a list")
        tasks = tuple(
            SyntheticTask(
                str(item["task_id"]),
                str(item["kind"]),
                str(item["difficulty"]),
                str(item["prompt"]),
                tuple(item["solution_path"]),
                int(item["optimal_cost_micros"]),
                str(item["prefix_group"]),
            )
            for item in raw_tasks
        )
    except (KeyError, TypeError, ValueError) as error:
        raise WorkloadError(f"manifest: invalid record: {error}") from error
    if seed < 0 or not tasks:
        raise WorkloadError("manifest: invalid seed or empty tasks")
    return seed, tasks


def optimal_profile(tasks: tuple[SyntheticTask, ...]) -> dict[str, int]:
    """Aggregate known-optimal fictional costs by difficulty."""
    if not tasks:
        raise WorkloadError("optimal profile: expected tasks")
    result = {difficulty: 0 for difficulty in DIFFICULTIES}
    for task in tasks:
        result[task.difficulty] += task.optimal_cost_micros
    result["total"] = sum(task.optimal_cost_micros for task in tasks)
    return result


def split_folds(
    tasks: tuple[SyntheticTask, ...], folds: int
) -> tuple[tuple[SyntheticTask, ...], ...]:
    """Assign stable task IDs to non-empty evaluation folds."""
    import hashlib

    if folds < 2 or len(tasks) < folds:
        raise WorkloadError("folds: need at least two non-empty folds")
    buckets: list[list[SyntheticTask]] = [[] for _ in range(folds)]
    for task in tasks:
        index = int.from_bytes(hashlib.sha256(task.task_id.encode()).digest()[:8], "big") % folds
        buckets[index].append(task)
    if any(not bucket for bucket in buckets):
        ordered = sorted(tasks, key=lambda task: task.task_id)
        buckets = [list(ordered[index::folds]) for index in range(folds)]
    return tuple(tuple(bucket) for bucket in buckets)
