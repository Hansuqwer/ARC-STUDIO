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

# Import legacy command handlers to register them on the app.
# These will be extracted into per-command modules in Phases 25.2-25.6.
from .. import _legacy_cli  # noqa: F401

__all__ = ["app", "main"]
