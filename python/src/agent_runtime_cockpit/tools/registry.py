"""Tool registry for managing available tools."""

from __future__ import annotations


class ToolRegistrationError(Exception):
    """Raised when tool registration fails validation."""
    pass


class ToolRegistry:
    """Registry for tool handlers with trust-level enforcement per ADR-019."""

    def __init__(self) -> None:
        self._handlers: dict[str, any] = {}

    def register(self, handler: any) -> None:
        """Register a tool handler.
        
        Raises:
            ToolRegistrationError: if handler lacks output_trust_level or declares invalid level
        """
        if not hasattr(handler, "output_trust_level"):
            raise ToolRegistrationError(
                f"Tool {handler.name!r} must declare output_trust_level "
                f"(one of 'untrusted', 'trusted', 'mixed')"
            )
        if handler.output_trust_level not in ("untrusted", "trusted", "mixed"):
            raise ToolRegistrationError(
                f"Tool {handler.name!r} declared invalid output_trust_level="
                f"{handler.output_trust_level!r}"
            )
        if handler.name in self._handlers:
            raise ToolRegistrationError(f"Tool {handler.name!r} already registered")
        self._handlers[handler.name] = handler

    def get(self, name: str) -> any | None:
        """Get a registered tool handler by name."""
        return self._handlers.get(name)

    def list_tools(self) -> list[str]:
        """List all registered tool names."""
        return list(self._handlers.keys())

    def all_handlers(self) -> list[any]:
        """Get all registered handlers."""
        return list(self._handlers.values())
