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


@pytest.mark.parametrize("exit_code", [-1, 0, 1, 124, 126, 130])
def test_tool_results_preserve_signed_exit_codes(exit_code: int) -> None:
    assert m.ToolResult("c", exit_code, b"", b"").exit_code == exit_code


def test_tool_result_rejects_boolean_exit_code() -> None:
    with pytest.raises(m.ToolError, match="exit code"):
        m.ToolResult("c", True, b"", b"")
