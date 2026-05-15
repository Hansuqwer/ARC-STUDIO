# ARC Studio - Agent Context

## Project Overview

ARC Studio is an Agent Runtime Cockpit IDE built on Eclipse Theia. It provides a graphical interface for developing, executing, and monitoring AI agent workflows using SwarmGraph and LangGraph.

## Architecture

### Repository Structure

```
arc-theia-studio/
├── packages/
│   ├── arc-ag-ui/           # Agent UI components (React)
│   ├── arc-browser-app/     # Theia browser application entry
│   ├── arc-extension/       # Main ARC extension (backend + frontend)
│   ├── arc-protocol-ts/     # TypeScript protocol types
│   └── arc-test-fixtures/   # Test fixtures and sample projects
├── theia-extensions/
│   ├── arc-adapters/        # Runtime adapters
│   ├── arc-audit/           # Audit logging
│   ├── arc-context/         # Context management
│   ├── arc-core/            # Core ARC services
│   ├── arc-event-stream/    # Event stream visualization
│   ├── arc-health/          # Health monitoring
│   ├── arc-product/         # Product-specific UI
│   ├── arc-runs/            # Run timeline visualization
│   ├── arc-schemas/         # Schema inspector
│   ├── arc-settings/        # Settings/preferences
│   └── arc-workflows/       # Workflow graph visualization
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
- `arc-backend-service.ts` - Orchestration layer (276 lines). Coordinates services via DI.
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

ARC services communicate via JSON-RPC over Theia's connection infrastructure. Protocol types defined in `src/common/arc-protocol.ts`.

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
- Coverage: 61.84% statements, 67.34% branches, 53.78% functions, 63.18% lines
- Total tests: 239 (across 6 test suites)
- Location: `packages/arc-extension/jest.config.js`

## Architecture Decisions

### P0-3: Backend Modularization
Split the monolithic `arc-backend-service.ts` (1,329 lines) into:
- Orchestration layer (276 lines)
- 4 specialized service modules (each < 500 lines)
- Explicit DI bindings for testability
- Replaced `execSync` with safe `spawn('which', [name], {shell:false})`

### P0-4: Frontend Modularization
Split the monolithic `arc-widget.tsx` (974 lines) into:
- Orchestration widget (~450 lines)
- 8 reusable UI components in `components/` directory
- Clean props-based interfaces
- Centralized exports via `index.ts`

### P1-6: ESLint + Prettier
- ESLint v9 flat config with TypeScript type-checked linting
- Prettier for consistent formatting (single quotes, 100 width, 4-space tabs)
- JS files linted with Node globals, no type checks

### P1-7: Test Coverage
- 81 new tests added (239 total)
- UI components tested via source-pattern contract tests (NOT runtime jsdom tests)
- Backend services tested with Jest unit tests
- Branch coverage improved from 57.51% → 67.34%
- Added spawn-mocked tests for WorkflowExecutor (ARC_SWARMGRAPH_CLI, workspace-local CLI, timeout, parsing, cancel)

### P1-8: Build Optimization
- Webpack split chunks configured
- Main bundle reduced from 27 MiB → 50 KiB (our code)
- Monaco editor, Theia core, React, and vendors cached separately
- Custom `webpack.config.js` in `packages/arc-browser-app/`

## Workflow

### Before Each PR Implementation
**ALWAYS read the research document first:**
1. Search `docs/research/IMPLEMENTATION_RESEARCH.md` for the relevant PR section
2. Read any code scaffolds provided there
3. Check `docs/adr/` for relevant ADRs
4. Then implement following the research doc guidance

### Implementation Flow
1. Understand the PR spec from `docs/IMPLEMENTATION_PLAN.md` (table rows)
2. Research the existing codebase for relevant code
3. Read `docs/research/IMPLEMENTATION_RESEARCH.md` for scaffolds/guidance
4. Check `docs/adr/` for architecture decisions
5. Implement the change
6. Write tests
7. Run full test suite: `cd python && uv run pytest -q`
8. Verify TypeScript builds: `pnpm --filter @arc-studio/protocol build && pnpm --filter arc-extension build`
9. Commit with descriptive message

### Green-Test Continuation Rule
When a slice is implemented and verification is green, continue directly to the next ordered item in `docs/handover/HANDOVER.md`, `docs/IMPLEMENTATION_PLAN.md`, or the active todo list. Do not stop to ask for permission unless:
- tests/builds fail and the failure is not quickly fixable
- the next item requires destructive action, secrets, paid/live provider calls, external publishing, or force-push/reset
- requirements conflict or are ambiguous enough that implementation would be guesswork
- the user explicitly asks to pause, summarize only, or wait

Use this prompt when resuming continuation work:

```text
Continue implementing the next ordered ARC Studio plan item. First read `docs/handover/HANDOVER.md`, `docs/IMPLEMENTATION_PLAN.md`, `docs/research/IMPLEMENTATION_RESEARCH.md`, and relevant ADRs. Pick the smallest correct vertical slice, implement it, add/update tests, run `cd python && uv run pytest -q` plus `pnpm --filter @arc-studio/protocol build && pnpm --filter arc-extension build`, fix issues, then continue to the next slice if all verification is green. Preserve unrelated worktree changes. Do not overclaim features; document scaffolds and not-wired behavior honestly.
```

## Current Status

### Completed (P0 - Critical)
- ✅ P0-1: Python build fixed (hatch wheel config)
- ✅ P0-2: Backup artifacts cleaned + .gitignore
- ✅ P0-3: Backend refactored (1,329→276 lines + 4 services)
- ✅ P0-4: Frontend refactored (974→~450 lines + 8 components)
- ✅ P0-5: TypeScript strict mode verified

### Completed (P1 - High)
- ✅ P1-6: ESLint + Prettier configured
- ✅ P1-7: Test coverage improved (239 tests, 67.34% branches)
- ✅ P1-8: Build optimization (split chunks)
- ✅ P1-9: Documentation consolidated

### Completed (P2 - Critical Review Fixes)
- ✅ P2-1: Historical docs archived under docs/archive/
- ✅ P2-2: workflow-executor.ts uses discovered cliPath (not literal 'swarmgraph')
- ✅ P2-3: findExecutable accepts workspaceRoot (not process.cwd())
- ✅ P2-4: replaced `null as any` with `null!` for running-process preinsert
- ✅ P2-5: Spawn-mocked WorkflowExecutor tests added (6 new test cases)

### Completed (P3 - Audit Fixes)
- ✅ F-0 through F-13, G4F, #19, #20 — all resolved

### Completed (Recommended First 23 PRs)
- ✅ PR 1: Docs truth cleanup
- ✅ PR 2: Release checklist
- ✅ PR 3: Theia version-skew audit
- ✅ PR 4: Extension build on Theia 1.71
- ✅ PR 5: Browser app canonical wiring
- ✅ PR 6: Extension migration inventory
- ✅ PR 7: CLI discoverability A (version, health)
- ✅ PR 8: CLI discoverability B (status, doctor all)
- ✅ PR 9: Register/hide AG2
- ✅ PR 10: Capability schema v1
- ✅ PR 11: OpenAI Agents export target
- ✅ PR 12: CLI daemon parity A (arc runs diff)
- ✅ PR 13: CLI daemon parity B (provider diagnostics/proxy)
- ✅ PR 14: Event schema registry (ADR-004)
- ✅ PR 15-16: Adoption protocol + registry skeleton
- ✅ PR 17: Delete stale deploy script
- ✅ PR 18: Manual SSE proof endpoint
- ✅ PR 19: Event broker core
- ✅ PR 20: Supervisor wiring
- ✅ PR 21: Keychain storage spike
- ✅ PR 22: Trust resolver external store
- ✅ PR 23: Dossier scaffold hardening

### Completed (P1a — Execution Core Infrastructure)
- ✅ **SQLite index beside JSONL (ADR-003)**: `IndexedTraceStore` wraps JSONL + SQLite with dual-write; `backfill_index()` for idempotent rebuild; 20 storage tests
- ✅ **Isolation provider interface (ADR-006)**: `isolation/` package with `IsolationProvider` base, `NoneIsolationProvider` (direct subprocess), `SubprocessIsolationProvider` (env-filtered); `arc isolation status/doctor/list` CLI; 16 tests
- ✅ **Run lifecycle CLI**: `arc runs status/delete/export/backfill` commands added (15 CLI run tests)
- ✅ **Audit path on RunRecord**: `audit_path` field added to `RunRecord` schema for trace-to-audit-chain linkage
- ✅ **Combo semantics**: Already implemented via `ComboRuntimeAdapter` (sequential multi-runtime)
- ✅ **Config model (ADR-001)**: `ArcConfig` Pydantic model, YAML loader, env/workspace/user/default precedence, `arc config init/show`; 14 tests

### Completed (P1b — Adoption Foundation)
- ✅ **SwarmGraph import path spike**: vendored `swarm_shared` and `hive-swarm` modules import from ARC Python venv; documented in `docs/SPIKE_SWARMGRAPH_IMPORT.md`

### Completed (P2 — Runtime + SwarmGraph Integrations)
- ✅ **Prompt optimizer foundation**: `optimizer/local.py` with rule-based prompt structuring, `arc prompt optimize/diff` CLI; optional `tiktoken>=0.12`
- ✅ **Adoption runners**: LangGraph (SwarmGraph queen/consensus), AG2, CrewAI, OpenAI Agents, LlamaIndex — all with fake-tested paths, real deps gated
- ✅ **HMAC audit**: `audit/key_manager.py`, `audit/hmac_chain.py`, `audit/hitl.py`, CLI `arc audit verify/export/key *`
- ✅ **Trust enforcement**: `ensure_trusted()` blocks untrusted workspaces before run record creation
- ✅ **HITL supervisor flow**: event types `HITL_PROMPT`, `HITL_RESPONSE`, `HITL_TIMEOUT`; `JobSupervisor.request_hitl()`, `respond_hitl()`, `pending_hitl()`
- ✅ **Eval CLI basics**: `arc eval save/delete/report/list`, `arc eval run --batch`; 9 eval tests
- ✅ **Trace replay + HITL CLI**: `arc runs import/replay`, `arc hitl pending/respond/approve/reject`

### Completed (P3 — Theia UX Productization)
- ✅ **Theia UI ports**: workflow graph, run timeline, event stream, adapters widgets into canonical `packages/arc-extension`
- ✅ **Product config CLI**: `arc profiles list/show`, `arc workspace init/info/config`, `arc providers quota show/reset`
- ✅ **Eval/observability CLI**: `arc runs search` (SQLite index), `arc doctor env/network/storage`, `arc bug-report`
- ✅ **Docker-compatible isolation**: `DockerIsolationProvider` with OrbStack/Podman/Colima detection; `arc isolation setup/test`; optional `docker>=7.1`; 13 Docker tests

### Completed (P4 — Audit, Replay, HITL, Security Hardening)
- ✅ **Eval batch mode**: `arc eval run --batch` evaluates against all saved golden traces
- ✅ **HITL persistence hardening**: single-use tokens, expiry/TTL, replay-attack protection, `prune_expired`; 6 new HITL tests

### P1a Items Still Open
- Add ARC trace/audit refs (adapters should populate `audit_path` on RunRecord) — P2 scope (HMAC wiring)
- Hard subprocess env allowlists — covered by existing `SwarmGraphAdapter._filtered_env()`; other adapters are in-process

### Known Issues
- ESLint has 247 problems (113 errors, 134 warnings) — all pre-existing in other packages; our files have 0 errors
- Browser files (arc-widget.tsx, etc.) show 0% coverage due to Theia runtime dependency — UI tests are static contract tests only
- Coverage targets: 70% not reached for statements (61.84%), functions (53.78%), lines (63.18%). Only branches (67.34%) close
- Monaco editor bundle is 15.9 MiB (expected, not reducible)
- Total frontend entrypoint ~28.8 MiB (Monaco + Theia core + React + vendors); ARC Studio code chunk is 50 KiB

### Test Metrics
- Python: 531 passed, 6 skipped (was 435 before P2/P3/P4 work)
- TypeScript protocol build: clean
- arc-extension build: clean

### Remaining Issues
See `docs/handover/REMAINING_ISSUES_PLAN.md` for full details. Summary:

- **R-1 (Node CI: arc-ag-ui test exits 1)**: Unquoted glob `./test/**/*.test.js` fails under POSIX sh. Fix: quote the glob.
- **R-2 (ARC Roadmap Gate: native-keymap gyp crash)**: Missing `apt-get install libx11-dev libxkbfile-dev` step.
- **R-3 (Python CI: 2 AG2 adapter test errors)**: `conftest.py` autouse fixture calls `get_event_loop()` which emits `DeprecationWarning` on Python 3.12.
- **R-4 (10 unmerged remote branches)**: 3 may have salvageable work; 7 intentionally parked.
- **R-5 (.env history scrub)**: Schedule `git filter-repo` ≥7 days before public release.
- **e2e workflow**: Still in progress.

## Related Documentation

### Source of Truth
- `docs/IMPLEMENTATION_PLAN.md` — Canonical PR list "Recommended First 23 PRs"
- `docs/research/IMPLEMENTATION_RESEARCH.md` — Detailed scaffolds and guidance (MUST READ before each PR)
- `docs/adr/` — Architecture Decision Records (000-008)
- `docs/RELEASE_CHECKLIST.md` — v0.1.0-alpha release checklist

### Archived Handover
The following documents contain historical context in `docs/archive/`:
- `CRITICAL_REVIEW_GENSPARK.md`
- `IMPLEMENTATION_PLAN_KIMI.md`
- `EXECUTE_NEXT_PROMPT.md`
- `FINAL_HANDOFF_GENSPARK.md`
- `HANDOVER_SUMMARY.md`
- `PROOF_OF_CONCEPT_COMPLETE.md`
- `README_HANDOVER.md`
