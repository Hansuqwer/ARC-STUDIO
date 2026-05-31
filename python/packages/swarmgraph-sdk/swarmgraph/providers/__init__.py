from __future__ import annotations

import uuid
from typing import Any, Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field


class ProviderMessage(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    role: Literal["system", "user", "assistant", "tool"]
    content: str
    trust: Literal["system", "user", "workspace", "untrusted"] = "user"


class ProviderRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    call_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    model: str
    messages: list[ProviderMessage] = Field(min_length=1)
    max_tokens: int = Field(default=1024, gt=0, le=200_000)
    temperature: float = Field(default=1.0, ge=0.0, le=2.0)
    metadata: dict[str, Any] = Field(default_factory=dict)


class UsageRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    available: bool = True
    input_tokens: int = Field(default=0, ge=0)
    output_tokens: int = Field(default=0, ge=0)
    cache_creation_input_tokens: int = Field(default=0, ge=0)
    cache_read_input_tokens: int = Field(default=0, ge=0)


class ProviderResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    call_id: str
    model: str
    content: str
    finish_reason: Literal["stop", "length", "tool_use", "content_filter", "cancelled", "error"]
    usage: UsageRecord = Field(default_factory=UsageRecord)
    tool_calls: list[dict[str, Any]] = Field(default_factory=list)
    degraded: bool = False
    degraded_reason: str | None = None


class CostRates(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    input_per_million: float = Field(ge=0)
    output_per_million: float = Field(ge=0)
    cache_write_per_million: float | None = Field(default=None, ge=0)
    cache_read_per_million: float | None = Field(default=None, ge=0)


class ProviderCapability(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    provider_id: str = Field(min_length=1)
    provider_name: str = Field(min_length=1)
    supported_models: list[str] = Field(min_length=1)
    default_model: str = Field(min_length=1)
    max_context_tokens: int = Field(default=4096, gt=0)
    cost_rates: dict[str, CostRates] = Field(default_factory=dict)


class CancellationTokenLike(Protocol):
    is_cancelled: Any

    def raise_if_cancelled(self) -> None: ...


class Provider(Protocol):
    def capabilities(self) -> ProviderCapability: ...

    async def complete(
        self,
        request: ProviderRequest,
        *,
        cancellation_token: CancellationTokenLike,
    ) -> ProviderResponse: ...


__all__ = [
    "CancellationTokenLike",
    "CostRates",
    "Provider",
    "ProviderCapability",
    "ProviderMessage",
    "ProviderRequest",
    "ProviderResponse",
    "UsageRecord",
]
