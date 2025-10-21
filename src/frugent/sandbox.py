"""Declarative command, path, and environment policy decisions."""

from __future__ import annotations

from dataclasses import dataclass


class SandboxError(ValueError):
    """Raised for malformed policies or requests."""


@dataclass(frozen=True, slots=True)
class Policy:
    command_prefixes: tuple[tuple[str, ...], ...]
    path_globs: tuple[str, ...]
    allowed_env: frozenset[str]

    def __post_init__(self) -> None:
        if not self.command_prefixes or any(
            not prefix or any(not part for part in prefix) for prefix in self.command_prefixes
        ):
            raise SandboxError("sandbox policy: command prefixes must be non-empty")
        if any(not pattern for pattern in self.path_globs) or any(
            not name.isidentifier() for name in self.allowed_env
        ):
            raise SandboxError("sandbox policy: invalid path glob or environment name")


@dataclass(frozen=True, slots=True)
class Decision:
    allowed: bool
    reason: str
    rule: str | None = None


def command_decision(policy: Policy, argv: tuple[str, ...]) -> Decision:
    """Match an argv vector without invoking a shell."""
    if not argv or any(not isinstance(arg, str) or not arg for arg in argv):
        return Decision(False, "command is empty or contains an empty argument")
    for prefix in policy.command_prefixes:
        if argv[: len(prefix)] == prefix:
            return Decision(True, "command prefix allowed", " ".join(prefix))
    return Decision(False, "command prefix is not allowlisted")


SHELL_METACHARACTERS = frozenset({";", "&&", "||", "|", "`", "$(", ">", "<"})


def injection_decision(argv: tuple[str, ...]) -> Decision:
    """Reject shell syntax even though execution uses argv directly."""
    for argument in argv:
        if any(token in argument for token in SHELL_METACHARACTERS):
            return Decision(False, f"shell metacharacter in argument: {argument!r}")
        if "\n" in argument or "\x00" in argument:
            return Decision(False, "control character in argument")
    return Decision(True, "arguments contain no shell syntax")


def path_decision(policy: Policy, path: str) -> Decision:
    """Resolve a relative POSIX path and apply declared glob rules."""
    from pathlib import PurePosixPath

    candidate = PurePosixPath(path)
    if candidate.is_absolute() or ".." in candidate.parts or not path:
        return Decision(False, "path is absolute, empty, or traverses parent")
    normalized = str(candidate)
    for pattern in policy.path_globs:
        if candidate.match(pattern):
            return Decision(True, "path glob allowed", pattern)
    return Decision(False, f"path is outside allowlist: {normalized}")
