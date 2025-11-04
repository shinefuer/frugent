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
