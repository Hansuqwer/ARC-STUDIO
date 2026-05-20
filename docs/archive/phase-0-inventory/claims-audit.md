# Phase 0 — Banned Claims Audit

Status: DRAFT (Phase 0 inventory, non-destructive)
Scope: grep every banned claim across the repo and propose remediation.
Output: list of file:line hits that Phase 1 must rewrite, delete, or caveat.

## How to fill this file

1. For each claim below, run a case-insensitive grep across the repo (excluding `docs/archive/`).
2. Record every hit as file:line with surrounding sentence.
3. Remediation: Rewrite | Delete | Keep-with-caveat | False-positive.
4. Phase column: which phase fixes the hit (1 = docs cleanup; 2/3/4/5 if code-adjacent).

## Banned claims source (locked)

Canonical list lives at `scripts/banned-claims.txt` (created in Phase 1).
This audit is the input to that list.

| # | Claim | Permitted only when |
|---|---|---|
| 1 | "SwarmGraph has real model intelligence" | native provider_backed implemented + tested |
| 2 | "SwarmGraph is provider-backed" | same |
| 3 | "SwarmGraph paid execution is complete" | same |
| 4 | "CLI is 100% done" | all CLI 100% criteria met |
| 5 | "IDE is 100% done" | all IDE 100% criteria met |
| 6 | "SwarmGraph is 100% done" | all SwarmGraph 100% criteria met |
| 7 | "ARC Studio is production-ready" | all three surfaces 100% + release gate pass |
| 8 | "End-to-end real SwarmGraph agents" | native provider_backed wired CLI+IDE+tested |
| 9 | "Broad provider-backed SwarmGraph adoption" | locked roadmap forbids until lock changes |
| 10 | "arc-studio is deprecated" | never (it is a supported alias) |
| 11 | "Provider-backed mode exists in native SwarmGraph" | Phase 4 tests pass |
| 12 | "IDE matches CLI semantics" | Phase 5 parity tests pass |
| 13 | "External SwarmGraph CLI proves native provider-backed" | never |
| 14 | "ARC Studio docs consolidation complete" | Phase 1 acceptance met |
| 15 | "Single source of truth enforced" | Phase 3 contract tests pass |
| 16 | "Cost numbers shown are measured" | event has source=measured |
| 17 | "All runtimes support all modes" | never (per-runtime capability report is authoritative) |
| 18 | "arc CLI matches Claude Code UX" | Phase 5 parity tests cover picker, popup, footer, shortcuts, streaming |
| 19 | "TUI is feature-complete" | full locked slash inventory implemented + tested |
| 20 | "Session picker works" | cwd-scoped picker with preview implemented + tested |
| 21 | "Slash popup is live" | fuzzy-filtered popup with categories implemented + tested |
| 22 | "Terminal graph is visual" | `/graph` renders topology from `SWARMGRAPH_TOPOLOGY` events with present/absent/degraded states tested |
| 23 | "Provider controls are live" | gates passed and `/provider-action` path tested end-to-end |
| 24 | "Budget is measured" | every shown cost field tagged `source=measured` from event payload |
| 25 | "Workflow picker runs everything" | capability report's `runnable=true` honored; blocked rows non-selectable |
| 26 | "HITL approve/reject works inline" | inline approval card tested for approve/reject/respond/expired states |
| 27 | "Context pack is integrated" | `/context pack` wraps `arc context pack` and is tested |
| 28 | "Topology timeline shows real events" | `/graph --timeline` reads event log, no synthesized timestamps |
| 29 | "Memory gives perfect recall" | never |
| 30 | "Session memory is safe by default" | memory trust/source tagging + delete tests pass |
| 31 | "Project memory is enabled by default" | explicit trust + opt-in implemented |
| 32 | "Plans are automatically correct" | never; plans require review/approval semantics |
| 33 | "Auto mode can bypass approval" | never |
| 34 | "Build mode can edit without gates" | never |
| 35 | "Bare arc always opens the TUI" | only TTY + guardrails + `ARC_NO_TUI` honored |
| 36 | "Non-TTY arc launches interactive UI" | never |
| 37 | "Streaming is always available" | stream transport connected and fallback tested |
| 38 | "Cancellation stops all work instantly" | process/tree cancellation semantics tested; otherwise caveat |
| 39 | "Delete removes all data" | retention/delete policy + storage vacuum tests pass |
| 40 | "Runtime switching preserves full compatibility" | capability report validates selected runtime/mode |
| 41 | "All runtime dropdown choices are runnable" | Python capability report says `can_run=true` |
| 42 | "Provider-backed switch is one click" | profile + paid + env + confirmation gates pass |
| 43 | "JSON output is stable" | envelope contract tests pass |
| 44 | "@ file picker can attach any path" | workspace boundary + trust tests pass |

## Hits

| Claim # | File:line | Surrounding sentence | Remediation | Phase |
|---|---|---|---|---|---|
| 9 | `python/tests/test_providers.py:238` | `# ─── Broad Provider-Backed Adoption Tests ──────────────────────────────────` | Rename section header to `# ─── Provider Action Gating Tests ──────────────────────────────────`. Tests verify gates (all assert `provider_backed is False`), no adoption claim intended. | 1 |
| 9 | `docs/LOCKED_REMAINING_ROADMAP.md:241` | `All 6 previously-deferred items (effect-boundary replay, BudgetVector interrupts, SwarmGraph internal capture, broad provider-backed adoption, new adapters, Electron packaging) were implemented in commit 4b0f6b5.` | **False-positive** — describing the deferred ledger item. Context says "gated provider action" not adoption. OK. | — |
| 15 | `docs/adr/004-event-schema-versioning.md` | `# Event type registry — single source of truth` | **False-positive** — unrelated to docs consolidation claim. About event type registry. OK. | — |
| 15 | `docs/adr/007-provider-routing-unification.md` | `- Gateway remains the single source of truth for inference` | **False-positive** — unrelated to docs consolidation claim. About provider routing. OK. | — |
| 15 | `docs/research/feature-roadmap-review/11-sessions-daemon.md` | `Rationale: Multi-client attach requires a single source of truth.` | **False-positive** — about daemon session lock, not docs consolidation. OK. | — |
| 15 | `docs/research/IMPLEMENTATION_RESEARCH.md` | `4. Version management: Single source of truth in python/pyproject.toml version field.` | **False-positive** — about version management, not docs consolidation. OK. | — |
| 4 | `docs/LOCKED_REMAINING_ROADMAP.md:214` | `R8/Phase 12 → R10/Phase 14 → R9/Phase 13 → R11/Phase 15 → R12/Phase 16. All 6 previously-deferred items (...) were implemented in 4b0f6b5.` | **False-positive** — locked roadmap describing deferred item status, not claiming "CLI is 100% done". OK. | — |
| 7 | (no hits) | — | No production-ready claim found outside archive. OK. | — |
| 10 | (no hits) | — | No "arc-studio is deprecated" claim found outside archive. OK. | — |
| 8 | (no hits) | — | No "End-to-end real SwarmGraph agents" claim found outside archive. OK. | — |
| 11–44 | (no hits) | — | No remaining banned claim hits found outside `docs/archive/`, `runtimes/swarmgraph/`, or false-positive contexts. | — |

## Safe-wording replacements (locked)

Use these exact phrasings instead of banned variants:

| Instead of | Use |
|---|---|
| "SwarmGraph is provider-backed" | "Native SwarmGraph default path is fake/offline and tested." |
| "SwarmGraph paid execution is complete" | "External `ARC_SWARMGRAPH_CLI` path can delegate to provider-backed execution when configured and gated." |
| "SwarmGraph has real model intelligence" | "Provider subsystem has gated provider action capability for OpenAI-compatible smoke calls." |
| "End-to-end real SwarmGraph agents" | "Native SwarmGraph provider-backed execution is not yet implemented." |
| "CLI is 100% done" | "CLI has architectural debt (two implementations) that must be consolidated." |
| "IDE matches CLI semantics" | "IDE has runtime default alignment but needs parity verification." |
| "arc-studio is deprecated" | "`arc-studio` is a supported alias for `arc studio`." |
| "arc CLI matches Claude Code UX" | "ARC Studio targets a peer TUI UX; implementation is tracked by the Phase 0/Phase 2 inventory." |
| "TUI is feature-complete" | "The locked TUI target is defined; implementation remains pending until tests prove the full inventory." |
| "Session picker works" | "Session picker is a locked UX target pending Phase 2 implementation/tests." |
| "Slash popup is live" | "Slash popup is a locked UX target pending Phase 2 implementation/tests." |
| "Terminal graph is visual" | "Terminal graph rendering is event-backed only and pending `/graph` implementation/tests." |
| "Provider controls are live" | "Provider controls remain gated; live action requires all explicit gates and tests." |
| "Budget is measured" | "Budget values are shown as measured only when event payload has `source=measured`." |
| "Workflow picker runs everything" | "Workflow picker must honor runtime capability reports; blocked workflows remain non-selectable." |
| "HITL approve/reject works inline" | "Inline HITL handling is a locked UX target pending tests." |
| "Context pack is integrated" | "Context pack integration is a locked UX target pending tests." |
| "Topology timeline shows real events" | "Timeline rendering must read stored event logs and avoid synthesized timestamps." |
| "Memory gives perfect recall" | "Memory is scoped, source-tagged context that may be summarized or absent." |
| "Auto mode can bypass approval" | "Auto mode remains bounded by runtime, paid-call, trust, and HITL gates." |
| "Bare arc always opens the TUI" | "Bare `arc` may open the TUI only in guarded interactive TTY contexts." |
| "Streaming is always available" | "Streaming uses the best available transport and must show degraded fallback when unavailable." |
| "Delete removes all data" | "Delete behavior follows the documented retention and storage policy." |

## CI enforcement (locked, Phase 1 implements)

`scripts/check-banned-claims.sh` must run against, at minimum:

```text
README.md AGENTS.md docs/roadmap.md docs/phases.md docs/agents.md docs/architecture/product-lock.md docs/release/checklist.md
```

Phase 1 wires this list into CI. Phase 0 only records hits.

## Acceptance for this file

- Every claim #1–28 has been greppped against the repo.
- Every hit recorded with Remediation and Phase.
- No "Unknown" remediation.
- Safe-wording table preserved verbatim.

## ADR-013 Banned Claims (#74–83)

| # | Claim | Permitted only when |
|---|---|---|
| 74 | "SwarmGraph always fans out to workers" | fan-out gate is documented + tested |
| 75 | "Workers see the full plan" | context isolation tests pass |
| 76 | "SwarmGraph achieves Byzantine consensus" | proof-of-thought tested against arXiv 2603.01213 benchmark |
| 77 | "SwarmGraph handles all multi-agent failures" | claim restricted to the 13 named modes |
| 78 | "Consensus is automatic" | claim acknowledges per-step selection |
| 79 | "SwarmGraph optimization is automated" | MASS + GEPA pipelines run in Phase 6.5 |
| 80 | "Hierarchical SwarmGraph is unbounded" | claim acknowledges 3-level limit |
| 81 | "Workers are independent" | claim acknowledges queen-mediated state |
| 82 | "Checkpoint resume is lossless" | claim acknowledges in-flight tool call exceptions |
| 83 | "SwarmGraph supports swarm/handoff" | never; explicitly not supported |

## ADR-014 Banned Claims (#84–91)

| # | Claim | Permitted only when |
|---|---|---|
| 84 | "ARC is prompt-injection resistant" | 5 canonical attack tests + tool poisoning + rug pull tests pass |
| 85 | "Workspace trust eliminates injection risk" | claim acknowledges trust is one of six layers |
| 86 | "L2 classifier catches all injections" | never (classifier supplements, not replaces) |
| 87 | "Workers can elevate privileges" | never; workers cannot elevate |
| 88 | "ARC's MCP integration is impenetrable" | claim restricted to the three detected MCP failure modes |
| 89 | "Tool poisoning is impossible in ARC" | never; manifest verification != impossibility |
| 90 | "MCP rug pulls are silently prevented" | claim acknowledges detection-with-user-repin |
| 91 | "External content can be trusted after classifier scan" | never; trust remains level 4 |

## ADR-015 Banned Claims (#92–97)

| # | Claim | Permitted only when |
|---|---|---|
| 92 | "ARC is EU AI Act compliant" | never (claim restricted to "produces compliance evidence") |
| 93 | "AssuranceTab replaces a compliance officer" | never |
| 94 | "Audit chain is tamper-proof" | external timestamping or hardware attestation added (Phase 8+) |
| 95 | "Compliance bundle satisfies any regulator" | never; regulators determine sufficiency |
| 96 | "Receipts are signed by default" | signatures enabled by default in workspace config |
| 97 | "Retention is automatically enforced" | storage vacuum tested against retention policy |

## Safe-Wording Replacements (ADR-013/014/015 additions)

| Instead of | Use |
|---|---|
| "SwarmGraph plans and executes" | "SwarmGraph synthesizes plans (queen), executes via isolated workers, and verifies via selectable consensus" |
| "ARC blocks prompt injection" | "ARC implements six defense layers against prompt injection, with detection and audit emission" |
| "ARC IDE is audit-ready" | "ARC IDE AssuranceTab produces audit-grade evidence aligned with EU AI Act Article 12/19" |
| "MCP integration is safe" | "MCP integration is allowlist-gated, manifest-pinned, and sandboxed per server transport" |
| "Audit logs are tamper-proof" | "Audit chain is tamper-evident via sha256 chaining; tamper-proof requires external timestamping (Phase 8+)" |
