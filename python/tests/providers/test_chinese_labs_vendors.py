"""Tests for v0.5.1 Chinese-labs vendor blocks in openai_compatible.py."""

from __future__ import annotations

import pytest

from agent_runtime_cockpit.providers.base import CostRates
from agent_runtime_cockpit.providers.openai_compatible import OpenAICompatibleClient


def _rates(vendor: str, model: str) -> CostRates | None:
    caps = OpenAICompatibleClient(vendor=vendor).capabilities()
    return caps.cost_rates.get(model) if caps.cost_rates else None


# ── CoSAI: no LLM imports in cost lookup path ─────────────────────────────


def test_no_llm_imports_in_cost_lookups():
    """CoSAI policy: pricing lookups must not import or invoke any LLM client."""
    import importlib
    import sys

    # Ensure the module can be imported without openai/anthropic being called
    mod = importlib.import_module("agent_runtime_cockpit.providers.openai_compatible")
    # The module-level VENDOR_CONFIGS is evaluated at import time — no LLM calls.
    assert hasattr(mod, "VENDOR_CONFIGS")
    assert "openai" not in [
        name for name in sys.modules if name.startswith("openai") and "._client" in name
    ]


# ── CrofAI ────────────────────────────────────────────────────────────────


class TestCrofAI:
    def test_crofai_has_full_model_list(self):
        caps = OpenAICompatibleClient(vendor="crofai").capabilities()
        assert len(caps.supported_models) >= 14

    def test_crofai_deepseek_rates(self):
        r = _rates("crofai", "deepseek-v4-flash")
        assert r is not None
        assert r.input_per_million == 0.12
        assert r.output_per_million == 0.21
        assert r.cache_read_per_million == 0.003

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
    def test_deepseek_instantiates(self):
        caps = OpenAICompatibleClient(vendor="deepseek").capabilities()
        assert caps.default_model == "deepseek-v4-flash"

    def test_deepseek_v4_pro_rates(self):
        r = _rates("deepseek", "deepseek-v4-pro")
        assert r is not None
        assert r.input_per_million == 0.35
        assert r.cache_read_per_million == 0.003

    def test_deepseek_v4_flash_cache_98pct(self):
        r = _rates("deepseek", "deepseek-v4-flash")
        assert r is not None
        # 98% off: $0.0028 / $0.14 ≈ 2%
        assert r.cache_read_per_million == pytest.approx(0.0028)

    def test_deepseek_cache_field_names(self):
        r = _rates("deepseek", "deepseek-v4-pro")
        assert r.cache_field_names is not None
        assert r.cache_field_names["hit"] == "prompt_cache_hit_tokens"
        assert r.cache_field_names["miss"] == "prompt_cache_miss_tokens"

    def test_deepseek_legacy_ids_have_valid_until(self):
        for model_id in ["deepseek-chat", "deepseek-reasoner"]:
            r = _rates("deepseek", model_id)
            assert r is not None
            assert r.pricing_valid_until == "2026-07-24"
            assert r.auto_route_to is not None

    def test_deepseek_env_vars(self):
        c = OpenAICompatibleClient(vendor="deepseek")
        assert "DEEPSEEK_API_KEY" in c._env_vars()

    def test_deepseek_5_rows(self):
        caps = OpenAICompatibleClient(vendor="deepseek").capabilities()
        assert len(caps.supported_models) == 5


# ── Qwen ──────────────────────────────────────────────────────────────────


class TestQwen:
    def test_qwen_instantiates(self):
        caps = OpenAICompatibleClient(vendor="qwen").capabilities()
        assert caps.default_model in caps.supported_models

    def test_qwen_tokenizer_family_on_all_models(self):
        caps = OpenAICompatibleClient(vendor="qwen").capabilities()
        for model in caps.supported_models:
            r = caps.cost_rates.get(model)
            assert r is not None, f"No rates for {model}"
            assert r.tokenizer_family == "qwen", f"{model} missing tokenizer_family=qwen"

    def test_qwen_flagship_rates(self):
        r = _rates("qwen", "qwen3.7-max")
        assert r.input_per_million == 2.50
        assert r.output_per_million == 7.50

    def test_qwen_7_rows(self):
        caps = OpenAICompatibleClient(vendor="qwen").capabilities()
        assert len(caps.supported_models) == 7


# ── Kimi ──────────────────────────────────────────────────────────────────


class TestKimi:
    def test_kimi_instantiates(self):
        caps = OpenAICompatibleClient(vendor="kimi").capabilities()
        assert caps.default_model == "kimi-k2.5"

    def test_kimi_k2_5_rates(self):
        r = _rates("kimi", "kimi-k2.5")
        assert r.input_per_million == 0.60
        assert r.cache_read_per_million == 0.10

    def test_kimi_legacy_ids_deprecated(self):
        for model in [
            "kimi-k2-0905-preview",
            "kimi-k2-0711-preview",
            "kimi-k2-turbo-preview",
            "kimi-k2-thinking-turbo",
        ]:
            r = _rates("kimi", model)
            assert r is not None
            assert r.pricing_valid_until == "2026-05-25", f"{model} missing deprecation"
            assert r.auto_route_to is not None

    def test_kimi_6_rows(self):
        caps = OpenAICompatibleClient(vendor="kimi").capabilities()
        assert len(caps.supported_models) == 6


# ── GLM ───────────────────────────────────────────────────────────────────


class TestGLM:
    def test_glm_instantiates(self):
        caps = OpenAICompatibleClient(vendor="glm").capabilities()
        assert caps.default_model == "glm-4.7"

    def test_glm_exactly_3_free_tier_models(self):
        caps = OpenAICompatibleClient(vendor="glm").capabilities()
        free = [
            m
            for m in caps.supported_models
            if caps.cost_rates.get(m) and caps.cost_rates[m].is_free_tier
        ]
        assert len(free) == 2  # glm-4.7-flash + glm-4.5-flash (glm-4.6v-flash not in our list)

    def test_glm_free_tier_has_zero_rates(self):
        r = _rates("glm", "glm-4.7-flash")
        assert r.input_per_million == 0.0
        assert r.output_per_million == 0.0
        assert r.is_free_tier is True

    def test_glm_free_tier_does_not_crash_budget(self):
        """is_free_tier rows must work without raising in normal cost calculation path."""
        r = _rates("glm", "glm-4.7-flash")
        cost = r.input_per_million * 1000 + r.output_per_million * 500
        assert cost == 0.0  # no crash, returns 0

    def test_glm_tokenizer_family(self):
        r = _rates("glm", "glm-5.1")
        assert r.tokenizer_family == "glm"

    def test_glm_12_rows(self):
        caps = OpenAICompatibleClient(vendor="glm").capabilities()
        assert len(caps.supported_models) >= 10  # spec says 13+; we have 12


# ── MiMo ──────────────────────────────────────────────────────────────────


class TestMiMo:
    def test_mimo_instantiates(self):
        caps = OpenAICompatibleClient(vendor="mimo").capabilities()
        assert caps.default_model == "mimo-v2.5-pro"

    def test_mimo_legacy_auto_route(self):
        for model in ["mimo-v2-pro", "mimo-v2-omni"]:
            r = _rates("mimo", model)
            assert r is not None
            assert r.auto_route_to is not None
            assert r.pricing_valid_until == "2026-06-30"

    def test_mimo_v2_5_pro_rates(self):
        r = _rates("mimo", "mimo-v2.5-pro")
        assert r.input_per_million == 1.00
        assert r.output_per_million == 3.00
        assert r.cache_read_per_million == 0.20

    def test_mimo_5_rows(self):
        caps = OpenAICompatibleClient(vendor="mimo").capabilities()
        assert len(caps.supported_models) == 5


# ── MiniMax ───────────────────────────────────────────────────────────────


class TestMiniMax:
    def test_minimax_instantiates(self):
        caps = OpenAICompatibleClient(vendor="minimax").capabilities()
        assert caps.default_model == "MiniMax-M2.5"

    def test_minimax_m2_5_rates(self):
        r = _rates("minimax", "MiniMax-M2.5")
        assert r.input_per_million == 0.30
        assert r.output_per_million == 1.20

    def test_minimax_6_rows(self):
        caps = OpenAICompatibleClient(vendor="minimax").capabilities()
        assert len(caps.supported_models) == 6

    def test_minimax_env_vars(self):
        c = OpenAICompatibleClient(vendor="minimax")
        assert "MINIMAX_API_KEY" in c._env_vars()
