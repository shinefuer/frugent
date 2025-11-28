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
        return AdapterResponse(
            str(record["request_id"]),
            bytes.fromhex(str(record["content_hex"])),
            str(record["model"]),
            int(record["prompt_tokens"]),
            int(record["completion_tokens"]),
        )
    except (KeyError, ValueError) as error:
        raise AdapterError(f"adapter response record: {error}") from error
