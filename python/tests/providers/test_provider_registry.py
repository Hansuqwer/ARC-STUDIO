"""Tests for provider registry and auto-registration (Phase 27)."""

from __future__ import annotations

import pytest

from agent_runtime_cockpit.providers import AnthropicClient, ProviderClient
from agent_runtime_cockpit.providers.registry import get, known, register


def test_anthropic_auto_registered():
    """AnthropicClient should be auto-registered on module import."""
    assert "anthropic" in known()


def test_get_anthropic_returns_client():
    """get('anthropic') should return an AnthropicClient instance."""
    client = get("anthropic")
    assert isinstance(client, AnthropicClient)


def test_get_anthropic_implements_protocol():
    """Retrieved client should implement ProviderClient protocol."""
    client = get("anthropic")
    assert isinstance(client, ProviderClient)


def test_get_anthropic_has_capabilities():
    """Retrieved client should have valid capabilities."""
    client = get("anthropic")
    caps = client.capabilities()
    assert caps.provider_id == "anthropic"
    assert caps.provider_name == "Anthropic"
    assert len(caps.supported_models) > 0
    assert caps.default_model in caps.supported_models


def test_get_unknown_provider_raises():
    """get() should raise KeyError for unknown providers."""
    with pytest.raises(KeyError, match="not registered"):
        get("unknown-provider")


def test_register_duplicate_raises():
    """Registering the same provider twice should raise ValueError."""
    with pytest.raises(ValueError, match="already registered"):
        register("anthropic", AnthropicClient)


def test_known_returns_sorted_list():
    """known() should return a sorted list of provider names."""
    providers = known()
    assert isinstance(providers, list)
    assert providers == sorted(providers)
    assert "anthropic" in providers
