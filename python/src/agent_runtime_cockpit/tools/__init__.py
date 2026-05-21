"""Tool execution framework for Phase 5."""

from .registry import ToolRegistry, ToolRegistrationError
from .protocol import ToolHandler, ToolResult
from .wrapping import wrap_tool_result
from .builtin import GetCurrentTimeTool, ListDirectoryTool, ReadFileTool


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
