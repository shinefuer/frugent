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


def test_scripted_tools_require_exact_call_order() -> None:
    call = m.ToolCall("c", ("read", "x"))
    result = m.ToolResult("c", 0, b"data", b"")
    tools = m.ScriptedTools(((call, result),))
    assert tools.execute(call) == result
    assert tools.complete


def test_scripted_tools_reject_mismatched_call() -> None:
    expected = m.ToolCall("a", ("read", "x"))
    tools = m.ScriptedTools(((expected, m.ToolResult("a", 0, b"", b"")),))
    with pytest.raises(m.ToolError, match="does not match"):
        tools.execute(m.ToolCall("b", ("read", "x")))


def test_tool_dry_run_does_not_execute_command() -> None:
    from frugent.sandbox import Policy

    call = m.ToolCall("c", ("echo", "safe"))
    result = m.dry_run(call, Policy((("echo",),), (), frozenset()))
    assert result.exit_code == 0
    assert b'"mode":"dry_run"' in result.stdout
    assert b"safe\n" not in result.stdout


def test_execute_runs_allowed_argv_without_shell(tmp_path: object) -> None:
    import sys
    from pathlib import Path

    from frugent.sandbox import Policy

    call = m.ToolCall("c", (sys.executable, "-c", "__import__('sys').stdout.buffer.write(b'ok')"))
    policy = Policy(((sys.executable, "-c"),), (), frozenset())
    result = m.execute(call, policy, cwd=str(Path.cwd()))
    assert result == m.ToolResult("c", 0, b"ok", b"")


def test_execute_returns_denial_without_spawning() -> None:
    from frugent.sandbox import Policy

    result = m.execute(
        m.ToolCall("c", ("forbidden",)), Policy((("allowed",),), (), frozenset()), cwd="."
    )
    assert result.exit_code == 126
    assert b"allowlisted" in result.stderr
