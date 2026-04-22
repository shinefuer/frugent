"""Offline scripted, replay, and local-loopback model adapter protocols."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


class AdapterError(RuntimeError):
    """Raised for invalid adapter requests or replay mismatches."""


@dataclass(frozen=True, slots=True)
class AdapterRequest:
    request_id: str
    prompt: bytes
    seed: int

    def __post_init__(self) -> None:
        if not self.request_id or self.seed < 0:
            raise AdapterError("adapter request: invalid id or seed")


@dataclass(frozen=True, slots=True)
class AdapterResponse:
    request_id: str
    content: bytes
    model: str
    prompt_tokens: int
    completion_tokens: int


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


def response_from_record(record: dict[str, object]) -> AdapterResponse:
    try:
        request_id, model = record["request_id"], record["model"]
        prompt_tokens, completion_tokens = record["prompt_tokens"], record["completion_tokens"]
        if not isinstance(request_id, str) or not isinstance(model, str):
            raise AdapterError("adapter response record: identity fields must be strings")
        if not all(
            isinstance(value, int) and not isinstance(value, bool)
            for value in (prompt_tokens, completion_tokens)
        ):
            raise AdapterError("adapter response record: token counts must be integers")
        return AdapterResponse(
            request_id,
            bytes.fromhex(str(record["content_hex"])),
            model,
            prompt_tokens,
            completion_tokens,
        )
    except (KeyError, ValueError) as error:
        raise AdapterError(f"adapter response record: {error}") from error


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
