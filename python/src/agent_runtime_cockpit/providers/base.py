"""ProviderClient protocol for provider-backed runtimes."""

from __future__ import annotations

import re
import uuid
from abc import abstractmethod
from enum import StrEnum
from typing import Any, AsyncIterator, Final, Literal, Protocol, runtime_checkable

from pydantic import BaseModel, Field, field_validator, model_validator

from agent_runtime_cockpit.cli_repl.cancellation import CancellationToken


class ProviderFeature(StrEnum):
    STREAMING = "streaming"
    TOOL_USE = "tool_use"
    PROMPT_CACHING = "prompt_caching"
    VISION = "vision"
    SYSTEM_PROMPT = "system_prompt"
    STOP_SEQUENCES = "stop_sequences"
    JSON_MODE = "json_mode"


class CostRates(BaseModel):
    input_per_million: float
    output_per_million: float
    cache_write_per_million: float | None = None
    cache_read_per_million: float | None = None

    @field_validator(
        "input_per_million",
        "output_per_million",
        "cache_write_per_million",
        "cache_read_per_million",
    )
    @classmethod
    def _non_negative(cls, value: float | None) -> float | None:
        if value is not None and value < 0:
            raise ValueError("Token cost rates must be non-negative")
        return value


class ProviderCapability(BaseModel):
    schema_version: int = 1
    provider_id: str = Field(min_length=1)
    provider_name: str
    supported_models: list[str] = Field(min_length=1)
    default_model: str
    features: list[ProviderFeature] = Field(default_factory=list)
    max_context_tokens: int = Field(gt=0)
    cost_rates: dict[str, CostRates]
    timeout_seconds: int = Field(default=60, gt=0)

    @field_validator("provider_id")
    @classmethod
    def _valid_provider_id(cls, value: str) -> str:
        return validate_provider_id(value)

    @field_validator("default_model")
    @classmethod
    def _default_in_supported(cls, value: str, info: Any) -> str:
        supported = info.data.get("supported_models", [])
        if supported and value not in supported:
            raise ValueError(f"default_model {value!r} must appear in supported_models")
        return value

    @field_validator("cost_rates")
    @classmethod
    def _rates_cover_supported(cls, value: dict[str, CostRates], info: Any) -> dict[str, CostRates]:
        missing = [model for model in info.data.get("supported_models", []) if model not in value]
        if missing:
            raise ValueError(f"cost_rates missing entries for supported_models: {missing}")
        return value

    def supports(self, feature: ProviderFeature) -> bool:
        return feature in self.features


class CacheBreakpoint(BaseModel):
    position: Literal["system", "tools", "messages"]
    index: int = Field(ge=0)
    ttl_seconds: int | None = None

    @model_validator(mode="after")
    def _check_index_for_position(self) -> "CacheBreakpoint":
        if self.position in ("system", "tools") and self.index != 0:
            raise ValueError(
                f"CacheBreakpoint position={self.position!r} requires index=0, got index={self.index}"
            )
        return self


class ProviderMessage(BaseModel):
    role: Literal["system", "user", "assistant", "tool"]
    content: str
    trust: Literal["system", "user", "workspace", "untrusted"] = "user"


class ProviderRequest(BaseModel):
    call_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    model: str
    messages: list[ProviderMessage] = Field(min_length=1)
    max_tokens: int = Field(gt=0, le=200_000)
    temperature: float = Field(default=1.0, ge=0.0, le=2.0)
    stop_sequences: list[str] = Field(default_factory=list)
    cache_control: list[CacheBreakpoint] = Field(default_factory=list)
    tools: list[dict[str, Any]] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class UsageRecord(BaseModel):
    available: bool = True
    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)
    cache_creation_input_tokens: int = Field(default=0, ge=0)
    cache_read_input_tokens: int = Field(default=0, ge=0)


class ProviderResponse(BaseModel):
    call_id: str
    model: str
    content: str
    finish_reason: Literal["stop", "length", "tool_use", "content_filter", "cancelled", "error"]
    usage: UsageRecord
    tool_calls: list[dict[str, Any]] = Field(default_factory=list)
    degraded: bool = False
    degraded_reason: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class StreamChunk(BaseModel):
    call_id: str
    delta: str = ""
    chunk_type: Literal["start", "delta", "tool_use", "stop", "error"]
    payload: dict[str, Any] = Field(default_factory=dict)


class ProviderError(Exception):
    retryable = False
    user_facing_reason = ""

    def __init__(self, message: str, *, retryable: bool | None = None) -> None:
        super().__init__(message)
        if retryable is not None:
            self.retryable = retryable


class RateLimitError(ProviderError):
    retryable = True
    user_facing_reason = "Provider rate limit hit; retrying with backoff."


class NetworkError(ProviderError):
    retryable = True
    user_facing_reason = "Network error reaching provider; retrying."


class AuthError(ProviderError):
    retryable = False
    user_facing_reason = "Provider authentication failed. Check API key."


class ValidationError(ProviderError):
    retryable = False
    user_facing_reason = "Request rejected by provider. Check parameters."


class ModelError(ProviderError):
    retryable = False
    user_facing_reason = "Model rejected the request."


class CancelledError(ProviderError):
    retryable = False
    user_facing_reason = "Call cancelled."


class CostExtractionError(ProviderError):
    """Raised when a model is not found in a provider's cost rate map.

    Non-retryable — this is a configuration bug (missing rate entry for
    a known model), not a transient failure. Carries the provider ID,
    the requested model, and the list of configured models so operators
    can diagnose rate-map misconfiguration without reading source.
    """

    retryable = False

    def __init__(
        self,
        model: str,
        provider_id: str,
        configured_models: list[str],
    ) -> None:
        self.model = model
        self.provider_id = provider_id
        self.configured_models = sorted(configured_models)
        super().__init__(
            f"Model {model!r} not in rate map for provider {provider_id!r}. "
            f"Configured models: {self.configured_models}. "
            f"Add the model to ProviderCapability.cost_rates or use a "
            f"configured model."
        )


@runtime_checkable
class ProviderClient(Protocol):
    @abstractmethod
    def capabilities(self) -> ProviderCapability: ...

    @abstractmethod
    async def complete(
        self,
        request: ProviderRequest,
        *,
        cancellation_token: CancellationToken,
    ) -> ProviderResponse: ...

    @abstractmethod
    async def stream(
        self,
        request: ProviderRequest,
        *,
        cancellation_token: CancellationToken,
    ) -> AsyncIterator[StreamChunk]: ...

    @abstractmethod
    async def cancel(self, call_id: str) -> None: ...


_PROVIDER_ID_PATTERN: Final = r"^[a-z][a-z0-9-]{1,31}$"


def validate_provider_id(provider_id: str) -> str:
    if not re.match(_PROVIDER_ID_PATTERN, provider_id):
        raise ValueError(f"Invalid provider_id {provider_id!r}. Must match {_PROVIDER_ID_PATTERN}.")
    return provider_id
