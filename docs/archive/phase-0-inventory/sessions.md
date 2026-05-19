# Phase 0 — Session Format Inventory

Status: DRAFT (Phase 0 inventory, non-destructive)
Scope: every persisted session format currently produced or read by ARC Studio CLI.
No schema is changed in Phase 0. This file produces the proposed canonical schema for Phase 2.

## How to fill this file

1. Inspect `cli_studio.py` (`StudioSession`) and `cli_repl/session.py` (`ChatSession`) for fields.
2. List actual on-disk layouts found under `~/.arc/sessions/` in dev/test fixtures.
3. List every env var that touches session storage.
4. Propose canonical schema (declarative, no code).

## Schema A: StudioSession (legacy)

| Field | Type | Required | Source | Notes |
|---|---|---|---|---|
| session_id | str | yes | cli_studio.py | |
| messages | list | yes | | |
| mode | str | yes | | plan/build/auto |
| created | str (ISO) | yes | | |
| updated | str (ISO) | yes | | |
| <add row> | | | | |

Storage layout: `~/.arc/sessions/<id>.json` (flat file)
Latest pointer: `~/.arc/sessions/latest` (symlink)
Producer: `arc-studio`
Consumer: `arc-studio` only

## Schema B: ChatSession (current canonical candidate)

| Field | Type | Required | Source | Notes |
|---|---|---|---|---|
| id | str | yes | cli_repl/session.py | |
| history | list | yes | | |
| created_at | datetime | yes | | |
| updated_at | datetime | yes | | |
| metadata | dict | no | | |
| <add row> | | | | |

Storage layout: `~/.arc/sessions/<id>/session.json` (dir per session)
Latest pointer: <fill>
Producer: `arc studio chat`
Consumer: `arc studio chat`, `arc studio sessions`

## Field diff (A vs B)

| Concept | StudioSession | ChatSession | Canonical decision |
|---|---|---|---|
| id field name | session_id | id | `id` |
| message field name | messages | history | `history` |
| timestamps | created/updated (str) | created_at/updated_at (datetime) | datetime |
| mode | top-level | metadata or top-level? | top-level, enum |
| runtime_id | absent | absent | add, top-level |
| profile_id | absent | absent | add, top-level |
| isolation_id | absent | absent | add, top-level |
| allow_paid_calls | absent | absent | add, top-level, default false |
| version | absent | absent | add, int, schema version |
| attached_runs | absent | absent | add, list of run ids |

## Proposed canonical schema (Phase 2 target)

| Field | Type | Required | Default | Notes |
|---|---|---|---|---|
| version | int | yes | 1 | schema version |
| id | str | yes | — | uuid |
| history | list[Message] | yes | [] | |
| mode | enum(plan/build/auto) | yes | build | |
| runtime_id | str | yes | swarmgraph | |
| runtime_mode | enum(fake_offline/gated_local/provider_backed) | yes | fake_offline | |
| profile_id | str | yes | local-safe | |
| isolation_id | str | yes | subprocess | |
| allow_paid_calls | bool | yes | false | |
| attached_runs | list[str] | no | [] | |
| cwd | str | yes | current working directory | absolute path |
| project_id | str | yes | derived | stable hash of git root or cwd |
| fork_parent_id | str \| null | no | null | parent session id if forked |
| fork_turn_id | str \| null | no | null | turn id/index in parent at fork point |
| attached_context | list[str] | no | [] | paths attached via `@` or `/context add` |
| last_run_id | str \| null | no | null | most recent run id for continuity |
| active_workflow | str \| null | no | null | selected by `/workflows pick` |
| runtime_model | str \| null | no | null | active model id; provider-backed only |
| created_at | datetime | yes | — | |
| updated_at | datetime | yes | — | |
| metadata | dict | no | {} | |

Storage: `~/.arc/sessions/<id>/session.json` (dir per session)
Latest pointer: `~/.arc/sessions/latest` → `<id>/`

## Env vars touching sessions

| Var | Read by | Effect | Disposition |
|---|---|---|---|
| `ARC_STUDIO_SESSIONS_DIR` | <fill> | override sessions root | Keep |
| `ARC_STUDIO_HISTORY_FILE` | <fill> | history file path | Add (Phase 2) |
| `ARC_STUDIO_DEFAULT_SCOPE` | <fill> | default session scope: cwd or all | Add (Phase 2), default cwd |
| <add row> | | | |

## CWD-scoped session UX requirements

| Requirement | Locked behavior |
|---|---|
| Default scope | current working directory / project id |
| Global scope | explicit `--all` |
| Session picker preview | first user message truncated to 80 chars |
| Session picker metadata | updated_at, runtime badge, mode badge, profile badge |
| Resume | picker by default; `--last` jumps most recent |
| Continue | no picker; most recent cwd session |
| Fork | creates new session from chosen turn; records parent id + turn id |

## TUI UX requirements

| Area | Locked minimum |
|---|---|
| Footer status line | cwd, runtime, mode, profile, isolation, paid-calls on/off, session id short |
| Enter | send |
| Shift+Enter | newline |
| Esc Esc | cancel current generation |
| Ctrl+C | cancel input |
| Ctrl+D | exit |
| Ctrl+L | clear screen; transcript preserved |
| Ctrl+R | reverse history search |
| Up/Down | history navigation |
| `/` | slash popup |
| `!` | passthrough mode for one line |
| `@` | file/context picker |
| Streaming output | token stream plus tool/runtime/budget/HITL cards with boundaries |
| Approval prompts | inline y/N, default N, confirmation token where required |

## Migration policy (locked)

- Legacy flat `<id>.json` files: readable, never written.
- Mixed storage: list/show operations enumerate both layouts.
- Write path: canonical `<id>/session.json` only.
- Explicit migration: `arc studio sessions migrate` (Phase 2).
- Tests required (Phase 2):
  - Read legacy flat session.
  - List mixed storage directory.
  - Write produces canonical layout only.
  - Migrate command converts legacy → canonical idempotently.

## Current Code Evidence

| Item | Evidence | Current behavior | Phase 2 implication |
|---|---|---|---|
| Legacy flat sessions | `python/src/agent_runtime_cockpit/cli_studio.py:33`, `57-127`, `245-289` | writes `~/.arc/sessions/<id>.json` and `latest` symlink; no env override | keep readable only; shim to canonical writer |
| Canonical candidate sessions | `python/src/agent_runtime_cockpit/cli_repl/session.py:12-62` | writes `$ARC_STUDIO_SESSIONS_DIR/<id>/session.json`; default `~/.arc/sessions`; no latest pointer | make canonical; add cwd/project scope + latest pointer |
| REPL history | `python/src/agent_runtime_cockpit/cli_repl/chat_repl.py:9-20` | writes `~/.arc/repl_history.txt`; no env override | add `ARC_STUDIO_HISTORY_FILE`; default no real home writes in tests |
| Non-interactive save | `python/src/agent_runtime_cockpit/cli_repl/chat_repl.py:23-41` | initial prompt can run once and save | preserve; add JSON/plain output contract |
| Cancel behavior | `python/src/agent_runtime_cockpit/cli_repl/chat_repl.py:48-68`, `cli_studio.py:254-262` | EOF/KeyboardInterrupt saves session then exits | Phase 2 distinguishes input cancel, generation cancel, process exit |
| Current mode storage | `python/src/agent_runtime_cockpit/cli_studio.py:35-38`, `57-76` | legacy session stores plan/build/auto; `ChatSession` does not | add top-level `mode` canonical field |

## Memory + Planning Fields

| Field | Type | Required | Default | Notes |
|---|---|---|---|---|
| memory_enabled | bool | yes | true | controls session/project/user memory injection |
| memory_refs | list[MemoryRef] | no | [] | explicit memory ids included in prompt construction |
| session_summary | str \| null | no | null | result of `/memory compact`; no perfect-recall claim |
| context_window_budget | int \| null | no | null | max tokens/chars available for packed context |
| active_plan | Plan \| null | no | null | plan shown/approved/edited via `/plan` |
| plan_status | enum(none/draft/approved/running/done/discarded) | yes | none | gates `/build` and `/auto` semantics |
| plan_turn_id | str \| null | no | null | turn that produced current draft plan |
| mode_policy | dict | no | {} | plan/build/auto permission policy snapshot |

## Schema Version + Migration Rules

| Version | Meaning | Write target | Migration rule |
|---|---|---|---|
| absent | legacy `StudioSession` or early `ChatSession` | never | read with adapter; write v1 on explicit migrate only |
| 1 | Phase 2 canonical session schema | `<sessions>/<id>/session.json` | current target |

- Readers tolerate missing optional fields and default conservatively.
- Writers include `version` and never rewrite legacy flat files implicitly.
- Migration is idempotent and preserves original legacy file until explicit delete confirmation.

## Config Precedence

| Rank | Source | Applies to |
|---|---|---|
| 1 | command flags / slash args | one command or current turn |
| 2 | current session fields | TUI continuity |
| 3 | workspace ARC config | project defaults |
| 4 | user config / env refs | user defaults, never raw secrets |
| 5 | built-in defaults | `runtime_id=swarmgraph`, `runtime_mode=fake_offline`, `profile_id=local-safe`, `isolation_id=subprocess` |

## TTY / Output / Cancellation Contract

| Context | Locked behavior |
|---|---|
| bare `arc` + TTY | may launch TUI after Phase 2 guardrails |
| bare `arc` + non-TTY/CI | must not launch TUI; show help or require subcommand |
| `ARC_NO_TUI=1` | disables bare TUI |
| `--json` | emits ARC envelope only, no Rich UI |
| `NO_COLOR=1` | no color escapes in plain output |
| exit codes | `0` success, `1` user/config/runtime error, `2` usage error, `130` cancelled |
| Esc Esc | cancel current generation, preserve transcript |
| Ctrl+C | cancel current input/generation; second Ctrl+C exits |

## Prompt Construction Order

1. System policy and runtime capability report.
2. Mode policy (`plan`/`build`/`auto`) and active gates.
3. Active plan if approved or explicitly shown.
4. Session summary and selected memory refs.
5. Attached context pack, bounded by `context_window_budget`.
6. Recent transcript turns.
7. Current user message.

Memory/context must be tagged by trust source. No memory item can grant privileges or override gates.

## Acceptance for this file

- Schema A and B tables fully filled from code.
- Field diff has a canonical decision per row.
- Proposed schema is complete enough that Phase 2 needs no further design.
- Env var table covers every var grep finds for `ARC_STUDIO_*`.
- CWD scope, picker metadata, footer fields, and keyboard shortcuts are represented in the canonical schema or UX requirements.
