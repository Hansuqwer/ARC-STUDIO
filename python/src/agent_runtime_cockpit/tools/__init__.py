"""Tool execution framework for Phase 5."""

from .registry import ToolRegistry, ToolRegistrationError
from .protocol import ToolHandler, ToolResult
from .wrapping import wrap_tool_result

__all__ = [
    "ToolHandler",
    "ToolResult",
    "ToolRegistry",
    "ToolRegistrationError",
    "wrap_tool_result",
]
