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
    continuum,  # noqa: F401 — Phase 279 / R86b: session persistence list/resume
    diff_cmd,  # noqa: F401 — Phase 291 / R89a: arc diff apply --interactive
    hub,  # noqa: F401 — Phase 316 / R91: arc hub list/add/remove/verify/inspect
    vision,  # noqa: F401 — Phase 318 / R93: arc vision screenshot/click/type/scroll
    advisor,  # noqa: F401 — Phase 319 / R94: arc advisor analyze/simulate/pricing
    voice,  # noqa: F401 — Phase 321 / R96: arc voice transcribe/listen/status
    composer,  # noqa: F401 — Phase 323 / R98: arc composer generate/validate
    debug,  # noqa: F401 — Phase 324 / R99: arc debug launch/attach/status
    notebook,  # noqa: F401 — Phase 325 / R100: arc notebook new/show/export/add-cell
    index_cmd,  # noqa: F401 — Phase 303 / R84: arc index build/search
    context_cmd,  # noqa: F401 — Phase 305 / R85: arc context suggest/attach
    memory_cmd,  # noqa: F401 — Phase 307 / R90: arc memory save/load/search
    predict_cmd,  # noqa: F401 — Phase 309 / R83: arc predict next-edit
    discover,  # noqa: F401
    edit,  # noqa: F401 — Phase 85: safety-gated edit loop
    events,  # noqa: F401
    exec,  # noqa: F401
    git_native,  # noqa: F401 — Phase 289 / R88a: git-native init + auto-branch
    info,  # noqa: F401
    ir,  # noqa: F401 — SwarmGraph IR compile/inspect/validate/policy
    simulate,  # noqa: F401 — SwarmGraph IR action simulation (arc ir simulate)
    capabilities,  # noqa: F401 — Capability Cards (arc capabilities)
    capabilities_policy,  # noqa: F401 — Capability Cards policy linting
    flight,  # noqa: F401 — Local Agent Flight Recorder (arc flight)
    obs,  # noqa: F401 — Observability export (arc obs)
    mobile,  # noqa: F401 — Mobile Runtime SDK (arc mobile)
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
    runtime_pack,  # noqa: F401 — Runtime Pack SDK commands
)
from ._app import app, main

__all__ = ["app", "main"]
