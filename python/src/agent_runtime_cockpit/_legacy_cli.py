"""
ARC CLI — Agent Runtime Cockpit command-line interface.

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
from .cli._app import app, main, console, err_console  # noqa: F401
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
from .cli._helpers import (  # noqa: F401
    JSON_FLAG,
    WORKSPACE_FLAG,
    DEBUG_FLAG,
    LOCAL_REAL_GATE_ENVS,
    _setup_logging,
    _workspace,
    _out,
    _profile_payload,
    _validate_runtime_mode,
    _local_real_gate_open,
    _local_real_gate_state,
    _run_preflight,
    check_swarmgraph_runtime,
)


# ─── version ──────────────────────────────────────────────────────────────────
