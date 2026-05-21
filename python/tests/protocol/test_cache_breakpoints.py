"""Tests for cache breakpoint computation."""

from __future__ import annotations

import pytest

from agent_runtime_cockpit.protocol.cache_breakpoints import (
    CacheBreakpoint,
    CacheBreakpointInput,
    MAX_BREAKPOINTS,
    MessageTokenInfo,
    compute_breakpoints,
    estimate_cache_savings,
)


class TestComputeBreakpoints:
    def test_empty_input_returns_empty_list(self):
        assert compute_breakpoints(CacheBreakpointInput()) == []

    def test_system_prompt_cached_when_above_threshold(self):
        result = compute_breakpoints(CacheBreakpointInput(system_prompt_tokens=1500))
        assert [(bp.position, bp.index, bp.estimated_tokens) for bp in result] == [("system", 0, 1500)]

    def test_system_prompt_below_threshold_skipped(self):
        assert compute_breakpoints(CacheBreakpointInput(system_prompt_tokens=100)) == []

    def test_tools_cached_when_above_threshold(self):
        result = compute_breakpoints(CacheBreakpointInput(tool_definition_tokens=1200))
        assert [(bp.position, bp.index, bp.estimated_tokens) for bp in result] == [("tools", 0, 1200)]

    def test_compute_breakpoints_emits_message_indices(self):
        input_data = CacheBreakpointInput(
            messages=[
                MessageTokenInfo(index=0, tokens=100),
                MessageTokenInfo(index=1, tokens=2000),
                MessageTokenInfo(index=2, tokens=50),
                MessageTokenInfo(index=3, tokens=1500),
            ],
            threshold=1024,
        )
        result = compute_breakpoints(input_data)
        indices = [bp.index for bp in result if bp.position == "messages"]
        assert indices == [1, 3]

    def test_compute_breakpoints_caps_at_four_total(self):
        input_data = CacheBreakpointInput(
            system_prompt_tokens=2000,
            tool_definition_tokens=2000,
            messages=[MessageTokenInfo(index=i, tokens=1500) for i in range(10)],
            threshold=1024,
        )
        result = compute_breakpoints(input_data)
        assert len(result) == MAX_BREAKPOINTS
        message_bps = [bp for bp in result if bp.position == "messages"]
        assert len(message_bps) == 2

    def test_compute_breakpoints_prefers_largest_messages_when_capped(self):
        input_data = CacheBreakpointInput(
            messages=[
                MessageTokenInfo(index=0, tokens=1100),
                MessageTokenInfo(index=1, tokens=5000),
                MessageTokenInfo(index=2, tokens=1200),
                MessageTokenInfo(index=3, tokens=8000),
                MessageTokenInfo(index=4, tokens=1500),
                MessageTokenInfo(index=5, tokens=10000),
            ],
            threshold=1024,
        )
        result = compute_breakpoints(input_data)
        indices = [bp.index for bp in result if bp.position == "messages"]
        assert indices == [1, 3, 4, 5]

    def test_compute_breakpoints_below_threshold_emits_nothing(self):
        input_data = CacheBreakpointInput(
            system_prompt_tokens=100,
            messages=[MessageTokenInfo(index=0, tokens=100)],
            threshold=1024,
        )
        assert compute_breakpoints(input_data) == []

    def test_system_breakpoint_rejects_nonzero_index(self):
        with pytest.raises(ValueError, match="requires index=0"):
            CacheBreakpoint(position="system", index=1)

    def test_tools_breakpoint_rejects_nonzero_index(self):
        with pytest.raises(ValueError, match="requires index=0"):
            CacheBreakpoint(position="tools", index=2)

    def test_negative_breakpoint_index_rejected(self):
        with pytest.raises(ValueError, match=">= 0"):
            CacheBreakpoint(position="messages", index=-1)

    def test_invalid_position_rejected(self):
        with pytest.raises(ValueError, match="position"):
            CacheBreakpoint(position="context", index=0)  # type: ignore[arg-type]

    def test_arbitrary_string_position_rejected(self):
        with pytest.raises(ValueError, match="position"):
            CacheBreakpoint(position="bad", index=0)  # type: ignore[arg-type]

    def test_negative_message_index_rejected(self):
        with pytest.raises(ValueError, match=">= 0"):
            MessageTokenInfo(index=-1, tokens=100)

    def test_negative_message_tokens_rejected(self):
        with pytest.raises(ValueError, match=">= 0"):
            MessageTokenInfo(index=0, tokens=-1)

    def test_default_threshold_is_1024(self):
        assert CacheBreakpointInput().threshold == 1024


class TestEstimateCacheSavings:
    def test_empty_breakpoints_save_zero(self):
        assert estimate_cache_savings([]) == 0

    def test_multiple_breakpoints(self):
        bps = [
            CacheBreakpoint(position="system", estimated_tokens=200),
            CacheBreakpoint(position="tools", estimated_tokens=600),
            CacheBreakpoint(position="messages", index=2, estimated_tokens=1500),
        ]
        assert estimate_cache_savings(bps) == 2300

    def test_ttl_not_counted_in_savings(self):
        bps = [CacheBreakpoint(position="system", estimated_tokens=100, ttl_seconds=300)]
        assert estimate_cache_savings(bps) == 100
