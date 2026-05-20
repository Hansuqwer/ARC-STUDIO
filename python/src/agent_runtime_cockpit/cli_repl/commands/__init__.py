"""
Unified slash command registry for ARC Studio CLI REPL.

Provides a declarative registry of all slash commands, their aliases,
categories, required gates, and handler functions. The registry is the
single source of truth for both the CLI REPL and IDE command palette.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class CommandDef:
    """Declarative definition of a slash command."""

    name: str  # leading "/" stripped
    help_text: str  # one-line summary
    category: str  # session | runtime | run | provider | workspace | meta | passthrough | context | memory | planning | compliance
    handler: Callable[..., str | None]
    aliases: list[str] = field(default_factory=list)
    gates_required: list[str] = field(default_factory=list)
    mode_required: list[str] = field(default_factory=list)
    visible_in_ide: bool = True
    popup_visible: bool = True
    renders: list[str] = field(default_factory=lambda: ["present"])
    requires_events: list[str] = field(default_factory=list)
    privileged: bool = False
    trust_required: str | None = None  # system | user | workspace


class CommandRegistry:
    """Declarative registry of slash commands."""

    def __init__(self) -> None:
        self._commands: dict[str, CommandDef] = {}
        self._aliases: dict[str, str] = {}

    def register(self, cmd: CommandDef) -> None:
        """Register a command definition."""
        if cmd.name in self._commands:
            msg = f"Command '{cmd.name}' already registered"
            raise ValueError(msg)
        self._commands[cmd.name] = cmd
        for alias in cmd.aliases:
            if alias in self._aliases:
                msg = f"Alias '{alias}' already registered"
                raise ValueError(msg)
            self._aliases[alias] = cmd.name

    def get(self, name: str) -> CommandDef | None:
        """Look up a command by name (with or without leading /)."""
        clean = name.lstrip("/").lower()
        if clean in self._commands:
            return self._commands[clean]
        if clean in self._aliases:
            alias_target = self._aliases[clean]
            return self._commands.get(alias_target)
        return None

    def has(self, name: str) -> bool:
        """Check if a command is registered."""
        return self.get(name) is not None

    def list_commands(self, category: str | None = None) -> list[CommandDef]:
        """List all registered commands, optionally filtered by category."""
        cmds = list(self._commands.values())
        if category:
            cmds = [c for c in cmds if c.category == category]
        return sorted(cmds, key=lambda c: c.name)

    def categories(self) -> list[str]:
        """Return all unique categories in the registry."""
        return sorted({c.category for c in self._commands.values()})

    @property
    def commands(self) -> dict[str, CommandDef]:
        return dict(self._commands)

    @property
    def aliases(self) -> dict[str, str]:
        return dict(self._aliases)

    def help_text(self, category: str | None = None) -> str:
        """Generate formatted help text."""
        lines: list[str] = []
        cmds = self.list_commands(category)
        if not cmds:
            return "No commands available."

        by_cat: dict[str, list[CommandDef]] = {}
        for c in cmds:
            by_cat.setdefault(c.category, []).append(c)

        for cat in sorted(by_cat):
            lines.append(f"\n  [{cat.upper()}]")
            for c in by_cat[cat]:
                alias_str = ""
                if c.aliases:
                    alias_str = f" ({', '.join('/' + a for a in c.aliases)})"
                lines.append(f"    /{c.name}{alias_str}  {c.help_text}")
        return "\n".join(lines)


# Global singleton registry
_registry: CommandRegistry | None = None


def get_registry() -> CommandRegistry:
    """Get or create the global command registry singleton."""
    global _registry  # noqa: PLW0603
    if _registry is None:
        _registry = CommandRegistry()
    return _registry


def reset_registry() -> None:
    """Reset the global registry (for testing)."""
    global _registry  # noqa: PLW0603
    _registry = None
