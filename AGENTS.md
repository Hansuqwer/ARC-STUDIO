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

### Completed (P3 - Audit Fixes, 2026-05-14)
- ✅ F-0: Broken lockfile regenerated (pnpm install --frozen-lockfile passes)
- ✅ F-1: Stale FastAPI test deleted (python/tests/test_routes_execute.py)
- ✅ F-2/F-4/F-9: arc-arena excluded from workspace & electron deps
- ✅ F-3: .env untracked (git rm --cached)
- ✅ F-5/F-6/F-11: README tag claim fixed, CLI table eval added, .tool-versions pnpm 9.15.9
- ✅ F-7: CI step ordering fixed (install before hygiene, --frozen-lockfile restored)
- ✅ F-8/F-10: check-artifacts.sh allowlists src-gen/, check-pr.sh excludes swarmgraph/
- ✅ F-12: ruff --fix applied (44 issues), 14 style-only ignored in pyproject.toml
- ✅ F-13: console.log in trace-parser.ts replaced with breadcrumb comment
- ✅ G4F removed: 5 provider definitions deleted from providers.py & arc-service-impl.ts
- ✅ #19 fix: StatsJsonPlugin disabled in CI (stats.toJson all:true removed + !CI guard) — CI verified: webpack no longer crashes
- ✅ #20 fix: replaced deprecated `datetime.datetime.utcnow()` with `datetime.datetime.now(datetime.timezone.utc)` across 8 Python files — resolves all 52 CI test failures (both web 500s and CLI deprecation errors)

### Known Issues (2026-05-14)
- ESLint has 247 problems (113 errors, 134 warnings) — all pre-existing in other packages; our files have 0 errors
- Browser files (arc-widget.tsx, etc.) show 0% coverage due to Theia runtime dependency — UI tests are static contract tests only
- Coverage targets: 70% not reached for statements (61.84%), functions (53.78%), lines (63.18%). Only branches (67.34%) close
- Monaco editor bundle is 15.9 MiB (expected, not reducible)
- Total frontend entrypoint ~28.8 MiB (Monaco + Theia core + React + vendors); ARC Studio code chunk is 50 KiB
- **#19 (webpack V8 crash on CI)**: ✅ RESOLVED. Fixed by removing `all: true` from `stats.toJson()` and skipping `StatsJsonPlugin` when `process.env.CI` is set. CI verified: webpack no longer crashes.
- **#20 (Python 3.12 web test 500s)**: ✅ RESOLVED. Fixed by replacing all 8 `utcnow()` calls with `now(timezone.utc)`. CI verified: 245 passed, 6 skipped, 0 failed, 2 errors (AG2 pre-existing).

### Remaining Issues (2026-05-14)
See `docs/handover/REMAINING_ISSUES_PLAN.md` for full details. Summary:

- **R-1 (Node CI: arc-ag-ui test exits 1)**: Unquoted glob `./test/**/*.test.js` fails under POSIX sh. Fix: quote the glob. **Original diagnosis in handover was incorrect** — test/ directory exists with 4 real tests; the issue is shell glob expansion, not missing tests.
- **R-2 (ARC Roadmap Gate: native-keymap gyp crash)**: Missing `apt-get install libx11-dev libxkbfile-dev` step. Fix: add native build deps step (mirrors node.yml).
- **R-3 (Python CI: 2 AG2 adapter test errors)**: `conftest.py` autouse fixture calls `get_event_loop()` which emits `DeprecationWarning` on Python 3.12 for synchronous tests. Fix: delete the fixture (pytest-asyncio ≥0.23 owns loop lifecycle).
- **R-4 (10 unmerged remote branches)**: `handoff/no-mockups-github-ready` safe to delete; `recovered/troubleshooting-docs` and `runtime/api-runs-start-field` may have salvageable work; 7 `roadmap/*` branches intentionally parked.
- **R-5 (.env history scrub)**: Schedule `git filter-repo` ≥7 days before public release.
- **e2e workflow**: Still in progress (expected, builds full Theia app).

## Related Documentation (Archived Handover)
The following documents contain historical context and are preserved for reference in `docs/archive/`:
- `CRITICAL_REVIEW_GENSPARK.md` - Initial code review
- `IMPLEMENTATION_PLAN_KIMI.md` - Original implementation plan with code examples
- `EXECUTE_NEXT_PROMPT.md` - Task execution prompts
- `FINAL_HANDOFF_GENSPARK.md` - Phase handoff documentation
- `HANDOVER_SUMMARY.md` - Summary of handover
- `PROOF_OF_CONCEPT_COMPLETE.md` - PoC completion notes
- `README_HANDOVER.md` - Handover instructions
