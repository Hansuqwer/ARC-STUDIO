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
| `arc` (no args) | python/src/agent_runtime_cockpit/cli.py | `_no_args_help` | launch TUI in cwd | `arc studio` | Add | new behavior; bare CLI becomes primary TUI entry; currently `no_args_is_help=True` |
| `arc version` | `cli.py:303` | `version` | print ARC version info | — | Keep | |
| `arc health` | `cli.py:321` | `health` | check daemon + env health | — | Keep | |
| `arc status` | `cli.py:382` | `status` | show workspace/runtime overview | — | Keep | |
| `arc inspect` | `cli.py:437` | `inspect` | inspect workspace, detect runtimes | — | Keep | |
| `arc runtimes` | `cli.py:481` | `runtimes` | list detected runtimes | — | Keep | also `--capabilities` |
| `arc workflows` | `cli.py:552` | `workflows` | list detected workflows | — | Keep | |
| `arc schemas` | `cli.py:581` | `schemas` | list detected schemas | — | Keep | |
| `arc serve` | `cli.py:610` | `serve` | start HTTP daemon | — | Keep | |
| `arc run` | `cli.py:627` | `run_workflow` | execute workflow with runtime/profile/gates | — | Keep | canonical execution entry |
| `arc bug-report` | `cli.py:1064` | `bug_report` | collect diagnostic info for bug reports | — | Keep | secrets redacted |

## Command groups (`arc <group> <sub>`)

| Group | Subcommand | File | Entry symbol | Purpose | Duplicate-of | Disposition | Notes |
|---|---|---|---|---|---|---|---|
| runs | (default) | `cli.py:1424` | `runs` (callback) | list stored run records | — | Keep | `invoke_without_command=True` |
| runs | search | `cli.py:1706` | `runs_search` | search runs via SQLite index | — | Keep | |
| runs | get | `cli.py:1474` | `runs_get` | load one stored run record | — | Keep | |
| runs | diff | `cli.py:1493` | `runs_diff` | compare two stored run records | — | Keep | |
| runs | trace | `cli.py:1517` | `runs_trace` | return trace file metadata + tail | — | Keep | |
| runs | status | `cli.py:1544` | `runs_status` | show status of a stored run | — | Keep | |
| runs | delete | `cli.py:1576` | `runs_delete` | delete stored run + trace file | — | Keep | |
| runs | export | `cli.py:1604` | `runs_export` | export run record as JSON | — | Keep | |
| runs | import | `cli.py:1626` | `runs_import` | import run record JSON into store | — | Keep | |
| runs | replay | `cli.py:1655` | `runs_replay` | replay stored trace events | — | Keep | |
| runs | backfill | `cli.py:1680` | `runs_backfill` | backfill SQLite index from JSONL | — | Keep | idempotent |
| runs | prune | `cli.py:1443` | `runs_prune` | prune oldest trace files | — | Keep | |
| runs | fork | `cli.py:1766` | `runs_fork` | fork stored run into new PENDING run | — | Keep | effect-boundary replay |
| runs | links | `cli.py:1844` | `runs_links` | get cross-linked event chains | — | Keep | |
| runs | contract | `cli.py:2834` | `runs_contract` | show run contract | — | Keep | |
| runs | budget | `cli.py:2873` | `runs_budget` | show budget + usage for run | — | Keep | |
| runs | autopsy | `cli.py:2953` | `runs_autopsy` | show failure autopsy for failed run | — | Keep | |
| providers | list | `cli.py:716` | `providers_list` | list built-in provider definitions | — | Keep | no network calls |
| providers | catalog | `cli.py:724` | `providers_catalog` | list provider auth catalog entries | — | Keep | no secrets/network |
| providers | status | `cli.py:1116` | `providers_status` | dry-run provider status from env presence | — | Keep | |
| providers | diagnostics | `cli.py:1125` | `providers_diagnostics` | redacted provider diagnostics | — | Keep | no network calls |
| providers | proxy | `cli.py:1137` | `providers_proxy` | dry-run provider proxy | — | Keep | gated live |
| providers | action | `cli.py:1184` | `providers_action` | narrow gated provider action | — | Keep | 3-layer gate |
| providers | accounts list | `cli.py:1307` | `providers_accounts_list` | list provider accounts | — | Keep | |
| providers | accounts add | `cli.py:1316` | `providers_accounts_add` | add env-var-backed account | — | Keep | |
| providers | accounts disable | `cli.py:1332` | `providers_accounts_disable` | disable provider account | — | Keep | |
| providers | accounts delete | `cli.py:1348` | `providers_accounts_delete` | delete provider account | — | Keep | |
| providers | key status | `cli.py:1230` | `providers_key_status` | show provider key status | — | Keep | |
| providers | key set | `cli.py:1263` | `providers_key_set` | save env-var-backed key ref | — | Keep | never stores raw keys |
| providers | key unset | `cli.py:1288` | `providers_key_unset` | delete saved key refs | — | Keep | |
| providers | quota show | `cli.py:1365` | `providers_quota_show` | show today's local quota usage | — | Keep | |
| providers | quota reset | `cli.py:1384` | `providers_quota_reset` | reset local quota counters | — | Keep | local-only |
| providers | routing get | `cli.py:1401` | `providers_routing_get` | return persisted routing policy | — | Keep | |
| providers | routing set | `cli.py:1409` | `providers_routing_set` | persist routing policy | — | Keep | |
| doctor | all | `cli.py:742` | `doctor_all` | run all diagnostic checks | — | Keep | includes storage per ADR-009 |
| doctor | swarmgraph | `cli.py:732` | `doctor_swarmgraph` | check SwarmGraph runtime availability | — | Keep | |
| doctor | env | `cli.py:936` | `doctor_env` | check env vars + Python config | — | Keep | |
| doctor | network | `cli.py:981` | `doctor_network` | check endpoint network connectivity | — | Keep | |
| doctor | storage | `cli.py:1021` | `doctor_storage` | check workspace storage + traces | — | Keep | standalone subcheck |
| workspace | trust-status | `cli.py:2581` | `workspace_trust_status` | show workspace trust status | — | Keep | |
| workspace | trust | `cli.py:2595` | `workspace_trust` | mark workspace as trusted | — | Keep | external DB |
| workspace | untrust | `cli.py:2610` | `workspace_untrust` | remove workspace from trust DB | — | Keep | |
| isolation | status | `cli.py:1924` | `isolation_status` | show provider health status | — | Keep | |
| isolation | doctor | `cli.py:1955` | `isolation_doctor` | run provider diagnostics | — | Keep | |
| isolation | list | `cli.py:1994` | `isolation_list` | list available isolation providers | — | Keep | |
| isolation | setup | `cli.py:2016` | `isolation_setup` | set up an isolation provider | — | Keep | docker only |
| isolation | test | `cli.py:2060` | `isolation_test` | test provider with simple command | — | Keep | |
| config | init | `cli.py:2626` | `config_init` | generate default .arc/config.yaml | — | Keep | ADR-001 |
| config | show | `cli.py:2640` | `config_show` | show resolved workspace config | — | Keep | |
| hitl | pending | `cli.py:2448` | `hitl_pending` | list pending HITL prompts | — | Keep | single-use tokens |
| hitl | respond | `cli.py:2480` | `hitl_respond` | respond to HITL prompt | — | Keep | requires token |
| hitl | approve | `cli.py:2513` | `hitl_approve` | approve HITL prompt | `hitl respond` | Merge | delegates to hitl_respond |
| hitl | reject | `cli.py:2526` | `hitl_reject` | reject HITL prompt | `hitl respond` | Merge | delegates to hitl_respond |
| storage | vacuum | `cli.py:2104` | `storage_vacuum` | vacuum SQLite index | — | Keep | |
| storage | status | `cli.py:2143` | `storage_status` | show storage usage stats | — | Keep | |
| context | pack | `cli.py:2195` | `context_pack` | generate context pack for task | — | Keep | |
| adapter | test | `cli.py:2214` | `adapter_test` | run conformance tests on adapter | — | Keep | |
| adapter | list | `cli.py:2261` | `adapter_list` | list all registered adapters | — | Keep | |
| eval | run | `cli.py:2279` | `eval_run` | evaluate run vs golden trace | — | Keep | |
| eval | save | `cli.py:2361` | `eval_save` | save golden trace expectation | — | Keep | |
| eval | delete | `cli.py:2391` | `eval_delete` | delete saved golden trace | — | Keep | |
| eval | report | `cli.py:2407` | `eval_report` | report golden trace inventory | — | Keep | |
| eval | list | `cli.py:2423` | `eval_list` | list saved golden traces | — | Keep | |
| receipt | show | `cli.py:2673` | `receipt_show` | show run receipt | — | Keep | |
| receipt | export | `cli.py:2713` | `receipt_export` | export receipt to file | — | Keep | json/markdown |
| receipt | verify | `cli.py:2772` | `receipt_verify` | verify receipt HMAC signature | — | Keep | |
| audit | verify | `cli.py:3002` | `audit_verify` | verify HMAC-SHA256 audit chain | — | Keep | |
| audit | export | `cli.py:3051` | `audit_export` | export audit chain records | — | Keep | |
| audit | key init | `cli.py:3095` | `audit_key_init` | generate and store HMAC audit key | — | Keep | |
| audit | key show | `cli.py:3121` | `audit_key_show` | show audit key status | — | Keep | key never printed |
| audit | key delete | `cli.py:3142` | `audit_key_delete` | delete stored HMAC audit key | — | Keep | keychain only |
| profiles | list | `cli.py:3169` | `profiles_list` | list available run profiles | — | Keep | |
| profiles | show | `cli.py:3197` | `profiles_show` | show one run profile | — | Keep | |
| studio | chat | python/src/agent_runtime_cockpit/cli.py | `studio_chat` | REPL using cli_repl/ | — | Merge | merge with cli_studio.py REPL |
| studio | sessions | `cli.py:2563` | `studio_sessions` | list saved chat sessions | — | Keep | lists ChatSession records |
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
| `arc-studio` (no args) | python/src/agent_runtime_cockpit/cli_studio.py | `main` (callback, line 271) | interactive REPL | `arc studio` (REPL default) | Alias | shim ≤30 lines target |
| `arc-studio <message>` | `cli_studio.py:265` | `_oneshot` | one-shot dispatch | `arc studio run "<msg>"` | Alias | |
| `arc-studio --version` | `cli_studio.py:271` | `main` (--version flag) | print version | `arc --version` / `arc studio --version` | Alias | |
| `arc-studio` internal `_doctor()` | `cli_studio.py:158` | `_doctor` | run doctor | `arc doctor` | Retire | duplicates arc doctor |
| `arc-studio` internal `_runs()` | `cli_studio.py:176` | `_runs` | list runs | `arc runs` | Retire | |
| `arc-studio` internal `_status()` | `cli_studio.py:143` | `_status` | show status | `arc runs status` | Retire | |

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
| command groups | `cli.py:51-68` | groups: context, adapter, doctor, workspace, isolation, config, hitl, storage, studio |
| command sub-groups | `cli.py:706-713`, `1223-1227`, `1361-1362`, `1397-1398`, `2657-2658`, `2998-2999`, `3165-3166` | subgroups: runs, eval, providers, accounts, key, quota, routing, receipt, audit, profiles |
| runtime preflight | `cli.py:140-260` | runtime/profile/paid/local-real gates scaffolded; provider-backed claim false |
| studio chat | `cli.py:2542` | `arc studio chat` routes to `cli_repl.run_chat_repl` |
| studio sessions | `cli.py:2563` | lists `ChatSession` records |
| separate binary | `python/src/agent_runtime_cockpit/cli_studio.py:24-29`, `245-289` | `arc-studio` is separate Typer app; local shell/no agent execution |
| shipped slash drift | `cli_studio.py:40-54`; `cli_repl/slash_commands.py:27-95` | two registries, overlapping commands, different behavior |

## Actual `arc` command decorators found

`cli.py` contains **91** Typer command/callback decorators across top-level and groups: app commands at lines `303`, `321`, `382`, `437`, `481`, `552`, `581`, `610`, `627`, `1064`; doctor at `732`, `742`, `936`, `981`, `1021`; isolation at `1924`, `1955`, `1994`, `2016`, `2060`; storage at `2104`, `2143`; context at `2195`; adapter at `2214`, `2261`; HITL at `2448`, `2480`, `2513`, `2526`; studio at `2542`, `2563`; workspace at `2581`, `2595`, `2610`, `3264`, `3291`, `3322`; config at `2626`, `2640`; runs at `1424`, `1443`, `1474`, `1493`, `1517`, `1544`, `1576`, `1604`, `1626`, `1655`, `1680`, `1706`, `1766`, `1844`, `2834`, `2873`, `2953`; providers at `716`, `724`, `1116`, `1125`, `1137`, `1184`; key at `1230`, `1263`, `1288`; accounts at `1307`, `1316`, `1332`, `1348`; quota at `1365`, `1384`; routing at `1401`, `1409`; eval at `2279`, `2361`, `2391`, `2407`, `2423`; receipt at `2673`, `2713`, `2772`; audit at `3002`, `3051`, `3095`, `3121`, `3142`; profiles at `3169`, `3197`.

Phase 0 note: table rows above include target additions beyond current code. Phase 2 must split current-vs-target in implementation tasks without claiming those additions exist.

## Acceptance for this file

- Every command above has File, Entry symbol, Duplicate-of, Disposition filled.
- No row left with Disposition = Unknown.
- Drift table covers every Disposition = Merge | Alias | Retire row.
