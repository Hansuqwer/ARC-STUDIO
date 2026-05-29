"""Tool execution framework for Phase 5."""

from pathlib import Path

from .builtin import GetCurrentTimeTool, ListDirectoryTool, ReadFileTool
from .protocol import ToolHandler, ToolResult
from .registry import ToolRegistrationError, ToolRegistry
from .shell import BashTool
from .wrapping import wrap_tool_result
from .write import CreateFileTool, EditFileTool, WriteFileTool


def default_tool_registry(
    workspace_root: Path | None = None, trust_db: Path | None = None
) -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(ReadFileTool())
    registry.register(ListDirectoryTool())
    registry.register(GetCurrentTimeTool())
    if trust_db is None:
        registry.register(WriteFileTool(workspace_root))
        registry.register(EditFileTool(workspace_root))
        registry.register(CreateFileTool(workspace_root))
        registry.register(BashTool(workspace_root))
    else:
        registry.register(WriteFileTool(workspace_root, trust_db))
        registry.register(EditFileTool(workspace_root, trust_db))
        registry.register(CreateFileTool(workspace_root, trust_db))
        registry.register(BashTool(workspace_root, trust_db=trust_db))
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
    "WriteFileTool",
    "EditFileTool",
    "CreateFileTool",
    "BashTool",
    "wrap_tool_result",
]
