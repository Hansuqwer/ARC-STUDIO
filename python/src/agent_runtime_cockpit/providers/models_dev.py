"""models.dev catalog helpers for OpenAI-compatible runtime providers.

The bundled snapshot is intentionally compact. It gives ARC a no-network
provider catalog path while avoiding claims that every models.dev provider has
been runtime-verified here.
"""

from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel, Field

from .base import CostRates, ProviderFeature


class ModelsDevModelConfig(BaseModel):
    id: str
    name: str | None = None
    tool_call: bool = False
    modalities: dict[str, list[str]] = Field(default_factory=dict)
    limit: dict[str, int] = Field(default_factory=dict)
    cost: dict[str, float] = Field(default_factory=dict)


class ModelsDevProviderConfig(BaseModel):
    id: str
    name: str
    api: str
    env: list[str] = Field(min_length=1)
    npm: str | None = None
    doc: str | None = None
    models: dict[str, ModelsDevModelConfig] = Field(min_length=1)


def sanitize_provider_env_id(provider_id: str) -> str:
    return re.sub(r"[^A-Za-z0-9]", "_", provider_id).upper()


def load_models_dev_catalog(raw: dict[str, Any]) -> dict[str, ModelsDevProviderConfig]:
    providers: dict[str, ModelsDevProviderConfig] = {}
    for provider_id, payload in raw.items():
        api = payload.get("api")
        npm = payload.get("npm") or ""
        if not api or "openai" not in npm:
            continue
        models = payload.get("models") or {}
        if not models:
            continue
        providers[provider_id] = ModelsDevProviderConfig(
            id=payload.get("id") or provider_id,
            name=payload.get("name") or provider_id,
            api=api,
            env=list(payload.get("env") or []),
            npm=npm,
            doc=payload.get("doc"),
            models={model_id: ModelsDevModelConfig(**model) for model_id, model in models.items()},
        )
    return providers


def select_default_model(provider: ModelsDevProviderConfig) -> str:
    def score(item: tuple[str, ModelsDevModelConfig]) -> tuple[int, int, int, str]:
        model_id, model = item
        outputs_text = "text" in model.modalities.get("output", [])
        context = int(model.limit.get("context") or 0)
        preview_penalty = -1 if "preview" in model_id.lower() else 0
        return (1 if model.tool_call else 0, 1 if outputs_text else 0, context, preview_penalty)

    return max(provider.models.items(), key=score)[0]


def provider_features(provider: ModelsDevProviderConfig) -> list[ProviderFeature]:
    features = [ProviderFeature.STREAMING]
    models = list(provider.models.values())
    if any(model.tool_call for model in models):
        features.append(ProviderFeature.TOOL_USE)
    if any("image" in model.modalities.get("input", []) for model in models):
        features.append(ProviderFeature.VISION)
    return features


def cost_rates(provider: ModelsDevProviderConfig) -> dict[str, CostRates]:
    rates: dict[str, CostRates] = {}
    for model_id, model in provider.models.items():
        cost = model.cost or {}
        rates[model_id] = CostRates(
            input_per_million=float(cost.get("input") or 0),
            output_per_million=float(cost.get("output") or 0),
            cache_read_per_million=cost.get("cache_read"),
            cache_write_per_million=cost.get("cache_write"),
        )
    return rates


def max_context_tokens(provider: ModelsDevProviderConfig) -> int:
    return (
        max((int(model.limit.get("context") or 0) for model in provider.models.values()), default=0)
        or 128_000
    )


MODELS_DEV_OPENAI_COMPATIBLE_SNAPSHOT: dict[str, Any] = {
    "alibaba": {
        "id": "alibaba",
        "env": ["DASHSCOPE_API_KEY"],
        "npm": "@ai-sdk/openai-compatible",
        "api": "https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
        "name": "Alibaba",
        "doc": "https://www.alibabacloud.com/help/en/model-studio/models",
        "models": {
            "qwen3.5-122b-a10b": {
                "id": "qwen3.5-122b-a10b",
                "name": "qwen3.5-122b-a10b",
                "tool_call": True,
                "modalities": {"input": ["text"], "output": ["text"]},
                "limit": {"context": 262144, "output": 8192},
                "cost": {"input": 0.4, "output": 3.2},
            },
            "qwen3-next-80b-a3b-instruct": {
                "id": "qwen3-next-80b-a3b-instruct",
                "name": "qwen3-next-80b-a3b-instruct",
                "tool_call": True,
                "modalities": {"input": ["text"], "output": ["text"]},
                "limit": {"context": 131072, "output": 8192},
                "cost": {"input": 0.5, "output": 2.0},
            },
        },
    },
    "deepseek": {
        "id": "deepseek",
        "env": ["DEEPSEEK_API_KEY"],
        "npm": "@ai-sdk/openai-compatible",
        "api": "https://api.deepseek.com",
        "name": "DeepSeek",
        "doc": "https://api-docs.deepseek.com/quick_start/pricing",
        "models": {
            "deepseek-chat": {
                "id": "deepseek-chat",
                "name": "deepseek-chat",
                "tool_call": True,
                "modalities": {"input": ["text"], "output": ["text"]},
                "limit": {"context": 1000000, "output": 8192},
                "cost": {"input": 0.14, "output": 0.28, "cache_read": 0.028},
            },
            "deepseek-reasoner": {
                "id": "deepseek-reasoner",
                "name": "deepseek-reasoner",
                "tool_call": True,
                "modalities": {"input": ["text"], "output": ["text"]},
                "limit": {"context": 1000000, "output": 8192},
                "cost": {"input": 0.14, "output": 0.28, "cache_read": 0.028},
            },
        },
    },
    "github-models": {
        "id": "github-models",
        "env": ["GITHUB_TOKEN"],
        "npm": "@ai-sdk/openai-compatible",
        "api": "https://models.github.ai/inference",
        "name": "GitHub Models",
        "doc": "https://docs.github.com/en/github-models",
        "models": {
            "deepseek/deepseek-v3-0324": {
                "id": "deepseek/deepseek-v3-0324",
                "name": "DeepSeek V3 0324",
                "tool_call": True,
                "modalities": {"input": ["text"], "output": ["text"]},
                "limit": {"context": 128000, "output": 8192},
                "cost": {"input": 0, "output": 0},
            },
            "ai21-labs/ai21-jamba-1.5-large": {
                "id": "ai21-labs/ai21-jamba-1.5-large",
                "name": "AI21 Jamba 1.5 Large",
                "tool_call": True,
                "modalities": {"input": ["text"], "output": ["text"]},
                "limit": {"context": 256000, "output": 4096},
                "cost": {"input": 0, "output": 0},
            },
            "meta/llama-3.3-70b-instruct": {
                "id": "meta/llama-3.3-70b-instruct",
                "name": "Llama 3.3 70B Instruct",
                "tool_call": True,
                "modalities": {"input": ["text"], "output": ["text"]},
                "limit": {"context": 128000, "output": 8192},
                "cost": {"input": 0, "output": 0},
            },
            "openai/gpt-4.1-mini": {
                "id": "openai/gpt-4.1-mini",
                "name": "GPT-4.1 Mini",
                "tool_call": True,
                "modalities": {"input": ["text"], "output": ["text"]},
                "limit": {"context": 1047576, "output": 32768},
                "cost": {"input": 0, "output": 0},
            },
        },
    },
    "moonshotai": {
        "id": "moonshotai",
        "env": ["MOONSHOT_API_KEY"],
        "npm": "@ai-sdk/openai-compatible",
        "api": "https://api.moonshot.ai/v1",
        "name": "Moonshot AI",
        "doc": "https://platform.moonshot.ai/docs/api/chat",
        "models": {
            "kimi-k2.6": {
                "id": "kimi-k2.6",
                "name": "kimi-k2.6",
                "tool_call": True,
                "modalities": {"input": ["text"], "output": ["text"]},
                "limit": {"context": 262144, "output": 8192},
                "cost": {"input": 0.95, "output": 4.0, "cache_read": 0.16},
            },
            "kimi-k2-thinking": {
                "id": "kimi-k2-thinking",
                "name": "kimi-k2-thinking",
                "tool_call": True,
                "modalities": {"input": ["text"], "output": ["text"]},
                "limit": {"context": 262144, "output": 8192},
                "cost": {"input": 0.6, "output": 2.5, "cache_read": 0.15},
            },
        },
    },
    "zai": {
        "id": "zai",
        "env": ["ZHIPU_API_KEY"],
        "npm": "@ai-sdk/openai-compatible",
        "api": "https://api.z.ai/api/paas/v4",
        "name": "Z.AI",
        "doc": "https://docs.z.ai/guides/overview/pricing",
        "models": {
            "glm-4.6": {
                "id": "glm-4.6",
                "name": "glm-4.6",
                "tool_call": True,
                "modalities": {"input": ["text"], "output": ["text"]},
                "limit": {"context": 204800, "output": 8192},
                "cost": {"input": 0.6, "output": 2.2, "cache_read": 0.11},
            },
            "glm-4.5-flash": {
                "id": "glm-4.5-flash",
                "name": "glm-4.5-flash",
                "tool_call": True,
                "modalities": {"input": ["text"], "output": ["text"]},
                "limit": {"context": 131072, "output": 8192},
                "cost": {"input": 0, "output": 0, "cache_read": 0},
            },
        },
    },
    # ── Additional providers from models.dev catalog (official API docs) ──
    # Groq: https://api.groq.com/openai/v1, GROQ_API_KEY
    "groq": {
        "id": "groq",
        "env": ["GROQ_API_KEY"],
        "npm": "@ai-sdk/openai-compatible",
        "api": "https://api.groq.com/openai/v1",
        "name": "Groq",
        "doc": "https://console.groq.com/docs/openai",
        "models": {
            "llama-3.3-70b-versatile": {
                "id": "llama-3.3-70b-versatile",
                "name": "Llama 3.3 70B Versatile",
                "tool_call": True,
                "modalities": {"input": ["text"], "output": ["text"]},
                "limit": {"context": 131072, "output": 32768},
                "cost": {"input": 0.59, "output": 0.79},
            },
            "llama-3.1-8b-instant": {
                "id": "llama-3.1-8b-instant",
                "name": "Llama 3.1 8B Instant",
                "tool_call": True,
                "modalities": {"input": ["text"], "output": ["text"]},
                "limit": {"context": 131072, "output": 131072},
                "cost": {"input": 0.05, "output": 0.08},
            },
        },
    },
    # Together AI: https://api.together.xyz/v1, TOGETHER_API_KEY
    "together": {
        "id": "together",
        "env": ["TOGETHER_API_KEY"],
        "npm": "@ai-sdk/openai-compatible",
        "api": "https://api.together.xyz/v1",
        "name": "Together AI",
        "doc": "https://docs.together.ai",
        "models": {
            "meta-llama/Llama-3.3-70B-Instruct-Turbo": {
                "id": "meta-llama/Llama-3.3-70B-Instruct-Turbo",
                "name": "Llama 3.3 70B Instruct Turbo",
                "tool_call": True,
                "modalities": {"input": ["text"], "output": ["text"]},
                "limit": {"context": 131072, "output": 8192},
                "cost": {"input": 0.88, "output": 0.88},
            },
            "deepseek-ai/DeepSeek-V3": {
                "id": "deepseek-ai/DeepSeek-V3",
                "name": "DeepSeek V3",
                "tool_call": True,
                "modalities": {"input": ["text"], "output": ["text"]},
                "limit": {"context": 128000, "output": 8192},
                "cost": {"input": 1.25, "output": 1.25},
            },
        },
    },
    # Fireworks AI: https://api.fireworks.ai/inference/v1, FIREWORKS_API_KEY
    "fireworks": {
        "id": "fireworks",
        "env": ["FIREWORKS_API_KEY"],
        "npm": "@ai-sdk/openai-compatible",
        "api": "https://api.fireworks.ai/inference/v1",
        "name": "Fireworks AI",
        "doc": "https://docs.fireworks.ai",
        "models": {
            "accounts/fireworks/models/llama4-maverick-instruct-basic": {
                "id": "accounts/fireworks/models/llama4-maverick-instruct-basic",
                "name": "Llama 4 Maverick Instruct",
                "tool_call": True,
                "modalities": {"input": ["text"], "output": ["text"]},
                "limit": {"context": 131072, "output": 16384},
                "cost": {"input": 0.22, "output": 0.88},
            },
            "accounts/fireworks/models/deepseek-v3": {
                "id": "accounts/fireworks/models/deepseek-v3",
                "name": "DeepSeek V3",
                "tool_call": True,
                "modalities": {"input": ["text"], "output": ["text"]},
                "limit": {"context": 131072, "output": 16384},
                "cost": {"input": 0.9, "output": 0.9},
            },
        },
    },
    # Deep Infra: https://api.deepinfra.com/v1/openai, DEEPINFRA_API_KEY
    "deepinfra": {
        "id": "deepinfra",
        "env": ["DEEPINFRA_API_KEY"],
        "npm": "@ai-sdk/openai-compatible",
        "api": "https://api.deepinfra.com/v1/openai",
        "name": "Deep Infra",
        "doc": "https://deepinfra.com/docs",
        "models": {
            "meta-llama/Llama-3.3-70B-Instruct-Turbo": {
                "id": "meta-llama/Llama-3.3-70B-Instruct-Turbo",
                "name": "Llama 3.3 70B Turbo",
                "tool_call": True,
                "modalities": {"input": ["text"], "output": ["text"]},
                "limit": {"context": 131072, "output": 8192},
                "cost": {"input": 0.59, "output": 0.79},
            },
            "deepseek-ai/DeepSeek-V3": {
                "id": "deepseek-ai/DeepSeek-V3",
                "name": "DeepSeek V3",
                "tool_call": True,
                "modalities": {"input": ["text"], "output": ["text"]},
                "limit": {"context": 65536, "output": 8192},
                "cost": {"input": 0.49, "output": 0.89},
            },
        },
    },
    # OpenAI: https://api.openai.com/v1, OPENAI_API_KEY
    "openai": {
        "id": "openai",
        "env": ["OPENAI_API_KEY"],
        "npm": "@ai-sdk/openai-compatible",
        "api": "https://api.openai.com/v1",
        "name": "OpenAI",
        "doc": "https://platform.openai.com/docs",
        "models": {
            "gpt-4.1": {
                "id": "gpt-4.1",
                "name": "GPT-4.1",
                "tool_call": True,
                "modalities": {"input": ["text"], "output": ["text"]},
                "limit": {"context": 1047576, "output": 32768},
                "cost": {"input": 2.0, "output": 8.0},
            },
            "gpt-4.1-mini": {
                "id": "gpt-4.1-mini",
                "name": "GPT-4.1 Mini",
                "tool_call": True,
                "modalities": {"input": ["text"], "output": ["text"]},
                "limit": {"context": 1047576, "output": 32768},
                "cost": {"input": 0.4, "output": 1.6},
            },
            "o4-mini": {
                "id": "o4-mini",
                "name": "o4-mini",
                "tool_call": True,
                "modalities": {"input": ["text"], "output": ["text"]},
                "limit": {"context": 200000, "output": 100000},
                "cost": {"input": 1.1, "output": 4.4},
            },
        },
    },
    # NVIDIA: https://integrate.api.nvidia.com/v1, NVIDIA_API_KEY
    "nvidia": {
        "id": "nvidia",
        "env": ["NVIDIA_API_KEY"],
        "npm": "@ai-sdk/openai-compatible",
        "api": "https://integrate.api.nvidia.com/v1",
        "name": "NVIDIA",
        "doc": "https://build.nvidia.com",
        "models": {
            "nvidia/llama-3.1-nemotron-ultra-253b-v1": {
                "id": "nvidia/llama-3.1-nemotron-ultra-253b-v1",
                "name": "Llama 3.1 Nemotron Ultra 253B",
                "tool_call": True,
                "modalities": {"input": ["text"], "output": ["text"]},
                "limit": {"context": 131072, "output": 32768},
                "cost": {"input": 0.0, "output": 0.0},
            },
            "nvidia/llama-3.3-nemotron-super-49b-v1": {
                "id": "nvidia/llama-3.3-nemotron-super-49b-v1",
                "name": "Llama 3.3 Nemotron Super 49B",
                "tool_call": True,
                "modalities": {"input": ["text"], "output": ["text"]},
                "limit": {"context": 131072, "output": 32768},
                "cost": {"input": 0.0, "output": 0.0},
            },
        },
    },
    # ── Free-tier providers added from models.dev / official docs ──────────
    # Cerebras: free tier (CEREBRAS_API_KEY, rate-limited).
    # Base URL: https://api.cerebras.ai/v1  (official OpenAI compat docs)
    "cerebras": {
        "id": "cerebras",
        "env": ["CEREBRAS_API_KEY"],
        "npm": "@ai-sdk/openai-compatible",
        "api": "https://api.cerebras.ai/v1",
        "name": "Cerebras",
        "doc": "https://inference-docs.cerebras.ai/introduction",
        "models": {
            "gpt-oss-120b": {
                "id": "gpt-oss-120b",
                "name": "GPT-OSS 120B",
                "tool_call": True,
                "modalities": {"input": ["text"], "output": ["text"]},
                # Free tier — no listed per-token price on their public page
                "limit": {"context": 131072, "output": 65536},
                "cost": {"input": 0, "output": 0},
            },
        },
    },
    # OpenRouter: unified gateway, OPENROUTER_API_KEY required.
    # Models with :free suffix are served at $0/$0 and are a good default for
    # new users. Base URL: https://openrouter.ai/api/v1  (official docs)
    "openrouter": {
        "id": "openrouter",
        "env": ["OPENROUTER_API_KEY"],
        "npm": "@ai-sdk/openai-compatible",
        "api": "https://openrouter.ai/api/v1",
        "name": "OpenRouter",
        "doc": "https://openrouter.ai/docs/quickstart",
        "models": {
            "deepseek/deepseek-r1:free": {
                "id": "deepseek/deepseek-r1:free",
                "name": "DeepSeek R1 (free)",
                "tool_call": False,
                "modalities": {"input": ["text"], "output": ["text"]},
                "limit": {"context": 65536, "output": 8192},
                "cost": {"input": 0, "output": 0},
            },
            "meta-llama/llama-3.3-70b-instruct:free": {
                "id": "meta-llama/llama-3.3-70b-instruct:free",
                "name": "Llama 3.3 70B Instruct (free)",
                "tool_call": True,
                "modalities": {"input": ["text"], "output": ["text"]},
                "limit": {"context": 131072, "output": 8192},
                "cost": {"input": 0, "output": 0},
            },
            "mistralai/mistral-7b-instruct:free": {
                "id": "mistralai/mistral-7b-instruct:free",
                "name": "Mistral 7B Instruct (free)",
                "tool_call": False,
                "modalities": {"input": ["text"], "output": ["text"]},
                "limit": {"context": 32768, "output": 4096},
                "cost": {"input": 0, "output": 0},
            },
        },
    },
}


def bundled_openai_compatible_providers() -> dict[str, ModelsDevProviderConfig]:
    return load_models_dev_catalog(MODELS_DEV_OPENAI_COMPATIBLE_SNAPSHOT)


async def fetch_models_dev_catalog() -> dict[str, ModelsDevProviderConfig]:
    """Fetch the live models.dev catalog and parse it.

    Falls back to the bundled snapshot on any error. Only called when
    ARC_MODELS_DEV_LIVE=1 is set — never at normal startup (no silent
    network calls).
    """

    url = "https://models.dev/api.json"
    try:
        import aiohttp  # aiohttp is a standard ARC dep

        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                raw = await resp.json(content_type=None)
        return load_models_dev_catalog(raw)
    except Exception:
        return bundled_openai_compatible_providers()


def active_providers() -> dict[str, ModelsDevProviderConfig]:
    """Return providers to register — live catalog if flag set, else bundled."""
    import asyncio
    import os

    if os.environ.get("ARC_MODELS_DEV_LIVE"):
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Inside an async context: return bundled (caller must await
                # fetch_models_dev_catalog() directly for async use).
                pass
            else:
                return loop.run_until_complete(fetch_models_dev_catalog())
        except Exception:
            pass
    return bundled_openai_compatible_providers()


def free_providers_hint() -> str:
    """Return a one-line hint listing providers with ≥1 free (cost=0) model.

    Used in the TUI welcome message. Never hard-coded — derived from snapshot.
    """
    free: list[str] = []
    for p in bundled_openai_compatible_providers().values():
        has_free = any(
            not (m.cost.get("input", 1) or m.cost.get("output", 1)) for m in p.models.values()
        )
        if has_free:
            env = p.env[0] if p.env else "?"
            free.append(f"{p.name} ({env})")
    if not free:
        return ""
    return "Free-tier providers: " + ", ".join(free)
