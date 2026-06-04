"""OpenAI-compatible ProviderClient implementation.

Supports multiple vendors (OpenAI, Together, Groq, DeepInfra, Fireworks, llama.cpp)
through a single adapter with configurable base_url and per-vendor allowlists.

The client is dependency-injected/testable and imports the OpenAI SDK lazily
so default test suites never require credentials or make network calls.
"""

from __future__ import annotations

import json
import os
from collections.abc import Callable
from typing import Any, AsyncIterator, Literal, TypeAlias, cast

from agent_runtime_cockpit.cli_repl.cancellation import CancellationToken, Cancelled

from .base import (
    AuthError,
    CancelledError,
    CostRates,
    ModelError,
    NetworkError,
    ProviderCapability,
    ProviderMessage,
    ProviderFeature,
    ProviderRequest,
    ProviderResponse,
    RateLimitError,
    StreamChunk,
    UsageRecord,
    ValidationError,
)
from .models_dev import (
    ModelsDevProviderConfig,
    cost_rates,
    max_context_tokens,
    provider_features,
    sanitize_provider_env_id,
    select_default_model,
)


OpenAICompatibleConfig: TypeAlias = dict[str, Any]

# Vendor configuration
VendorName = Literal[
    "openai",
    "together",
    "groq",
    "deepinfra",
    "fireworks",
    "llamacpp",
    "9router",
    "crofai",
    "gemini",
    "deepseek",
    "qwen",
    "kimi",
    "glm",
    "mimo",
    "minimax",
]

VENDOR_CONFIGS = {
    "openai": {
        "base_url": "https://api.openai.com/v1",
        "default_model": "gpt-4o-mini",
        "supported_models": [
            "gpt-5.5",
            "gpt-5.4",
            "gpt-5.4-mini",
            "gpt-5.4-nano",
            "gpt-5.2",
            "gpt-5",
            "gpt-4.1",
            "gpt-4.1-mini",
            "gpt-4.1-nano",
            "gpt-4o",
            "gpt-4o-mini",
            "gpt-4-turbo",
            "gpt-3.5-turbo",
        ],
        "features": [
            ProviderFeature.STREAMING,
            ProviderFeature.TOOL_USE,
            ProviderFeature.VISION,
            ProviderFeature.JSON_MODE,
        ],
        "cost_rates": {
            # GPT-5.x current-gen: 90% cache discount (0.10× input) per pricing-snapshot-2026Q2.md §1
            "gpt-5.5": CostRates(
                input_per_million=5.0, output_per_million=30.0, cache_read_per_million=0.50
            ),
            "gpt-5.4": CostRates(
                input_per_million=2.5, output_per_million=15.0, cache_read_per_million=0.25
            ),
            "gpt-5.4-mini": CostRates(
                input_per_million=0.75, output_per_million=4.50, cache_read_per_million=0.075
            ),
            "gpt-5.4-nano": CostRates(
                input_per_million=0.20, output_per_million=1.25, cache_read_per_million=0.02
            ),
            "gpt-5.2": CostRates(
                input_per_million=1.75, output_per_million=14.0, cache_read_per_million=0.175
            ),
            "gpt-5": CostRates(
                input_per_million=1.25, output_per_million=10.0, cache_read_per_million=0.125
            ),
            # GPT-4.1 family: 75% cache discount (0.25× input)
            "gpt-4.1": CostRates(
                input_per_million=2.0, output_per_million=8.0, cache_read_per_million=0.50
            ),
            "gpt-4.1-mini": CostRates(
                input_per_million=0.40, output_per_million=1.60, cache_read_per_million=0.10
            ),
            "gpt-4.1-nano": CostRates(
                input_per_million=0.10, output_per_million=0.40, cache_read_per_million=0.025
            ),
            # Legacy: gpt-4o-mini retains 50% cache discount; gpt-4o legacy rates
            "gpt-4o": CostRates(input_per_million=2.50, output_per_million=10.0),
            "gpt-4o-mini": CostRates(
                input_per_million=0.15, output_per_million=0.60, cache_read_per_million=0.075
            ),
            "gpt-4-turbo": CostRates(input_per_million=10.0, output_per_million=30.0),
            "gpt-3.5-turbo": CostRates(input_per_million=0.50, output_per_million=1.50),
        },
    },
    "together": {
        "base_url": "https://api.together.xyz/v1",
        "default_model": "meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo",
        "supported_models": [
            "meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo",
            "meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo",
        ],
        "features": [ProviderFeature.STREAMING, ProviderFeature.TOOL_USE],
        "cost_rates": {
            "meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo": CostRates(
                input_per_million=0.20, output_per_million=0.20
            ),
            "meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo": CostRates(
                input_per_million=0.88, output_per_million=0.88
            ),
        },
    },
    "groq": {
        "base_url": "https://api.groq.com/openai/v1",
        "default_model": "llama-3.3-70b-versatile",
        "supported_models": ["llama-3.3-70b-versatile", "llama-3.1-8b-instant"],
        "features": [ProviderFeature.STREAMING, ProviderFeature.TOOL_USE],
        "cost_rates": {
            "llama-3.3-70b-versatile": CostRates(input_per_million=0.59, output_per_million=0.79),
            "llama-3.1-8b-instant": CostRates(input_per_million=0.05, output_per_million=0.08),
        },
    },
    "deepinfra": {
        "base_url": "https://api.deepinfra.com/v1/openai",
        "default_model": "meta-llama/Meta-Llama-3.1-8B-Instruct",
        "supported_models": ["meta-llama/Meta-Llama-3.1-8B-Instruct"],
        "features": [ProviderFeature.STREAMING],
        "cost_rates": {
            "meta-llama/Meta-Llama-3.1-8B-Instruct": CostRates(
                input_per_million=0.08, output_per_million=0.08
            )
        },
    },
    "fireworks": {
        "base_url": "https://api.fireworks.ai/inference/v1",
        "default_model": "accounts/fireworks/models/llama-v3p1-8b-instruct",
        "supported_models": ["accounts/fireworks/models/llama-v3p1-8b-instruct"],
        "features": [ProviderFeature.STREAMING, ProviderFeature.TOOL_USE],
        "cost_rates": {
            "accounts/fireworks/models/llama-v3p1-8b-instruct": CostRates(
                input_per_million=0.20, output_per_million=0.20
            )
        },
    },
    "llamacpp": {
        "base_url": "http://localhost:8080/v1",
        "default_model": "local-model",
        "supported_models": ["local-model"],
        "features": [ProviderFeature.STREAMING],
        "cost_rates": {"local-model": CostRates(input_per_million=0.0, output_per_million=0.0)},
    },
    "9router": {
        "base_url": "http://127.0.0.1:20128/v1",
        "default_model": "ag/gemini-3.5-flash-extra-low",
        "supported_models": [
            "ag/gemini-3.5-flash-extra-low",
            "qwen/qwen3-coder",
            "qwen/qwen-plus",
            "qwen/qwen-max",
        ],
        "features": [ProviderFeature.STREAMING, ProviderFeature.TOOL_USE],
        "cost_rates": {
            "ag/gemini-3.5-flash-extra-low": CostRates(
                input_per_million=0.0, output_per_million=0.0
            ),
            "qwen/qwen3-coder": CostRates(input_per_million=0.0, output_per_million=0.0),
            "qwen/qwen-plus": CostRates(input_per_million=0.0, output_per_million=0.0),
            "qwen/qwen-max": CostRates(input_per_million=0.0, output_per_million=0.0),
        },
    },
    "crofai": {
        # CrofAI unified proxy — prices from /v1/models API 2026-06-05.
        # Covers all Chinese-lab models under one CROFAI key. Not OpenRouter.
        "base_url": "https://crof.ai/v1",
        "default_model": "deepseek-v4-flash",
        "supported_models": [
            "deepseek-v4-pro",
            "deepseek-v4-pro-lightning",
            "deepseek-v4-flash",
            "deepseek-v3.2",
            "kimi-k2.6",
            "kimi-k2.5",
            "kimi-k2.5-lightning",
            "glm-5.1",
            "glm-5",
            "glm-4.7",
            "glm-4.7-flash",
            "mimo-v2.5-pro",
            "minimax-m2.5",
            "qwen3.5-397b-a17b",
            "qwen3.5-9b",
            "qwen3.6-27b",
        ],
        "features": [ProviderFeature.STREAMING, ProviderFeature.TOOL_USE, ProviderFeature.VISION],
        "cost_rates": {
            "deepseek-v4-pro": CostRates(
                input_per_million=0.35,
                output_per_million=0.80,
                cache_read_per_million=0.003,
                cache_field_names={"hit": "prompt_cache_hit_tokens"},
            ),
            "deepseek-v4-pro-lightning": CostRates(
                input_per_million=0.80,
                output_per_million=1.60,
                cache_read_per_million=0.02,
                cache_field_names={"hit": "prompt_cache_hit_tokens"},
            ),
            "deepseek-v4-flash": CostRates(
                input_per_million=0.12,
                output_per_million=0.21,
                cache_read_per_million=0.003,
                cache_field_names={"hit": "prompt_cache_hit_tokens"},
            ),
            "deepseek-v3.2": CostRates(
                input_per_million=0.18,
                output_per_million=0.35,
                cache_read_per_million=0.04,
                cache_field_names={"hit": "prompt_cache_hit_tokens"},
                pricing_valid_until="2026-07-24",
            ),
            "kimi-k2.6": CostRates(input_per_million=0.50, output_per_million=1.99),
            "kimi-k2.5": CostRates(input_per_million=0.35, output_per_million=1.70),
            "kimi-k2.5-lightning": CostRates(input_per_million=1.00, output_per_million=3.00),
            "glm-5.1": CostRates(
                input_per_million=0.45, output_per_million=2.15, tokenizer_family="glm"
            ),
            "glm-5": CostRates(
                input_per_million=0.48, output_per_million=1.90, tokenizer_family="glm"
            ),
            "glm-4.7": CostRates(
                input_per_million=0.25, output_per_million=1.10, tokenizer_family="glm"
            ),
            "glm-4.7-flash": CostRates(
                input_per_million=0.04,
                output_per_million=0.30,
                tokenizer_family="glm",
                is_free_tier=True,
            ),
            "mimo-v2.5-pro": CostRates(
                input_per_million=0.40, output_per_million=0.80, cache_read_per_million=0.08
            ),
            "minimax-m2.5": CostRates(input_per_million=0.11, output_per_million=0.95),
            "qwen3.5-397b-a17b": CostRates(
                input_per_million=0.35, output_per_million=1.75, tokenizer_family="qwen"
            ),
            "qwen3.5-9b": CostRates(
                input_per_million=0.04, output_per_million=0.15, tokenizer_family="qwen"
            ),
            "qwen3.6-27b": CostRates(
                input_per_million=0.20, output_per_million=1.50, tokenizer_family="qwen"
            ),
        },
    },
    # ── DeepSeek native API — prices cross-checked with OpenRouter 2026-06-05 ──
    "deepseek": {
        "base_url": "https://api.deepseek.com/v1",
        "default_model": "deepseek-v4-flash",
        "supported_models": [
            "deepseek-v4-pro",
            "deepseek-v4-flash",
            "deepseek-v3.2",
            "deepseek-r1",
            "deepseek-r1-0528",
            "deepseek-chat",
        ],
        "features": [ProviderFeature.STREAMING, ProviderFeature.TOOL_USE],
        "cost_rates": {
            "deepseek-v4-pro": CostRates(
                input_per_million=0.435,
                output_per_million=0.87,
                cache_read_per_million=0.0036,
                cache_field_names={
                    "hit": "prompt_cache_hit_tokens",
                    "miss": "prompt_cache_miss_tokens",
                },
            ),
            "deepseek-v4-flash": CostRates(
                input_per_million=0.098,
                output_per_million=0.197,
                cache_read_per_million=0.020,
                cache_field_names={
                    "hit": "prompt_cache_hit_tokens",
                    "miss": "prompt_cache_miss_tokens",
                },
            ),
            "deepseek-v3.2": CostRates(
                input_per_million=0.229,
                output_per_million=0.343,
                cache_field_names={
                    "hit": "prompt_cache_hit_tokens",
                    "miss": "prompt_cache_miss_tokens",
                },
            ),
            "deepseek-r1": CostRates(
                input_per_million=0.70,
                output_per_million=2.50,
                cache_field_names={
                    "hit": "prompt_cache_hit_tokens",
                    "miss": "prompt_cache_miss_tokens",
                },
            ),
            "deepseek-r1-0528": CostRates(
                input_per_million=0.50,
                output_per_million=2.15,
                cache_read_per_million=0.35,
                cache_field_names={
                    "hit": "prompt_cache_hit_tokens",
                    "miss": "prompt_cache_miss_tokens",
                },
            ),
            "deepseek-chat": CostRates(
                input_per_million=0.20,
                output_per_million=0.80,
                cache_field_names={
                    "hit": "prompt_cache_hit_tokens",
                    "miss": "prompt_cache_miss_tokens",
                },
                auto_route_to="deepseek-v4-flash",
            ),
        },
    },
    # ── Qwen (Alibaba DashScope) — prices cross-checked with OpenRouter 2026-06-05 ──
    "qwen": {
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "default_model": "qwen3-235b-a22b",
        "supported_models": [
            "qwen3.7-max",
            "qwen3.7-plus",
            "qwen3-235b-a22b",
            "qwen3-32b",
            "qwen3-14b",
            "qwen3-8b",
            "qwen3-30b-a3b",
            "qwen3-coder",
            "qwen-plus",
            "qwen2.5-72b-instruct",
        ],
        "features": [ProviderFeature.STREAMING, ProviderFeature.TOOL_USE, ProviderFeature.VISION],
        "cost_rates": {
            "qwen3.7-max": CostRates(
                input_per_million=1.25,
                output_per_million=3.75,
                cache_read_per_million=0.25,
                tokenizer_family="qwen",
            ),
            "qwen3.7-plus": CostRates(
                input_per_million=0.40,
                output_per_million=1.60,
                cache_read_per_million=0.08,
                tokenizer_family="qwen",
            ),
            "qwen3-235b-a22b": CostRates(
                input_per_million=0.455, output_per_million=1.82, tokenizer_family="qwen"
            ),
            "qwen3-32b": CostRates(
                input_per_million=0.08, output_per_million=0.28, tokenizer_family="qwen"
            ),
            "qwen3-14b": CostRates(
                input_per_million=0.10, output_per_million=0.24, tokenizer_family="qwen"
            ),
            "qwen3-8b": CostRates(
                input_per_million=0.05,
                output_per_million=0.40,
                cache_read_per_million=0.05,
                tokenizer_family="qwen",
            ),
            "qwen3-30b-a3b": CostRates(
                input_per_million=0.09, output_per_million=0.45, tokenizer_family="qwen"
            ),
            "qwen3-coder": CostRates(
                input_per_million=0.22, output_per_million=1.80, tokenizer_family="qwen"
            ),
            "qwen-plus": CostRates(
                input_per_million=0.26,
                output_per_million=0.78,
                cache_read_per_million=0.052,
                tokenizer_family="qwen",
            ),
            "qwen2.5-72b-instruct": CostRates(
                input_per_million=0.36, output_per_million=0.40, tokenizer_family="qwen"
            ),
        },
    },
    # ── Kimi (Moonshot AI) — prices cross-checked with OpenRouter 2026-06-05 ──
    "kimi": {
        "base_url": "https://api.moonshot.ai/v1",
        "default_model": "kimi-k2.5",
        "supported_models": [
            "kimi-k2.6",
            "kimi-k2.5",
            "kimi-k2",
            "kimi-k2-0905",
            "kimi-k2-thinking",
        ],
        "features": [ProviderFeature.STREAMING, ProviderFeature.TOOL_USE, ProviderFeature.VISION],
        "cost_rates": {
            "kimi-k2.6": CostRates(
                input_per_million=0.684, output_per_million=3.42, cache_read_per_million=0.144
            ),
            "kimi-k2.5": CostRates(
                input_per_million=0.40, output_per_million=1.90, cache_read_per_million=0.09
            ),
            "kimi-k2": CostRates(input_per_million=0.57, output_per_million=2.30),
            "kimi-k2-0905": CostRates(
                input_per_million=0.60,
                output_per_million=2.50,
                pricing_valid_until="2026-05-25",
                auto_route_to="kimi-k2.5",
            ),
            "kimi-k2-thinking": CostRates(input_per_million=0.60, output_per_million=2.50),
        },
    },
    # ── GLM (Zhipu / Z.AI) — prices cross-checked with OpenRouter 2026-06-05 ──
    "glm": {
        "base_url": "https://open.bigmodel.cn/api/paas/v4/",
        "default_model": "glm-4.7",
        "supported_models": [
            "glm-5.1",
            "glm-5v-turbo",
            "glm-5-turbo",
            "glm-5",
            "glm-4.7",
            "glm-4.7-flash",
            "glm-4.6v",
            "glm-4.6",
            "glm-4.5v",
            "glm-4.5",
            "glm-4.5-air",
            "glm-4-32b",
        ],
        "features": [ProviderFeature.STREAMING, ProviderFeature.TOOL_USE, ProviderFeature.VISION],
        "cost_rates": {
            "glm-5.1": CostRates(
                input_per_million=0.98,
                output_per_million=3.08,
                cache_read_per_million=0.182,
                tokenizer_family="glm",
            ),
            "glm-5v-turbo": CostRates(
                input_per_million=1.20,
                output_per_million=4.00,
                cache_read_per_million=0.24,
                tokenizer_family="glm",
            ),
            "glm-5-turbo": CostRates(
                input_per_million=1.20,
                output_per_million=4.00,
                cache_read_per_million=0.24,
                tokenizer_family="glm",
            ),
            "glm-5": CostRates(
                input_per_million=0.60,
                output_per_million=1.92,
                cache_read_per_million=0.12,
                tokenizer_family="glm",
            ),
            "glm-4.7": CostRates(
                input_per_million=0.40,
                output_per_million=1.75,
                cache_read_per_million=0.08,
                tokenizer_family="glm",
            ),
            "glm-4.7-flash": CostRates(
                input_per_million=0.06,
                output_per_million=0.40,
                cache_read_per_million=0.01,
                tokenizer_family="glm",
            ),
            "glm-4.6v": CostRates(
                input_per_million=0.30,
                output_per_million=0.90,
                cache_read_per_million=0.05,
                tokenizer_family="glm",
            ),
            "glm-4.6": CostRates(
                input_per_million=0.43,
                output_per_million=1.74,
                cache_read_per_million=0.08,
                tokenizer_family="glm",
            ),
            "glm-4.5v": CostRates(
                input_per_million=0.60,
                output_per_million=1.80,
                cache_read_per_million=0.11,
                tokenizer_family="glm",
            ),
            "glm-4.5": CostRates(
                input_per_million=0.60,
                output_per_million=2.20,
                cache_read_per_million=0.11,
                tokenizer_family="glm",
            ),
            "glm-4.5-air": CostRates(
                input_per_million=0.125,
                output_per_million=0.85,
                cache_read_per_million=0.06,
                tokenizer_family="glm",
                is_free_tier=True,
            ),
            "glm-4-32b": CostRates(
                input_per_million=0.10, output_per_million=0.10, tokenizer_family="glm"
            ),
        },
    },
    # ── MiMo (Xiaomi) — prices cross-checked with OpenRouter 2026-06-05 ──
    "mimo": {
        "base_url": "https://api.xiaomimimo.com/v1",
        "default_model": "mimo-v2.5-pro",
        "supported_models": ["mimo-v2.5-pro", "mimo-v2.5", "mimo-v2-flash"],
        "features": [ProviderFeature.STREAMING, ProviderFeature.TOOL_USE, ProviderFeature.VISION],
        "cost_rates": {
            "mimo-v2.5-pro": CostRates(
                input_per_million=0.435, output_per_million=0.87, cache_read_per_million=0.0036
            ),
            "mimo-v2.5": CostRates(
                input_per_million=0.14, output_per_million=0.28, cache_read_per_million=0.0028
            ),
            "mimo-v2-flash": CostRates(
                input_per_million=0.10, output_per_million=0.30, cache_read_per_million=0.01
            ),
        },
    },
    # ── MiniMax — prices cross-checked with OpenRouter 2026-06-05 ──
    "minimax": {
        "base_url": "https://api.minimax.io/v1",
        "default_model": "minimax-m2.5",
        "supported_models": [
            "minimax-m3",
            "minimax-m2.7",
            "minimax-m2.5",
            "minimax-m2-her",
            "minimax-m2.1",
            "minimax-m1",
        ],
        "features": [ProviderFeature.STREAMING, ProviderFeature.TOOL_USE],
        "cost_rates": {
            "minimax-m3": CostRates(
                input_per_million=0.30, output_per_million=1.20, cache_read_per_million=0.06
            ),
            "minimax-m2.7": CostRates(input_per_million=0.279, output_per_million=1.20),
            "minimax-m2.5": CostRates(input_per_million=0.15, output_per_million=1.15),
            "minimax-m2-her": CostRates(
                input_per_million=0.30, output_per_million=1.20, cache_read_per_million=0.03
            ),
            "minimax-m2.1": CostRates(
                input_per_million=0.29, output_per_million=0.95, cache_read_per_million=0.03
            ),
            "minimax-m1": CostRates(input_per_million=0.40, output_per_million=2.20),
        },
    },
    "gemini": {
        # Google AI Studio OpenAI-compatible endpoint (requires GEMINI_API_KEY)
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
        "default_model": "gemini-2.5-flash",
        "supported_models": [
            "gemini-2.5-pro",
            "gemini-2.5-flash",
            "gemini-2.5-flash-lite",
            "gemini-3-flash",
            "gemini-3.5-flash",
        ],
        "features": [ProviderFeature.STREAMING, ProviderFeature.TOOL_USE, ProviderFeature.VISION],
        # Rates per pricing-snapshot-2026Q2.md §1 (≤200K context window tier)
        "cost_rates": {
            "gemini-2.5-pro": CostRates(
                input_per_million=1.25, output_per_million=10.0, cache_read_per_million=0.125
            ),
            "gemini-2.5-flash": CostRates(
                input_per_million=0.30, output_per_million=2.50, cache_read_per_million=0.03
            ),
            "gemini-2.5-flash-lite": CostRates(
                input_per_million=0.10, output_per_million=0.40, cache_read_per_million=0.01
            ),
            "gemini-3-flash": CostRates(
                input_per_million=0.50, output_per_million=3.00, cache_read_per_million=0.05
            ),
            "gemini-3.5-flash": CostRates(
                input_per_million=1.50, output_per_million=9.00, cache_read_per_million=0.15
            ),
        },
    },
}


def _maybe_compact(request: "ProviderRequest") -> "ProviderRequest":
    """Apply R-02 compaction if enabled and context is near the limit."""
    import os

    if os.environ.get("ARC_COMPACTION_ENABLED", "1") == "0":
        return request
    try:
        from ..context.compaction import compact

        context_limit = int(os.environ.get("ARC_CONTEXT_LIMIT", "200000"))
        result = compact(request.messages, context_limit=context_limit)
        if result.compacted:
            return request.model_copy(update={"messages": list(result.messages_kept)})
    except Exception:
        pass
    return request


class OpenAICompatibleClient:
    """OpenAI-compatible provider client supporting multiple vendors.

    Supports: OpenAI, Together, Groq, DeepInfra, Fireworks, and local llama.cpp
    servers through configurable base_url.
    """

    def __init__(
        self,
        *,
        vendor: VendorName = "openai",
        base_url: str | None = None,
        config: OpenAICompatibleConfig | None = None,
        sdk_factory: Callable[[], Any] | None = None,
    ) -> None:
        """Initialize OpenAI-compatible client.

        Args:
            vendor: Vendor name (openai, together, groq, deepinfra, fireworks, llamacpp)
            base_url: Override base URL (defaults to vendor's default)
            sdk_factory: Optional factory for dependency injection

        """
        if config is None and vendor not in VENDOR_CONFIGS:
            raise ValueError(f"Unknown vendor {vendor!r}. Known: {sorted(VENDOR_CONFIGS)}")

        self._vendor = vendor
        self._vendor_config = config or cast(OpenAICompatibleConfig, VENDOR_CONFIGS[vendor])
        self._base_url = base_url or self._vendor_config["base_url"]
        self._sdk_factory = sdk_factory
        self._client: Any | None = None
        self._cancelled_calls: set[str] = set()

    def capabilities(self) -> ProviderCapability:
        """Return provider capabilities for the configured vendor."""
        config = self._vendor_config
        provider_id = str(config.get("provider_id") or f"openai-{self._vendor}")
        provider_name = str(
            config.get("provider_name") or f"OpenAI-Compatible ({self._vendor.title()})"
        )
        env_id = sanitize_provider_env_id(provider_id.removeprefix("openai-"))
        model = os.environ.get(f"ARC_{env_id}_DEFAULT_MODEL", config["default_model"])
        timeout = int(os.environ.get(f"ARC_{env_id}_TIMEOUT_SECONDS", "60"))

        return ProviderCapability(
            provider_id=provider_id,
            provider_name=provider_name,
            supported_models=config["supported_models"],
            default_model=model,
            features=config["features"],
            max_context_tokens=int(config.get("max_context_tokens") or 128_000),
            cost_rates=config["cost_rates"],
            timeout_seconds=timeout,
        )

    async def complete(
        self, request: ProviderRequest, *, cancellation_token: CancellationToken
    ) -> ProviderResponse:
        """Execute a completion request."""
        try:
            cancellation_token.raise_if_cancelled()
            request = _maybe_compact(request)
            kwargs = self._request_kwargs(request, stream=False)
            response = self._client_instance().chat.completions.create(**kwargs)
            cancellation_token.raise_if_cancelled()
        except Cancelled as exc:
            raise CancelledError(str(exc)) from exc
        except Exception as exc:
            raise self._map_error(exc) from exc

        return ProviderResponse(
            call_id=request.call_id,
            model=str(getattr(response, "model", request.model)),
            content=self._extract_content(response),
            finish_reason=self._finish_reason(getattr(response, "finish_reason", None)),
            usage=self._usage_record(getattr(response, "usage", None)),
            degraded=getattr(response, "usage", None) is None,
            degraded_reason=(
                None
                if getattr(response, "usage", None) is not None
                else "provider usage data unavailable"
            ),
            tool_calls=self._extract_tool_calls(response),
        )

    async def stream(
        self, request: ProviderRequest, *, cancellation_token: CancellationToken
    ) -> AsyncIterator[StreamChunk]:
        """Execute a streaming completion request."""
        try:
            cancellation_token.raise_if_cancelled()
            yield StreamChunk(call_id=request.call_id, chunk_type="start")

            stream = self._client_instance().chat.completions.create(
                **self._request_kwargs(request, stream=True)
            )

            usage: UsageRecord | None = None
            for chunk in stream:
                cancellation_token.raise_if_cancelled()
                if hasattr(chunk, "choices") and chunk.choices:
                    delta = getattr(chunk.choices[0], "delta", None)
                    if delta and hasattr(delta, "content") and delta.content:
                        yield StreamChunk(
                            call_id=request.call_id, chunk_type="delta", delta=str(delta.content)
                        )

                # Extract usage from final chunk if available
                if hasattr(chunk, "usage") and chunk.usage:
                    usage = self._usage_record(chunk.usage)

            yield StreamChunk(
                call_id=request.call_id,
                chunk_type="stop",
                payload={"usage": usage.model_dump(mode="json") if usage else None},
            )
        except Cancelled as exc:
            raise CancelledError(str(exc)) from exc
        except Exception as exc:
            yield StreamChunk(
                call_id=request.call_id,
                chunk_type="error",
                payload={"error": str(self._map_error(exc))},
            )

    async def cancel(self, call_id: str) -> None:
        """Cancel an in-flight request."""
        self._cancelled_calls.add(call_id)

    def _client_instance(self) -> Any:
        """Get or create OpenAI client instance."""
        if self._vendor == "gemini":
            # Gemini's OpenAI-compatible endpoint behaves unreliably with the
            # long-lived OpenAI SDK client in openai>=2.x. Use a fresh client per call.
            return self._create_client()

        if self._client is None:
            self._client = self._create_client()
        return self._client

    def _create_client(self) -> Any:
        if self._sdk_factory is not None:
            return self._sdk_factory()

        try:
            from openai import OpenAI
        except ImportError as exc:
            raise AuthError("openai SDK is not installed") from exc

        api_key_var, api_key = self._api_key()
        if not api_key and self._env_vars():
            raise AuthError(f"{api_key_var} environment variable not set")

        return OpenAI(
            api_key=api_key or "not-needed",
            base_url=self._base_url,
            timeout=self.capabilities().timeout_seconds,
        )

    def _api_key(self) -> tuple[str, str | None]:
        env_vars = self._env_vars()
        for name in env_vars:
            if os.environ.get(name):
                return name, os.environ[name]
        return " or ".join(env_vars), None

    def _env_vars(self) -> list[str]:
        configured = self._vendor_config.get("env_vars")
        if configured is not None:
            return list(configured)
        if self._vendor == "openai":
            return ["OPENAI_API_KEY"]
        if self._vendor == "9router":
            return ["NINEROUTER_API_KEY", "ROUTER9_API_KEY"]
        if self._vendor == "crofai":
            return ["CROFAI_API_KEY", "CROF_API_KEY", "CROFAI"]
        if self._vendor == "gemini":
            return ["GEMINI_API_KEY", "GOOGLE_API_KEY"]
        if self._vendor == "llamacpp":
            return []
        return [f"{self._vendor.upper()}_API_KEY"]

    def _request_kwargs(self, request: ProviderRequest, *, stream: bool) -> dict[str, Any]:
        """Build OpenAI API request kwargs.

        ORDER STABLE: system messages → conversation history.
        For OpenAI auto-prefix-cache, the stable prefix (system) must come
        first. Tools are passed separately via kwargs["tools"], not in messages.
        Do NOT reorder — cache stability depends on this.
        """
        # Enforce byte-stable order: system first, then non-system.
        system_msgs = [_openai_message(m) for m in request.messages if m.role == "system"]
        other_msgs = [_openai_message(m) for m in request.messages if m.role != "system"]
        messages = system_msgs + other_msgs

        kwargs: dict[str, Any] = {
            "model": request.model,
            "messages": messages,
            "max_tokens": request.max_tokens,
            "temperature": request.temperature,
            "stream": stream,
        }

        if request.stop_sequences:
            kwargs["stop"] = request.stop_sequences

        if request.tools:
            kwargs["tools"] = [self._openai_tool_schema(tool) for tool in request.tools]

        return kwargs

    @staticmethod
    def _openai_tool_schema(tool: dict[str, Any]) -> dict[str, Any]:
        if tool.get("type") == "function":
            return tool
        return {
            "type": "function",
            "function": {
                "name": tool.get("name", ""),
                "description": tool.get("description", ""),
                "parameters": tool.get("input_schema", tool.get("parameters", {})),
            },
        }

    @staticmethod
    def _extract_content(response: Any) -> str:
        """Extract text content from completion response."""
        if not hasattr(response, "choices") or not response.choices:
            return ""

        choice = response.choices[0]
        message = getattr(choice, "message", None)

        content = getattr(message, "content", None) if message is not None else None
        if content:
            return str(content)

        if message is not None and hasattr(message, "model_dump"):
            dumped = message.model_dump()
            content = dumped.get("content")
            if content:
                return str(content)

        return ""

    @staticmethod
    def _extract_tool_calls(response: Any) -> list[dict[str, Any]]:
        if not hasattr(response, "choices") or not response.choices:
            return []
        message = getattr(response.choices[0], "message", None)
        calls = getattr(message, "tool_calls", None) if message is not None else None
        if calls is None or not isinstance(calls, list | tuple):
            return []
        result: list[dict[str, Any]] = []
        for call in calls:
            fn = getattr(call, "function", None)
            raw_args = getattr(fn, "arguments", "{}") if fn is not None else "{}"
            try:
                args = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
            except json.JSONDecodeError:
                args = {}
            result.append(
                {
                    "id": getattr(call, "id", None),
                    "name": getattr(fn, "name", "") if fn is not None else "",
                    "args": args,
                }
            )
        return result

    @staticmethod
    def _usage_record(usage: Any) -> UsageRecord:
        """Convert OpenAI usage to UsageRecord."""
        if usage is None:
            return UsageRecord(available=False, input_tokens=0, output_tokens=0)

        return UsageRecord(
            input_tokens=int(getattr(usage, "prompt_tokens", 0) or 0),
            output_tokens=int(getattr(usage, "completion_tokens", 0) or 0),
            cache_creation_input_tokens=0,  # OpenAI doesn't expose cache metrics
            cache_read_input_tokens=0,
        )

    @staticmethod
    def _finish_reason(reason: Any) -> str:
        """Map OpenAI finish_reason to ProviderResponse finish_reason."""
        if reason is None:
            return "stop"

        reason_str = str(reason)
        mapping = {
            "stop": "stop",
            "length": "length",
            "tool_calls": "tool_use",
            "content_filter": "content_filter",
        }
        return mapping.get(reason_str, "stop")

    @staticmethod
    def _map_error(exc: Exception) -> Exception:
        """Map OpenAI SDK exceptions to ProviderError types."""
        name = type(exc).__name__.lower()
        text = str(exc)

        if "rate" in name or "rate" in text.lower() or "429" in text:
            return RateLimitError(text)
        if "auth" in name or "401" in text or "api key" in text.lower():
            return AuthError(text)
        if "validation" in name or "400" in text:
            return ValidationError(text)
        if "connection" in name or "network" in name or "timeout" in name:
            return NetworkError(text)

        return ModelError(text)


def _openai_message(message: ProviderMessage) -> dict[str, str]:
    if message.role == "tool":
        return {
            "role": "user",
            "content": "Tool result:\n" + message.content,
        }
    return {"role": message.role, "content": message.content}


def config_from_models_dev(provider: ModelsDevProviderConfig) -> OpenAICompatibleConfig:
    return {
        "base_url": provider.api,
        "default_model": select_default_model(provider),
        "supported_models": list(provider.models),
        "features": provider_features(provider),
        "cost_rates": cost_rates(provider),
        "env_vars": provider.env,
        "provider_id": f"openai-{provider.id}",
        "provider_name": f"OpenAI-Compatible ({provider.name})",
        "max_context_tokens": max_context_tokens(provider),
    }
