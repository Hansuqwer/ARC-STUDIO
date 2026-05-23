"""ProviderClient interface — the single boundary every provider adapter implements."""

from __future__ import annotations

from typing import AsyncIterator, Iterator, Protocol, runtime_checkable

from pydantic import BaseModel


class ProviderCapabilities(BaseModel):
    streaming: bool
    tool_use: bool
    prompt_caching: bool
    vision: bool
    json_mode: bool


class ProviderMessage(BaseModel):
    role: str
    content: str


class ProviderToolCall(BaseModel):
    name: str
    arguments: dict


@runtime_checkable
class ProviderClient(Protocol):
    """Single boundary all provider-SDK adapters conform to.

    Every method must route through enforce_paid_call_gate and
    enforce_network_gate at the call/transport boundary.
    """

    name: str

    def capabilities(self) -> ProviderCapabilities: ...

    def complete(
        self, messages: list[ProviderMessage], *, model: str, max_tokens: int
    ) -> ProviderMessage: ...

    def stream(
        self, messages: list[ProviderMessage], *, model: str, max_tokens: int
    ) -> Iterator[str]: ...

    async def astream(
        self, messages: list[ProviderMessage], *, model: str, max_tokens: int
    ) -> AsyncIterator[str]: ...

    def stream_tool_calls(
        self, messages: list[ProviderMessage], tools: list[dict], *, model: str
    ) -> Iterator[ProviderToolCall]: ...
