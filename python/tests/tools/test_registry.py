"""Tests for tool registry and trust boundaries per ADR-019."""

from __future__ import annotations

import pytest
from pydantic import BaseModel

from agent_runtime_cockpit.cli_repl.cancellation import CancellationToken, never_cancelled
from agent_runtime_cockpit.tools import (
    ToolHandler,
    ToolRegistry,
    ToolRegistrationError,
    ToolResult,
    wrap_tool_result,
)


class _NoOpArgs(BaseModel):
    pass


class _TrustedTool:
    name = "get_time"
    description = "Get current time"
    output_trust_level = "trusted"
    args_schema = _NoOpArgs
    output_byte_limit = 65536

    def execute(self, args: BaseModel, cancellation_token: CancellationToken) -> ToolResult:
        return ToolResult(content="2026-05-21T18:00:00Z")


class _UntrustedTool:
    name = "read_file"
    description = "Read file contents"
    output_trust_level = "untrusted"
    args_schema = _NoOpArgs
    output_byte_limit = 65536

    def execute(self, args: BaseModel, cancellation_token: CancellationToken) -> ToolResult:
        return ToolResult(content="file contents")


class _MixedTool:
    name = "git_log"
    description = "Git log with mixed trust"
    output_trust_level = "mixed"
    args_schema = _NoOpArgs
    output_byte_limit = 65536

    def execute(self, args: BaseModel, cancellation_token: CancellationToken) -> ToolResult:
        return ToolResult(
            content={"sha": "abc123", "message": "user commit message"},
            trust_overrides={"sha": "trusted", "message": "untrusted"},
        )


class _NoTrustLevelTool:
    name = "bad_tool"
    description = "Missing trust level"
    args_schema = _NoOpArgs

    def execute(self, args: BaseModel, cancellation_token: CancellationToken) -> ToolResult:
        return ToolResult(content="bad")


class _InvalidTrustLevelTool:
    name = "invalid_tool"
    description = "Invalid trust level"
    output_trust_level = "unknown"
    args_schema = _NoOpArgs

    def execute(self, args: BaseModel, cancellation_token: CancellationToken) -> ToolResult:
        return ToolResult(content="invalid")


def test_registry_registers_trusted_tool():
    registry = ToolRegistry()
    tool = _TrustedTool()
    registry.register(tool)
    assert registry.get("get_time") == tool
    assert "get_time" in registry.list_tools()


def test_registry_registers_untrusted_tool():
    registry = ToolRegistry()
    tool = _UntrustedTool()
    registry.register(tool)
    assert registry.get("read_file") == tool


def test_registry_registers_mixed_tool():
    registry = ToolRegistry()
    tool = _MixedTool()
    registry.register(tool)
    assert registry.get("git_log") == tool


def test_registry_rejects_tool_without_trust_level():
    registry = ToolRegistry()
    with pytest.raises(ToolRegistrationError) as exc:
        registry.register(_NoTrustLevelTool())
    assert "must declare output_trust_level" in str(exc.value)


def test_registry_rejects_tool_with_invalid_trust_level():
    registry = ToolRegistry()
    with pytest.raises(ToolRegistrationError) as exc:
        registry.register(_InvalidTrustLevelTool())
    assert "invalid output_trust_level" in str(exc.value)


def test_registry_rejects_duplicate_registration():
    registry = ToolRegistry()
    registry.register(_TrustedTool())
    with pytest.raises(ToolRegistrationError) as exc:
        registry.register(_TrustedTool())
    assert "already registered" in str(exc.value)


def test_wrap_trusted_tool_result():
    result = ToolResult(content="2026-05-21T18:00:00Z")
    wrapped = wrap_tool_result("get_time", "trusted", result)
    assert wrapped == '<tool_result trust="trusted" tool="get_time">2026-05-21T18:00:00Z</tool_result>'


def test_wrap_untrusted_tool_result():
    result = ToolResult(content="file contents")
    wrapped = wrap_tool_result("read_file", "untrusted", result)
    assert wrapped == '<tool_result trust="untrusted" tool="read_file">file contents</tool_result>'


def test_wrap_mixed_tool_result_raises_not_implemented():
    result = ToolResult(
        content={"sha": "abc123", "message": "user message"},
        trust_overrides={"sha": "trusted", "message": "untrusted"},
    )
    with pytest.raises(NotImplementedError) as exc:
        wrap_tool_result("git_log", "mixed", result)
    assert "deferred to Phase 7+" in str(exc.value)
    assert "ADR-019" in str(exc.value)


def test_tool_result_with_trust_overrides_requires_dict():
    with pytest.raises(ValueError) as exc:
        ToolResult(content="string", trust_overrides={"field": "trusted"})
    assert "trust_overrides requires content to be a dict" in str(exc.value)


def test_tool_result_dict_content_without_overrides():
    result = ToolResult(content={"key": "value"})
    assert result.content == {"key": "value"}
    assert result.trust_overrides == {}


def test_registry_list_tools_returns_all_names():
    registry = ToolRegistry()
    registry.register(_TrustedTool())
    registry.register(_UntrustedTool())
    names = registry.list_tools()
    assert set(names) == {"get_time", "read_file"}


def test_registry_all_handlers_returns_all_tools():
    registry = ToolRegistry()
    trusted = _TrustedTool()
    untrusted = _UntrustedTool()
    registry.register(trusted)
    registry.register(untrusted)
    handlers = registry.all_handlers()
    assert len(handlers) == 2
    assert trusted in handlers
    assert untrusted in handlers
