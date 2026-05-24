"""ARC CLI — decomposed command modules (Phase 25).

This package replaces the monolithic ``cli.py`` (4225 lines) with per-command
modules. Legacy command handlers are imported from ``_legacy_commands`` for
backward compatibility during the decomposition.
"""

# Legacy re-exports for backward compatibility.
from .. import _legacy_cli  # noqa: F401

# Phase 25.2: extracted info commands
# Phase 25.3: extracted discovery and execution commands
# Phase 25.4: extracted runs, receipt, audit, profile commands
# Phase 26: extracted MCP commands
# Phase 25.5: extracted providers, mgmt, studio_workspace, prompt commands
# Phase 34: battle mode commands
from . import (
    audit,  # noqa: F401
    battle,  # noqa: F401
    discover,  # noqa: F401
    exec,  # noqa: F401
    info,  # noqa: F401
    mcp,  # noqa: F401
    mgmt,  # noqa: F401
    profiles,  # noqa: F401
    prompt,  # noqa: F401
    providers,  # noqa: F401
    receipt,  # noqa: F401
    runs,  # noqa: F401
    sandbox,  # noqa: F401
    studio_workspace,  # noqa: F401
)
from ._app import app, main

__all__ = ["app", "main"]
