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
