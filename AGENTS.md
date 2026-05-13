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
```

### Test Configuration
- Framework: Jest with ts-jest
- Environment: Node (for backend), source-pattern matching (for UI components)
- Coverage: 61.84% statements, 67.34% branches
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
- 75 new tests added (233 total)
- UI components tested via source-pattern contract tests
- Backend services tested with Jest unit tests
- Branch coverage improved from 57.51% → 67.34%

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
- ✅ P1-7: Test coverage improved (233 tests, 67.34% branches)
- ✅ P1-8: Build optimization (split chunks)
- ✅ P1-9: Documentation consolidated

### Known Issues
- ESLint has ~37 files with warnings (mostly pre-existing, non-blocking)
- Browser files (arc-widget.tsx, etc.) show 0% coverage due to Theia runtime dependency
- Monaco editor bundle is 15.9 MiB (expected, not reducible)

## Related Documentation (Archived Handover)
The following documents contain historical context and are preserved for reference:
- `CRITICAL_REVIEW_GENSPARK.md` - Initial code review
- `IMPLEMENTATION_PLAN_KIMI.md` - Original implementation plan with code examples
- `EXECUTE_NEXT_PROMPT.md` - Task execution prompts
- `FINAL_HANDOFF_GENSPARK.md` - Phase handoff documentation
- `HANDOVER_SUMMARY.md` - Summary of handover
- `PROOF_OF_CONCEPT_COMPLETE.md` - PoC completion notes
- `README_HANDOVER.md` - Handover instructions
