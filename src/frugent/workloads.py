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
