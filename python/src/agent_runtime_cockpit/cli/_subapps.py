"""All Typer sub-app instances for ARC CLI (Phase 25.4).

Each sub-app is defined here and imported by command modules and _app.py.
This avoids circular imports and keeps sub-app creation in one place.
"""

import typer

context_app = typer.Typer(name="context", help="Context retrieval commands")
adapter_app = typer.Typer(name="adapter", help="Adapter management commands")
continuum_app = typer.Typer(
    name="continuum", help="Session persistence — list and resume sessions (R86)"
)
git_native_app = typer.Typer(
    name="git-native",
    help="Git-native agent workflow — init workspace, auto-branch per session (R88)",
)
diff_app = typer.Typer(
    name="diff",
    help="Inline diff viewer and interactive patch apply (R89)",
)
index_app = typer.Typer(
    name="index",
    help="Local codebase index — build + search (R84)",
)
predict_app = typer.Typer(
    name="predict",
    help="Next-edit autocomplete predictions (R83)",
)
arena_app = typer.Typer(name="arena", help="LM Arena model battle and comparison")
doctor_app = typer.Typer(name="doctor", help="ARC diagnostics")
workspace_app = typer.Typer(name="workspace", help="Workspace configuration and trust management")
isolation_app = typer.Typer(name="isolation", help="Execution isolation providers")
sandbox_app = typer.Typer(name="sandbox", help="Sandbox policy and command execution")
sandbox_audit_app = typer.Typer(name="audit", help="Sandbox audit query commands")
sandbox_app.add_typer(sandbox_audit_app)
policy_app = typer.Typer(name="policy", help="Sandbox policy explanation")
config_app = typer.Typer(name="config", help="ARC workspace configuration (ADR-001)")
hitl_app = typer.Typer(name="hitl", help="Human-in-the-loop approval commands")
storage_app = typer.Typer(name="storage", help="Storage management commands")
studio_app = typer.Typer(name="studio", help="ARC Studio — chat REPL, sessions, and IDE tooling")
studio_sessions_app = typer.Typer(name="sessions", help="ARC Studio chat sessions")
runs_app = typer.Typer(
    name="runs", help="List and manage stored run records", invoke_without_command=True
)
eval_app = typer.Typer(name="eval", help="Evaluate runs against golden traces")
providers_app = typer.Typer(name="providers", help="Provider definitions and dry-run routing")
accounts_app = typer.Typer(name="accounts", help="Provider account metadata")
key_app = typer.Typer(name="key", help="Provider key references (env vars only)")
quota_app = typer.Typer(name="quota", help="Provider quota management")
routing_app = typer.Typer(name="routing", help="Provider routing policy")
receipt_app = typer.Typer(name="receipt", help="Run receipt commands (show/export/verify)")
audit_app = typer.Typer(name="audit", help="Audit chain verification and key management (ADR-005)")
profiles_app = typer.Typer(name="profiles", help="Run profile management")
prompt_app = typer.Typer(name="prompt", help="Prompt optimization commands (P1b local)")
mcp_app = typer.Typer(name="mcp", help="MCP Local Control Plane server (Phase 26 / R19)")
mcp_workbench_app = typer.Typer(
    name="workbench",
    help="MCP workbench diagnostics — inspect servers, check local MCP status (Phase 78 / R48)",
)
mcp_app.add_typer(mcp_workbench_app)
memory_app = typer.Typer(
    name="memory", help="Swarm memory graph research commands (Phase 59 / R26)"
)
task_app = typer.Typer(name="task", help="Async task execution and management (Phase 27 / R20)")
replay_app = typer.Typer(name="replay", help="Replay capability analysis (Phase 28 / R21)")
battle_app = typer.Typer(name="battle", help="SwarmGraph battle mode (Phase 34 / R26A)")
batch_app = typer.Typer(name="batch", help="Deterministic Phase 42 batch command execution")
events_app = typer.Typer(
    name="events", help="Event notifications, watch, and webhooks (Phase 32 / R25)"
)
swarmgraph_app = typer.Typer(
    name="swarmgraph",
    help="SwarmGraph commands — risk assessment, consensus protocol (Phase 51 / R24)",
)
review_app = typer.Typer(
    name="review",
    help="Review evidence — trace-aware review mode (Phase 74)",
)
plan_app = typer.Typer(
    name="plan",
    help="Plan/Apply/Review — deterministic plan-before-execution (Phase 75)",
)
testbench_app = typer.Typer(
    name="testbench",
    help="Test bench — detect and run tests through sandbox (Phase 79 / R49)",
)
ci_app = typer.Typer(
    name="ci",
    help="ARC CI guardrails — offline checks, PR summaries, audit verification (Phase 80 / R51)",
)
edit_app = typer.Typer(
    name="edit",
    help="Agentic edit loop — safety-gated plan/apply commands (Phase 85)",
)
ir_app = typer.Typer(
    name="ir",
    help="SwarmGraph IR — compile/inspect/validate normalized workflow graphs",
)
capabilities_app = typer.Typer(
    name="capabilities",
    help="Capability Cards — generate, inspect, validate, and lint typed capability manifests",
)
flight_app = typer.Typer(
    name="flight",
    help="Local Agent Flight Recorder — status/verify/export/prune/inspect",
)
obs_app = typer.Typer(
    name="obs",
    help="Observability export — OpenInference / OpenTelemetry local file export",
)
mobile_app = typer.Typer(
    name="mobile",
    help="ARC Mobile Runtime SDK — capabilities, simulator, runtime pack",
)
agents_app = typer.Typer(
    name="agents-md",
    help="AGENTS.md workspace ingestion — discover, pin, drift, cards",
)
skills_app = typer.Typer(
    name="skills",
    help="SKILL.md catalog — discover and inspect workspace skill definitions",
)
a2a_app = typer.Typer(
    name="a2a",
    help="A2A AgentCard — generate, inspect, verify, approve, invoke (loopback only)",
)
hub_app = typer.Typer(
    name="hub",
    help="Local-first catalog — share provider presets, policies, swarms, eval suites, themes (R91)",
    no_args_is_help=True,
)
vision_app = typer.Typer(
    name="vision",
    help="HITL-gated browser automation — screenshot, click, type, scroll (R93)",
    no_args_is_help=True,
)
advisor_app = typer.Typer(
    name="advisor",
    help="Token cost optimization advisor — analyze, simulate, pricing (R94)",
    no_args_is_help=True,
)
voice_app = typer.Typer(
    name="voice",
    help="Local voice-to-command — transcribe, listen, status (R96)",
    no_args_is_help=True,
)
composer_app = typer.Typer(
    name="composer",
    help="Visual SwarmGraph builder — generate, validate (R98)",
    no_args_is_help=True,
)
debug_app = typer.Typer(
    name="debug",
    help="DAP debugger — launch, attach, status (R99)",
    no_args_is_help=True,
)
notebook_app = typer.Typer(
    name="notebook",
    help="Agent workbook .arcnb — new, show, export, add-cell (R100)",
    no_args_is_help=True,
)
time_travel_app = typer.Typer(
    name="time-travel",
    help="Run replay & diff debugger — record, replay, branch, compare (R101)",
    no_args_is_help=True,
)
migrate_app = typer.Typer(
    name="migrate",
    help="Cross-adapter migration — detect, analyze, run, validate (R102)",
    no_args_is_help=True,
)
