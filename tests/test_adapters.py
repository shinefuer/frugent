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


def test_adapter_response_record_roundtrip() -> None:
    response = m.AdapterResponse("r", b"\x00\xff", "scripted", 7, 3)
    assert m.response_from_record(m.response_record(response)) == response


def test_recording_adapter_does_not_change_observable_response() -> None:
    inner = m.ScriptedAdapter("m", {b"p": b"r"})
    adapter = m.RecordingAdapter(inner)
    request = m.AdapterRequest("id", b"p", 0)
    assert adapter.complete(request) == inner.complete(request)
    assert adapter.records[0][0] == request


@pytest.mark.parametrize("payload", [b"", b"text", b"\x00\xff", bytes(range(16))])
def test_recording_wrapper_preserves_binary_response(payload: bytes) -> None:
    adapter = m.RecordingAdapter(m.ScriptedAdapter("m", {b"p": payload}))
    response = adapter.complete(m.AdapterRequest("r", b"p", 0))
    assert response.content == payload
    assert adapter.records[0][1].content == payload


def test_loopback_payload_codec_is_credential_free() -> None:
    request = m.AdapterRequest("r", b"prompt", 9)
    encoded = m.loopback_request_record(request)
    assert encoded == b'{"prompt_hex":"70726f6d7074","request_id":"r","seed":9}'
    assert b"api_key" not in encoded and b"endpoint" not in encoded


def test_loopback_adapter_rejects_nonlocal_url() -> None:
    with pytest.raises(m.AdapterError, match="only local"):
        m.complete_loopback("https://example.invalid/api", m.AdapterRequest("r", b"p", 0))


def test_loopback_adapter_rejects_local_https() -> None:
    with pytest.raises(m.AdapterError, match="only local"):
        m.complete_loopback("https://127.0.0.1/api", m.AdapterRequest("r", b"p", 0))


def test_same_request_has_identical_loopback_payload() -> None:
    request = m.AdapterRequest("r", b"payload", 7)
    assert m.loopback_request_record(request) == m.loopback_request_record(request)


def test_session_fingerprint_is_order_and_content_sensitive() -> None:
    first = (m.AdapterRequest("1", b"a", 0), m.AdapterResponse("1", b"x", "m", 1, 1))
    second = (m.AdapterRequest("2", b"b", 0), m.AdapterResponse("2", b"y", "m", 1, 1))
    assert m.session_fingerprint((first, second)) == m.session_fingerprint((first, second))
    assert m.session_fingerprint((first, second)) != m.session_fingerprint((second, first))
