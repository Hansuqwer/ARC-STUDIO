# Phase 0 — CLI Command Inventory

Status: DRAFT (Phase 0 inventory, non-destructive)
Scope: every `arc *` and `arc-studio *` command currently shipped.
Source of truth: code, not docs. If docs and code disagree, code wins and the row is flagged.

## How to fill this file

1. Walk `python/src/agent_runtime_cockpit/cli.py` and `python/src/agent_runtime_cockpit/cli_studio.py`.
2. For each Typer command and subcommand, add one row.
3. Disposition is one of: Keep | Merge | Alias | Retire | Unknown.
4. Duplicate-of is the canonical command this row collapses into, or `—`.
5. Do not modify any code in Phase 0.

## Top-level commands (`arc`)

| Command | File | Entry symbol | Purpose (one line) | Duplicate-of | Disposition | Notes |
|---|---|---|---|---|---|---|
| `arc` (no args) | python/src/agent_runtime_cockpit/cli.py | <target> | launch TUI in cwd | `arc studio` | Add | new behavior; bare CLI becomes primary TUI entry |
| `arc run` | python/src/agent_runtime_cockpit/cli.py | `run_workflow` | execute workflow with runtime/profile/gates | — | Keep | canonical execution entry |
| `arc bug-report` | <path> | <symbol> | <one line> | — | <Keep/Merge/...> | |
| `arc serve` | <path> | <symbol> | | | | |
| `arc workflows` | <path> | <symbol> | | | | |
| `arc runtimes` | <path> | <symbol> | | | | |

## Command groups (`arc <group> <sub>`)

| Group | Subcommand | File | Entry symbol | Purpose | Duplicate-of | Disposition | Notes |
|---|---|---|---|---|---|---|---|
| runs | search | | | | — | Keep | |
| runs | get | | | | | | |
| runs | diff | | | | | | |
| runs | trace | | | | | | |
| runs | status | | | | | | |
| runs | delete | | | | | | |
| runs | export | | | | | | |
| runs | import | | | | | | |
| runs | replay | | | | | | |
| runs | backfill | | | | | | |
| runs | prune | | | | | | |
| runs | fork | | | | | | |
| runs | links | | | | | | |
| runs | contract | | | | | | |
| runs | budget | | | | | | |
| runs | autopsy | | | | | | |
| providers | list | | | | | | |
| providers | catalog | | | | | | |
| providers | status | | | | | | |
| providers | diagnostics | | | | | | |
| providers | proxy | | | | | | |
| providers | action | | | | | | |
| providers | accounts list | | | | | | |
| providers | accounts add | | | | | | |
| providers | accounts disable | | | | | | |
| providers | accounts delete | | | | | | |
| providers | key status | | | | | | |
| providers | key set | | | | | | |
| providers | key unset | | | | | | |
| providers | quota show | | | | | | |
| providers | quota reset | | | | | | |
| providers | routing get | | | | | | |
| providers | routing set | | | | | | |
| doctor | all | | | | | | |
| doctor | swarmgraph | | | | | | |
| doctor | env | | | | | | |
| doctor | network | | | | | | |
| doctor | storage | | | | | | |
| workspace | trust-status | | | | | | |
| workspace | trust | | | | | | |
| workspace | untrust | | | | | | |
| isolation | status | | | | | | |
| isolation | doctor | | | | | | |
| isolation | list | | | | | | |
| isolation | setup | | | | | | |
| isolation | test | | | | | | |
| config | init | | | | | | |
| config | show | | | | | | |
| hitl | pending | | | | | | |
| hitl | respond | | | | | | |
| hitl | approve | | | | | | |
| hitl | reject | | | | | | |
| storage | vacuum | | | | | | |
| storage | status | | | | | | |
| context | pack | | | | | | |
| adapter | test | | | | | | |
| adapter | list | | | | | | |
| eval | run | | | | | | |
| eval | save | | | | | | |
| eval | delete | | | | | | |
| eval | report | | | | | | |
| eval | list | | | | | | |
| receipt | show | | | | | | |
| receipt | export | | | | | | |
| receipt | verify | | | | | | |
| audit | verify | | | | | | |
| audit | export | | | | | | |
| audit | key init | | | | | | |
| audit | key show | | | | | | |
| studio | chat | python/src/agent_runtime_cockpit/cli.py | `studio_chat` | REPL using cli_repl/ | — | Merge | merge with cli_studio.py REPL |
| studio | sessions | | | | | | |
| studio | run | | | one-shot run/chat execution | — | Add | `arc studio run "<msg>"` |
| studio | continue | | | reattach to most recent cwd-scoped session | — | Add | also `arc studio --continue`, `-c` |
| studio | resume | | | resume by id or picker | — | Add | also `arc studio --resume [<id>]` |
| studio | sessions show | | | show one session | — | Add | cwd-scoped unless `--all` |
| studio | sessions delete | | | delete one session | — | Add | confirmation-gated |
| studio | sessions migrate | | | migrate legacy flat sessions | — | Add | legacy read → canonical write |
| studio | fork | | | fork session at turn | — | Add | session-level fork, distinct from `arc runs fork` |
| studio | doctor | | | studio-specific diagnostics | `arc doctor` | Add | only studio-specific checks; full surface remains `arc doctor` |
| studio | graph | | | render topology/timeline/raw event payload | — | Add | `arc studio graph <run-id> [--timeline] [--json]` |
| studio | topology | | | topology alias | `arc studio graph` | Add | alias only, no separate renderer |
| studio | timeline | | | timeline alias | `arc studio graph --timeline` | Add | alias only, no separate renderer |
| studio | workflows | | | workflow table/picker | `arc workflows` | Add | `arc studio workflows [pick]` |
| studio | providers | | | provider diagnostics/detail/refresh | `arc providers` | Add | `arc studio providers [<name>] [refresh]` |
| studio | quota | | | local ARC quota counters/reset | `arc providers quota` | Add | no remote-provider reset claim |
| studio | provider-action | | | gated provider action | `arc providers action` | Add | inline 3-layer gate |
| studio | budget | | | measured/estimated/absent budget view | `arc runs budget` | Add | event/material-backed only |
| studio | audit | | | audit verify/export/view | `arc audit` | Add | material-backed only |
| studio | hitl | | | HITL pending/respond/approve/reject | `arc hitl` | Add | inline approval cards |
| studio | context | | | context show/pack/clear/add | `arc context pack` | Add | `@` quick attach maps here |

## Separate entry: `arc-studio` (cli_studio.py)

| Command | File | Entry symbol | Purpose | Duplicate-of | Disposition | Notes |
|---|---|---|---|---|---|---|
| `arc-studio` (no args) | python/src/agent_runtime_cockpit/cli_studio.py | `<symbol>` | interactive REPL | `arc studio` (REPL default) | Alias | shim ≤30 lines target |
| `arc-studio <message>` | | | one-shot dispatch | `arc studio run "<msg>"` | Alias | |
| `arc-studio --version` | | | print version | `arc --version` / `arc studio --version` | Alias | |
| `arc-studio` internal `_doctor()` | | | | `arc doctor` | Retire | duplicates arc doctor |
| `arc-studio` internal `_runs()` | | | | `arc runs` | Retire | |
| `arc-studio` internal `_status()` | | | | `arc runs status` | Retire | |

## Duplicate / drift summary

| Drift | CLI A | CLI B | Resolution target | Phase |
|---|---|---|---|---|
| Two REPL impls | `arc studio chat` (cli_repl/) | `arc-studio` (cli_studio.py) | One REPL under `arc studio`, alias-only shim | 2 |
| Two session schemas | `ChatSession` (Pydantic, dir-per-session) | `StudioSession` (flat JSON) | Canonical `ChatSession`, legacy read adapter | 2 |
| Two slash registries | cli_repl/ | cli_studio.py | One declarative registry | 2 |
| Doctor duplication | `arc doctor` | `arc-studio` `_doctor()` | `arc doctor` only | 2 |
| Bare command UX | `arc` dispatcher/help | competitor-style TUI target | `arc` no args launches `arc studio` TUI | 2 |
| TUI/script parity | slash-only actions | missing non-interactive siblings | every slash command has `arc studio <subcommand>` sibling | 2 |

## Current Code Evidence Summary

| Area | Evidence | Finding |
|---|---|---|
| main app | `python/src/agent_runtime_cockpit/cli.py:45-68` | `arc` Typer app has `no_args_is_help=True`; bare TUI not implemented |
| command groups | `cli.py:51-59` | groups: context, adapter, doctor, workspace, isolation, config, hitl, storage, studio |
| runtime preflight | `cli.py:140-260` | runtime/profile/paid/local-real gates scaffolded; provider-backed claim false |
| studio chat | `cli.py:2542` | `arc studio chat` routes to `cli_repl.run_chat_repl` |
| studio sessions | `cli.py:2563` | lists `ChatSession` records |
| separate binary | `python/src/agent_runtime_cockpit/cli_studio.py:24-29`, `245-289` | `arc-studio` is separate Typer app; local shell/no agent execution |
| shipped slash drift | `cli_studio.py:40-54`; `cli_repl/slash_commands.py:27-95` | two registries, overlapping commands, different behavior |

## Actual `arc` command decorators found

`cli.py` contains 39 Typer command decorators across top-level and groups: app commands at lines `303`, `321`, `382`, `437`, `481`, `552`, `581`, `610`, `627`, `1064`; doctor at `732`, `742`, `936`, `981`, `1021`; isolation at `1924`, `1955`, `1994`, `2016`, `2060`; storage at `2104`, `2143`; context at `2195`; adapter at `2214`, `2261`; HITL at `2448`, `2480`, `2513`, `2526`; studio at `2542`, `2563`; workspace at `2581`, `2595`, `2610`, `3264`, `3291`, `3322`; config at `2626`, `2640`.

Phase 0 note: table rows above include target additions beyond current code. Phase 2 must split current-vs-target in implementation tasks without claiming those additions exist.

## Acceptance for this file

- Every command above has File, Entry symbol, Duplicate-of, Disposition filled.
- No row left with Disposition = Unknown.
- Drift table covers every Disposition = Merge | Alias | Retire row.
