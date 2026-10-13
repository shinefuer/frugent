"""Command-line entry point for deterministic offline mechanisms."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

from frugent import __version__
from frugent.codec import canonical_json


@dataclass(frozen=True, slots=True)
class CommandOutput:
    data: dict[str, object]
    artifact: bytes | None = None


Handler = Callable[[argparse.Namespace], CommandOutput]
COMMANDS: dict[str, tuple[str, Handler]] = {}


def register(name: str, help_text: str) -> Callable[[Handler], Handler]:
    def decorate(handler: Handler) -> Handler:
        if name in COMMANDS:
            raise RuntimeError(f"duplicate command: {name}")
        COMMANDS[name] = (help_text, handler)
        return handler

    return decorate


def build_parser() -> argparse.ArgumentParser:
    """Build the root parser and every registered offline subcommand."""
    parser = argparse.ArgumentParser(prog="frugent", description="离线运行时机制工具包")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    subparsers = parser.add_subparsers(dest="command")
    for name in sorted(COMMANDS):
        help_text, handler = COMMANDS[name]
        command = subparsers.add_parser(name, help=help_text, description=help_text)
        command.add_argument("--seed", type=int, default=0)
        command.add_argument("--tasks", type=int, default=12)
        command.add_argument("--token-budget", type=int, default=4096)
        command.add_argument("--cost-budget", type=int, default=100_000)
        command.add_argument("--format", choices=("json", "markdown", "html"), default="json")
        command.add_argument("--output", type=Path)
        command.set_defaults(handler=handler)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Execute a command, returning 2 for validated input failures."""
    arguments = build_parser().parse_args(argv)
    handler = getattr(arguments, "handler", None)
    if handler is None:
        return 0
    try:
        output = handler(arguments)
        body = (
            output.artifact if output.artifact is not None else canonical_json(output.data) + b"\n"
        )
        if arguments.output is not None:
            arguments.output.write_bytes(body)
        else:
            sys.stdout.buffer.write(body)
    except (OSError, ValueError) as error:
        print(f"frugent: {error}", file=sys.stderr)
        return 2
    return 0


@register("route", "measure prefix-aware routing on a planted affinity trace")
def route_command(arguments: argparse.Namespace) -> CommandOutput:
    from frugent.prefix import PrefixTrie
    from frugent.prompt_router import Instance, greedy_fixed_assignment, routed_hit_tokens

    left, right = PrefixTrie(), PrefixTrie()
    left.insert(("repo:a", "policy:offline"))
    right.insert(("repo:b", "policy:offline"))
    instances = (Instance("left", left), Instance("right", right))
    requests = (("repo:a", "policy:offline", "edit"), ("repo:b", "policy:offline", "test"))
    assignments = greedy_fixed_assignment(instances, requests)
    return CommandOutput(
        {
            "synthetic": True,
            "assignments": list(assignments),
            "cached_tokens": routed_hit_tokens(instances, assignments, requests),
        }
    )


@register("cache", "replay exact prompt-cache lifecycle events")
def cache_command(arguments: argparse.Namespace) -> CommandOutput:
    from frugent.prompt_cache import CachePolicy, metrics, replay_trace

    outcomes = replay_trace((("a", 8, 0), ("b", 4, 1), ("a", 8, 2)), CachePolicy(16, 100))
    measured = metrics(outcomes)
    return CommandOutput(
        {
            "requests": measured.requests,
            "hits": measured.hits,
            "cached_tokens": measured.cached_tokens,
            "hit_rate": measured.hit_rate,
        }
    )


@register("compress", "measure planted-needle recall under token budgets")
def compress_command(arguments: argparse.Namespace) -> CommandOutput:
    from frugent.compression import Block, recall_curve

    if arguments.token_budget < 0:
        raise ValueError("compress: token budget must be non-negative")
    blocks = tuple(
        Block(
            f"b{index}",
            "needle" if index in {1, 3} else "context",
            2,
            index,
            planted_relevance=10 if index in {1, 3} else 1,
        )
        for index in range(5)
    )
    budgets = tuple(sorted({0, max(0, arguments.token_budget // 1024), 6, 10}))
    curve = recall_curve(blocks, frozenset({"b1", "b3"}), budgets)
    return CommandOutput({"synthetic": True, "curve": [list(point) for point in curve]})


@register("batch", "measure exact deduplication and synthetic micro-batches")
def batch_command(arguments: argparse.Namespace) -> CommandOutput:
    from frugent.batching import BatchRequest, batch_metrics, micro_batches

    requests = (
        BatchRequest("a", b"same", 0),
        BatchRequest("b", b"same", 1),
        BatchRequest("c", b"other", 7),
    )
    batches = micro_batches(requests, window_ms=3, max_size=4)
    measured = batch_metrics(requests, batches)
    return CommandOutput(
        {
            "requests": measured.requests,
            "executions": measured.executions,
            "batches": measured.batches,
            "dedup_ratio": measured.dedup_ratio,
        }
    )


@register("budget", "allocate hard token and fictional micro-cost budgets")
def budget_command(arguments: argparse.Namespace) -> CommandOutput:
    from frugent.scheduling import Task, schedule, schedule_totals

    if arguments.tasks < 0:
        raise ValueError("budget: tasks must be non-negative")
    tasks = tuple(
        Task(f"t{index}", index % 3, 20 + index, 30 + index * 2) for index in range(arguments.tasks)
    )
    decisions = schedule(tasks, arguments.token_budget, arguments.cost_budget)
    tokens, cost = schedule_totals(decisions)
    return CommandOutput(
        {
            "decisions": [list(item) for item in decisions],
            "allocated_tokens": tokens,
            "allocated_cost_micros": cost,
        }
    )


@register("trace", "export a checksummed offline pipeline trace")
def trace_command(arguments: argparse.Namespace) -> CommandOutput:
    from frugent.pipeline import PipelineConfig, compare, trace_bytes
    from frugent.trace_io import import_trace, trace_fingerprint

    config = PipelineConfig(
        arguments.seed, arguments.tasks, arguments.token_budget, arguments.cost_budget
    )
    trace = trace_bytes(config, compare(config))
    header, events = import_trace(trace)
    return CommandOutput(
        {"run_id": header.run_id, "events": len(events), "fingerprint": trace_fingerprint(trace)},
        trace if arguments.format != "json" else None,
    )


@register("bench", "compare baseline and stack on identical synthetic tasks")
def bench_command(arguments: argparse.Namespace) -> CommandOutput:
    from frugent.benchmark import cache_hit_uplift, cost_per_completed
    from frugent.pipeline import PipelineConfig, compare, stack_stages

    config = PipelineConfig(
        arguments.seed, arguments.tasks, arguments.token_budget, arguments.cost_budget
    )
    comparison = compare(config)
    stages = stack_stages(config)
    stack_cost_per_completed = (
        cost_per_completed(comparison.stack.cost_micros, comparison.stack.completed)
        if comparison.stack.completed
        else None
    )
    return CommandOutput(
        {
            "synthetic": True,
            "fictional_rate_card": True,
            "completed": comparison.stack.completed,
            "token_savings": comparison.token_savings,
            "cost_savings_micros": comparison.cost_savings_micros,
            "cache_hit_uplift": cache_hit_uplift(0, stages.cache_hits, stages.requests),
            "stack_cost_per_completed_micros": stack_cost_per_completed,
        }
    )


@register("report", "render a measured synthetic cost report")
def report_command(arguments: argparse.Namespace) -> CommandOutput:
    from frugent.pipeline import PipelineConfig, run_pipeline

    if arguments.format == "json":
        raise ValueError("report: --format must be markdown or html")
    artifacts = run_pipeline(
        PipelineConfig(
            arguments.seed, arguments.tasks, arguments.token_budget, arguments.cost_budget
        )
    )
    content = artifacts.markdown if arguments.format == "markdown" else artifacts.html
    return CommandOutput({"format": arguments.format}, content.encode())


@register("run", "execute synthesis, accounting, tracing, and reporting")
def run_command(arguments: argparse.Namespace) -> CommandOutput:
    from frugent.pipeline import PipelineConfig, run_pipeline, stack_stages
    from frugent.trace_io import trace_fingerprint

    config = PipelineConfig(
        arguments.seed, arguments.tasks, arguments.token_budget, arguments.cost_budget
    )
    artifacts = run_pipeline(config)
    stages = stack_stages(config)
    comparison = artifacts.comparison
    return CommandOutput(
        {
            "completed": comparison.stack.completed,
            "token_savings": comparison.token_savings,
            "cost_savings_micros": comparison.cost_savings_micros,
            "routed_prefix_tokens": stages.routed_prefix_tokens,
            "cache_hits": stages.cache_hits,
            "micro_batches": stages.batches,
            "budget_admissions": stages.admitted,
            "trace_fingerprint": trace_fingerprint(artifacts.trace),
        }
    )


@register("demo", "run the complete offline demonstration with honest labels")
def demo_command(arguments: argparse.Namespace) -> CommandOutput:
    from frugent.pipeline import PipelineConfig, run_pipeline, stack_stages

    config = PipelineConfig(
        arguments.seed, arguments.tasks, arguments.token_budget, arguments.cost_budget
    )
    artifacts = run_pipeline(config)
    stages = stack_stages(config)
    comparison = artifacts.comparison
    data = {
        "scope": "offline synthetic workload",
        "rate_card": "fictional",
        "tasks_completed": comparison.stack.completed,
        "measured_token_savings": comparison.token_savings,
        "measured_cost_savings_micros": comparison.cost_savings_micros,
        "measured_routed_prefix_tokens": stages.routed_prefix_tokens,
        "measured_cache_hits": stages.cache_hits,
        "measured_micro_batches": stages.batches,
        "measured_budget_admissions": stages.admitted,
    }
    artifact = artifacts.html.encode() if arguments.format == "html" else None
    return CommandOutput(data, artifact)
