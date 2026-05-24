"""ARC CLI — Agent Runtime Cockpit command-line interface.

Commands:
  arc version    — print ARC version information
  arc health     — check ARC daemon and environment health
  arc status     — show ARC workspace and runtime status overview
  arc inspect    — inspect workspace, detect runtimes
  arc runtimes   — list detected runtimes
  arc workflows  — list detected workflows
  arc schemas    — list detected schemas
  arc serve      — start HTTP daemon
  arc run        — execute a workflow
  arc runs       — list stored runs
  arc doctor     — diagnostics (swarmgraph, all)
  arc context    — context retrieval commands
  arc adapter    — adapter management and conformance testing
"""

from __future__ import annotations

# Phase 25: decomposed CLI modules. Re-export for backward compatibility.
from .cli._app import app, console, err_console, main  # noqa: F401
from .cli._helpers import (  # noqa: F401
    DEBUG_FLAG,
    JSON_FLAG,
    LOCAL_REAL_GATE_ENVS,
    WORKSPACE_FLAG,
    _local_real_gate_open,
    _local_real_gate_state,
    _out,
    _profile_payload,
    _run_preflight,
    _setup_logging,
    _validate_runtime_mode,
    _workspace,
    check_swarmgraph_runtime,
)
from .cli._subapps import (  # noqa: F401
    accounts_app,
    adapter_app,
    config_app,
    context_app,
    doctor_app,
    eval_app,
    hitl_app,
    isolation_app,
    key_app,
    profiles_app,
    prompt_app,
    providers_app,
    quota_app,
    routing_app,
    storage_app,
    studio_app,
    studio_sessions_app,
    workspace_app,
)


# ─── version ──────────────────────────────────────────────────────────────────
