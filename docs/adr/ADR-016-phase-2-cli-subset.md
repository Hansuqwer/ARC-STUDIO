# ADR-016: Phase 2 CLI Consolidation Subset

Status: Proposed
Date: 2026-05-20
Deciders: ARC Studio core team
Refines: ADR-011, docs/phases.md Phase 18, Phase 0 CLI inventory

## Context

Phase 0 inventory files list the full target slash registry and canonical session schema. The Phase 18 implementation landed the consolidation infrastructure and a smaller command subset. The Phase 18 review rejected the phase because `docs/archive/phase-0-inventory/slash-commands.md` and `docs/archive/phase-0-inventory/sessions.md` could reasonably be read as immediate Phase 2 acceptance, not the multi-phase CLI target.

## Decision

Phase 18 is accepted only as the Phase 2 CLI consolidation subset, not the full target registry. Phase 18 may complete when it provides one registry, one canonical session writer, the legacy-session migration path, bare `arc` TTY behavior, explicit metadata for registered commands, and cancellation/gate handling for `/run`.

In-scope Phase 18 slash commands are:

| Command | Status | Notes |
|---|---|---|
| `/help` | In scope | Registry help output |
| `/version` | In scope | Version output |
| `/exit`, `/quit` | In scope | Exit aliases |
| `/clear` | In scope | Session transcript clear |
| `/summary` | In scope | Session summary |
| `/sessions` | In scope | Session list |
| `/history` | In scope | Recent history |
| `/run` | In scope | Must be mode-gated and cancellation-aware |
| `/plan`, `/build`, `/auto` | In scope | Mode switches only; full planning semantics deferred |
| `/status`, `/doctor`, `/runs` | In scope | Merged from legacy `arc-studio` shell |

In-scope Phase 18 session fields are `version`, `id`, `mode`, `created_at`, `updated_at`, `history`, and `metadata`. Legacy flat sessions are readable and migratable but never written. Legacy file content is tagged with workspace-trust metadata on read.

Deferred items:

| Item | Deferred to | Reason |
|---|---|---|
| Full `/plan`, `/plan show`, `/plan approve`, `/plan edit`, `/plan discard` semantics | Phase 4.7 | Needs planner verification and reflection loop |
| `/graph`, `/timeline`, `/topology` | Phase 4 | Needs SwarmGraph event envelope and topology renderer hardening per ADR-013 |
| `/providers`, `/quota`, `/provider-action` | Phase 4 | Needs provider/runtime gate UX integration |
| `/budget`, `/audit`, `/receipt`, `/contract` | Phase 5 | Needs receipt v2/compliance material per ADR-015 |
| `/hitl` | Phase 5 | Needs HITL queue UX and token flow consolidation |
| `/memory`, `/memory show`, `/memory add`, `/memory forget`, `/compact` | Phase 4.5 | Needs memory subsystem and trust policy |
| Full `/context` and `@` picker | Phase 4.5 | Needs context attachment store and picker |
| `/search`, `/fetch` | Phase 5.5 | Needs SearchProvider abstraction and ADR-014 trust tagging |
| `/mcp` commands | Phase 5.6 | Needs MCP allowlist, manifest pinning, authorization, and output isolation |
| `/skill` commands | Phase 5.7 | Needs skills loader and trust policy |
| Session `runtime_id`, `runtime_mode`, `profile_id`, `isolation_id`, `allow_paid_calls` | Phase 3 | Needs runtime/profile semantics unification |
| Session `cwd`, `project_id`, `attached_context`, `last_run_id`, `active_workflow`, `runtime_model` | Phase 3 | Needs project/session scope model and workflow picker |
| `ARC_STUDIO_HISTORY_FILE`, `ARC_STUDIO_DEFAULT_SCOPE` | Phase 3 | Needs history/scope config policy |

## Consequences

Positive: Phase 18 has a bounded, reviewable acceptance contract and future reviews can separate infrastructure consolidation from the full CLI product surface.

Negative: Phase 18 ships fewer slash commands and fewer session fields than the Phase 0 inventory target. Docs and CHANGELOG must describe this as a subset.

## Acceptance

- `docs/phases.md` references this ADR and avoids claiming the full Phase 0 inventory is complete.
- `arc studio sessions migrate` exists and is tested.
- Every registered command has explicit category, gates, mode, trust, privilege, render, and event metadata.
- `/run` is mode-gated and cancellation-aware.
- Legacy flat session reads attach workspace-trust metadata.
- Deferred items are listed in this ADR.
