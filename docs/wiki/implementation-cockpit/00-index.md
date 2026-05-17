# ARC Studio Implementation Wiki — Cockpit Redesign

**Date:** 2026-05-16
**Goal:** Implement CLI/IDE cockpit redesign per `ARC_STUDIO_UX_SPEC.md` and `CLI_IDE_REDESIGN_PLAN.md`

## File Map

| File | Covers |
|------|--------|
| `00-index.md` | This file — overview, dependency graph, PR plan |
| `01-architecture-map.md` | System architecture — all layers, entry points, DI |
| `02-contracts-and-schemas.md` | RunContract, RunReceipt, FailureAutopsy, EvidenceRef, TrustDiff, CapabilitySnapshot, RuntimeManifest extensions, stable IDs, Python+TS+JSON+storage+redaction+validation+migration+tests for each |
| `03-python-backend-guide.md` | Python backend: CLI, config, web, storage, security, orchestration |
| `04-cli-guide.md` | CLI redesign: chat REPL, slash commands, session, install |
| `05-theia-frontend-guide.md` | Theia frontend: tabs, chat, runs, config, graph, status bar |
| `06-event-stream-and-sse.md` | Event broker, SSE streaming, event types |
| `07-run-contract.md` | RunContract schema, lifecycle, rendering |
| `08-run-receipt.md` | RunReceipt schema, CLI verbs, verification |
| `09-failure-autopsy.md` | FailureAutopsy schema, knows/guesses, rendering |
| `10-evidence-refs.md` | EvidenceRef schema, cross-surface linking |
| `11-runtime-capabilities.md` | RuntimeCapabilities, capability negotiation |
| `12-trust-diff-policy.md` | TrustDiff, policy loader, workspace trust UX |
| `13-graph-chat-linking.md` | Graph/Chat/Evidence cross-highlighting, stable IDs |
| `14-testing-strategy.md` | Testing: Python, TS, E2E, accessibility |
| `15-implementation-slices.md` | Vertical implementation slices with acceptance criteria |
| `16-agent-task-prompts.md` | Model assignment plan, dependency graph, PR plan |

## Dependency Graph

```
PR 1: Schema contracts    ← no deps
PR 2: Trust diff + policy ← no deps (config loader exist)
PR 3: EventBroker SSE     ← no deps (EventBroker exists)
PR 4: Run Receipt CLI     ← depends on PR 1
PR 5: Failure Autopsy     ← depends on PR 1
PR 6: EvidenceRefs        ← depends on PR 1
PR 7: Runtime capabilities ← depends on PR 1 (capabilities.py exists)
PR 8: Graph/Chat linking  ← depends on PR 6, PR 3
PR 9: CLI chat REPL       ← depends on PR 4, PR 5, PR 6
PR 10: Theia tab redesign ← depends on PR 9
```

## Source Docs

- `docs/research/ARC_STUDIO_UX_SPEC.md` — UX spec with all component interfaces
- `docs/research/CLI_IDE_REDESIGN_PLAN.md` — CLI + IDE redesign plan
- `docs/research/feature-roadmap-review/` — 18 feature reviews with gap analysis
- `docs/research/innovation-critical-review/` — Innovation analysis, 10 recommendations
- `docs/adr/000-008` — Architecture decisions (core contract, config, state machine, storage, event schema, audit, trust, routing, daemon)
- `AGENTS.md` — Project overview, build commands, CI

## Status Legend

Throughout this wiki:
- `[EXISTS]` — Code exists and is implemented
- `[STUB]` — Interface/class exists but missing content
- `[MISSING]` — No code, spec only
- `[RESERVED]` — Spec says v0.2+, no implementation
