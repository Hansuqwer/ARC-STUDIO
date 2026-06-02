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
    arena,  # noqa: F401
    audit,  # noqa: F401
    batch,  # noqa: F401
    battle,  # noqa: F401
    ci,  # noqa: F401 — Phase 80 / R51: CI guardrails
    discover,  # noqa: F401
    edit,  # noqa: F401 — Phase 85: safety-gated edit loop
    events,  # noqa: F401
    exec,  # noqa: F401
    info,  # noqa: F401
    ir,  # noqa: F401 — SwarmGraph IR compile/inspect/validate/policy
    mcp,  # noqa: F401
    memory,  # noqa: F401
    mgmt,  # noqa: F401
    plan,  # noqa: F401 — Phase 75: plan/apply/review
    profiles,  # noqa: F401
    prompt,  # noqa: F401
    providers,  # noqa: F401
    receipt,  # noqa: F401
    review,  # noqa: F401 — Phase 74: trace-aware review
    runs,  # noqa: F401
    sandbox,  # noqa: F401
    studio_workspace,  # noqa: F401
    testbench,  # noqa: F401
    swarmgraph,  # noqa: F401 — Phase 51: arc swarmgraph assess-risk
    task,  # noqa: F401 — Phase 27 / Phase 56: task CLI
)
from ._app import app, main

__all__ = ["app", "main"]
