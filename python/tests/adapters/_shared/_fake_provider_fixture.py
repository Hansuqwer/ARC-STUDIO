"""Deterministic fake provider for adapter tests. Wraps the existing fake-provider infrastructure."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterator


@dataclass
class FakeProviderFixture:
    tokens: list[str] = field(default_factory=list)
    network_log: list[dict] = field(default_factory=list)

    def stream_tokens(self, prompt: str) -> Iterator[str]:
        self.network_log.append({"op": "stream_tokens", "prompt": prompt})
        yield from self.tokens

    def emit_tool_call(self, name: str, args: dict) -> dict:
        self.network_log.append({"op": "tool_call", "name": name, "args": args})
        return {"tool": name, "result": "<fake>"}

    def raise_provider_error(self, code: int = 500) -> None:
        self.network_log.append({"op": "error", "code": code})
        raise RuntimeError(f"fake provider error code={code}")
