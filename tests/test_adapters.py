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
