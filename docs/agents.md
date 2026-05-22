# ARC Studio - Agent Context

**Last reality refresh:** 2026-05-22. This file is agent onboarding/context, not a status source of truth.

When in doubt, `docs/roadmap.md` and `docs/phases.md` override this file. Do not resolve conflicts by creating a new roadmap/status/handover doc; update the locked docs instead.

## Project Overview

ARC Studio is an Agent Runtime Cockpit IDE built on Eclipse Theia. It provides a graphical interface for developing, executing, and monitoring AI agent workflows using SwarmGraph and LangGraph.

## Architecture

### Repository Structure

```
arc-theia-studio/
├── packages/
│   ├── arc-ag-ui/           # Agent UI components (React)
│   ├── arc-extension/       # Main ARC extension (backend + frontend)
│   ├── arc-protocol-ts/     # TypeScript protocol types
│   └── arc-test-fixtures/   # Test fixtures and sample projects
├── docs/archive/theia-extensions/  # Archived legacy sources only; not workspace-active
├── applications/
│   └── browser/             # Canonical browser app (Theia 1.71.0) — primary release target
├── python/
│   └── src/agent_runtime_cockpit/  # Python backend
└── tests/                   # E2E and unit tests
```

### Key Packages

#### Python Backend (`python/src/agent_runtime_cockpit/`)
**Storage:**
- `storage/jsonl.py` — `JsonlTraceStore` (JSONL canonical traces)
- `storage/sqlite.py` — `SqliteStore` (run metadata index, ADR-003 schema)
- `storage/indexed_store.py` — `IndexedTraceStore` (dual-write: JSONL + SQLite index)

**Orchestration:**
- `orchestration/event_broker.py` — `EventBroker` (bounded queue pub/sub, SSE, replay)
- `orchestration/supervisor.py` — `JobSupervisor` (run lifecycle, cancel, orphan recovery)
- `orchestration/runtime_router.py` — `RuntimeRouter` with combo/adoption routing

**Security:**
- `security/trust.py` — Workspace trust resolver (external DB at `~/.arc/trusted-workspaces.json`)
- `security/redaction.py` — Secret redaction in adapter outputs
- `security/profiles.py` — `RunProfile` with env allowlist, paid-call gating

**Configuration:**
- `config/model.py` — Pydantic models for workspace ARC config (ADR-001)
- `config/loader.py` — YAML loader with 4-level precedence (env > workspace > user > defaults)

**Isolation:**
- `isolation/base.py` — `IsolationProvider` ABC + `IsolationResult`
- `isolation/none.py` — `NoneIsolationProvider` (direct subprocess, no filtering)
- `isolation/subprocess.py` — `SubprocessIsolationProvider` (env-filtered, blocked secrets)

#### `packages/arc-extension`
The primary extension package. Contains backend services and frontend widgets.

**Backend (`src/node/`):**
- `arc-backend-service.ts` - Orchestration layer (1125 lines). Coordinates services via DI; needs follow-up split.
- `services/workflow-executor.ts` - SwarmGraph workflow execution with process management
- `services/trace-parser.ts` - JSONL trace parsing, streaming, validation
- `services/workflow-detector.ts` - SwarmGraph/LangGraph detection via safe spawn
- `services/file-manager.ts` - Trace file listing, metadata, deletion
- `security-utils.ts` - Input validation and sanitization
- `arc-extension-backend-module.ts` - DI module with explicit bindings

**Frontend (`src/browser/`):**
- `arc-widget.tsx` - Main ARC Studio widget (~450 lines, orchestration layer)
- `components/ProgressBar.tsx` - Progress bar rendering
- `components/ToastContainer.tsx` - Toast notifications with auto-dismiss
- `components/ShortcutsModal.tsx` - Keyboard shortcuts help dialog
- `components/ExecutionSteps.tsx` - Workflow execution progress steps
- `components/ErrorBanner.tsx` - Error display with retry action
- `components/WorkflowExecutionSection.tsx` - Workflow execution UI section
- `components/TraceViewerSection.tsx` - Trace viewer UI section with filtering
- `components/WorkflowDetectionSection.tsx` - Workflow detection UI section

### Dependency Injection

Uses Inversify DI (@theia/core/shared/inversify). Backend services are bound explicitly in `arc-extension-backend-module.ts` using `toDynamicValue` for factory injection.

### Protocol

ARC services communicate via JSON-RPC over Theia's connection infrastructure. Protocol types defined in:
- `src/common/arc-protocol.ts` (theia-extension wire protocol)
- `packages/arc-protocol-ts/src/` (shared TypeScript types, including `audit-events.ts`)
- `python/src/agent_runtime_cockpit/schemas/` (Pydantic v2 Python mirrors, including `audit_events.py`)

## Build & Test

### Prerequisites
- Node.js >= 18
- pnpm >= 8

### Commands

```bash
# Install dependencies
pnpm install

# Build all packages
pnpm build

# Build specific package
pnpm --filter arc-extension build

# Run all tests
pnpm test

# Run specific package tests
pnpm --filter arc-extension test

# Test with coverage
cd packages/arc-extension && npx jest --coverage

# Lint & Format
pnpm lint          # ESLint check
pnpm lint:fix      # ESLint auto-fix
pnpm format        # Prettier format
pnpm format:check  # Prettier check

# Start browser app (development)
pnpm start:browser

# Python CI
cd python && uv run pytest -q -W error         # All tests
cd python && uv run pytest tests/web/           # Web tests only
cd python && uv run pytest tests/web/ --log-cli-level=DEBUG -s  # Web tests with verbose logging
```

### Test Configuration
- Framework: Jest with ts-jest
- Environment: Node (for backend), source-pattern matching (for UI components)
- Current test counts and release evidence live in `docs/phases.md` and `docs/release/checklist.md`; do not duplicate volatile counts here.
- Location: `packages/arc-extension/jest.config.js`

## Refactoring History

Historical sprint labels below are orientation notes, not current roadmap status. ADRs under `docs/adr/` are the architecture-decision source of truth.

### P0-3: Backend Modularization
Split the monolithic `arc-backend-service.ts` (1,329 lines) into:
- Orchestration layer (now 1125 lines — grew post-refactor with config/CLI/receipt/autopsy/HITL/audit/replay methods; needs re-split into config-service + run-lifecycle-service)
- 4 specialized service modules (each < 500 lines)
- Explicit DI bindings for testability
- Replaced `execSync` with safe `spawn('which', [name], {shell:false})`

### P0-4: Frontend Modularization
Split the monolithic `arc-widget.tsx` (974 lines) into:
- Orchestration widget (`arc-widget.tsx`, ~440 lines, now marked Legacy)
- Primary widget: `arc-studio-widget.tsx` (176 lines, tabbed: Chat/Runs/Workflows/Config)
- 13 reusable UI components in `components/` directory (grew from original 8)
- 4 tab components in `tabs/` directory (ChatTab, RunsTab, WorkflowsTab, ConfigTab)
- Ported widgets from theia-extensions: arc-adapters-widget, arc-workflow-graph, arc-run-timeline, arc-event-stream
- Clean props-based interfaces
- Centralized exports via `index.ts`

### P1-6: ESLint + Prettier
- ESLint v9 flat config (`eslint.config.mjs`) with TypeScript type-checked linting
- `.prettierrc.json` configured (single quotes, 100 width, 4-space tabs)
- JS files linted with Node globals, no type checks
- Note: `pnpm lint` delegates to per-package scripts; root eslint config not yet wired into workspace lint command. Prettier not installed as a root dependency — `format`/`format:check` scripts need proper wiring as a separate task.

### P1-7: Test Coverage
- arc-extension grew from 239 to 581 tests; Python now has 782 passed, 14 skipped
- UI components tested via source-pattern contract tests (NOT runtime jsdom tests)
- Backend services tested with Jest unit tests
- Branch coverage improved from 57.51% → 67.34%
- Added spawn-mocked tests for WorkflowExecutor (ARC_SWARMGRAPH_CLI, workspace-local CLI, timeout, parsing, cancel)

### B.3: Getting Started Guide
- Rewrote `docs/tutorials/getting-started.md` with install, first workflow via CLI, CLI exploration, browser IDE, viewing runs, next steps, troubleshooting, and more resources sections.

### B.4: Architecture Overview
- Created `docs/architecture/overview.md` with three-layer ASCII diagram (Browser App → Theia Extension → Python Backend), data flow description, 6 key subsystem explanations, protocol boundary, and links to 11 related docs/ADRs.

### D.1: Audit Event Schema
- Created shared audit event types in TS (`packages/arc-protocol-ts/src/audit-events.ts`) covering `AuditEventType` (7 literal types), `AuditEventSeverity` (3 levels), `AuditEvent`, `AuditChainLink`, and `AuditChainManifest`.
- Created Pydantic v2 Python mirror (`python/src/agent_runtime_cockpit/schemas/audit_events.py`) with camelCase aliases and equivalent models.
- Added 6 TS tests + 12 Python tests (all passing).
- Note: The `replayCategoryForType` function (in both `arc-backend-service.ts` and the Python event broker) already mapped `AUDIT` → `'audit'` — no changes needed there.

### P1-8: Build Optimization
- Webpack split chunks configured
- Main bundle reduced from 27 MiB → 50 KiB (our code)
- Monaco editor, Theia core, React, and vendors cached separately
- Custom webpack split chunks live in the canonical `applications/browser/` app path.

## Workflow

### Locked Planning Documents
The only active roadmap/implementation plan documents are:
- `docs/roadmap.md` — remaining product roadmap/status
- `docs/phases.md` — ordered phase/slice execution plan

Do not create new roadmap, implementation-plan, phase-plan, status, next-steps, or handover markdown files. Update the two docs above after every commit that changes implementation status. Historical plans belong under `docs/archive/stale-roadmaps/` and are not sources of truth.

### Gated Paths + Claim Safety
- Gated execution path details live in `docs/roadmap.md` under `Gated Execution Paths`.
- Event/data producer status lives in `docs/roadmap.md` under `Producer Inventory`.
- UI panels that depend on topology, consensus, cost, HITL, or audit events must render honest empty/degraded states when producers/material are absent; never fabricate data.
- Release-facing docs must pass `scripts/check-banned-claims.sh`. Do not claim broad provider-backed adoption, live Arena product behavior, adapter-wide keyed audit, production readiness, shared-server readiness, or tenant isolation unless the locked docs and tests explicitly support it.

### Before Each Implementation Slice
1. Read `docs/roadmap.md` and `docs/phases.md`.
2. Search `docs/research/IMPLEMENTATION_RESEARCH.md` only for supporting scaffolds/guidance.
3. Check relevant `docs/adr/` records.
4. Then implement the largest coherent phase chunk that can be completed safely with tests green in the current session. Avoid tiny micro-slices unless risk/ambiguity requires them.

### Implementation Flow
1. Understand the next phase/chunk from `docs/phases.md`
2. Research the existing codebase for relevant code
3. Read `docs/research/IMPLEMENTATION_RESEARCH.md` for scaffolds/guidance
4. Check `docs/adr/` for architecture decisions
5. Implement the change
6. Write tests
7. Run full test suite: `cd python && uv run pytest -q`
8. Verify TypeScript builds: `pnpm --filter @arc-studio/protocol build && pnpm --filter arc-extension build`
9. Commit with descriptive message

After every commit, update `docs/roadmap.md` and `docs/phases.md` if implementation status changed. These updates must be in the same commit or an immediate follow-up docs commit.

### Green-Test Continuation Rule
When a phase chunk is implemented and verification is green, continue directly to the next ordered item in `docs/phases.md` or the active todo list. Prefer bundling related slices into one larger implementation when they share files/tests and can be verified together. Do not stop to ask for permission unless:
- tests/builds fail and the failure is not quickly fixable
- the next item requires destructive action, secrets, paid/live provider calls, external publishing, or force-push/reset
- requirements conflict or are ambiguous enough that implementation would be guesswork
- the user explicitly asks to pause, summarize only, or wait

Use this prompt when resuming continuation work:

```text
Continue implementing the next ordered ARC Studio plan item. First read `docs/roadmap.md`, `docs/phases.md`, `docs/research/IMPLEMENTATION_RESEARCH.md`, and relevant ADRs. Pick the largest coherent phase chunk that can be safely completed and verified in this session, implement it, add/update tests, run `cd python && uv run pytest -q` plus `pnpm --filter @arc-studio/protocol build && pnpm --filter arc-extension build`, fix issues, update the locked docs if status changed, then continue to the next phase/chunk if all verification is green. Preserve unrelated worktree changes. Do not overclaim features; document scaffolds and not-wired behavior honestly.
```

## Current Status

Do not maintain detailed implementation status in this agent-context file. Current status, evidence anchors, gated paths, producer inventory, deferred items, and v0.2 Option A scope live in:

- `docs/roadmap.md`
- `docs/phases.md`
- `docs/release/checklist.md`

Historical P0/P1/P2/P3/P4/P5 milestone labels, the 23-PR sequence, Slice 7 details, and old remaining-issue summaries are archive context only. Use `docs/archive/` for historical reconstruction, not execution planning.

Stable constraints to remember:

- Browser/Theia UI tests are mostly static/source-contract tests because runtime jsdom coverage is limited.
- Monaco/Theia bundle size is expected to be large; optimize ARC-owned chunks, not Monaco itself.
- Adapter-wide keyed audit, broad provider-backed adoption, live Arena, production readiness, shared-server readiness, and tenant isolation remain unclaimed unless the locked docs and tests say otherwise.

## Related Documentation

### Source of Truth
- `docs/roadmap.md` — Locked remaining roadmap/status
- `docs/phases.md` — Locked ordered phase/slice plan
- `docs/research/IMPLEMENTATION_RESEARCH.md` — Supporting scaffolds/guidance only, not a roadmap
- `docs/adr/` — Architecture Decision Records (000-008)
- `docs/release/checklist.md` — v0.1.0-alpha release checklist

### Archived Handover
The following documents contain historical context in `docs/archive/`:
- `CRITICAL_REVIEW_GENSPARK.md`
- `IMPLEMENTATION_PLAN_KIMI.md`
- `EXECUTE_NEXT_PROMPT.md`
- `FINAL_HANDOFF_GENSPARK.md`
- `HANDOVER_SUMMARY.md`
- `PROOF_OF_CONCEPT_COMPLETE.md`
- `README_HANDOVER.md`
