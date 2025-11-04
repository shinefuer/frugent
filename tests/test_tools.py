"""Behavior and invariant tests."""

from __future__ import annotations

import pytest

import frugent.tools as m


def test_tool_call_freezes_sorted_environment() -> None:
    call = m.ToolCall("c", ("echo", "x"), environment=(("A", "1"), ("B", "2")))
    assert dict(call.environment) == {"A": "1", "B": "2"}


def test_tool_call_rejects_empty_argv() -> None:
    with pytest.raises(m.ToolError, match="tool call"):
        m.ToolCall("c", ())


def test_tool_result_preserves_non_utf8_output() -> None:
    result = m.ToolResult("c", 0, b"\x00\xff", b"")
    assert result.stdout == b"\x00\xff"


def test_tool_result_rejects_conflicting_terminal_states() -> None:
    with pytest.raises(m.ToolError, match="both timed out"):
        m.ToolResult("c", -1, b"", b"", timed_out=True, cancelled=True)
