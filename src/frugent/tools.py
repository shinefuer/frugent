"""Sandboxed argv execution and deterministic scripted tool replay."""

from __future__ import annotations

from dataclasses import dataclass


class ToolError(RuntimeError):
    """Raised for invalid, denied, or failed tool execution."""


@dataclass(frozen=True, slots=True)
class ToolCall:
    call_id: str
    argv: tuple[str, ...]
    paths: tuple[str, ...] = ()
    environment: tuple[tuple[str, str], ...] = ()

    def __post_init__(self) -> None:
        if not self.call_id or not self.argv or any(not arg for arg in self.argv):
            raise ToolError("tool call: identity and argv must be non-empty")
        if tuple(sorted(self.environment)) != self.environment:
            raise ToolError("tool call: environment must be sorted")


@dataclass(frozen=True, slots=True)
class ToolResult:
    call_id: str
    exit_code: int
    stdout: bytes
    stderr: bytes
    timed_out: bool = False
    cancelled: bool = False

    def __post_init__(self) -> None:
        if (
            not self.call_id
            or isinstance(self.exit_code, bool)
            or not isinstance(self.exit_code, int)
        ):
            raise ToolError("tool result: invalid identity or exit code")
        if self.timed_out and self.cancelled:
            raise ToolError("tool result: cannot be both timed out and cancelled")
