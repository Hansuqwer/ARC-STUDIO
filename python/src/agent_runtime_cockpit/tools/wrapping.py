"""Tool result trust wrapping per ADR-019."""

from __future__ import annotations


def wrap_tool_result(
    tool_name: str,
    trust_level: str,
    result: any,
) -> str:
    """Wrap tool result with trust envelope per ADR-019.

    Args:
        tool_name: Name of the tool that produced the result
        trust_level: "trusted", "untrusted", or "mixed"
        result: ToolResult instance

    Returns:
        XML-wrapped tool result string

    Raises:
        NotImplementedError: if trust_level is "mixed" (deferred to Phase 7+)

    """
    content = result.content if hasattr(result, "content") else str(result)

    if trust_level == "trusted":
        return f'<tool_result trust="trusted" tool="{tool_name}">{content}</tool_result>'

    if trust_level == "untrusted":
        return f'<tool_result trust="untrusted" tool="{tool_name}">{content}</tool_result>'

    if trust_level == "mixed":
        raise NotImplementedError(
            f"Mixed-trust tool results are deferred to Phase 7+. "
            f"Tool {tool_name!r} declared output_trust_level='mixed' but the wrapper "
            f"implementation is not yet available. See ADR-019 for the contract."
        )

    raise ValueError(f"Invalid trust_level: {trust_level!r}")
