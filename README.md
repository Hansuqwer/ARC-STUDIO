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

## Features

### Current (Phase 1 - Bootstrap)

- ✅ Project structure initialized
- ✅ Theia extension scaffold
- ✅ Basic UI widget
- ✅ Backend service structure
- ✅ Python API endpoints
- ✅ Build configuration

### Planned

- Phase 2: Research Lock ✅ (Complete)
- Phase 3: Discovery Lock ✅ (Complete)
- Phase 4: Independent Fixes (In Progress)
  - SwarmGraph execution
  - Trace file parsing
  - Workflow detection
- Phase 5: Integration Fixes
- Phase 6: Alpha Acceptance
- Phase 7: Final Handover

## Documentation

Comprehensive documentation is available in the `docs/` directory:

- [Research Notes](docs/RESEARCH_NOTES.md) - Technology research findings
- [Implementation Decisions](docs/IMPLEMENTATION_DECISIONS.md) - Architectural decisions
- [Phase 2 Complete](docs/PHASE_2_COMPLETE.md) - Research phase sign-off
- [Phase 3 Discovery](docs/PHASE_3_DISCOVERY.md) - Current state analysis

## Architecture Decisions

Key architectural decisions (see [docs/IMPLEMENTATION_DECISIONS.md](docs/IMPLEMENTATION_DECISIONS.md)):

1. **Context7**: Opt-in with explicit config
2. **SwarmGraph**: Subprocess execution + JSONL parsing
3. **LangGraph**: Hybrid static/runtime detection
4. **Events**: JSONL format in `.arc/traces/`
5. **Theia**: Side panel widget + backend service
6. **Security**: Multi-layered (workspace, keychain, sandbox)
7. **Offline-first**: Full functionality without internet

## Contributing

This project follows a 7-phase development workflow. See `arc_prompt.txt` for detailed phase descriptions.

## License

EPL-2.0 OR GPL-2.0 WITH Classpath-exception-2.0

## Links

- Repository: https://github.com/Hansuqwer/arc-theia-studio
- SwarmGraph: https://github.com/Hansuqwer/SwarmGraph
- Eclipse Theia: https://theia-ide.org/
