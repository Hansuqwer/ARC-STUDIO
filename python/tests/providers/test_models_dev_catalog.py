from __future__ import annotations

import pytest

from agent_runtime_cockpit.providers.base import AuthError, ProviderFeature
from agent_runtime_cockpit.providers.models_dev import (
    load_models_dev_catalog,
    sanitize_provider_env_id,
    select_default_model,
)
from agent_runtime_cockpit.providers.openai_compatible import (
    OpenAICompatibleClient,
    config_from_models_dev,
)
from agent_runtime_cockpit.providers.registry import get, known


def _fixture_catalog():
    return {
        "example-ai": {
            "id": "example-ai",
            "env": ["EXAMPLE_API_KEY", "EXAMPLE_TOKEN"],
            "npm": "@ai-sdk/openai-compatible",
            "api": "https://example.test/v1",
            "name": "Example AI",
            "models": {
                "small-preview": {
                    "id": "small-preview",
                    "tool_call": True,
                    "modalities": {"input": ["text"], "output": ["text"]},
                    "limit": {"context": 8000, "output": 1024},
                    "cost": {"input": 0.1, "output": 0.2},
                },
                "large-tool": {
                    "id": "large-tool",
                    "tool_call": True,
                    "modalities": {"input": ["text", "image"], "output": ["text"]},
                    "limit": {"context": 128000, "output": 4096},
                    "cost": {"input": 1.0, "output": 2.0, "cache_read": 0.25},
                },
                "huge-no-tool": {
                    "id": "huge-no-tool",
                    "tool_call": False,
                    "modalities": {"input": ["text"], "output": ["text"]},
                    "limit": {"context": 200000, "output": 4096},
                    "cost": {"input": 0.5, "output": 0.5},
                },
            },
        },
        "native-only": {
            "id": "native-only",
            "env": ["NATIVE_API_KEY"],
            "npm": "@ai-sdk/native",
            "api": "https://native.test/v1",
            "name": "Native Only",
            "models": {"native": {"id": "native"}},
        },
    }


def test_models_dev_fixture_parses_only_openai_compatible_providers():
    providers = load_models_dev_catalog(_fixture_catalog())
    assert list(providers) == ["example-ai"]
    assert providers["example-ai"].env == ["EXAMPLE_API_KEY", "EXAMPLE_TOKEN"]


def test_default_model_prefers_tool_text_large_context():
    provider = load_models_dev_catalog(_fixture_catalog())["example-ai"]
    assert select_default_model(provider) == "large-tool"


def test_dynamic_provider_maps_features_costs_and_context():
    provider = load_models_dev_catalog(_fixture_catalog())["example-ai"]
    client = OpenAICompatibleClient(
        config=config_from_models_dev(provider), sdk_factory=lambda: object()
    )
    caps = client.capabilities()
    assert caps.provider_id == "openai-example-ai"
    assert caps.default_model == "large-tool"
    assert caps.max_context_tokens == 200000
    assert ProviderFeature.TOOL_USE in caps.features
    assert ProviderFeature.VISION in caps.features
    assert caps.cost_rates["large-tool"].input_per_million == 1.0
    assert caps.cost_rates["large-tool"].cache_read_per_million == 0.25


def test_dynamic_provider_env_default_model_override(monkeypatch):
    provider = load_models_dev_catalog(_fixture_catalog())["example-ai"]
    monkeypatch.setenv("ARC_EXAMPLE_AI_DEFAULT_MODEL", "small-preview")
    client = OpenAICompatibleClient(
        config=config_from_models_dev(provider), sdk_factory=lambda: object()
    )
    assert client.capabilities().default_model == "small-preview"
    assert sanitize_provider_env_id("example-ai") == "EXAMPLE_AI"


def test_dynamic_provider_uses_first_configured_env_var(monkeypatch):
    provider = load_models_dev_catalog(_fixture_catalog())["example-ai"]
    monkeypatch.setenv("EXAMPLE_TOKEN", "sk-test")
    client = OpenAICompatibleClient(
        config=config_from_models_dev(provider), sdk_factory=lambda: object()
    )
    assert client._api_key() == ("EXAMPLE_TOKEN", "sk-test")


def test_dynamic_provider_missing_key_lists_accepted_env_vars(monkeypatch):
    provider = load_models_dev_catalog(_fixture_catalog())["example-ai"]
    monkeypatch.delenv("EXAMPLE_API_KEY", raising=False)
    monkeypatch.delenv("EXAMPLE_TOKEN", raising=False)
    client = OpenAICompatibleClient(config=config_from_models_dev(provider))
    with pytest.raises(AuthError, match="EXAMPLE_API_KEY or EXAMPLE_TOKEN"):
        client._client_instance()


def test_bundled_models_dev_providers_registered():
    provider_names = set(known())
    assert {"alibaba", "deepseek", "github-models", "moonshotai", "zai"}.issubset(provider_names)
    caps = get("deepseek").capabilities()
    assert caps.provider_id == "openai-deepseek"
    assert "deepseek-chat" in caps.supported_models


def test_9router_custom_behavior_unchanged(monkeypatch):
    monkeypatch.delenv("NINEROUTER_API_KEY", raising=False)
    monkeypatch.setenv("ROUTER9_API_KEY", "sk-test")
    monkeypatch.setenv("ARC_9ROUTER_DEFAULT_MODEL", "ag/gemini-3.5-flash-extra-low")
    client = get("9router")
    assert client.capabilities().default_model == "ag/gemini-3.5-flash-extra-low"
    assert client._api_key() == ("ROUTER9_API_KEY", "sk-test")
