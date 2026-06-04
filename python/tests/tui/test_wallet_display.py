"""Tests for v0.5.1 wallet display: free tier, tokenizer qualifier, deprecation, auto_route."""

from __future__ import annotations

from agent_runtime_cockpit.budget.wallet import model_display_notes
from agent_runtime_cockpit.providers.base import CostRates


def _rates(**kwargs) -> CostRates:
    defaults = dict(input_per_million=1.0, output_per_million=3.0)
    defaults.update(kwargs)
    return CostRates(**defaults)


# ── 1. FREE TIER rendering ────────────────────────────────────────────────


def test_free_tier_shows_free_tier_label():
    notes = model_display_notes(
        "glm-4.5-air", _rates(is_free_tier=True, input_per_million=0.0, output_per_million=0.0)
    )
    assert len(notes) == 1
    assert "FREE TIER" in notes[0]
    assert "rate-limited" in notes[0]


def test_free_tier_returns_early_no_other_annotations():
    """is_free_tier=True suppresses all other annotations."""
    notes = model_display_notes(
        "glm-4.5-air",
        _rates(
            is_free_tier=True,
            input_per_million=0.0,
            output_per_million=0.0,
            tokenizer_family="glm",
            pricing_valid_until="2025-01-01",
        ),
    )
    assert len(notes) == 1
    assert "FREE TIER" in notes[0]
    assert "≈" not in notes[0]


# ── 2. ≈ qualifier for non-cl100k tokenizer ──────────────────────────────


def test_tokenizer_family_qwen_gets_qualifier():
    notes = model_display_notes("qwen3-235b", _rates(tokenizer_family="qwen"))
    assert any("≈" in n and "qwen" in n for n in notes)


def test_tokenizer_family_cl100k_no_qualifier():
    notes = model_display_notes("gpt-4o", _rates(tokenizer_family="cl100k_base"))
    assert not any("≈" in n for n in notes)


def test_tokenizer_family_none_no_qualifier():
    notes = model_display_notes("gpt-4o", _rates())
    assert not any("≈" in n for n in notes)


# ── 3. Deprecation warning ───────────────────────────────────────────────


def test_expired_pricing_valid_until_shows_warning():
    notes = model_display_notes("kimi-k2-0905", _rates(pricing_valid_until="2026-05-25"))
    assert any("⚠" in n and "EXPIRED" in n for n in notes)


def test_future_pricing_valid_until_shows_expiry():
    notes = model_display_notes("some-model", _rates(pricing_valid_until="2099-12-31"))
    assert any("expires 2099-12-31" in n for n in notes)


def test_expired_with_auto_route_mentions_route():
    notes = model_display_notes(
        "deepseek-chat",
        _rates(pricing_valid_until="2026-07-24", auto_route_to="deepseek-v4-flash"),
    )
    assert any("deepseek-v4-flash" in n for n in notes)


# ── 4. auto_route_to annotation ──────────────────────────────────────────


def test_auto_route_without_valid_until_shows_annotation():
    notes = model_display_notes("legacy-model", _rates(auto_route_to="new-model"))
    assert any("routed to new-model" in n for n in notes)


def test_auto_route_with_valid_until_shown_in_deprecation_line():
    """auto_route_to combined with pricing_valid_until: appears on deprecation line."""
    notes = model_display_notes(
        "old", _rates(pricing_valid_until="2026-01-01", auto_route_to="new")
    )
    combined = " ".join(notes)
    assert "new" in combined
    assert "routed to new" not in combined  # deduplicated — appears on stale line only


# ── 5. Empty notes for clean modern model ────────────────────────────────


def test_clean_model_returns_no_notes():
    notes = model_display_notes("gpt-4o", _rates())
    assert notes == []
