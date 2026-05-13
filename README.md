# ARC Studio

**Agent Runtime Cockpit IDE** - A development environment for building, executing, and debugging agent workflows built on Eclipse Theia.

## Overview

ARC Studio is an IDE for agent workflow development, supporting:
- **SwarmGraph** - AI provider routing and quota management
- **LangGraph** - Stateful agent orchestration
- **Trace Visualization** - Real-time execution monitoring
- **Workflow Detection** - Automatic workflow discovery

## Architecture

Built on Eclipse Theia with:
- **Frontend**: React-based UI with custom widgets
- **Backend**: Node.js services + Python API
- **Event Streaming**: JSONL trace format
- **Security**: Multi-layered (workspace isolation, credential storage, sandbox execution)

## Quick Start

### Prerequisites

- Node.js >= 18.0.0
- pnpm >= 8.0.0
- Python >= 3.11
- Git

### Installation

```bash
# Check environment
bash scripts/check-env.sh

# Bootstrap development environment
bash scripts/bootstrap-dev.sh

# Start browser application
pnpm start:browser
```

Visit http://localhost:3000 to access ARC Studio.

## Development

### Project Structure

```
arc-theia-studio/
├── packages/
│   ├── arc-extension/       # Main Theia extension
│   ├── arc-browser-app/     # Browser application
│   ├── arc-electron-app/    # Electron application (TODO)
│   └── arc-test-fixtures/   # Test utilities (TODO)
├── python/
│   ├── src/                 # Python backend
│   └── tests/               # Python tests
├── docs/                    # Documentation
└── scripts/                 # Build and setup scripts
```

### Available Commands

```bash
# Development
pnpm install              # Install dependencies
pnpm build               # Build all packages
pnpm watch               # Watch mode for development
pnpm clean               # Clean build artifacts

# Running
pnpm start:browser       # Start browser app (port 3000)
pnpm start:electron      # Start Electron app (TODO)

# Testing
pnpm test                # Run all tests
pnpm test:e2e            # Run E2E tests (TODO)
pnpm lint                # Lint code

# Python
cd python
uv run pytest -q         # Run Python tests
uv run ruff check        # Lint Python code
uv run mypy src tests    # Type check Python code
```

## Current Status

### Development Phase

| Phase | Status | Description |
|-------|--------|-------------|
| Phase 1: Bootstrap Lock | ✅ Complete | Project structure and Theia scaffold |
| Phase 2: Research Lock | ✅ Complete | Technology research and selection |
| Phase 3: Discovery Lock | ✅ Complete | Architecture decisions finalized |
| Phase 4: Independent Fixes | ✅ Complete | Security hardening, JSONL parser, perf instrumentation |
| Phase 5: Integration Fixes | ✅ Complete | Run timeline + schema inspector extensions wired |
| Phase 6: Alpha Acceptance | 🔄 In Progress | Documentation review, test coverage, verification |
| Phase 7: Final Handover | ⏳ Pending | Production release |

### What's Working

- ✅ Project structure with pnpm workspaces
- ✅ Theia extension scaffold with React widget
- ✅ Python FastAPI backend with security validation
- ✅ SwarmGraph CLI integration (subprocess execution)
- ✅ Trace file management (JSONL format)
- ✅ Security utilities (input sanitization, path validation)

### What's In Progress (Phase 6)

- 🔄 Documentation review and completion
- 🔄 Test coverage expansion
- 🔄 Alpha acceptance verification

### Known Limitations

- Electron signing/notarization is not configured
- LangGraph runtime execution beyond dynamic workflow export not yet implemented
- CrewAI, OpenAI Agents SDK, AG2 adapters not yet implemented
- Rate limiting and authentication not yet implemented (planned for Phase 7)

## Features

### Workflow Execution

Execute SwarmGraph workflows directly from the IDE:

```typescript
// Via JSON-RPC (Theia extension)
const result = await arcService.executeWorkflow(
  "Summarize the latest news",
  { backend: 'gateway', costAllowed: true }
);
console.log(`Run ID: ${result.runId}`);
console.log(`Trace: ${result.tracePath}`);
```

```bash
# Via REST API
curl -X POST http://localhost:8000/api/execute \
  -H "Content-Type: application/json" \
  -d '{"prompt": "What is 2+2?", "backend": "stub"}'
```

### Trace Visualization

Browse and inspect execution traces stored in `.arc/traces/`:

```bash
# List all traces
curl http://localhost:8000/api/traces

# Get a specific trace
curl http://localhost:8000/api/traces/run-sg-abc123
```

Traces are stored in JSONL format — one event per line:

```jsonl
{"type":"RUN_STARTED","timestamp":"2026-05-12T20:30:00Z","runId":"run-sg-abc123","sequence":0,"data":{}}
{"type":"NODE_COMPLETED","timestamp":"2026-05-12T20:30:10Z","runId":"run-sg-abc123","sequence":1,"data":{"nodeId":"agent-1"}}
{"type":"RUN_COMPLETED","timestamp":"2026-05-12T20:30:15Z","runId":"run-sg-abc123","sequence":2,"data":{}}
```

### Workflow Detection

Automatically detect SwarmGraph and LangGraph workflows in your workspace:

```typescript
const workflows = await arcService.detectWorkflows();
// [{ type: 'swarmgraph', path: '/usr/local/bin/swarmgraph', name: 'SwarmGraph CLI' }]
```

### Security

Multi-layered security model:
- Input sanitization (prompts, trace IDs)
- Path traversal prevention
- Subprocess isolation (`shell: false`)
- Workspace boundary enforcement

### Runtime Support

| Runtime | Current support | Missing |
| --- | --- | --- |
| SwarmGraph | Detection, AST workflow/schema export heuristics, local/gateway execution, JSONL trace replay/export | Audit integrations |
| LangGraph | Detection, AST workflow heuristics, dynamic export/run hook, fixture schema | Streaming/events; see `docs/RUNTIMES.md` |
| CrewAI | Not implemented | Adapter |
| OpenAI Agents SDK | Not implemented | Adapter |
| AG2 | Not implemented | Adapter |

## Documentation

Comprehensive documentation is available in the `docs/` directory:

- [API Reference](docs/API.md) - REST API and JSON-RPC protocol
- [Architecture](docs/ARCHITECTURE.md) - System architecture and components
- [Development Guide](docs/DEVELOPMENT.md) - Setup and development workflow
- [Security](docs/SECURITY.md) - Security implementation and best practices
- [Testing](docs/TESTING.md) - Test setup and execution
- [Troubleshooting](docs/TROUBLESHOOTING.md) - Common issues and solutions
- [Extensions](docs/EXTENSIONS.md) - Theia extension development
- [Roadmap](docs/ROADMAP.md) - Future development plans
- [Research Notes](docs/RESEARCH_NOTES.md) - Technology research findings
- [Implementation Decisions](docs/IMPLEMENTATION_DECISIONS.md) - Architectural decisions

## Architecture Decisions

Key architectural decisions (see [docs/IMPLEMENTATION_DECISIONS.md](docs/IMPLEMENTATION_DECISIONS.md)):

1. **Context7**: Opt-in with explicit config
2. **SwarmGraph**: Subprocess execution + JSONL parsing
3. **LangGraph**: Hybrid static/runtime detection
4. **Events**: JSONL format in `.arc/traces/`
5. **Theia**: Side panel widget + backend service
6. **Security**: Multi-layered (workspace, keychain, sandbox)
7. **Offline-first**: Full functionality without internet

## Troubleshooting

### Build Errors

**Issue:** TypeScript compilation fails

**Solution:**
1. Clean and rebuild: `pnpm clean && pnpm build`
2. Check for missing dependencies: `pnpm install`
3. Verify Node.js >= 18.0.0: `node --version`

### Installation Issues

**Issue:** `pnpm install` fails or takes too long

**Solution:**
- Ensure Node.js >= 18.0.0: `node --version`
- Ensure pnpm >= 8.0.0: `pnpm --version`
- Clear pnpm cache: `pnpm store prune`
- Retry installation: `pnpm install`

**Issue:** Python dependencies fail to install

**Solution:**
- Ensure Python >= 3.11: `python --version`
- Install uv if missing: `pip install uv`
- Navigate to python directory: `cd python`
- Install dependencies: `uv pip install -e .`

### Runtime Issues

**Issue:** SwarmGraph command not found

**Solution:**
- Verify SwarmGraph is installed: `which swarmgraph`
- If missing, install from: https://github.com/Hansuqwer/SwarmGraph
- Ensure it's in your PATH

**Issue:** Application won't start

**Solution:**
- Build all packages first: `pnpm build`
- If build fails, see "Build Errors" above
- Check port 3000 is available: `lsof -i :3000`
- Try starting: `pnpm start:browser`

### Known Issues

- **Electron signing not configured** - Requires CSC_LINK, CSC_KEY_PASSWORD, and Apple ID
- **LangGraph runtime execution** - Only dynamic workflow export is implemented
- **No rate limiting** - Planned for Phase 7
- **No authentication** - Planned for Phase 7

For more issues, see [GitHub Issues](https://github.com/Hansuqwer/arc-theia-studio/issues).

## Contributing

This project follows a 7-phase development workflow. See `arc_prompt.txt` for detailed phase descriptions.

### Development Workflow

1. Create a feature branch from `build/no-mockups-handoff`
2. Make changes following the architectural decisions in `docs/IMPLEMENTATION_DECISIONS.md`
3. Add tests (when test infrastructure is available)
4. Run `pnpm build` and `pnpm lint` to verify
5. Submit a pull request

### Code Style

- TypeScript: Follow Theia conventions
- Python: Follow PEP 8, use type hints
- Documentation: Add JSDoc comments for public APIs

## License

EPL-2.0 OR GPL-2.0 WITH Classpath-exception-2.0

## Links

- Repository: https://github.com/Hansuqwer/arc-theia-studio
- SwarmGraph: https://github.com/Hansuqwer/SwarmGraph
- Eclipse Theia: https://theia-ide.org/
- Documentation: [docs/](docs/)
