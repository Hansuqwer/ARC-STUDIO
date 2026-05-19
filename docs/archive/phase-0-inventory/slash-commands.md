# Phase 0 — Slash Command Inventory

Status: DRAFT (Phase 0 inventory, non-destructive)
Scope: every slash command in `cli_studio.py` and `cli_repl/`.
Output: unified declarative registry shape for Phase 2.

## How to fill this file

1. Grep both REPLs for slash handlers.
2. For each, record current behavior, gates touched, and target registry entry.
3. Disposition: Keep | Merge | Add | Retire.

## Current: cli_studio.py slash commands

| Command | Handler | Behavior summary | Gates touched | Disposition | Target name |
|---|---|---|---|---|---|
| /help | <symbol> | list commands | none | Merge | /help |
| /status | <symbol> | print status | none | Merge | /status |
| /doctor | <symbol> | run doctor | none | Retire | use `!arc doctor` passthrough |
| /runs | <symbol> | list runs | none | Merge | /runs |
| /plan | <symbol> | switch mode=plan | none | Merge | /mode plan |
| /build | <symbol> | switch mode=build | none | Merge | /mode build |
| /auto | <symbol> | switch mode=auto | none | Merge | /mode auto |
| /exit | <symbol> | quit | none | Merge | /exit |

## Current: cli_repl/ slash commands

| Command | Handler | Behavior summary | Gates touched | Disposition | Target name |
|---|---|---|---|---|---|
| /help | <symbol> | list commands | none | Merge | /help |
| /clear | <symbol> | clear transcript | none | Keep | /clear |
| /run | <symbol> | execute via SwarmGraphRunner | none currently | Merge | /run (gate-aware in Phase 2) |
| /summary | <symbol> | session summary | none | Keep | /summary |
| /sessions | <symbol> | list sessions | none | Merge | /sessions |
| /history | <symbol> | history view | none | Keep | /history |
| /version | <symbol> | print version | none | Keep | /version |
| /quit | <symbol> | quit | none | Merge | /exit |
| /exit | <symbol> | quit | none | Keep | /exit |

## Target unified registry (Phase 2)

Registry location (locked): `python/src/agent_runtime_cockpit/cli_repl/commands/`
Entry shape (declarative):

| Field | Type | Required | Notes |
|---|---|---|---|
| name | str | yes | leading `/` stripped |
| aliases | list[str] | no | e.g. /quit → /exit |
| help | str | yes | one-line summary |
| gates_required | list[str] | no | e.g. ["paid_call"] |
| mode_required | list[str] | no | e.g. ["build", "auto"] |
| handler | callable | yes | sync or async |
| visible_in_ide | bool | yes | IDE command palette reads only visible=true |
| category | str | yes | session/runtime/run/provider/workspace/meta/passthrough/context |
| popup_visible | bool | yes | shown in slash popup |
| renders | list[str] | yes | present/absent/degraded/blocked states command can produce |
| requires_events | list[str] | no | event names required for present state |

## Renderer contract (locked)

| State | Meaning | Required behavior |
|---|---|---|
| present | event/material exists | render real data |
| absent | no event/material | render no-data message with reason |
| degraded | partial event/material | render partial data + degraded badge/reason |
| blocked | gate not satisfied | render gate name and remediation |
| measured | cost/topology field tagged `source=measured` | show without caveat |
| estimated | cost/topology field tagged `source=estimated` | show with estimated badge |

Never fabricate numbers, hide degraded state, show measured badge unless `source=measured`, or show topology unless `SWARMGRAPH_TOPOLOGY` events are present.

## Full target slash inventory

| Category | Command | Aliases | Renders | Requires events | Gates | Phase |
|---|---|---|---|---|---|---|
| session | /new | | present | — | — | 2 |
| session | /resume | | present, absent | — | — | 2 |
| session | /continue | | present, absent | — | — | 2 |
| session | /fork | | present | — | — | 2 |
| session | /sessions | | present, absent | — | — | 2 |
| session | /compact | /memory compact | present | — | — | 2 |
| session | /clear | | present | — | — | 2 |
| session | /history | | present, absent | — | — | 2 |
| session | /summary | | present, absent | — | — | 2 |
| session | /export | | present, absent | — | — | 2 |
| runtime | /runtime | | present, blocked | capability_report | — | 2 |
| runtime | /mode | | present, blocked | capability_report | — | 2 |
| runtime | /profile | | present | — | — | 2 |
| runtime | /isolation | | present | — | — | 2 |
| runtime | /model | | present, blocked, absent | capability_report | provider-backed only | 2 |
| runtime | /preflight | | present, blocked | — | — | 2 |
| run | /run | | present, blocked | — | paid_call if provider-backed | 2 |
| run | /runs | | present, absent | — | — | 2 |
| run | /status | | present, absent | — | — | 2 |
| run | /graph | /topology | present, absent, degraded | SWARMGRAPH_TOPOLOGY | — | 2 |
| run | /timeline | alias /graph --timeline | present, absent, degraded | SWARMGRAPH_EVENT | — | 2 |
| run | /budget | | present, absent, degraded | COST_EVENT | — | 2 |
| run | /audit | | present, absent, degraded | AUDIT_EVENT | — | 2 |
| run | /hitl | | present, absent, degraded | HITL_PROMPT | — | 2 |
| provider | /providers | | present, absent, blocked | provider_diagnostics | — | 2 |
| provider | /quota | | present, absent | quota_counter | — | 2 |
| provider | /provider-action | | present, blocked | — | 3-layer gate | 2 |
| workspace | /init | | present | — | — | 2 |
| workspace | /config | | present | — | — | 2 |
| workspace | /doctor | | present, degraded | — | — | 2 |
| workspace | /workflows | | present, absent, blocked | workflow_detection | — | 2 |
| workspace | /context | | present, absent | — | — | 2 |
| meta | /help | | present | — | — | 2 |
| meta | /version | | present | — | — | 2 |
| meta | /update | | present, absent | — | — | 2 |
| meta | /exit | /quit | present | — | — | 2 |
| passthrough | ! | | depends | — | depends on subcommand | 2 |
| context | @ | | present, absent | — | — | 2 |
| memory | /memory | | present, absent, blocked | memory_index | workspace trust | 2 |
| memory | /memory show | | present, absent | memory_index | workspace trust | 2 |
| memory | /memory add | | present, blocked | — | workspace trust | 2 |
| memory | /memory forget | | present, blocked | — | confirmation | 2 |
| memory | /memory compact | /compact | present | — | — | 2 |
| planning | /plan | | present, blocked | — | — | 2 |
| planning | /plan show | | present, absent | — | — | 2 |
| planning | /plan approve | | present, blocked | — | confirmation | 2 |
| planning | /plan edit | | present, blocked | — | build/auto mode | 2 |
| planning | /plan discard | | present, blocked | — | confirmation | 2 |
| planning | /build | | present, blocked | — | mode policy | 2 |
| planning | /auto | | present, blocked | — | mode policy + gates | 2 |
| compliance | /receipt | | present, absent, degraded | receipt material | — | 2 |
| compliance | /contract | | present, absent, degraded | run contract | — | 2 |

## Alias and renderer lock

| UX entry | Canonical handler | Notes |
|---|---|---|
| `/graph [run-id]` | graph renderer topology view | queen → workers tree |
| `/topology [run-id]` | `/graph` | alias only, no separate impl |
| `/graph --timeline [run-id]` | graph renderer timeline view | event-ordered timeline |
| `/timeline [run-id]` | `/graph --timeline` | alias only, no separate impl |
| `/graph --json [run-id]` | graph renderer raw view | raw event-backed graph data |

## Provider UX lock

| Command | Locked behavior |
|---|---|
| `/providers` | table columns: provider, configured, key_source, default_model, dry_run/live, quota_used, quota_limit, blocked_reason |
| `/providers <name>` | full diagnostics, routing rules, accounts list if available |
| `/providers refresh` | re-run diagnostics |
| `/quota` | ARC local quota counters only; no remote-provider reset claim |
| `/quota reset [provider]` | inline confirmation-gated |
| `/provider-action` | env gate + paid gate + exact token + inline y/N; blocked state if any gate missing |

## HITL UX lock

| Command | Locked behavior |
|---|---|
| `/hitl` | pending prompts table: id, run_id, prompt, created, expires; cwd-scoped by default, `--all` global |
| `/hitl <id>` | full prompt text |
| `/hitl approve <id> [--note <text>]` | inline approval card |
| `/hitl reject <id> [--note <text>]` | inline rejection card |
| `/hitl respond <id> <response>` | multiline editor; Esc Esc cancels |

## Workflow UX lock

| Command | Locked behavior |
|---|---|
| `/workflows` | table columns: name, runtime, source_path, runnable/blocked, remediation |
| `/workflows <name>` | detail view with capability report and input schema if present |
| `/workflows pick` | picker sets active workflow; blocked rows greyed out and not selectable |
| `/run` | active workflow → run it; composer text → prompt-run; otherwise opens `/workflows pick` |

## Context UX lock

| Command | Locked behavior |
|---|---|
| `@<path>` | fuzzy file/context picker scoped to workspace |
| `/context` | show currently attached context |
| `/context pack` | invoke `arc context pack` for current session |
| `/context clear` | detach all context |
| `/context add <path>` | same as `@<path>` |

## ADR-013/014/015 slash inventory additions

| Category | Command | Aliases | Renders | Requires events | Gates | Phase |
|---|---|---|---|---|---|---|
| swarmgraph | /swarmgraph | | present | swarmgraph.* | — | 4 |
| swarmgraph | /swarmgraph fan-out | | present, absent | swarmgraph.fan_out | — | 4 |
| swarmgraph | /swarmgraph consensus | | present, absent | swarmgraph.consensus | — | 4 |
| swarmgraph | /swarmgraph checkpoint | | present, absent | swarmgraph.checkpoint | — | 4 |
| swarmgraph | /swarmgraph checkpoint show | | present | swarmgraph.checkpoint | — | 4 |
| swarmgraph | /swarmgraph failure | | present, absent | swarmgraph.failure_mode | — | 4.7 |
| swarmgraph | /swarmgraph roles | | present | — | — | 4 |
| mcp | /mcp diff | | present, absent | — | — | 5.6 |
| mcp | /mcp repin | | present | — | workspace trust | 5.6 |
| mcp | /mcp verify | | present, degraded | — | — | 5.6 |
| mcp | /mcp audit | | present, absent | MCP audit events | — | 5.6 |
| trust | /trust | | present | — | — | 4 |
| trust | /trust show | | present | — | — | 4 |
| trust | /trust downgrade | | present | — | — | 4 |
| trust | /trust audit | | present, absent | trust_change events | — | 4 |
| compliance | /receipt verify | | present, degraded | — | — | 4 |
| compliance | /receipt export | | present | — | — | 4 |
| compliance | /receipt export --compliance | | present | — | — | 5 |

## Current Code Evidence

| Source | Commands | Evidence | Notes |
|---|---|---|---|
| `cli_studio.py` | `/help`, `/status`, `/doctor`, `/runs`, `/plan`, `/build`, `/auto`, `/exit` | `python/src/agent_runtime_cockpit/cli_studio.py:40-54`, `195-242` | local shell only; prints "No agent execution in v0.1" for non-slash messages |
| `cli_repl/slash_commands.py` | `/help`, `/clear`, `/run`, `/summary`, `/sessions`, `/history`, `/version`, `/quit`, `/exit` | `python/src/agent_runtime_cockpit/cli_repl/slash_commands.py:10-95` | `/run` directly constructs `SwarmGraphRunner`; no gates/profile/preflight yet |
| `cli_repl/chat_repl.py` | non-slash prompt execution | `python/src/agent_runtime_cockpit/cli_repl/chat_repl.py:92-101` | direct native fake/offline SwarmGraph run; no command registry yet |

## Planning Semantics Lock

| Command | Locked behavior |
|---|---|
| `/plan` | produce or update draft plan; read-only by default; no file edits |
| `/plan show` | render active plan plus status/source turn |
| `/plan approve` | set `plan_status=approved`; required before build in strict policy |
| `/plan edit` | edit draft plan, preserves plan history |
| `/plan discard` | set `plan_status=discarded`; does not delete transcript |
| `/build` | switch to build mode and execute approved step or current request within gates |
| `/auto` | policy-driven plan/build loop; never bypasses paid/security/HITL gates |

SwarmGraph target flow: `queen_plan -> queen_decompose -> worker_execute -> consensus_review`. Current native runner begins at `queen_prepare_agents/queen_decompose` and lacks explicit `queen_plan` naming (`swarmgraph/runner.py:50-93`).

## Memory Semantics Lock

| Memory type | Scope | Default | Rule |
|---|---|---|---|
| session | current session | enabled | transcript summary + user-approved facts |
| project | cwd/project id | disabled until trusted | workspace trust required |
| user | user profile | disabled until explicit opt-in | never stores secrets/raw credentials |
| runtime | capability/report cache | enabled | informational only; cannot grant permissions |

`/compact` is an alias to `/memory compact`; implementation must avoid implying perfect recall.

## Registry Entry Shape (final, with ADR-014 additions)

| Field | Type | Required | Notes |
|---|---|---|---|
| name | str | yes | leading `/` stripped |
| aliases | list[str] | no | e.g. /quit → /exit |
| help | str | yes | one-line summary |
| category | str | yes | see categories below |
| gates_required | list[str] | no | e.g. ["paid_call", "workspace_trust"] |
| trust_required | enum | no | system | user | workspace |
| privileged | bool | yes | true = queen-authorization required |
| mode_required | list[str] | no | e.g. ["build", "auto"] |
| renders | list[str] | yes | present | absent | degraded | blocked |
| requires_events | list[str] | no | event types needed for "present" |
| handler | callable | yes | sync or async |
| popup_visible | bool | yes | IDE command palette visibility |
| visible_in_ide | bool | yes | as previously locked |

Categories: session | runtime | run | provider | workspace | meta | passthrough | context | memory | search | mcp | skills | swarmgraph | trust | compliance

## Acceptance for this file

- Both current registries fully enumerated.
- Every current command has a Disposition and Target name.
- Target unified registry table covers every command listed in the Product Lock §7 and UX Lock v2.
- Phase column assigns all core slash commands to Phase 2; Phase 5 is polish only.
