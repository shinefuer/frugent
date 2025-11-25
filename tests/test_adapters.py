"""Behavior and invariant tests."""

from __future__ import annotations

import pytest

import frugent.adapters as m


def test_adapter_records_preserve_binary_payloads() -> None:
    request = m.AdapterRequest("r", b"\x00prompt", 3)
    response = m.AdapterResponse("r", b"\xffresult", "scripted", 2, 1)
    assert request.prompt.startswith(b"\x00")
    assert response.content.startswith(b"\xff")


def test_adapter_request_requires_identity() -> None:
    with pytest.raises(m.AdapterError, match="adapter request"):
        m.AdapterRequest("", b"x", 0)


def test_scripted_adapter_returns_planted_exact_response() -> None:
    adapter = m.ScriptedAdapter("scripted-small", {b"fix x": b"edit x"})
    response = adapter.complete(m.AdapterRequest("r", b"fix x", 1))
    assert response == m.AdapterResponse("r", b"edit x", "scripted-small", 2, 2)
    assert isinstance(adapter, m.Adapter)


def test_scripted_adapter_rejects_unplanted_prompt() -> None:
    with pytest.raises(m.AdapterError, match="not planted"):
        m.ScriptedAdapter("m", {}).complete(m.AdapterRequest("r", b"unknown", 0))


def test_scripted_adapter_detects_one_byte_prompt_drift() -> None:
    adapter = m.ScriptedAdapter("m", {b"prompt": b"result"})
    with pytest.raises(m.AdapterError, match="not planted"):
        adapter.complete(m.AdapterRequest("r", b"prompT", 0))


def test_replay_adapter_requires_recorded_order() -> None:
    request = m.AdapterRequest("r", b"p", 0)
    response = m.AdapterResponse("r", b"c", "replay", 1, 1)
    adapter = m.ReplayAdapter(((request, response),))
    assert adapter.complete(request) == response
    with pytest.raises(m.AdapterError, match="exhausted"):
        adapter.complete(request)
