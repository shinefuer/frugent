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


def stack_run(config: PipelineConfig) -> PolicyRun:
    """Measure runtime mechanics over the identical planted task corpus."""
    from frugent.prompt_cache import CachePolicy, replay_trace
    from frugent.ratecard import demo_rate_card, price_usage
    from frugent.tokenizer import HeuristicTokenizer
    from frugent.types import Usage
    from frugent.workloads import generate_corpus

    tasks = generate_corpus(config.seed, config.tasks)
    tokenizer = HeuristicTokenizer()
    prompts = tuple(tokenizer.count(task.prompt) for task in tasks)
    times = tuple(index * 10 for index in range(len(tasks)))
    requests = tuple(
        (task.prefix_group, max(1, tokens // 2), now)
        for task, tokens, now in zip(tasks, prompts, times, strict=True)
    )
    cache_outcomes = replay_trace(requests, CachePolicy(10_000, 10_000))
    cached = tuple(
        min(prompt, hit_tokens) if hit else 0
        for prompt, (hit, hit_tokens) in zip(prompts, cache_outcomes, strict=True)
    )
    rate = demo_rate_card().model_rate("scripted-medium")
    costs = tuple(
        price_usage(
            rate, Usage(prompt, 4 * len(task.solution_path), hit), batched=index % 3 != 0
        ).total_micros
        for index, (task, prompt, hit) in enumerate(zip(tasks, prompts, cached, strict=True))
    )
    latencies = tuple(
        22 + 8 * (len(task.solution_path) - 2) + index % 3 for index, task in enumerate(tasks)
    )
    completed = len(tasks) if sum(costs) <= config.cost_budget_micros else 0
    return PolicyRun("frugent-stack", completed, sum(prompts), sum(cached), sum(costs), latencies)


@dataclass(frozen=True, slots=True)
class Comparison:
    baseline: PolicyRun
    stack: PolicyRun

    @property
    def token_savings(self) -> float:
        if self.baseline.prompt_tokens == 0:
            return 0.0
        return round(self.stack.cached_tokens / self.baseline.prompt_tokens, 6)

    @property
    def cost_savings_micros(self) -> int:
        return self.baseline.cost_micros - self.stack.cost_micros


def compare(config: PipelineConfig) -> Comparison:
    return Comparison(baseline_run(config), stack_run(config))


def report_rows(comparison: Comparison) -> tuple[object, ...]:
    from frugent.reports import MetricRow
    from frugent.statistics import quantile

    def row(run: PolicyRun) -> MetricRow:
        values = tuple(float(value) for value in run.latencies_ms)
        return MetricRow(
            run.policy,
            run.completed,
            run.prompt_tokens - run.cached_tokens,
            run.cost_micros,
            quantile(values, 0.5),
            quantile(values, 0.95),
        )

    return row(comparison.baseline), row(comparison.stack)
