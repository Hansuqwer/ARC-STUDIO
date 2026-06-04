"""Tests for QW-4 tool-output virtualization interceptor."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch


from agent_runtime_cockpit.budget.storage import SQLiteWALStorage
from agent_runtime_cockpit.context.handles import HandleStore, URI_SCHEME
from agent_runtime_cockpit.context.tool_interceptor import virtualize_tool_outputs
from agent_runtime_cockpit.events import reset_bus
from agent_runtime_cockpit.events.types import ToolOutputVirtualized
from agent_runtime_cockpit.providers.base import ProviderMessage, ProviderRequest


def _request(tool_content: str, extra_msgs: list[ProviderMessage] | None = None) -> ProviderRequest:
    msgs = [ProviderMessage(role="user", content="call tool", trust="user")]
    msgs.append(ProviderMessage(role="tool", content=tool_content, trust="untrusted"))
    if extra_msgs:
        msgs.extend(extra_msgs)
    return ProviderRequest(model="claude-3-5-sonnet-latest", messages=msgs, max_tokens=100)


def _store(tmp_path: Path) -> HandleStore:
    return HandleStore(SQLiteWALStorage(tmp_path / "t.db"))


# ── 1. Small tool output not virtualized ──────────────────────────────────


def test_small_output_unchanged(tmp_path):
    hs = _store(tmp_path)
    req = _request("small")
    result = virtualize_tool_outputs(req, hs, threshold=8192)
    assert result is req  # same object — no copy
    assert result.messages[1].content == "small"


# ── 2. Large tool output virtualized ─────────────────────────────────────


def test_large_output_virtualized(tmp_path):
    hs = _store(tmp_path)
    big = "X" * 9000
    req = _request(big)
    result = virtualize_tool_outputs(req, hs, threshold=8192)
    assert result is not req
    replaced = result.messages[1].content
    assert "Handle: " + URI_SCHEME in replaced
    assert "/expand " in replaced


# ── 3. Non-tool messages not touched ─────────────────────────────────────


def test_non_tool_messages_untouched(tmp_path):
    hs = _store(tmp_path)
    big = "Y" * 9000
    req = _request(big)
    result = virtualize_tool_outputs(req, hs, threshold=8192)
    # user message at index 0 unchanged
    assert result.messages[0].content == "call tool"


# ── 4. ToolOutputVirtualized event emitted ───────────────────────────────


def test_event_emitted(tmp_path):
    reset_bus()
    hs = _store(tmp_path)
    emitted = []

    from agent_runtime_cockpit.events import get_bus

    get_bus().subscribe("tool_output_virtualized", emitted.append)

    req = _request("Z" * 9000)
    virtualize_tool_outputs(req, hs, threshold=8192)

    assert len(emitted) == 1
    ev = emitted[0]
    assert isinstance(ev, ToolOutputVirtualized)
    assert ev.original_size_bytes == 9000
    assert ev.handle_uri.startswith(URI_SCHEME)


# ── 5. No event emitted for small output ─────────────────────────────────


def test_no_event_for_small_output(tmp_path):
    reset_bus()
    hs = _store(tmp_path)
    emitted = []

    from agent_runtime_cockpit.events import get_bus

    get_bus().subscribe("tool_output_virtualized", emitted.append)

    req = _request("tiny")
    virtualize_tool_outputs(req, hs, threshold=8192)
    assert emitted == []


# ── 6. Multiple tool messages — only large ones virtualized ──────────────


def test_only_large_messages_virtualized(tmp_path):
    hs = _store(tmp_path)
    small_tool = ProviderMessage(role="tool", content="small output", trust="untrusted")
    big_content = "B" * 9000
    req = ProviderRequest(
        model="gpt-4o",
        messages=[
            ProviderMessage(role="user", content="query", trust="user"),
            ProviderMessage(role="tool", content=big_content, trust="untrusted"),
            small_tool,
        ],
        max_tokens=100,
    )
    result = virtualize_tool_outputs(req, hs, threshold=8192)
    assert "Handle:" in result.messages[1].content
    assert result.messages[2].content == "small output"


# ── 7. No LLM calls in virtualization path ───────────────────────────────


def test_no_llm_in_virtualization_path(tmp_path):
    """CoSAI: virtualization must not invoke any LLM client."""
    hs = _store(tmp_path)
    with patch("openai.OpenAI") as mock_openai:
        req = _request("W" * 9000)
        virtualize_tool_outputs(req, hs, threshold=8192)
        mock_openai.assert_not_called()


# ── 8. Handle URI in replaced content can be expanded ────────────────────


def test_virtualized_handle_is_expandable(tmp_path):
    hs = _store(tmp_path)
    original = "original content " * 600  # > 8KB
    req = _request(original)
    result = virtualize_tool_outputs(req, hs, threshold=8192)
    # Extract prefix from the replaced message
    replaced = result.messages[1].content
    prefix_line = [ln for ln in replaced.splitlines() if ln.startswith("To expand: /expand ")][0]
    prefix = prefix_line.split("/expand ")[1].strip()
    expanded = hs.expand(prefix)
    assert expanded.decode() == original
