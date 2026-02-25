"""End-to-end offline synthesis, runtime measurement, tracing, and reporting."""

from __future__ import annotations

from dataclasses import dataclass


class PipelineError(ValueError):
    """Raised for invalid offline pipeline requests."""


@dataclass(frozen=True, slots=True)
class PipelineConfig:
    seed: int = 0
    tasks: int = 24
    token_budget: int = 4096
    cost_budget_micros: int = 100_000

    def __post_init__(self) -> None:
        values = (self.seed, self.tasks, self.token_budget, self.cost_budget_micros)
        if any(isinstance(value, bool) or not isinstance(value, int) for value in values):
            raise PipelineError("pipeline config: integer fields required")
        if self.seed < 0 or self.tasks < 1 or self.token_budget < 1 or self.cost_budget_micros < 1:
            raise PipelineError("pipeline config: positive limits and non-negative seed required")


@dataclass(frozen=True, slots=True)
class PolicyRun:
    policy: str
    completed: int
    prompt_tokens: int
    cached_tokens: int
    cost_micros: int
    latencies_ms: tuple[int, ...]

    def __post_init__(self) -> None:
        counts = (self.completed, self.prompt_tokens, self.cached_tokens, self.cost_micros)
        if not self.policy or any(value < 0 for value in counts):
            raise PipelineError("policy run: non-negative measured counts required")
        if self.cached_tokens > self.prompt_tokens or any(value < 0 for value in self.latencies_ms):
            raise PipelineError("policy run: cache and latency measurements are inconsistent")


def baseline_run(config: PipelineConfig) -> PolicyRun:
    """Execute accounting for one fictional premium request per generated task."""
    from frugent.ratecard import demo_rate_card, price_usage
    from frugent.tokenizer import HeuristicTokenizer
    from frugent.types import Usage
    from frugent.workloads import generate_corpus

    tasks = generate_corpus(config.seed, config.tasks)
    tokenizer = HeuristicTokenizer()
    rate = demo_rate_card().model_rate("scripted-large")
    prompt_tokens = tuple(tokenizer.count(task.prompt) for task in tasks)
    completion_tokens = tuple(4 * len(task.solution_path) for task in tasks)
    costs = tuple(
        price_usage(rate, Usage(prompt, completion)).total_micros
        for prompt, completion in zip(prompt_tokens, completion_tokens, strict=True)
    )
    latencies = tuple(35 + 12 * (len(task.solution_path) - 2) for task in tasks)
    return PolicyRun("baseline-premium", len(tasks), sum(prompt_tokens), 0, sum(costs), latencies)
