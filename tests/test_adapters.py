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


def test_adapter_boundaries_reject_ambiguous_runtime_values() -> None:
    with pytest.raises(m.AdapterError, match="adapter request"):
        m.AdapterRequest("r", b"x", True)
    with pytest.raises(m.AdapterError, match="adapter request"):
        m.AdapterRequest("r", "x", 0)  # type: ignore[arg-type]
    with pytest.raises(m.AdapterError, match="adapter response"):
        m.AdapterResponse("r", b"ok", "", 1, 1)
    with pytest.raises(m.AdapterError, match="adapter response"):
        m.AdapterResponse("r", b"ok", "m", -1, 1)


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


def test_adapter_request_record_roundtrip_preserves_binary_prompt() -> None:
    request = m.AdapterRequest("r", b"\x00\xff", 12)
    assert m.request_from_record(m.request_record(request)) == request


def test_adapter_response_record_has_a_strict_schema() -> None:
    record = m.response_record(m.AdapterResponse("r", b"ok", "m", 1, 1))
    record["extra"] = "drift"
    with pytest.raises(m.AdapterError, match="unexpected fields"):
        m.response_from_record(record)
    del record["extra"]
    record["content_hex"] = 123
    with pytest.raises(m.AdapterError, match="identity fields"):
        m.response_from_record(record)


def test_recording_adapter_does_not_change_observable_response() -> None:
    inner = m.ScriptedAdapter("m", {b"p": b"r"})
    adapter = m.RecordingAdapter(inner)
    request = m.AdapterRequest("id", b"p", 0)
    assert adapter.complete(request) == inner.complete(request)
    assert adapter.records[0][0] == request


def test_replay_session_jsonl_roundtrips_in_recorded_order() -> None:
    pairs = (
        (m.AdapterRequest("a", b"one", 1), m.AdapterResponse("a", b"1", "m", 1, 1)),
        (m.AdapterRequest("b", b"two", 2), m.AdapterResponse("b", b"2", "m", 1, 1)),
    )
    encoded = m.export_session(pairs)
    assert m.import_session(encoded) == pairs
    replay = m.ReplayAdapter(m.import_session(encoded))
    assert tuple(replay.complete(request) for request, _ in pairs) == tuple(
        response for _, response in pairs
    )


def test_replay_session_rejects_truncation_and_checksum_mutation() -> None:
    pair = (m.AdapterRequest("r", b"p", 0), m.AdapterResponse("r", b"c", "m", 1, 1))
    encoded = m.export_session((pair,))
    with pytest.raises(m.AdapterError, match="newline-terminated"):
        m.import_session(encoded.rstrip(b"\n"))
    with pytest.raises(m.AdapterError, match=r"session\[0\]"):
        m.import_session(encoded.replace(b'"prompt_hex":"70"', b'"prompt_hex":"71"'))


def test_replay_session_has_stable_golden_digest() -> None:
    import hashlib

    pair = (m.AdapterRequest("r", b"p", 0), m.AdapterResponse("r", b"c", "m", 1, 1))
    assert (
        hashlib.sha256(m.export_session((pair,))).hexdigest()
        == "9bfe9129a300d1c7d247db9bfcee41b9939eff4b0074a2c842f5ea00858d0b0a"
    )


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


def test_loopback_adapter_roundtrips_against_local_mock_only() -> None:
    import threading
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

    received: list[bytes] = []
    response = m.AdapterResponse("r", b"mock result", "loopback-mock", 2, 2)
    response_body = m.response_record(response)

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:
            length = int(self.headers["Content-Length"])
            received.append(self.rfile.read(length))
            from frugent.codec import canonical_json

            body = canonical_json(response_body)
            self.send_response(200)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format: str, *args: object) -> None:
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    request = m.AdapterRequest("r", b"local prompt", 4)
    try:
        result = m.complete_loopback(f"http://127.0.0.1:{server.server_port}/complete", request)
    finally:
        server.shutdown()
        server.server_close()
        thread.join()
    assert result == response
    assert received == [m.loopback_request_record(request)]


def test_loopback_adapter_bounds_wait_and_response_size() -> None:
    request = m.AdapterRequest("r", b"p", 0)
    with pytest.raises(m.AdapterError, match="timeout"):
        m.complete_loopback("http://127.0.0.1:1", request, timeout_s=0)
    with pytest.raises(m.AdapterError, match="response limit"):
        m.complete_loopback("http://127.0.0.1:1", request, max_response_bytes=True)


def test_same_request_has_identical_loopback_payload() -> None:
    request = m.AdapterRequest("r", b"payload", 7)
    assert m.loopback_request_record(request) == m.loopback_request_record(request)


def test_session_fingerprint_is_order_and_content_sensitive() -> None:
    first = (m.AdapterRequest("1", b"a", 0), m.AdapterResponse("1", b"x", "m", 1, 1))
    second = (m.AdapterRequest("2", b"b", 0), m.AdapterResponse("2", b"y", "m", 1, 1))
    assert m.session_fingerprint((first, second)) == m.session_fingerprint((first, second))
    assert m.session_fingerprint((first, second)) != m.session_fingerprint((second, first))


def test_adapter_record_rejects_boolean_token_counts() -> None:
    response = m.AdapterResponse("r", b"ok", "scripted", 1, 1)
    record = m.response_record(response)
    record["prompt_tokens"] = True
    with pytest.raises(m.AdapterError, match="token counts"):
        m.response_from_record(record)
