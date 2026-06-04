"""Pricing refresh tests — verifies current-gen model rows and cache multipliers."""

from __future__ import annotations

from agent_runtime_cockpit.providers.anthropic import AnthropicClient
from agent_runtime_cockpit.providers.openai_compatible import OpenAICompatibleClient


def _anthropic_rates(model: str):
    import os

    old = os.environ.get("ARC_ANTHROPIC_DEFAULT_MODEL")
    os.environ["ARC_ANTHROPIC_DEFAULT_MODEL"] = model
    try:
        caps = AnthropicClient().capabilities()
    finally:
        if old is None:
            os.environ.pop("ARC_ANTHROPIC_DEFAULT_MODEL", None)
        else:
            os.environ["ARC_ANTHROPIC_DEFAULT_MODEL"] = old
    return caps.cost_rates.get(model)


def _openai_rates(model: str):
    caps = OpenAICompatibleClient(vendor="openai").capabilities()
    return caps.cost_rates.get(model) if caps.cost_rates else None


# ── Anthropic ────────────────────────────────────────────────────────────────


def test_haiku_45_rates() -> None:
    r = _anthropic_rates("claude-haiku-4-5")
    assert r is not None
    assert r.input_per_million == 1.0
    assert r.output_per_million == 5.0
    assert r.cache_read_per_million == 0.10


def test_sonnet_46_rates() -> None:
    r = _anthropic_rates("claude-sonnet-4-6")
    assert r is not None
    assert r.input_per_million == 3.0
    assert r.cache_read_per_million == 0.30


def test_opus_46_rates() -> None:
    r = _anthropic_rates("claude-opus-4-6")
    assert r is not None
    assert r.input_per_million == 5.0
    assert r.cache_read_per_million == 0.50


def test_opus_47_same_rate_card_as_46() -> None:
    """Opus 4.7 has same rate card as 4.6 but +35% tokenizer drift."""
    r46 = _anthropic_rates("claude-opus-4-6")
    r47 = _anthropic_rates("claude-opus-4-7")
    assert r47 is not None
    assert r47.input_per_million == r46.input_per_million
    assert r47.cache_read_per_million == r46.cache_read_per_million


# ── OpenAI ───────────────────────────────────────────────────────────────────


def test_gpt5x_current_gen_90pct_cache() -> None:
    """GPT-5.x current-gen: cache_read = 10% of input (90% off)."""
    for model in ("gpt-5.5", "gpt-5.4", "gpt-5.4-mini"):
        r = _openai_rates(model)
        assert r is not None, f"Missing rates for {model}"
        assert r.cache_read_per_million is not None
        # cache_read should be ~10% of input (90% discount)
        assert abs(r.cache_read_per_million / r.input_per_million - 0.10) < 0.01, (
            f"{model}: expected 90% cache discount, got {r.cache_read_per_million}/{r.input_per_million}"
        )


def test_gpt4o_mini_legacy_50pct_cache() -> None:
    """gpt-4o-mini is the only model still at 50% cache discount."""
    r = _openai_rates("gpt-4o-mini")
    assert r is not None
    assert r.cache_read_per_million is not None
    # 50% discount = 0.5 × input
    assert abs(r.cache_read_per_million / r.input_per_million - 0.50) < 0.01


def test_gpt41_family_75pct_cache() -> None:
    """GPT-4.1 family: 75% cache discount (0.25× input)."""
    r = _openai_rates("gpt-4.1")
    assert r is not None
    assert r.cache_read_per_million is not None
    assert abs(r.cache_read_per_million / r.input_per_million - 0.25) < 0.01
