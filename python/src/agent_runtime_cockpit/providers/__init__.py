from .anthropic import AnthropicClient
from .anthropic_cost import extract_cost
from .arena_provider import ArenaProvider
from .anthropic_estimator import (
    AnthropicCountTokensEstimator,
    EstimateFallback,
    TiktokenApproximateEstimator,
    select_estimator,
)
from .base import (
    AuthError,
    CacheBreakpoint,
    CancelledError,
    CostExtractionError,
    CostRates,
    ModelError,
    NetworkError,
    ProviderCapability,
    ProviderClient,
    ProviderError,
    ProviderFeature,
    ProviderMessage,
    ProviderRequest,
    ProviderResponse,
    RateLimitError,
    StreamChunk,
    UsageRecord,
    ValidationError,
    validate_provider_id,
)
from .budget_preflight import preflight_with_estimator
from .models_dev import bundled_openai_compatible_providers
from .openai_compatible import OpenAICompatibleClient, config_from_models_dev
from .registry import register
from .registry import _FACTORIES

__all__ = [
    "AnthropicClient",
    "AnthropicCountTokensEstimator",
    "ArenaProvider",
    "AuthError",
    "CostExtractionError",
    "EstimateFallback",
    "extract_cost",
    "select_estimator",
    "TiktokenApproximateEstimator",
    "CacheBreakpoint",
    "CancelledError",
    "CostRates",
    "ModelError",
    "NetworkError",
    "OpenAICompatibleClient",
    "ProviderCapability",
    "ProviderClient",
    "ProviderError",
    "ProviderFeature",
    "ProviderMessage",
    "ProviderRequest",
    "ProviderResponse",
    "preflight_with_estimator",
    "RateLimitError",
    "StreamChunk",
    "UsageRecord",
    "ValidationError",
    "validate_provider_id",
]

# Auto-register providers (Phase 27, Phase 28)
register("anthropic", AnthropicClient)

# Register OpenAI-compatible providers (Phase 28)
register("openai", lambda: OpenAICompatibleClient(vendor="openai"))
register("together", lambda: OpenAICompatibleClient(vendor="together"))
register("groq", lambda: OpenAICompatibleClient(vendor="groq"))
register("deepinfra", lambda: OpenAICompatibleClient(vendor="deepinfra"))
register("fireworks", lambda: OpenAICompatibleClient(vendor="fireworks"))
register("llamacpp", lambda: OpenAICompatibleClient(vendor="llamacpp"))
register("9router", lambda: OpenAICompatibleClient(vendor="9router"))
register("crofai", lambda: OpenAICompatibleClient(vendor="crofai"))

# Register Arena provider (Copilot Arena integration)
register("arena", ArenaProvider)

# R-PERF3: Lazy registration of the 109-provider bundled catalog.
# Deferred until first get() or known() call so `arc --help` and other
# CLI commands that don't need providers don't pay the parse cost.
_BUNDLED_REGISTERED = False


def _ensure_bundled_registered() -> None:
    """Register bundled OpenAI-compatible providers on first use (lazy)."""
    global _BUNDLED_REGISTERED
    if _BUNDLED_REGISTERED:
        return
    _BUNDLED_REGISTERED = True
    for _provider_id, _provider_config in bundled_openai_compatible_providers().items():
        if _provider_id not in _FACTORIES:
            register(
                _provider_id,
                lambda config=_provider_config: OpenAICompatibleClient(
                    config=config_from_models_dev(config)
                ),
            )


# Monkey-patch registry functions to trigger lazy registration on first use.
import agent_runtime_cockpit.providers.registry as _reg  # noqa: E402

_orig_get = _reg.get
_orig_known = _reg.known


def _lazy_get(name: str):  # type: ignore[no-untyped-def]
    _ensure_bundled_registered()
    return _orig_get(name)


def _lazy_known() -> list[str]:
    _ensure_bundled_registered()
    return _orig_known()


_reg.get = _lazy_get
_reg.known = _lazy_known
