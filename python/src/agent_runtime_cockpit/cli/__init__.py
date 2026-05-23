"""
ARC CLI — decomposed command modules (Phase 25).

This package replaces the monolithic ``cli.py`` (4225 lines) with per-command
modules. Legacy command handlers are imported from ``_legacy_commands`` for
backward compatibility during the decomposition.
"""

from ._app import app, main

# Phase 25.2: extracted info commands
from . import info  # noqa: F401

# Phase 25.3: extracted discovery and execution commands
from . import discover  # noqa: F401
from . import exec  # noqa: F401

# Phase 25.4: extracted runs, receipt, audit, profile commands
from . import runs  # noqa: F401
from . import receipt  # noqa: F401
from . import audit  # noqa: F401
from . import profiles  # noqa: F401

# Phase 25.5: extracted providers, mgmt, studio_workspace, prompt commands
from . import providers  # noqa: F401
from . import mgmt  # noqa: F401
from . import studio_workspace  # noqa: F401
from . import prompt  # noqa: F401

# Legacy re-exports for backward compatibility.
from .. import _legacy_cli  # noqa: F401

__all__ = ["app", "main"]
