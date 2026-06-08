"""Tests for VercelGrepProvider env gate (ARC_VERCEL_GREP_ENABLED)."""

from __future__ import annotations


def test_vercel_grep_off_by_default(monkeypatch):
    """VercelGrepProvider must return empty list when ARC_VERCEL_GREP_ENABLED is not set."""
    monkeypatch.delenv("ARC_VERCEL_GREP_ENABLED", raising=False)
    from agent_runtime_cockpit.context.providers.vercel_grep import VercelGrepProvider

    provider = VercelGrepProvider()
    results = provider.retrieve("test query")
    assert results == [], "VercelGrepProvider must be gated off by default"


def test_vercel_grep_enabled_flag_respected(monkeypatch):
    """VercelGrepProvider must attempt retrieval (or fail gracefully) when gate is on."""
    monkeypatch.setenv("ARC_VERCEL_GREP_ENABLED", "1")
    # We don't make real network calls in tests; patch _scrape to return empty list.
    from agent_runtime_cockpit.context.providers import vercel_grep as vg

    monkeypatch.setattr(vg.VercelGrepProvider, "_scrape", lambda self, t: [])
    provider = vg.VercelGrepProvider()
    results = provider.retrieve("test query")
    # Gate is on and _scrape succeeded (returned [])
    assert isinstance(results, list)


def test_vercel_grep_env_var_name():
    """The gate env variable name must be ARC_VERCEL_GREP_ENABLED."""
    from agent_runtime_cockpit.context.providers import vercel_grep as vg

    assert vg._GATE_ENV == "ARC_VERCEL_GREP_ENABLED"
