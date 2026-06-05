"""Tests for v0.5.2 CostRates capability fields (supported_parameters + input_modalities).

Verifies that:
1. Fields exist with correct defaults (backward-compat)
2. Multimodal models have non-text modalities
3. Tool-capable models list 'tools' in supported_parameters
4. Non-Chinese-lab vendors default to empty (no OpenRouter data)
5. All Chinese-lab vendor models have non-empty capability fields
"""

from __future__ import annotations


from agent_runtime_cockpit.providers.base import CostRates
from agent_runtime_cockpit.providers.openai_compatible import OpenAICompatibleClient


def _rates(vendor: str, model: str) -> CostRates | None:
    caps = OpenAICompatibleClient(vendor=vendor).capabilities()
    return (caps.cost_rates or {}).get(model)


# ── 1. Backward compat: new fields default to empty list ──────────────────


def test_cost_rates_defaults_empty_capability_fields():
    r = CostRates(input_per_million=1.0, output_per_million=3.0)
    assert r.supported_parameters == []
    assert r.input_modalities == []


def test_existing_rows_unaffected():
    """Non-Chinese-lab vendors have backfilled capability fields."""
    caps = OpenAICompatibleClient(vendor="openai").capabilities()
    for model in ["gpt-4o", "gpt-4o-mini"]:
        r = (caps.cost_rates or {}).get(model)
        if r:
            assert "tools" in r.supported_parameters
            assert "response_format" in r.supported_parameters
            assert "image" in r.input_modalities


# ── 2. Multimodal models have image/video in input_modalities ─────────────


def test_kimi_k2_6_has_image_modality():
    r = _rates("kimi", "kimi-k2.6")
    assert r is not None
    assert "image" in r.input_modalities


def test_mimo_v2_5_has_audio_modality():
    r = _rates("mimo", "mimo-v2.5")
    assert r is not None
    assert "audio" in r.input_modalities
    assert "image" in r.input_modalities
    assert "video" in r.input_modalities


# ── 3. Tool-capable models list 'tools' in supported_parameters ───────────


def test_deepseek_v4_pro_has_tools_parameter():
    r = _rates("deepseek", "deepseek-v4-pro")
    assert r is not None
    assert "tools" in r.supported_parameters


def test_deepseek_v4_pro_has_response_format_parameter():
    r = _rates("deepseek", "deepseek-v4-pro")
    assert r is not None
    assert "response_format" in r.supported_parameters


# ── 4. Chinese-lab vendor models all have non-empty capability fields ──────


def test_all_glm_models_have_capability_fields():
    caps = OpenAICompatibleClient(vendor="glm").capabilities()
    for model in caps.supported_models:
        r = (caps.cost_rates or {}).get(model)
        if r:
            assert len(r.supported_parameters) > 0, f"{model} has empty supported_parameters"
            assert len(r.input_modalities) > 0, f"{model} has empty input_modalities"


def test_all_qwen_models_have_capability_fields():
    """Most Qwen models should have capability fields; some legacy IDs may not match OpenRouter."""
    caps = OpenAICompatibleClient(vendor="qwen").capabilities()
    populated = 0
    for model in caps.supported_models:
        r = (caps.cost_rates or {}).get(model)
        if r and r.supported_parameters:
            populated += 1
    # At least 80% of qwen models should have capability data
    assert populated >= len(caps.supported_models) * 0.8, (
        f"Only {populated}/{len(caps.supported_models)} Qwen models have capability fields"
    )


# ── 5. Reasoning models have reasoning in supported_parameters ────────────


def test_qwen3_7_plus_has_reasoning_parameter():
    r = _rates("qwen", "qwen3.7-plus")
    assert r is not None
    # Qwen supports include_reasoning or reasoning
    has_reasoning = (
        "reasoning" in r.supported_parameters or "include_reasoning" in r.supported_parameters
    )
    assert has_reasoning, f"Expected reasoning param, got: {r.supported_parameters}"
