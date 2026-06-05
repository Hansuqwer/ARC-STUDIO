"""Tests for capability_gates.py (v0.6 Task 3)."""

from __future__ import annotations

from agent_runtime_cockpit.tui.widgets.capability_gates import (
    get_capabilities,
    is_capability_enabled,
)


# ── 1. Fail-closed invariant ──────────────────────────────────────────────


def test_unknown_model_hides_all_capability_widgets():
    """Invariant 3: unknown model → all gates False (fail-closed)."""
    caps = get_capabilities("totally-unknown-model-xyz-12345")
    assert all(not v for v in caps.values()), f"Expected all False for unknown model, got {caps}"


def test_unknown_vendor_hides_all_capabilities():
    caps = get_capabilities("gpt-4o", vendor="nonexistent_vendor_xyz")
    assert all(not v for v in caps.values())


def test_never_raises_on_garbage_input():
    """Fail-closed: must never raise."""
    import traceback

    try:
        caps = get_capabilities(None, vendor=None)  # type: ignore
    except Exception as e:
        pytest_fail = f"get_capabilities raised: {e}\n{traceback.format_exc()}"
        assert False, pytest_fail
    assert isinstance(caps, dict)


# ── 2. Vision capability ──────────────────────────────────────────────────


def test_kimi_k2_6_has_vision():
    assert is_capability_enabled("kimi-k2.6", "vision") is True


def test_kimi_k2_text_only_no_vision():
    """kimi-k2 has empty input_modalities → no vision."""
    assert is_capability_enabled("kimi-k2", "vision") is False


def test_mimo_v2_5_has_vision_audio_video():
    caps = get_capabilities("mimo-v2.5")
    assert caps["vision"] is True
    assert caps["audio"] is True
    assert caps["video"] is True


# ── 3. Tools capability ───────────────────────────────────────────────────


def test_deepseek_v4_pro_has_tools():
    assert is_capability_enabled("deepseek-v4-pro", "tools") is True


def test_tool_capability_via_vendor_hint():
    assert is_capability_enabled("deepseek-v4-pro", "tools", vendor="deepseek") is True


# ── 4. Reasoning capability ───────────────────────────────────────────────


def test_qwen_3_7_plus_has_reasoning():
    assert is_capability_enabled("qwen3.7-plus", "reasoning") is True


# ── 5. Structured output ──────────────────────────────────────────────────


def test_structured_output_for_models_with_response_format():
    caps = get_capabilities("deepseek-v4-pro")
    assert caps["structured_output"] is True


# ── 6. All gates returned ─────────────────────────────────────────────────


def test_returns_all_expected_gates():
    caps = get_capabilities("kimi-k2.6")
    expected = {"vision", "tools", "reasoning", "audio", "video", "structured_output"}
    assert set(caps.keys()) == expected
