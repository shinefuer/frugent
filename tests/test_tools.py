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


def test_dry_run_and_execute_agree_on_denial() -> None:
    from frugent.sandbox import Policy

    policy = Policy((("allowed",),), (), frozenset())
    call = m.ToolCall("c", ("denied",))
    assert m.dry_run(call, policy).exit_code == m.execute(call, policy, cwd=".").exit_code == 126


def test_timeout_result_preserves_clean_partial_output() -> None:
    result = m.timeout_result("c", b"before", b"warning")
    assert result.exit_code == 124
    assert result.timed_out
    assert result.stdout == b"before"
    assert not result.cancelled


def test_cancelled_result_is_distinct_from_timeout() -> None:
    result = m.cancelled_result("c", b"partial")
    assert result.exit_code == 130
    assert result.cancelled and not result.timed_out
    assert result != m.timeout_result("c", b"partial")


@pytest.mark.parametrize("payload", [b"", b"text", b"\x00\xff", bytes(range(64))])
def test_timeout_and_cancellation_preserve_partial_bytes(payload: bytes) -> None:
    assert m.timeout_result("t", payload).stdout == payload
    assert m.cancelled_result("c", payload).stdout == payload


def test_tool_result_record_roundtrip_handles_binary() -> None:
    result = m.ToolResult("c", 7, b"\x00\xff", b"err")
    record = m.result_record(result)
    assert record["stdout_hex"] == "00ff"
    assert m.result_from_record(record) == result


def test_tool_result_record_does_not_coerce_boolean_strings() -> None:
    record = m.result_record(m.ToolResult("x", 0, b"", b""))
    record["timed_out"] = "false"
    with pytest.raises(m.ToolError, match="booleans"):
        m.result_from_record(record)


def test_dry_run_does_not_create_an_allowlisted_output_file(tmp_path: object) -> None:
    import sys
    from pathlib import Path

    from frugent.sandbox import Policy

    destination = Path(tmp_path) / "must-not-exist"
    code = f"__import__('pathlib').Path({str(destination)!r}).write_text('bad')"
    call = m.ToolCall("dry", (sys.executable, "-c", code))
    result = m.dry_run(call, Policy(((sys.executable, "-c"),), (), frozenset()))
    assert result.exit_code == 0 and not destination.exists()
    assert b'"mode":"dry_run"' in result.stdout


def test_scripted_tool_replay_requires_exact_call_order() -> None:
    first, second = m.ToolCall("a", ("one",)), m.ToolCall("b", ("two",))
    replay = m.ScriptedTools(
        ((first, m.ToolResult("a", 0, b"1", b"")), (second, m.ToolResult("b", 0, b"2", b"")))
    )
    with pytest.raises(m.ToolError, match="does not match"):
        replay.execute(second)
    assert replay.execute(first).stdout == b"1"
    assert replay.execute(second).stdout == b"2" and replay.complete
