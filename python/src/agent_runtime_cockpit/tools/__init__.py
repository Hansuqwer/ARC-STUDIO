"""Tool execution framework for Phase 5."""

from .builtin import GetCurrentTimeTool, ListDirectoryTool, ReadFileTool
from .protocol import ToolHandler, ToolResult
from .registry import ToolRegistrationError, ToolRegistry
from .wrapping import wrap_tool_result


def default_tool_registry() -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(ReadFileTool())
    registry.register(ListDirectoryTool())
    registry.register(GetCurrentTimeTool())
    return registry


__all__ = [
    "ToolHandler",
    "ToolResult",
    "ToolRegistry",
    "ToolRegistrationError",
    "default_tool_registry",
    "GetCurrentTimeTool",
    "ListDirectoryTool",
    "ReadFileTool",
    "wrap_tool_result",
]
