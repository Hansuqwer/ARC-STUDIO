# Changelog

All notable changes to ARC Studio.

## [v0.6.0-alpha] - 2026-05-13

### Added
- ARC Studio Theia extension with workflow execution, trace viewing, workspace scanning
- Production build optimization (93% size reduction: 521 MB → 38 MB)
- Security hardening: input validation, command injection prevention, env allow-list
- 159 automated tests (63.86% coverage)
- Global keyboard shortcuts (Cmd+E/L/Shift+S/H)
- Comprehensive documentation (API, Architecture, Security, Deployment)

### Fixed
- Monaco ESM webpack build (added direct dependency)
- Security-utils wired into backend service (was dead code)
- Python env allow-list typo (_ALLOW_ENV → _ALLOWED_ENV)
- Keyboard shortcuts now global (not widget-scoped)
- Toast timeout memory leak (dispose cleanup)

### Security
- Command injection: list-form argv + shell:false (primary) + metacharacter rejection (defence-in-depth)
- Path traversal: workspace isolation on all file operations
- Environment: allow-listed vars only (12 vars, no unbounded inheritance)
- Error sanitization: no file paths or stack traces leaked

### Known Limitations
- @theia/file-search unavailable (ripgrep/Node.js v25 incompatibility)
- Test coverage: 63.86% (target 70%, widget tests need jsdom harness)
- No automated E2E tests (manual testing completed)

## [0.1.0] — 2026-05-13

### Added

- **Phase 1**: Project bootstrap with pnpm workspace and Eclipse Theia scaffold
- **Phase 2**: Technology research and selection (SwarmGraph, LangGraph, Theia)
- **Phase 3**: Architecture decisions finalized, JSONL trace format, security model
- **Phase 4**: Security hardening — command injection prevention, path traversal protection, input sanitization
- **Phase 4**: Robust JSONL trace parser with line-by-line streaming support
- **Phase 4**: Performance instrumentation with timing logs
- **Phase 4**: Comprehensive workflow detection (SwarmGraph CLI + LangGraph AST scanning)
- **Phase 5**: Run Timeline Theia extension with prompt input, trace replay, and status feedback
- **Phase 5**: Schema Inspector extension for runtime schema export
- **Phase 5**: Daemon server with SSE streaming for real-time trace updates
- **Phase 5**: AG-UI-compatible event format and bridge
- **Phase 5**: Context pack generation with 5 providers (Context7, GitHub, local repo, web search, Vercel grep)
- **Phase 5**: Adapter registry with conformance testing (SwarmGraph 8/8, LangGraph 9/9)
- **Phase 5**: JSONL trace store with save/load/list/prune operations
- **Phase 5**: Python CLI (`arc`) with inspect, adapter, runs, context commands
- **Phase 5**: Run management commands: `arc runs`, `arc runs get`, `arc runs trace`, `arc runs prune`
- **Phase 5**: Daemon integration tests for `/api/runs` and SSE replay
- **Phase 5**: E2E Playwright smoke tests
- **Phase 5**: Unsigned Electron packaging smoke test
- **Phase 6**: Comprehensive API documentation (all 7 ArcService methods, both REST servers)
- **Phase 6**: Documentation review — README, ARCHITECTURE, DEVELOPMENT, SECURITY updated
- **Phase 6**: CHANGELOG.md created

### Security

- Command injection prevention via `spawn()` with `shell: false` (TypeScript) and `subprocess.run()` with `shell=False` (Python)
- Path traversal protection with strict trace ID validation (`run-{prefix}-{hex}` pattern)
- Workspace boundary enforcement for all file operations
- Input sanitization — shell metacharacter rejection, control character removal, length limits
- Error message sanitization to prevent information leakage
- Subprocess environment allow-list to prevent credential leakage
- CORS restricted to `localhost:3000` on daemon server
- Security test suite: 12 Python tests covering redaction and path validation

### Fixed

- SwarmGraph fixture workflows restricted to test/demo paths only (no mock data in product)
- LangGraph dynamic workflow export via `ARC_LANGGRAPH_EXPORT=module:function`
- Provider-backed execution gated by `ARC_SWARMGRAPH_ALLOW_COSTS=true`
- Python workspace scanning excludes `.venv`, `node_modules`, `__pycache__`, and other cache dirs
- Trace parsing handles both single-line JSON and multi-line JSONL formats
- Trace status derived from event types when explicit status is missing
- Run ID extraction from multiple output formats (JSON fields, regex fallback)

### Known Limitations

- Electron signing/notarization not configured (requires CSC_LINK, CSC_KEY_PASSWORD, Apple ID)
- LangGraph runtime execution limited to dynamic workflow export only
- CrewAI, OpenAI Agents SDK, AG2 adapters not yet implemented
- Rate limiting and authentication not yet implemented
- Auto-update pipeline not configured

### Testing

- 82 Python tests passing
- 8 Node.js unit tests passing
- Test fixtures self-test passing
- E2E Playwright smoke tests configured
- Conformance tests: SwarmGraph 8/8, LangGraph 9/9
- Daemon integration tests for `/api/runs` and SSE

### Dependencies

- **Node.js**: >= 18.0.0
- **pnpm**: >= 8.0.0
- **Python**: >= 3.11
- **Eclipse Theia**: 1.45.0+
- **TypeScript**: 5.3.0
- **FastAPI**: Python REST framework
- **uv**: Python package manager
