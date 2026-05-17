# Knowledge Transfer Document

**Project:** ARC Studio  
**Version:** 0.6.0-alpha  
**Date:** 2026-05-13  
**Status:** Phase 7 - Final Handover  

---

## Project Overview

ARC Studio (Agent Runtime Cockpit IDE) is a Theia-based IDE for agent workflow development. It provides a complete environment for building, executing, and debugging agent workflows using SwarmGraph and LangGraph frameworks.

### Core Capabilities

- **Workflow Execution** — Run SwarmGraph workflows directly from the IDE with progress tracking and toast notifications
- **Trace Visualization** — Browse and inspect JSONL execution traces stored in `.arc/traces/`
- **Workspace Scanning** — Automatically detect SwarmGraph CLI and LangGraph Python workflows
- **Run Timeline** — Real-time execution monitoring with SSE streaming and replay
- **Schema Inspector** — Runtime schema export for adapter debugging
- **Global Keyboard Shortcuts** — Cmd+E (execute), Cmd+L (traces), Cmd+Shift+S (scan), Cmd+H (help)

### Target Users

Developers building agent workflows who need an integrated environment for execution, debugging, and trace analysis.

---

## Architecture

### High-Level Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                     Theia Browser App                        │
│  ┌────────────────────────────────────────────────────────┐ │
│  │              ARC Widget (React)                        │ │
│  │  - Workflow execution UI                               │ │
│  │  - Trace visualization                                 │ │
│  │  - Run Timeline with SSE replay                        │ │
│  └────────────────────────────────────────────────────────┘ │
│                          │                                   │
│                          │ JSON-RPC                          │
│                          ▼                                   │
│  ┌────────────────────────────────────────────────────────┐ │
│  │         ARC Backend Service (Node.js)                  │ │
│  │  - Workflow execution (subprocess)                     │ │
│  │  - Trace file management                               │ │
│  │  - Workspace scanning                                  │ │
│  │  - Security layer (input validation, env allow-list)   │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                           │
                           │ Subprocess
                           ▼
          ┌────────────────────────────────┐
          │    SwarmGraph CLI              │
          │  - Graph execution             │
          │  - LLM provider routing        │
          │  - Trace generation (JSONL)    │
          └────────────────────────────────┘
                           │
                           ▼
          ┌────────────────────────────────┐
          │    .arc/traces/                │
          │  - run-sg-{hash}.jsonl         │
          │  - Event stream storage        │
          └────────────────────────────────┘

          ┌────────────────────────────────┐
          │    Python Daemon (:7777)       │
          │  - /api/runs endpoints         │
          │  - SSE streaming               │
          │  - AG-UI event bridge          │
          └────────────────────────────────┘

          ┌────────────────────────────────┐
          │    Python FastAPI (:8000)      │
          │  - Legacy REST endpoints       │
          │  - External tool integration   │
          └────────────────────────────────┘
```

### Frontend

**Location:** `packages/arc-extension/src/browser/`

| File | Purpose |
|------|---------|
| `arc-widget.tsx` | Main UI widget (execution, traces, workspace scanning) |
| `arc-widget-contribution.ts` | Widget registration and menu contributions |
| `arc-extension-frontend-module.ts` | Inversify DI container setup |
| `arc-keybinding-contribution.ts` | Global keyboard shortcuts |
| `arc-widget.css` | CSS design system with Theia theme integration |

**Technology:** React, Theia ReactWidget, Inversify DI, TypeScript

### Backend (Node.js)

**Location:** `packages/arc-extension/src/node/`

| File | Purpose |
|------|---------|
| `arc-backend-service.ts` | Core business logic (1,341 lines) |
| `arc-extension-backend-module.ts` | Inversify DI container setup |
| `security-utils.ts` | Input validation, path traversal prevention, env allow-list |

**Technology:** Node.js, TypeScript, fs-extra, child_process

### Protocol Layer

**Location:** `packages/arc-extension/src/common/arc-protocol.ts`

Defines the `ArcService` interface with 7 methods:
1. `executeWorkflow()` — Execute SwarmGraph workflow
2. `cancelWorkflow()` — Cancel running workflow
3. `getTraces()` — List trace files
4. `readTrace()` — Read complete trace
5. `streamTrace()` — Stream trace events
6. `validateTrace()` — Validate trace format
7. `detectWorkflows()` — Auto-detect workflows

### Backend (Python)

**Location:** `python/src/`

| Component | Port | Purpose |
|-----------|------|---------|
| FastAPI server | :8000 | Legacy REST endpoints (execute, traces) |
| Daemon server | :7777 | Run management, SSE streaming, AG-UI bridge |

**Technology:** FastAPI, Pydantic, uvicorn, Python 3.11+

### Key Components Table

| Component | File | Lines | Purpose |
|-----------|------|-------|---------|
| Protocol | `arc-protocol.ts` | ~200 | RPC interface, types, error codes |
| Backend Service | `arc-backend-service.ts` | 1,341 | Workflow execution, trace management, detection |
| Security Utils (TS) | `security-utils.ts` | ~200 | Input sanitization, path validation, env allow-list |
| Widget | `arc-widget.tsx` | 884 | Main UI with execution, traces, scanning |
| Keybindings | `arc-keybinding-contribution.ts` | ~80 | Global shortcuts |
| CSS | `arc-widget.css` | 1,045 | Design system with Theia variables |
| Python Routes | `python/src/routes.py` | ~150 | FastAPI REST endpoints |
| Python Security | `python/src/security_utils.py` | ~120 | Input/path validation |
| Python Daemon | `python/src/daemon/` | ~500 | Run management, SSE, AG-UI bridge |

---

## Development Workflow

### Standard Process

1. **Create feature branch** from `build/no-mockups-handoff` (or `main` after merge)
2. **Make changes** following existing code patterns
3. **Build:** `pnpm build`
4. **Test:** `pnpm test` (Node.js) + `cd python && uv run pytest` (Python)
5. **Verify manually:** `pnpm start:browser` → open http://localhost:3000
6. **Lint:** `pnpm lint`
7. **Submit PR** with conventional commit format

### Key Commands

```bash
# Build
pnpm build                    # Build all packages
pnpm watch                    # Watch mode for development

# Run
pnpm start:browser            # Start browser app on port 3000

# Test
pnpm test                     # Run Node.js tests
cd python && uv run pytest    # Run Python tests
pnpm test:e2e                 # Run Playwright E2E tests

# Python CLI
cd python && uv run arc --help
uv run arc adapter test swarmgraph   # Conformance test
uv run arc runs --workspace <path>   # List traces

# Clean
pnpm clean                    # Remove build artifacts
```

### Branch Strategy

- `main` — Stable release branch (after Phase 7 merge)
- `build/no-mockups-handoff` — Development branch (all phases completed here)
- `feature/*` — Feature branches

---

## Key Decisions

| Decision | Chosen Approach | Reason |
|----------|----------------|--------|
| Framework | Eclipse Theia (not VS Code extension) | Extensible IDE framework, browser/Electron deployment, VS Code compatibility |
| Trace Format | JSONL (not binary/protobuf/SQLite) | Streaming-friendly, human-readable, incremental parsing, matches SwarmGraph |
| SwarmGraph Execution | Subprocess CLI (not library import) | Isolation, language-agnostic, easy timeout/kill |
| Security | List-form argv + shell:false + env allow-list | Command injection prevention, defence-in-depth |
| LangGraph Detection | Hybrid static AST + runtime execution | Dynamic graphs need execution; static analysis for quick discovery |
| Production Source Maps | Excluded (devtool: false) | 70 MB savings; acceptable for alpha |
| Credential Storage | System keychain (not plaintext config) | OS-managed encryption, most secure option |
| Context7 Integration | Opt-in with explicit config | Alpha must be safe; no surprise API calls |
| Monaco ESM | Direct dependency (not code-split) | Resolves webpack build issues; code splitting deferred |
| @theia/ripgrep | Pinned to v1.15.14 via pnpm overrides | Fixes build error with Node.js v25 |

Full decision log: `docs/IMPLEMENTATION_DECISIONS.md`

---

## Known Technical Debt

### High Priority

1. **Widget tests use source-code analysis** — Need jsdom harness with mocked Theia DI for runtime coverage (currently 0% widget coverage)
2. **Dual Python backend** — FastAPI (:8000) and daemon (:7777) overlap; should consolidate
3. **No automated E2E tests** — Playwright configured but tests deferred to Phase 7+

### Medium Priority

4. **Monaco bundle size** — ~29 MB (~50% of total); code splitting could save 10-15 MB
5. **Synchronous file I/O** in some trace operations — Should be fully async
6. **No input validation in frontend** — Relies entirely on backend validation
7. **Performance logging** — Uses console.log timing instead of structured metrics

### Low Priority

8. **AG-UI mapper parity** — Some event mappings incomplete
9. **@theia/file-search unavailable** — Upstream ripgrep/Node.js v25 incompatibility
10. **No CI/CD pipeline** — Manual build/test/deploy

---

## Future Work

### Immediate (Post-Handover)

- Tag and publish v0.6.0-alpha release
- Merge `build/no-mockups-handoff` to `main`
- Set up CI/CD pipeline (GitHub Actions)
- Configure monitoring (health check, metrics endpoints)

### Short-Term (1-2 Sprints)

- Boost test coverage to ≥80% (add jsdom harness for widget tests)
- Add automated E2E tests (Playwright)
- Implement Monaco code splitting
- Consolidate Python backends (FastAPI + daemon)
- Create OpenAPI/Swagger spec

### Medium-Term (1-3 Months)

- LangGraph runtime execution beyond dynamic workflow export
- CrewAI adapter implementation
- OpenAI Agents SDK adapter
- AG2 adapter
- Signed Electron installers with auto-update
- Rate limiting and authentication

### Long-Term (3+ Months)

- Production deployment automation
- Multi-user support with authentication
- Cloud deployment option
- Plugin marketplace
- Advanced trace analysis (diff, comparison, aggregation)
- Real-time collaboration features

---

## Contacts & Resources

### Repositories

- **ARC Studio:** https://github.com/Hansuqwer/arc-theia-studio
- **SwarmGraph:** https://github.com/Hansuqwer/SwarmGraph

### Documentation

- **Theia Docs:** https://theia-ide.org/docs/
- **FastAPI Docs:** https://fastapi.tiangolo.com/
- **LangGraph Docs:** https://langchain-ai.github.io/langgraph/

### Key Documents

| Document | Purpose |
|----------|---------|
| `README.md` | Project overview and quick start |
| `docs/API.md` | Complete API reference (JSON-RPC + REST) |
| `docs/ARCHITECTURE.md` | System architecture and component details |
| `docs/DEVELOPMENT.md` | Setup and development workflow |
| `docs/SECURITY.md` | Security implementation and best practices |
| `docs/TESTING.md` | Test setup and execution |
| `docs/TROUBLESHOOTING.md` | Common issues and solutions |
| `docs/DEPLOYMENT.md` | Production deployment guide |
| `docs/ROADMAP.md` | Future development priorities |
| `docs/IMPLEMENTATION_DECISIONS.md` | Architectural decision records |
| `CHANGELOG.md` | Version history and changes |
| `CONTRIBUTING.md` | Contribution guidelines |

### Issue Tracking

- **GitHub Issues:** https://github.com/Hansuqwer/arc-theia-studio/issues
- **GitHub Discussions:** https://github.com/Hansuqwer/arc-theia-studio/discussions

---

## Quick Reference

### Environment Requirements

| Tool | Minimum Version |
|------|----------------|
| Node.js | 18.0.0 |
| pnpm | 8.0.0 |
| Python | 3.11 |
| TypeScript | 5.3.0 |

### Key Environment Variables

| Variable | Purpose |
|----------|---------|
| `ARC_SWARMGRAPH_CLI` | Path to SwarmGraph CLI binary |
| `ARC_SWARMGRAPH_ALLOW_COSTS` | Gate for provider-backed execution (`true` to allow) |
| `ARC_LANGGRAPH_EXPORT` | LangGraph dynamic workflow export (`module:function`) |
| `ARC_CONTEXT7_API_KEY` | Context7 documentation API key |
| `GITHUB_TOKEN` | GitHub code search authentication |

### File Locations

| What | Where |
|------|-------|
| Trace files | `.arc/traces/*.jsonl` |
| Build output | `packages/*/lib/` |
| Python venv | `python/.venv/` |
| Generated Theia app | `packages/arc-browser-app/src-gen/` |
