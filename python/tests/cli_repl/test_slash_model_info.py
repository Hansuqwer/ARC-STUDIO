"""Tests for /model-info slash command (v0.6 Task 2)."""

from __future__ import annotations

from agent_runtime_cockpit.cli_repl.slash.model_info import run


def test_happy_path_shows_pricing():
    out = run("kimi/kimi-k2.6")
    assert "kimi-k2.6" in out
    assert "$" in out


def test_happy_path_shows_modalities():
    out = run("kimi/kimi-k2.6")
    assert "image" in out


def test_missing_model_returns_not_found():
    out = run("kimi/nonexistent-model-xyz")
    assert "[not found]" in out


def test_vendor_not_found():
    out = run("nonexistent_vendor/some-model")
    assert "[not found]" in out


def test_deprecated_model_shows_banner():
    # kimi-k2-0905 has pricing_valid_until=2026-05-25 (past date)
    out = run("kimi/kimi-k2-0905")
    assert "DEPRECATED" in out or "pricing expired" in out


def test_free_tier_model_shows_free_tier():
    out = run("glm/glm-4.5-air")
    assert "FREE TIER" in out


def test_bare_model_id_lookup():
    """Model ID without vendor prefix should still find the model."""
    out = run("deepseek-v4-flash")
    assert "[not found]" not in out
    assert "deepseek" in out.lower()
