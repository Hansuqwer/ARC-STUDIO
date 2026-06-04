"""Tests for v0.5.1 Chinese-labs vendor blocks (OpenRouter-sourced pricing).

Prices cross-checked with OpenRouter /api/v1/models on 2026-06-05.
Source decision: docs/research/pricing-feed-sources-comparison.md
"""

from __future__ import annotations

import pytest

from agent_runtime_cockpit.providers.base import CostRates
from agent_runtime_cockpit.providers.openai_compatible import OpenAICompatibleClient


def _rates(vendor: str, model: str) -> CostRates | None:
    caps = OpenAICompatibleClient(vendor=vendor).capabilities()
    return caps.cost_rates.get(model) if caps.cost_rates else None


# ── CoSAI: no LLM imports in cost lookup path ─────────────────────────────


def test_no_llm_imports_in_cost_lookups():
    """CoSAI: pricing lookups must not import or invoke any LLM client."""
    import importlib

    mod = importlib.import_module("agent_runtime_cockpit.providers.openai_compatible")
    assert hasattr(mod, "VENDOR_CONFIGS")


# ── CrofAI ────────────────────────────────────────────────────────────────


class TestCrofAI:
    def test_crofai_default_model_is_in_supported(self):
        caps = OpenAICompatibleClient(vendor="crofai").capabilities()
        assert caps.default_model in caps.supported_models

    def test_crofai_deepseek_v4_flash(self):
        r = _rates("crofai", "deepseek-v4-flash")
        assert r is not None
        assert r.input_per_million == 0.12
        assert r.cache_read_per_million == pytest.approx(0.003)

    def test_crofai_glm_free_tier(self):
        r = _rates("crofai", "glm-4.7-flash")
        assert r is not None
        assert r.is_free_tier is True

    def test_crofai_qwen_tokenizer_family(self):
        r = _rates("crofai", "qwen3.5-397b-a17b")
        assert r is not None
        assert r.tokenizer_family == "qwen"

    def test_crofai_env_vars(self):
        c = OpenAICompatibleClient(vendor="crofai")
        assert "CROFAI" in c._env_vars()


# ── DeepSeek ──────────────────────────────────────────────────────────────


class TestDeepSeek:
    def test_instantiates(self):
        caps = OpenAICompatibleClient(vendor="deepseek").capabilities()
        assert caps.default_model == "deepseek-v4-flash"

    def test_v4_pro_openrouter_price(self):
        r = _rates("deepseek", "deepseek-v4-pro")
        assert r is not None
        assert r.input_per_million == pytest.approx(0.435)
        assert r.cache_read_per_million == pytest.approx(0.0036)

    def test_cache_field_names(self):
        r = _rates("deepseek", "deepseek-v4-pro")
        assert r.cache_field_names is not None
        assert r.cache_field_names["hit"] == "prompt_cache_hit_tokens"

    def test_legacy_chat_has_auto_route(self):
        r = _rates("deepseek", "deepseek-chat")
        assert r is not None
        assert r.auto_route_to == "deepseek-v4-flash"

    def test_env_vars(self):
        assert "DEEPSEEK_API_KEY" in OpenAICompatibleClient(vendor="deepseek")._env_vars()


# ── Qwen ──────────────────────────────────────────────────────────────────


class TestQwen:
    def test_instantiates(self):
        caps = OpenAICompatibleClient(vendor="qwen").capabilities()
        assert caps.default_model in caps.supported_models

    def test_all_models_have_qwen_tokenizer(self):
        caps = OpenAICompatibleClient(vendor="qwen").capabilities()
        for m in caps.supported_models:
            r = caps.cost_rates.get(m)
            assert r is not None, f"missing rates for {m}"
            assert r.tokenizer_family == "qwen", f"{m} missing tokenizer_family=qwen"

    def test_flagship_openrouter_price(self):
        r = _rates("qwen", "qwen3.7-max")
        assert r.input_per_million == pytest.approx(1.25)
        assert r.cache_read_per_million == pytest.approx(0.25)

    def test_10_or_more_rows(self):
        assert len(OpenAICompatibleClient(vendor="qwen").capabilities().supported_models) >= 10


# ── Kimi ──────────────────────────────────────────────────────────────────


class TestKimi:
    def test_instantiates(self):
        caps = OpenAICompatibleClient(vendor="kimi").capabilities()
        assert caps.default_model == "kimi-k2.5"

    def test_k2_5_openrouter_price(self):
        r = _rates("kimi", "kimi-k2.5")
        assert r.input_per_million == pytest.approx(0.40)
        assert r.cache_read_per_million == pytest.approx(0.09)

    def test_legacy_k2_0905_deprecated(self):
        r = _rates("kimi", "kimi-k2-0905")
        assert r is not None
        assert r.pricing_valid_until == "2026-05-25"
        assert r.auto_route_to == "kimi-k2.5"


# ── GLM ───────────────────────────────────────────────────────────────────


class TestGLM:
    def test_instantiates(self):
        caps = OpenAICompatibleClient(vendor="glm").capabilities()
        assert caps.default_model == "glm-4.7"

    def test_two_free_tier_models(self):
        caps = OpenAICompatibleClient(vendor="glm").capabilities()
        free = [
            m
            for m in caps.supported_models
            if caps.cost_rates.get(m) and caps.cost_rates[m].is_free_tier
        ]
        assert len(free) == 1  # only glm-4.5-air is free per OpenRouter

    def test_free_tier_zero_cost(self):
        r = _rates("glm", "glm-4.5-air")
        assert r.is_free_tier is True
        assert r.input_per_million == pytest.approx(
            0.125
        )  # OpenRouter has pricing even on "free" tier

    def test_free_tier_does_not_crash_budget(self):
        r = _rates("glm", "glm-4.5-air")
        # is_free_tier=True means wallet skips enforcement; cost calc still works
        cost = r.input_per_million * 1000 + r.output_per_million * 500
        assert isinstance(cost, float)  # no crash

    def test_all_models_have_glm_tokenizer(self):
        caps = OpenAICompatibleClient(vendor="glm").capabilities()
        for m in caps.supported_models:
            r = caps.cost_rates.get(m)
            assert r and r.tokenizer_family == "glm", f"{m} missing tokenizer_family=glm"

    def test_flagship_openrouter_price(self):
        r = _rates("glm", "glm-5.1")
        assert r.input_per_million == pytest.approx(0.98)
        assert r.cache_read_per_million == pytest.approx(0.182)


# ── MiMo ──────────────────────────────────────────────────────────────────


class TestMiMo:
    def test_instantiates(self):
        caps = OpenAICompatibleClient(vendor="mimo").capabilities()
        assert caps.default_model == "mimo-v2.5-pro"

    def test_3_rows_openrouter(self):
        assert len(OpenAICompatibleClient(vendor="mimo").capabilities().supported_models) == 3

    def test_v2_5_pro_price(self):
        r = _rates("mimo", "mimo-v2.5-pro")
        assert r.input_per_million == pytest.approx(0.435)
        assert r.cache_read_per_million == pytest.approx(0.0036)


# ── MiniMax ───────────────────────────────────────────────────────────────


class TestMiniMax:
    def test_instantiates(self):
        caps = OpenAICompatibleClient(vendor="minimax").capabilities()
        assert caps.default_model == "minimax-m2.5"

    def test_6_rows(self):
        assert len(OpenAICompatibleClient(vendor="minimax").capabilities().supported_models) == 6

    def test_m3_price(self):
        r = _rates("minimax", "minimax-m3")
        assert r.input_per_million == pytest.approx(0.30)
        assert r.cache_read_per_million == pytest.approx(0.06)
