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
