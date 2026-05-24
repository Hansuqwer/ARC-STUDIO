"""Tests for local prompt optimizer."""

import pytest

from agent_runtime_cockpit.optimizer.local import (
    count_tokens,
    diff_prompts,
    estimate_cost,
    optimize_prompt,
)


def test_count_tokens_fallback():
    result = count_tokens("hello world this is a test", model="gpt-4")
    assert result.count > 0
    assert result.encoding in ("cl100k_base", "word-estimate")


def test_optimize_prompt_collapse_whitespace():
    prompt = "Hello\n\n\n\nWorld"
    result = optimize_prompt(prompt)
    assert "\n\n\n" not in result.optimized
    assert "collapse_whitespace" in result.changes


def test_optimize_prompt_strip_trailing():
    prompt = "Hello   \nWorld   \n"
    result = optimize_prompt(prompt)
    assert result.optimized.endswith("World\n")
    assert (
        "strip_trailing_whitespace" in result.changes
        or "remove_trailing_newlines" in result.changes
    )


def test_optimize_prompt_no_change():
    prompt = "Hello\n\nWorld\n"
    result = optimize_prompt(prompt)
    assert result.optimized == prompt
    assert result.tokens_saved == 0


def test_optimize_prompt_normalize_indent():
    prompt = "        deeply indented line"
    result = optimize_prompt(prompt)
    assert "    " in result.optimized
    assert "        " not in result.optimized
    assert "normalize_indent" in result.changes


def test_optimize_prompt_remove_trailing_newlines():
    prompt = "Hello\n\n\n"
    result = optimize_prompt(prompt)
    assert result.optimized == "Hello\n"
    assert "remove_trailing_newlines" in result.changes


def test_estimate_cost_known_model():
    cost = estimate_cost(1000, "gpt-4o")
    assert cost is not None
    assert cost == 0.0025


def test_estimate_cost_unknown_model():
    cost = estimate_cost(1000, "unknown-model-xyz")
    assert cost is None


def test_optimization_result_serialization():
    result = optimize_prompt("Test\n\n\n\nprompt")
    data = result.model_dump()
    assert "original" in data
    assert "optimized" in data
    assert "original_tokens" in data
    assert "tokens_saved" in data


def test_optimize_prompt_all_rules():
    prompt = "Line1   \n\n\n\n        deeply indented\n\n\n\n\n"
    result = optimize_prompt(prompt)
    # After collapse + strip + normalize + remove trailing:
    # "Line1\n\n    deeply indented\n"
    assert "collapse_whitespace" in result.changes
    assert "strip_trailing_whitespace" in result.changes
    assert "normalize_indent" in result.changes
    assert "remove_trailing_newlines" in result.changes
    assert result.tokens_saved > 0


def test_diff_prompts_identical():
    text = "Hello\nWorld\n"
    diff = diff_prompts(text, text)
    assert diff == ""


def test_diff_prompts_different():
    a = "Hello\nWorld\n"
    b = "Hello\nThere\nWorld\n"
    diff = diff_prompts(a, b)
    assert diff != ""
    assert "+There" in diff
    # "World" is a context line (present in both), not removed
    # Verify the header markers are present
    assert "--- prompt_a" in diff
    assert "+++ prompt_b" in diff


def test_diff_prompts_with_removal():
    a = "Hello\nOldLine\nWorld\n"
    b = "Hello\nNewLine\nWorld\n"
    diff = diff_prompts(a, b)
    assert "-OldLine" in diff
    assert "+NewLine" in diff


def test_count_tokens_empty_string():
    result = count_tokens("", model="gpt-4")
    assert result.count == 0


def test_estimate_cost_zero_tokens():
    cost = estimate_cost(0, "gpt-4o")
    assert cost == 0.0


def test_token_count_model_field():
    result = count_tokens("test", model="gpt-4o")
    assert result.model == "gpt-4o"


def test_optimize_prompt_mode_off():
    """Mode 'off' returns prompt unchanged."""
    prompt = "Hello\n\n\n\nWorld   \n"
    result = optimize_prompt(prompt, mode="off")
    assert result.optimized == prompt
    assert result.tokens_saved == 0
    assert result.changes == []


def test_optimize_prompt_mode_local():
    """Mode 'local' applies rule-based optimization."""
    prompt = "Hello\n\n\n\nWorld   \n"
    result = optimize_prompt(prompt, mode="local")
    assert result.optimized != prompt
    assert result.tokens_saved >= 0
    assert len(result.changes) > 0


def test_optimize_prompt_mode_local_model_not_implemented():
    """Mode 'local-model' raises NotImplementedError (gated)."""
    with pytest.raises(NotImplementedError, match="local-model"):
        optimize_prompt("test", mode="local-model")


def test_optimize_prompt_mode_provider_not_implemented():
    """Mode 'provider' raises NotImplementedError (gated)."""
    with pytest.raises(NotImplementedError, match="provider"):
        optimize_prompt("test", mode="provider")


def test_optimize_prompt_mode_swarmgraph_not_implemented():
    """Mode 'swarmgraph' raises NotImplementedError (gated)."""
    with pytest.raises(NotImplementedError, match="swarmgraph"):
        optimize_prompt("test", mode="swarmgraph")
