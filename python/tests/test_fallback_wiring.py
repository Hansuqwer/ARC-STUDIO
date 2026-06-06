"""Tests for ARC_FALLBACK_PROVIDERS env var wiring in _provider_client_for_run."""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch


def _make_stub(name: str):
    m = MagicMock()
    m.name = name
    m.capabilities.return_value = MagicMock()
    return m


@pytest.fixture(autouse=True)
def _disable_retry_sleep(monkeypatch):
    monkeypatch.setenv("ARC_DISABLE_RETRY_SLEEP", "1")


def _run(provider_name: str, fallback_env: str | None, stubs: dict):
    """Call _provider_client_for_run with patched registry and env."""
    import os

    env = {"ARC_FALLBACK_PROVIDERS": fallback_env} if fallback_env else {}
    with patch.dict(os.environ, env, clear=False):
        if fallback_env is None:
            os.environ.pop("ARC_FALLBACK_PROVIDERS", None)
        with patch(
            "agent_runtime_cockpit.cli_repl.slash_commands.get_provider_client",
            side_effect=lambda name: stubs[name],
        ):
            with patch(
                "agent_runtime_cockpit.cli_repl.slash_commands._detect_provider_name",
                return_value=provider_name,
            ):
                from agent_runtime_cockpit.cli_repl.slash_commands import _provider_client_for_run

                return _provider_client_for_run(None, session=None)


def test_no_fallback_env_returns_plain_client():
    stubs = {"anthropic": _make_stub("anthropic")}
    result = _run("anthropic", None, stubs)
    # Not wrapped in FallbackProviderClient.
    from agent_runtime_cockpit.providers.fallback import FallbackProviderClient

    assert not isinstance(result, FallbackProviderClient)


def test_fallback_env_wraps_in_fallback_client():
    stubs = {
        "anthropic": _make_stub("anthropic"),
        "openai": _make_stub("openai"),
    }
    result = _run("anthropic", "openai", stubs)
    from agent_runtime_cockpit.providers.fallback import FallbackProviderClient

    assert isinstance(result, FallbackProviderClient)
    assert result._clients[0].name == "anthropic"
    assert result._clients[1].name == "openai"


def test_duplicate_primary_in_fallback_env_is_skipped():
    stubs = {
        "anthropic": _make_stub("anthropic"),
        "openai": _make_stub("openai"),
    }
    # anthropic listed in both primary and fallback
    result = _run("anthropic", "anthropic,openai", stubs)
    from agent_runtime_cockpit.providers.fallback import FallbackProviderClient

    assert isinstance(result, FallbackProviderClient)
    assert len(result._clients) == 2  # primary + openai only
    assert result._clients[1].name == "openai"


def test_unavailable_fallback_skipped_gracefully():
    """A fallback provider that raises on construction is skipped with a warning."""

    def registry(name):
        if name == "anthropic":
            return _make_stub("anthropic")
        raise KeyError(f"{name!r} not registered")

    import os

    with patch.dict(os.environ, {"ARC_FALLBACK_PROVIDERS": "bad-provider"}, clear=False):
        with patch(
            "agent_runtime_cockpit.cli_repl.slash_commands.get_provider_client",
            side_effect=registry,
        ):
            with patch(
                "agent_runtime_cockpit.cli_repl.slash_commands._detect_provider_name",
                return_value="anthropic",
            ):
                from agent_runtime_cockpit.cli_repl.slash_commands import _provider_client_for_run

                result = _provider_client_for_run(None, session=None)
    # All fallbacks failed construction — falls back to plain primary.
    from agent_runtime_cockpit.providers.fallback import FallbackProviderClient

    assert not isinstance(result, FallbackProviderClient)
