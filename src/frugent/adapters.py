"""Offline scripted, replay, and local-loopback model adapter protocols."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable


class AdapterError(RuntimeError):
    """Raised for invalid adapter requests or replay mismatches."""


@dataclass(frozen=True, slots=True)
class AdapterRequest:
    request_id: str
    prompt: bytes
    seed: int

    def __post_init__(self) -> None:
        if (
            not isinstance(self.request_id, str)
            or not self.request_id
            or not isinstance(self.prompt, bytes)
            or isinstance(self.seed, bool)
            or not isinstance(self.seed, int)
            or self.seed < 0
        ):
            raise AdapterError("adapter request: invalid id or seed")


@dataclass(frozen=True, slots=True)
class AdapterResponse:
    request_id: str
    content: bytes
    model: str
    prompt_tokens: int
    completion_tokens: int

    def __post_init__(self) -> None:
        counts = (self.prompt_tokens, self.completion_tokens)
        if (
            not isinstance(self.request_id, str)
            or not self.request_id
            or not isinstance(self.content, bytes)
            or not isinstance(self.model, str)
            or not self.model
            or any(
                isinstance(value, bool) or not isinstance(value, int) or value < 0
                for value in counts
            )
        ):
            raise AdapterError(
                "adapter response: invalid identity, content, model, or token counts"
            )


@runtime_checkable
class Adapter(Protocol):
    def complete(self, request: AdapterRequest) -> AdapterResponse: ...


class ScriptedAdapter:
    """Map exact prompt bytes to planted responses without model inference."""

    def __init__(self, model: str, scripts: dict[bytes, bytes]) -> None:
        if not model:
            raise AdapterError("scripted adapter: model must be non-empty")
        self.model = model
        self.scripts = dict(scripts)

    def complete(self, request: AdapterRequest) -> AdapterResponse:
        if request.prompt not in self.scripts:
            raise AdapterError("scripted adapter: prompt is not planted")
        content = self.scripts[request.prompt]
        return AdapterResponse(
            request.request_id,
            content,
            self.model,
            len(request.prompt.split()),
            len(content.split()),
        )


class ReplayAdapter:
    """Consume exact request-response pairs in recorded order."""

    def __init__(self, records: tuple[tuple[AdapterRequest, AdapterResponse], ...]) -> None:
        self.records = records
        self.cursor = 0

    def complete(self, request: AdapterRequest) -> AdapterResponse:
        if self.cursor >= len(self.records):
            raise AdapterError("replay adapter: session exhausted")
        expected, response = self.records[self.cursor]
        if request != expected or response.request_id != request.request_id:
            raise AdapterError("replay adapter: request mismatch")
        self.cursor += 1
        return response


def response_record(response: AdapterResponse) -> dict[str, object]:
    return {
        "request_id": response.request_id,
        "content_hex": response.content.hex(),
        "model": response.model,
        "prompt_tokens": response.prompt_tokens,
        "completion_tokens": response.completion_tokens,
    }


def request_record(request: AdapterRequest) -> dict[str, object]:
    """Return the version-independent logical request payload."""
    return {
        "request_id": request.request_id,
        "prompt_hex": request.prompt.hex(),
        "seed": request.seed,
    }


def request_from_record(record: dict[str, object]) -> AdapterRequest:
    """Decode one strict request record without coercing field types."""
    if set(record) != {"request_id", "prompt_hex", "seed"}:
        raise AdapterError("adapter request record: unexpected fields")
    request_id, prompt_hex, seed = record["request_id"], record["prompt_hex"], record["seed"]
    if (
        not isinstance(request_id, str)
        or not isinstance(prompt_hex, str)
        or isinstance(seed, bool)
        or not isinstance(seed, int)
    ):
        raise AdapterError("adapter request record: invalid field types")
    try:
        return AdapterRequest(request_id, bytes.fromhex(prompt_hex), seed)
    except ValueError as error:
        raise AdapterError(f"adapter request record: {error}") from error


def response_from_record(record: dict[str, object]) -> AdapterResponse:
    expected = {
        "request_id",
        "content_hex",
        "model",
        "prompt_tokens",
        "completion_tokens",
    }
    if set(record) != expected:
        raise AdapterError("adapter response record: unexpected fields")
    try:
        request_id, model = record["request_id"], record["model"]
        content_hex = record["content_hex"]
        prompt_tokens, completion_tokens = record["prompt_tokens"], record["completion_tokens"]
        if (
            not isinstance(request_id, str)
            or not isinstance(model, str)
            or not isinstance(content_hex, str)
        ):
            raise AdapterError("adapter response record: identity fields must be strings")
        if (
            not isinstance(prompt_tokens, int)
            or isinstance(prompt_tokens, bool)
            or not isinstance(completion_tokens, int)
            or isinstance(completion_tokens, bool)
        ):
            raise AdapterError("adapter response record: token counts must be integers")
        return AdapterResponse(
            request_id,
            bytes.fromhex(content_hex),
            model,
            prompt_tokens,
            completion_tokens,
        )
    except (KeyError, ValueError) as error:
        raise AdapterError(f"adapter response record: {error}") from error


def export_session(records: tuple[tuple[AdapterRequest, AdapterResponse], ...]) -> bytes:
    """Export ordered replay pairs as independently checksummed JSONL."""
    from frugent.codec import encode_envelope

    lines = [encode_envelope("frugent.adapter.session.header", 1, {"records": len(records)})]
    for sequence, (request, response) in enumerate(records):
        if response.request_id != request.request_id:
            raise AdapterError(f"adapter session[{sequence}]: response id mismatch")
        lines.append(
            encode_envelope(
                "frugent.adapter.session.record",
                1,
                {
                    "sequence": sequence,
                    "request": request_record(request),
                    "response": response_record(response),
                },
            )
        )
    return b"\n".join(lines) + b"\n"


def import_session(data: bytes | str) -> tuple[tuple[AdapterRequest, AdapterResponse], ...]:
    """Verify and decode a complete replay session JSONL stream."""
    from frugent.codec import decode_envelope

    raw = data.encode() if isinstance(data, str) else data
    if not raw or not raw.endswith(b"\n"):
        raise AdapterError("adapter session: expected complete newline-terminated data")
    lines = raw.splitlines()
    try:
        version, header = decode_envelope(lines[0], "frugent.adapter.session.header")
    except ValueError as error:
        raise AdapterError(f"adapter session header: {error}") from error
    if (
        version != 1
        or not isinstance(header, dict)
        or set(header) != {"records"}
        or isinstance(header["records"], bool)
        or not isinstance(header["records"], int)
        or header["records"] < 0
        or header["records"] != len(lines) - 1
    ):
        raise AdapterError("adapter session header: invalid record count")
    records: list[tuple[AdapterRequest, AdapterResponse]] = []
    for expected_sequence, line in enumerate(lines[1:]):
        try:
            item_version, item = decode_envelope(line, "frugent.adapter.session.record")
        except ValueError as error:
            raise AdapterError(f"adapter session[{expected_sequence}]: {error}") from error
        if item_version != 1 or not isinstance(item, dict):
            raise AdapterError(f"adapter session[{expected_sequence}]: unsupported record")
        records.append(_session_pair(item, expected_sequence))
    return tuple(records)


def _session_pair(
    record: dict[str, Any], expected_sequence: int
) -> tuple[AdapterRequest, AdapterResponse]:
    if set(record) != {"sequence", "request", "response"}:
        raise AdapterError(f"adapter session[{expected_sequence}]: unexpected fields")
    if record["sequence"] != expected_sequence or isinstance(record["sequence"], bool):
        raise AdapterError(f"adapter session[{expected_sequence}]: sequence mismatch")
    request_data, response_data = record["request"], record["response"]
    if not isinstance(request_data, dict) or not isinstance(response_data, dict):
        raise AdapterError(f"adapter session[{expected_sequence}]: invalid payload")
    request = request_from_record(request_data)
    response = response_from_record(response_data)
    if request.request_id != response.request_id:
        raise AdapterError(f"adapter session[{expected_sequence}]: response id mismatch")
    return request, response


class RecordingAdapter:
    """Wrap an adapter and retain exact request-response pairs."""

    def __init__(self, inner: Adapter) -> None:
        self.inner = inner
        self.records: list[tuple[AdapterRequest, AdapterResponse]] = []

    def complete(self, request: AdapterRequest) -> AdapterResponse:
        response = self.inner.complete(request)
        self.records.append((request, response))
        return response


def loopback_request_record(request: AdapterRequest) -> bytes:
    """Encode the local HTTP adapter request without credentials or endpoints."""
    from frugent.codec import canonical_json

    return canonical_json(
        {"request_id": request.request_id, "prompt_hex": request.prompt.hex(), "seed": request.seed}
    )


def loopback_response(data: bytes) -> AdapterResponse:
    from frugent.codec import decode_json

    decoded = decode_json(data)
    if not isinstance(decoded, dict):
        raise AdapterError("loopback response: expected object")
    return response_from_record(decoded)


def complete_loopback(url: str, request: AdapterRequest, timeout_s: float = 2.0) -> AdapterResponse:
    """POST to an explicitly supplied local HTTP mock URL."""
    from urllib.parse import urlparse
    from urllib.request import Request, urlopen

    parsed = urlparse(url)
    if parsed.hostname not in {"127.0.0.1", "localhost", "::1"} or parsed.scheme != "http":
        raise AdapterError("loopback adapter: only local HTTP mock URLs are allowed")
    message = Request(
        url,
        data=loopback_request_record(request),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(message, timeout=timeout_s) as response:
            result = loopback_response(response.read())
    except OSError as error:
        raise AdapterError(f"loopback adapter: local request failed: {error}") from error
    if result.request_id != request.request_id:
        raise AdapterError("loopback adapter: response id mismatch")
    return result


def session_fingerprint(records: tuple[tuple[AdapterRequest, AdapterResponse], ...]) -> str:
    from frugent.codec import payload_digest

    logical = [
        {
            "request": {
                "id": request.request_id,
                "prompt": request.prompt.hex(),
                "seed": request.seed,
            },
            "response": response_record(response),
        }
        for request, response in records
    ]
    return payload_digest(logical)
