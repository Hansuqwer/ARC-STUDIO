"""Tests for cache breakpoint computation."""

from __future__ import annotations

import pytest

from agent_runtime_cockpit.protocol.cache_breakpoints import (
    CacheBreakpoint,
    CacheBreakpointInput,
    MAX_BREAKPOINTS,
    compute_breakpoints,
    estimate_cache_savings,
)


class TestComputeBreakpoints:
    def test_empty_input_returns_empty_list(self):
        result = compute_breakpoints(CacheBreakpointInput())
        assert result == []

    def test_system_prompt_always_cached_when_non_empty(self):
        result = compute_breakpoints(CacheBreakpointInput(system_prompt_tokens=500))
        assert len(result) == 1
        assert result[0].position == "system"
        assert result[0].estimated_tokens == 500

    def test_tools_cached_when_present(self):
        result = compute_breakpoints(
            CacheBreakpointInput(tool_definition_tokens=1200),
        )
        assert len(result) == 1
        assert result[0].position == "tools"
        assert result[0].estimated_tokens == 1200

    def test_system_and_tools_both_cached(self):
        result = compute_breakpoints(
            CacheBreakpointInput(system_prompt_tokens=300, tool_definition_tokens=800),
        )
        assert len(result) == 2
        assert result[0].position == "system"
        assert result[1].position == "tools"

    def test_context_attachments_above_threshold(self):
        result = compute_breakpoints(
            CacheBreakpointInput(
                context_attachments=[
                    ("readme.md", 500),
                    ("large_file.py", 2048),
                ],
                threshold=1024,
            ),
        )
        assert len(result) == 1
        assert result[0].position == "context"
        assert result[0].index == 1  # second attachment (large_file.py)
        assert result[0].estimated_tokens == 2048

    def test_context_attachments_below_threshold_skipped(self):
        result = compute_breakpoints(
            CacheBreakpointInput(
                context_attachments=[("small.py", 500)],
                threshold=1024,
            ),
        )
        assert result == []

    def test_system_tools_and_context_all_together(self):
        result = compute_breakpoints(
            CacheBreakpointInput(
                system_prompt_tokens=200,
                tool_definition_tokens=600,
                context_attachments=[("data.json", 1500)],
                threshold=1024,
            ),
        )
        assert len(result) == 3
        assert [bp.position for bp in result] == ["system", "tools", "context"]

    def test_drops_smallest_context_when_over_max(self):
        """When more breakpoints than MAX_BREAKPOINTS, drop smallest context."""
        result = compute_breakpoints(
            CacheBreakpointInput(
                system_prompt_tokens=100,
                tool_definition_tokens=200,
                context_attachments=[
                    ("small.py", 500),
                    ("medium.py", 2000),
                    ("large.py", 5000),
                    ("huge.py", 10000),
                ],
                threshold=1,  # all qualify
            ),
        )
        # 2 (system + tools) + 4 context = 6, limit is 4 → keep 2 largest context
        assert len(result) == MAX_BREAKPOINTS  # 4
        context_bps = [bp for bp in result if bp.position == "context"]
        assert len(context_bps) == 2
        # Should keep the two largest: huge (10000) and large (5000)
        assert {bp.estimated_tokens for bp in context_bps} == {5000, 10000}

    def test_max_breakpoints_constant_is_4(self):
        assert MAX_BREAKPOINTS == 4

    def test_context_ordered_by_original_index(self):
        """After dropping, remaining context breakpoints keep original order."""
        result = compute_breakpoints(
            CacheBreakpointInput(
                system_prompt_tokens=100,
                tool_definition_tokens=200,
                context_attachments=[
                    ("a.py", 5000),
                    ("b.py", 10000),
                    ("c.py", 2000),
                ],
                threshold=1,
            ),
        )
        # 2 (system+tools) + 3 context = 5, limit 4 → keep 2 largest context
        context_bps = [bp for bp in result if bp.position == "context"]
        assert len(context_bps) == 2
        # Order should be: a.py (5000), b.py (10000) — original index order
        assert context_bps[0].index == 0  # a.py
        assert context_bps[1].index == 1  # b.py

    def test_default_threshold_is_1024(self):
        assert CacheBreakpointInput().threshold == 1024

    def test_system_zero_tokens_skipped(self):
        result = compute_breakpoints(
            CacheBreakpointInput(system_prompt_tokens=0, tool_definition_tokens=500),
        )
        assert len(result) == 1
        assert result[0].position == "tools"

    def test_tools_zero_tokens_skipped(self):
        result = compute_breakpoints(
            CacheBreakpointInput(system_prompt_tokens=500, tool_definition_tokens=0),
        )
        assert len(result) == 1
        assert result[0].position == "system"


class TestEstimateCacheSavings:
    def test_empty_breakpoints_save_zero(self):
        assert estimate_cache_savings([]) == 0

    def test_single_breakpoint(self):
        bps = [CacheBreakpoint(position="system", estimated_tokens=500)]
        assert estimate_cache_savings(bps) == 500

    def test_multiple_breakpoints(self):
        bps = [
            CacheBreakpoint(position="system", estimated_tokens=200),
            CacheBreakpoint(position="tools", estimated_tokens=600),
            CacheBreakpoint(position="context", index=0, estimated_tokens=1500),
        ]
        assert estimate_cache_savings(bps) == 2300

    def test_ttl_not_counted_in_savings(self):
        """TTL affects cache hit rate, not the per-call token savings."""
        bps = [
            CacheBreakpoint(position="system", estimated_tokens=100, ttl_seconds=300),
        ]
        assert estimate_cache_savings(bps) == 100
