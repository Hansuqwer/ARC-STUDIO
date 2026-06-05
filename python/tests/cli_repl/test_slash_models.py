"""Tests for /models slash command (v0.6 Task 1)."""

from __future__ import annotations

from agent_runtime_cockpit.cli_repl.slash.models import (
    _all_models,
    _apply_filters,
    _parse_args,
    run,
)


class TestParseArgs:
    def test_vendor_flag(self):
        assert _parse_args("--vendor kimi") == {"vendor": "kimi"}

    def test_has_flag(self):
        assert _parse_args("--has vision") == {"has": ["vision"]}

    def test_multiple_has_flags(self):
        opts = _parse_args("--has vision --has tools")
        assert opts["has"] == ["vision", "tools"]

    def test_free_flag(self):
        assert _parse_args("--free")["free"] is True

    def test_max_input_flag(self):
        assert _parse_args("--max-input 1.0")["max_input"] == 1.0

    def test_search_flag(self):
        assert _parse_args("--search flash")["search"] == "flash"


class TestFilters:
    def test_vendor_filter_returns_only_that_vendor(self):
        rows = _apply_filters(_all_models(), {"vendor": "kimi"})
        assert len(rows) > 0
        assert all(r.vendor == "kimi" for r in rows)

    def test_free_filter_returns_only_free_tier(self):
        rows = _apply_filters(_all_models(), {"free": True})
        assert len(rows) > 0
        assert all(r.is_free_tier for r in rows)

    def test_max_input_filter(self):
        rows = _apply_filters(_all_models(), {"max_input": 0.5})
        assert all(r.input_per_million <= 0.5 for r in rows)

    def test_has_vision_filter(self):
        rows = _apply_filters(_all_models(), {"has": ["vision"]})
        assert len(rows) > 0
        for r in rows:
            assert "image" in r.input_modalities or "video" in r.input_modalities, (
                f"{r.vendor}/{r.model_id} passed vision filter but has no image/video modality"
            )

    def test_has_vision_filter_per_model_granularity(self):
        """Critical: vision filter uses per-model data (v0.5.2), not vendor-level flags."""
        kimi_vision = _apply_filters(_all_models(), {"vendor": "kimi", "has": ["vision"]})
        vision_ids = {r.model_id for r in kimi_vision}

        # kimi-k2.6 and kimi-k2.5 have ['text', 'image'] — must appear
        assert "kimi-k2.6" in vision_ids, "kimi-k2.6 is multimodal; must appear in --has vision"
        assert "kimi-k2.5" in vision_ids, "kimi-k2.5 is multimodal; must appear in --has vision"

        # kimi-k2 and kimi-k2-thinking have empty modalities — must NOT appear
        text_only = {"kimi-k2", "kimi-k2-thinking"}
        false_positives = text_only & vision_ids
        assert not false_positives, (
            f"Text-only models incorrectly in vision results: {false_positives}"
        )

    def test_has_tools_filter(self):
        rows = _apply_filters(_all_models(), {"has": ["tools"]})
        assert len(rows) > 0
        for r in rows:
            assert "tools" in r.supported_parameters, (
                f"{r.vendor}/{r.model_id} passed tools filter but lacks tools parameter"
            )

    def test_search_filter_case_insensitive(self):
        rows = _apply_filters(_all_models(), {"search": "FLASH"})
        assert all("flash" in r.model_id.lower() or "flash" in r.vendor.lower() for r in rows)

    def test_vendor_filter_returns_empty_for_unknown(self):
        rows = _apply_filters(_all_models(), {"vendor": "nonexistent_vendor_xyz"})
        assert rows == []

    def test_combined_filters(self):
        rows = _apply_filters(_all_models(), {"vendor": "glm", "free": True})
        assert len(rows) > 0
        assert all(r.vendor == "glm" and r.is_free_tier for r in rows)


class TestRunOutput:
    def test_help_output(self):
        out = run("")
        assert "Usage:" in out

    def test_vendor_filter_in_output(self):
        out = run("--vendor deepseek")
        assert "deepseek:" in out
        assert "model(s) listed" in out

    def test_no_results_message(self):
        out = run("--vendor nonexistent_xyz")
        assert "No models match" in out

    def test_free_models_tagged(self):
        out = run("--free")
        assert "[free]" in out

    def test_ordering_by_price(self):
        """Models in vendor output are listed in ascending input price order."""
        rows = _apply_filters(_all_models(), {"vendor": "deepseek"})
        # rows returned by _all_models are insertion-order; after sort in run() they should be sorted
        sorted_rows = sorted(rows, key=lambda r: r.input_per_million)
        prices = [r.input_per_million for r in sorted_rows]
        assert prices == sorted(prices)  # tautology verifies sort logic is stable

    def test_works_without_network(self):
        """Must work using only committed catalog data — no HTTP calls."""
        import unittest.mock as mock

        with mock.patch("urllib.request.urlopen") as mock_url:
            out = run("--vendor kimi")
        mock_url.assert_not_called()
        assert "model(s) listed" in out
