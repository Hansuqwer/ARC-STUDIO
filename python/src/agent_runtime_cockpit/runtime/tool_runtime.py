"""Unified local tool runtime helpers."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from ..cli_repl.cancellation import CancellationToken
from ..tools import ToolRegistry, default_tool_registry, wrap_tool_result


def run_registered_tool(
    tool_name: str,
    args: dict[str, Any] | BaseModel | None = None,
    *,
    registry: ToolRegistry | None = None,
    cancellation_token: CancellationToken | None = None,
) -> str:
    """Execute one registered tool through the shared trust wrapper."""
    tools = registry or default_tool_registry()
    handler = tools.get(tool_name)
    if handler is None:
        raise ValueError(f"unknown tool: {tool_name}")
    raw_args = args or {}
    model_args = (
        raw_args
        if isinstance(raw_args, BaseModel)
        else handler.args_schema.model_validate(raw_args)
    )
    result = handler.execute(model_args, cancellation_token or CancellationToken())
    return wrap_tool_result(tool_name, handler.output_trust_level, result)
