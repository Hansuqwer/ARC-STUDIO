# ARC Studio Feature Roadmap Review — Index

## Overview

This directory contains a comprehensive review of 18 feature areas in the ARC Studio v0.1 specification. Each review analyzes the current spec, compares against comparable products (Claude Code, Cursor, Aider, OpenCode, Codex CLI, LangGraph Studio, Temporal, Prefect, and others), identifies gaps, and recommends spec changes with priority and implementation scaffolds.

The synthesis in [18-roadmap-synthesis.md](18-roadmap-synthesis.md) consolidates findings into a Top 20 recommended changes list, must-lock contracts, bounded v0.1 scope, v0.2 reserved scope, deferred items, and a risk register.

## Feature Review Files

| # | File | Feature Area | One-Line Summary | Status | Owner |
|---|------|-------------|-----------------|--------|-------|
| 01 | [01-chat.md](01-chat.md) | Chat | Chat spec is strong but missing `@file`/`@folder` mentions — table stakes vs every competitor | must-change | TBD |
| 02 | [02-plan-tasks.md](02-plan-tasks.md) | Plan / Tasks | Plan mode spec is sound; Tasks panel needs Step view clarification and manual checklist | optional | TBD |
| 03 | [03-runtime-router.md](03-runtime-router.md) | Runtime Router | Router is v0.2 reserved with suggestion card stub; static eligibility scoring is the v0.2 foundation | deferred | TBD |
| 04 | [04-handoff-protocol.md](04-handoff-protocol.md) | Handoff Protocol | Handoff is v0.2 reserved with payload shape reserved; needs `PHASE_HANDOFF` event type to resolve naming collision | deferred | TBD |
| 05 | [05-graph.md](05-graph.md) | Graph | Spec says Cytoscape.js but codebase uses custom SVG; should switch to React Flow and add live state overlay via SSE | must-change | TBD |
| 06 | [06-runs-failure-recovery.md](06-runs-failure-recovery.md) | Runs / Failure Recovery | Runs panel spec is sound (list + summary only); needs status filters and inline expand for v0.1 | optional | TBD |
| 07 | [07-review-apply-rollback.md](07-review-apply-rollback.md) | Review / Apply / Rollback | Must use git-backed snapshots with `/undo`/`/redo` instead of custom snapshot system | must-change | TBD |
| 08 | [08-config-policy.md](08-config-policy.md) | Config / Policy | Policy loader is entirely unimplemented (zero Python code); user config path mismatch (`~/.arc/` vs `~/.config/arc-studio/`) must be resolved | must-change | TBD |
| 09 | [09-provider-keys-cost.md](09-provider-keys-cost.md) | Provider Keys / Cost | Paid-call confirmation, cost accumulator, keyring storage, and `arc providers test` are all P0 spec gaps with zero implementation | must-change | TBD |
| 10 | [10-workspace-trust-security.md](10-workspace-trust-security.md) | Workspace Trust / Security | Trust binding missing machine ID + user ID; needs parent folder trust and protected paths (`.arc/`, `.git/`) | must-change | TBD |
| 11 | [11-sessions-daemon.md](11-sessions-daemon.md) | Sessions / Daemon | Session spec is solid; needs `/sessions` list command and daemon auth token lifecycle definition | optional | TBD |
| 12 | [12-cli-command-system.md](12-cli-command-system.md) | CLI Command System | CLI spec is sound; needs command aliases (`/q`, `/s`) and fuzzy autocomplete; command queueing during active runs | optional | TBD |
| 13 | [13-ide-layout-panels.md](13-ide-layout-panels.md) | IDE Layout / Panels | Should use Theia's right sidebar for ARC panels instead of custom 3-column layout; Tasks steps as inline chat cards | optional | TBD |
| 14 | [14-hotloop-reservations.md](14-hotloop-reservations.md) | HotLoop Reservations | HotLoop is v0.2 reserved with panel slots, component stubs, events, and runtime manifest reserved; no v0.1 action | deferred | TBD |
| 15 | [15-mcp-acp-integrations.md](15-mcp-acp-integrations.md) | MCP / ACP Integrations | MCP/ACP not addressed in spec — correct for v0.1; MCP consumption is v0.2, ACP server mode is v0.3 | deferred | TBD |
| 16 | [16-install-update-distribution.md](16-install-update-distribution.md) | Install / Update / Distribution | npm + pipx distribution plan is sound; needs npm package structure with per-platform optional deps (Codex pattern) | optional | TBD |
| 17 | [17-testing-observability-docs.md](17-testing-observability-docs.md) | Testing / Observability / Docs | Test strategy is solid (550 Python, 239 TS, 12 E2E); needs axe-core accessibility audits in E2E | optional | TBD |
| 18 | [18-roadmap-synthesis.md](18-roadmap-synthesis.md) | Roadmap Synthesis | Consolidated synthesis: Top 20 changes, must-lock contracts, bounded v0.1 scope, v0.2 reserved, risk register | — | TBD |

## Synthesis

The consolidated synthesis is in [18-roadmap-synthesis.md](18-roadmap-synthesis.md).

Key outputs:
- **Top 20 Recommended Changes** — 8 P0 (must-have v0.1) + 12 P1 (should-have v0.1)
- **Must-Lock Contracts** — 7 protocol contracts + 5 UI component contracts that must be stable before implementation
- **Bounded v0.1 Scope** — Explicit in-scope and out-of-scope lists with protocol reservations
- **v0.2 Reserved Scope** — 15 features reserved for v0.2 with protocol stubs
- **Deferred Items** — 10 items explicitly deferred to v0.3+ or indefinitely
- **Risk Register** — 12 identified risks with likelihood, impact, and mitigations

## Status Legend

- **must-change**: Spec has critical gaps that must be addressed before implementation (P0 items in synthesis Top 20)
- **optional**: Spec is mostly sound; improvements are nice-to-have or P1 should-haves
- **deferred**: Feature is reserved for future versions (v0.2+); no v0.1 spec changes needed
- **—**: Not applicable (synthesis document)
