"""Tests for CostRates schema v0.5.1 extension (6 new optional fields)."""

from __future__ import annotations

import pytest

from agent_runtime_cockpit.providers.base import CostRates


class TestCostRatesSchema:
    def test_existing_rows_unaffected_by_new_fields(self):
        """Backward compat: existing construction still works."""
        r = CostRates(input_per_million=1.0, output_per_million=3.0)
        assert r.input_per_million == 1.0
        assert r.is_free_tier is False
        assert r.pricing_valid_until is None
        assert r.auto_route_to is None
        assert r.cache_field_names is None
        assert r.tokenizer_family == "cl100k_base"
        assert r.cache_storage_usd_per_million_per_hour is None

    def test_is_free_tier_flag(self):
        r = CostRates(input_per_million=0.0, output_per_million=0.0, is_free_tier=True)
        assert r.is_free_tier is True

    def test_pricing_valid_until(self):
        r = CostRates(
            input_per_million=1.0,
            output_per_million=3.0,
            pricing_valid_until="2026-07-24",
        )
        assert r.pricing_valid_until == "2026-07-24"

    def test_auto_route_to(self):
        r = CostRates(
            input_per_million=0.0,
            output_per_million=0.0,
            auto_route_to="mimo-v2.5",
        )
        assert r.auto_route_to == "mimo-v2.5"

    def test_cache_field_names(self):
        names = {"hit": "prompt_cache_hit_tokens", "miss": "prompt_cache_miss_tokens"}
        r = CostRates(
            input_per_million=0.14,
            output_per_million=0.28,
            cache_read_per_million=0.0028,
            cache_field_names=names,
        )
        assert r.cache_field_names == names

    def test_tokenizer_family_non_default(self):
        r = CostRates(
            input_per_million=0.35,
            output_per_million=1.75,
            tokenizer_family="qwen",
        )
        assert r.tokenizer_family == "qwen"

    def test_cache_storage_field(self):
        r = CostRates(
            input_per_million=3.0,
            output_per_million=15.0,
            cache_storage_usd_per_million_per_hour=0.48,
        )
        assert r.cache_storage_usd_per_million_per_hour == 0.48

    def test_cache_storage_non_negative(self):
        with pytest.raises(Exception):
            CostRates(
                input_per_million=1.0,
                output_per_million=1.0,
                cache_storage_usd_per_million_per_hour=-0.01,
            )

    def test_all_six_fields_together(self):
        r = CostRates(
            input_per_million=0.0,
            output_per_million=0.0,
            is_free_tier=True,
            pricing_valid_until="2026-12-31",
            auto_route_to="glm-5",
            cache_field_names={"hit": "prompt_cache_hit_tokens"},
            tokenizer_family="glm",
            cache_storage_usd_per_million_per_hour=0.0,
        )
        assert r.is_free_tier is True
        assert r.pricing_valid_until == "2026-12-31"
        assert r.auto_route_to == "glm-5"
        assert r.tokenizer_family == "glm"

    def test_serialization_omits_none_defaults(self):
        r = CostRates(input_per_million=1.0, output_per_million=3.0)
        d = r.model_dump(exclude_none=True)
        assert "pricing_valid_until" not in d
        assert "auto_route_to" not in d
        assert "cache_field_names" not in d
        assert "cache_storage_usd_per_million_per_hour" not in d
        # is_free_tier=False and tokenizer_family have non-None defaults so they appear
        assert d["is_free_tier"] is False
        assert d["tokenizer_family"] == "cl100k_base"
