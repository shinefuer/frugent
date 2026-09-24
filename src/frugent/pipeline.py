"""End-to-end offline synthesis, runtime measurement, tracing, and reporting."""

from __future__ import annotations

from dataclasses import dataclass

from frugent.reports import MetricRow


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


@dataclass(frozen=True, slots=True)
class TaskMeasurement:
    """Measured integer accounting for one planted synthetic task."""

    task_id: str
    prompt_tokens: int
    completion_tokens: int
    cached_tokens: int
    cost_micros: int
    latency_ms: int

    def __post_init__(self) -> None:
        values = (
            self.prompt_tokens,
            self.completion_tokens,
            self.cached_tokens,
            self.cost_micros,
            self.latency_ms,
        )
        if (
            not isinstance(self.task_id, str)
            or not self.task_id
            or any(
                isinstance(value, bool) or not isinstance(value, int) or value < 0
                for value in values
            )
            or self.cached_tokens > self.prompt_tokens
        ):
            raise PipelineError("task measurement: invalid identity, tokens, cost, or latency")

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens


def baseline_measurements(config: PipelineConfig) -> tuple[TaskMeasurement, ...]:
    """Measure one fictional premium request per generated task."""
    from frugent.ratecard import demo_rate_card, price_usage
    from frugent.tokenizer import HeuristicTokenizer
    from frugent.types import Usage
    from frugent.workloads import generate_corpus

    tasks = generate_corpus(config.seed, config.tasks)
    tokenizer = HeuristicTokenizer()
    rate = demo_rate_card().model_rate("scripted-large")
    prompt_tokens = tuple(tokenizer.count(task.prompt) for task in tasks)
    completion_tokens = tuple(4 * len(task.solution_path) for task in tasks)
    return tuple(
        TaskMeasurement(
            task.task_id,
            prompt,
            completion,
            0,
            price_usage(rate, Usage(prompt, completion)).total_micros,
            35 + 12 * (len(task.solution_path) - 2),
        )
        for task, prompt, completion in zip(tasks, prompt_tokens, completion_tokens, strict=True)
    )


def stack_measurements(config: PipelineConfig) -> tuple[TaskMeasurement, ...]:
    """Measure stack cache, batch, cost, and latency effects per task."""
    from frugent.prompt_cache import CachePolicy, replay_trace
    from frugent.ratecard import demo_rate_card, price_usage
    from frugent.tokenizer import HeuristicTokenizer
    from frugent.types import Usage
    from frugent.workloads import generate_corpus

    tasks = generate_corpus(config.seed, config.tasks)
    from frugent.batching import BatchRequest, micro_batches

    batch_requests = tuple(
        BatchRequest(task.task_id, task.prompt.encode(), index * 2)
        for index, task in enumerate(tasks)
    )
    batches = micro_batches(batch_requests, window_ms=4, max_size=3)
    batched_ids = {request.request_id for batch in batches if len(batch) > 1 for request in batch}
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
    return tuple(
        TaskMeasurement(
            task.task_id,
            prompt,
            4 * len(task.solution_path),
            hit,
            price_usage(
                rate,
                Usage(prompt, 4 * len(task.solution_path), hit),
                batched=task.task_id in batched_ids,
            ).total_micros,
            22 + 8 * (len(task.solution_path) - 2) + index % 3,
        )
        for index, (task, prompt, hit) in enumerate(zip(tasks, prompts, cached, strict=True))
    )


@dataclass(frozen=True, slots=True)
class StackStages:
    """Measured stage counts for one end-to-end synthetic stack run."""

    requests: int
    cache_hits: int
    cached_tokens: int
    batches: int
    executions: int
    admitted: int

    def __post_init__(self) -> None:
        values = (
            self.requests,
            self.cache_hits,
            self.cached_tokens,
            self.batches,
            self.executions,
            self.admitted,
        )
        if any(
            isinstance(value, bool) or not isinstance(value, int) or value < 0 for value in values
        ) or not (
            self.cache_hits <= self.requests
            and self.executions <= self.requests
            and self.admitted <= self.requests
            and self.batches <= self.requests
        ):
            raise PipelineError("stack stages: inconsistent measured counts")


def stack_stages(config: PipelineConfig) -> StackStages:
    """Run cache, micro-batch, and hard-budget stages over one corpus."""
    from frugent.batching import BatchRequest, batch_metrics, micro_batches
    from frugent.workloads import generate_corpus

    tasks = generate_corpus(config.seed, config.tasks)
    requests = tuple(
        BatchRequest(task.task_id, task.prompt.encode(), index * 2)
        for index, task in enumerate(tasks)
    )
    batches = micro_batches(requests, window_ms=4, max_size=3)
    measured_batches = batch_metrics(requests, batches)
    measurements = stack_measurements(config)
    admitted = admit_measurements(measurements, config.token_budget, config.cost_budget_micros)
    return StackStages(
        len(measurements),
        sum(item.cached_tokens > 0 for item in measurements),
        sum(item.cached_tokens for item in measurements),
        measured_batches.batches,
        measured_batches.executions,
        len(admitted),
    )


def _policy_run(policy: str, measurements: tuple[TaskMeasurement, ...]) -> PolicyRun:
    return PolicyRun(
        policy,
        len(measurements),
        sum(item.prompt_tokens for item in measurements),
        sum(item.cached_tokens for item in measurements),
        sum(item.cost_micros for item in measurements),
        tuple(item.latency_ms for item in measurements),
    )


def admit_measurements(
    measurements: tuple[TaskMeasurement, ...], token_budget: int, cost_budget_micros: int
) -> tuple[TaskMeasurement, ...]:
    """Admit seeded task order without crossing either hard session budget."""
    from frugent.budget import Budget, can_admit, reserve

    budget = Budget(token_budget, cost_budget_micros)
    admitted: list[TaskMeasurement] = []
    for measurement in measurements:
        if can_admit(budget, measurement.total_tokens, measurement.cost_micros):
            budget = reserve(budget, measurement.total_tokens, measurement.cost_micros)
            admitted.append(measurement)
    return tuple(admitted)


def baseline_run(config: PipelineConfig) -> PolicyRun:
    """Aggregate per-task baseline accounting."""
    return _policy_run("baseline-premium", baseline_measurements(config))


def stack_run(config: PipelineConfig) -> PolicyRun:
    """Aggregate stack accounting over the planted task corpus."""
    measurements = admit_measurements(
        stack_measurements(config), config.token_budget, config.cost_budget_micros
    )
    return _policy_run("frugent-stack", measurements)


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


def report_rows(comparison: Comparison) -> tuple[MetricRow, ...]:
    from frugent.statistics import quantile

    def row(run: PolicyRun) -> MetricRow:
        values = tuple(float(value) for value in run.latencies_ms)
        return MetricRow(
            run.policy,
            run.completed,
            run.prompt_tokens - run.cached_tokens,
            run.cost_micros,
            0.0 if not values else quantile(values, 0.5),
            0.0 if not values else quantile(values, 0.95),
        )

    return row(comparison.baseline), row(comparison.stack)


def trace_bytes(config: PipelineConfig, comparison: Comparison) -> bytes:
    from frugent.config import RuntimeConfig
    from frugent.ratecard import demo_rate_card, rate_card_fingerprint
    from frugent.trace_io import TraceHeader, export_trace

    runtime_config = RuntimeConfig(
        seed=config.seed,
        token_budget=config.token_budget,
        cost_budget_micros=config.cost_budget_micros,
    )
    header = TraceHeader(
        f"synthetic-{config.seed}",
        config.seed,
        runtime_config.fingerprint,
        rate_card_fingerprint(demo_rate_card()),
    )
    events = tuple(
        {
            "policy": run.policy,
            "completed": run.completed,
            "prompt_tokens": run.prompt_tokens,
            "cached_tokens": run.cached_tokens,
            "cost_micros": run.cost_micros,
        }
        for run in (comparison.baseline, comparison.stack)
    )
    return export_trace(header, events)


@dataclass(frozen=True, slots=True)
class PipelineArtifacts:
    comparison: Comparison
    trace: bytes
    markdown: str
    html: str


def run_pipeline(config: PipelineConfig) -> PipelineArtifacts:
    from frugent import __version__
    from frugent.config import RuntimeConfig
    from frugent.ratecard import demo_rate_card, rate_card_fingerprint
    from frugent.reports import (
        RunMetadata,
        coverage_limitations,
        html_report,
        markdown_report,
    )

    comparison = compare(config)
    runtime_config = RuntimeConfig(
        seed=config.seed,
        token_budget=config.token_budget,
        cost_budget_micros=config.cost_budget_micros,
    )
    metadata = RunMetadata(
        __version__,
        config.seed,
        runtime_config.fingerprint,
        rate_card_fingerprint(demo_rate_card()),
    )
    limitations = coverage_limitations(
        used_real_endpoint=False, used_external_data=False, model_evaluated=False
    )
    rows = report_rows(comparison)
    return PipelineArtifacts(
        comparison,
        trace_bytes(config, comparison),
        markdown_report(metadata, rows, limitations),
        html_report(metadata, rows, limitations),
    )
