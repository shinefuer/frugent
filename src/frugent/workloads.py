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
