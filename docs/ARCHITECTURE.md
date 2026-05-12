# ARC Studio Architecture

**Version:** 0.1.0  
**Last Updated:** 2026-05-12  
**Status:** Phase 4 - In Progress

---

## Overview

ARC Studio is an IDE for agent workflow development built on Eclipse Theia. It provides a complete environment for building, executing, and debugging agent workflows using SwarmGraph and LangGraph.

### Key Components

1. **Theia Extension** - Frontend UI and backend services
2. **Python API** - REST endpoints for workflow execution
3. **SwarmGraph Integration** - CLI execution and trace parsing
4. **Trace System** - JSONL-based event storage and visualization

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Theia Browser App                        │
│  ┌────────────────────────────────────────────────────────┐ │
│  │              ARC Widget (React)                        │ │
│  │  - Workflow execution UI                               │ │
│  │  - Trace visualization                                 │ │
│  │  - Workflow detection                                  │ │
│  └────────────────────────────────────────────────────────┘ │
│                          │                                   │
│                          │ JSON-RPC                          │
│                          ▼                                   │
│  ┌────────────────────────────────────────────────────────┐ │
│  │         ARC Backend Service (Node.js)                  │ │
│  │  - Workflow execution                                  │ │
│  │  - Trace file management                               │ │
│  │  - Workspace scanning                                  │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                          │
                          │ Subprocess
                          ▼
         ┌────────────────────────────────┐
         │    SwarmGraph CLI              │
         │  - Graph execution             │
         │  - LLM provider routing        │
         │  - Trace generation            │
         └────────────────────────────────┘
                          │
                          │ JSONL
                          ▼
         ┌────────────────────────────────┐
         │    .arc/traces/                │
         │  - run-sg-{hash}.jsonl         │
         │  - Event stream storage        │
         └────────────────────────────────┘

         ┌────────────────────────────────┐
         │    Python REST API (Optional)  │
         │  - FastAPI endpoints           │
         │  - External tool integration   │
         └────────────────────────────────┘
```

---

## Component Details

### 1. Theia Extension

**Location:** `packages/arc-extension/`

The Theia extension provides the core IDE functionality.

#### Frontend (Browser)

**Files:**
- `src/browser/arc-widget.tsx` - Main UI widget
- `src/browser/arc-widget-contribution.ts` - Widget registration
- `src/browser/arc-extension-frontend-module.ts` - Dependency injection

**Responsibilities:**
- Render workflow execution UI
- Display trace visualizations
- Handle user interactions
- Communicate with backend via JSON-RPC

**Technology:**
- React for UI components
- Theia's ReactWidget base class
- Inversify for dependency injection

#### Backend (Node.js)

**Files:**
- `src/node/arc-backend-service.ts` - Service implementation
- `src/node/arc-extension-backend-module.ts` - Dependency injection
- `src/common/arc-protocol.ts` - Shared protocol definitions

**Responsibilities:**
- Execute SwarmGraph CLI as subprocess
- Read/write trace files
- Scan workspace for workflows
- Manage file system operations

**Technology:**
- Node.js with TypeScript
- fs-extra for file operations
- child_process for subprocess execution

#### Protocol Layer

**File:** `src/common/arc-protocol.ts`

**Interfaces:**
- `ArcService` - Main service interface
- `ExecutionOptions` - Workflow execution configuration
- `ExecutionResult` - Execution result data
- `TraceFile` - Trace file metadata
- `TraceData` - Complete trace data
- `TraceEvent` - Individual trace event
- `WorkflowInfo` - Workflow detection result

**Communication:**
- JSON-RPC over Theia's connection handler
- Service path: `/services/arc`
- Bidirectional frontend-backend communication

---

### 2. Python API

**Location:** `python/src/`

Optional REST API for external tool integration.

#### Endpoints

**File:** `src/routes.py`

- `GET /` - Health check
- `POST /api/execute` - Execute workflow
- `GET /api/traces` - List traces
- `GET /api/traces/{trace_id}` - Get trace details

#### Security

**File:** `src/security_utils.py`

**Features:**
- Input sanitization (prompts, trace IDs)
- Path validation (prevent traversal)
- Backend type validation
- Workspace boundary enforcement

**Technology:**
- FastAPI for REST endpoints
- Pydantic for request/response models
- uvicorn for ASGI server

---

### 3. SwarmGraph Integration

**Execution Model:**

```
User Input (Prompt)
        │
        ▼
ARC Backend Service
        │
        │ spawn subprocess
        ▼
swarmgraph swarm --json "prompt"
        │
        │ writes JSONL
        ▼
.arc/traces/run-sg-{hash}.jsonl
        │
        │ read & parse
        ▼
ARC Widget (Visualization)
```

**Trace File Format:**

JSONL (JSON Lines) - one event per line:

```jsonl
{"type":"RUN_STARTED","timestamp":"2026-05-12T20:30:00Z","runId":"run-sg-abc123","sequence":0,"data":{}}
{"type":"NODE_COMPLETED","timestamp":"2026-05-12T20:30:10Z","runId":"run-sg-abc123","sequence":1,"data":{"nodeId":"agent-1"}}
{"type":"RUN_COMPLETED","timestamp":"2026-05-12T20:30:15Z","runId":"run-sg-abc123","sequence":2,"data":{}}
```

**Benefits:**
- Streaming-friendly (append-only)
- Human-readable for debugging
- Easy to parse incrementally
- Matches SwarmGraph's native format

---

### 4. Trace System

**Directory Structure:**

```
.arc/
└── traces/
    ├── run-sg-abc123.jsonl
    ├── run-sg-def456.jsonl
    └── run-sg-ghi789.jsonl
```

**Event Types:**

1. **RUN_STARTED** - Execution begins
2. **NODE_COMPLETED** - Graph node finishes
3. **MESSAGE** - Message sent/received
4. **RUN_COMPLETED** - Execution succeeds
5. **RUN_FAILED** - Execution fails

**Metadata:**
- Run ID (unique identifier)
- Timestamps (ISO 8601)
- Sequence numbers (ordering)
- Event-specific data

---

## Data Flow

### Workflow Execution Flow

```
1. User enters prompt in ARC Widget
        │
        ▼
2. Widget calls arcService.executeWorkflow() via JSON-RPC
        │
        ▼
3. Backend spawns SwarmGraph CLI subprocess
        │
        ▼
4. SwarmGraph executes workflow
   - Routes to LLM providers
   - Executes graph nodes
   - Writes events to trace file
        │
        ▼
5. Backend parses CLI output for run ID
        │
        ▼
6. Backend returns ExecutionResult to frontend
        │
        ▼
7. Widget displays result and trace path
```

### Trace Retrieval Flow

```
1. User clicks "Load Traces" in ARC Widget
        │
        ▼
2. Widget calls arcService.getTraces() via JSON-RPC
        │
        ▼
3. Backend scans .arc/traces/ directory
        │
        ▼
4. Backend reads each .jsonl file
        │
        ▼
5. Backend extracts metadata (ID, timestamp, status)
        │
        ▼
6. Backend returns sorted TraceFile[] to frontend
        │
        ▼
7. Widget displays trace list
        │
        ▼
8. User selects a trace
        │
        ▼
9. Widget calls arcService.readTrace(traceId)
        │
        ▼
10. Backend reads and parses full trace file
        │
        ▼
11. Backend returns TraceData with all events
        │
        ▼
12. Widget visualizes trace events
```

---

## Security Architecture

### Multi-Layer Security Model

**Layer 1: Workspace Isolation**
- All file operations restricted to workspace root
- Path validation prevents traversal attacks
- Trace files must be in `.arc/traces/`

**Layer 2: Input Validation**
- Prompts sanitized before execution
- Trace IDs validated (alphanumeric + hyphens only)
- Backend types validated against whitelist

**Layer 3: Subprocess Isolation**
- SwarmGraph runs in separate process
- Resource limits (planned for Phase 5)
- Timeout enforcement (5 minutes)

**Layer 4: Credential Storage** (Planned)
- System keychain integration
- No plaintext credentials
- OS-managed encryption

**Layer 5: Sandbox Execution** (Planned)
- User code runs in isolated environment
- Memory and CPU limits
- Network access controls

---

## Technology Stack

### Frontend
- **Framework:** Eclipse Theia 1.45.0
- **UI Library:** React
- **Language:** TypeScript 5.3.0
- **DI Container:** Inversify
- **Build Tool:** Webpack

### Backend (Node.js)
- **Runtime:** Node.js >= 18.0.0
- **Language:** TypeScript 5.3.0
- **File System:** fs-extra
- **Process Management:** child_process

### Backend (Python)
- **Runtime:** Python >= 3.11
- **Framework:** FastAPI
- **Server:** uvicorn
- **Validation:** Pydantic

### Build System
- **Package Manager:** pnpm >= 8.0.0
- **Monorepo:** pnpm workspaces
- **Compiler:** TypeScript compiler (tsc)

### External Dependencies
- **SwarmGraph:** CLI for workflow execution
- **LangGraph:** (Planned) Python library for stateful agents

---

## Design Patterns

### 1. Service-Oriented Architecture

**Pattern:** Frontend-Backend separation via JSON-RPC

**Benefits:**
- Clear separation of concerns
- Backend can be tested independently
- Frontend can be swapped (browser/Electron)

### 2. Subprocess Execution

**Pattern:** Execute external tools via subprocess

**Benefits:**
- Isolation from main process
- Language-agnostic (can call any CLI)
- Easy to timeout and kill

**Tradeoffs:**
- Overhead of process spawning
- IPC complexity
- Error handling across process boundaries

### 3. Event Sourcing (Traces)

**Pattern:** Store execution as sequence of events

**Benefits:**
- Complete execution history
- Replay capability
- Debugging and analysis
- Streaming-friendly

**Tradeoffs:**
- Storage overhead
- Parsing complexity
- Event schema evolution

### 4. Dependency Injection

**Pattern:** Inversify for component wiring

**Benefits:**
- Testability (mock dependencies)
- Loose coupling
- Follows Theia conventions

---

## File Organization

```
arc-theia-studio/
├── packages/
│   ├── arc-extension/          # Main Theia extension
│   │   ├── src/
│   │   │   ├── browser/        # Frontend code
│   │   │   ├── node/           # Backend code
│   │   │   └── common/         # Shared protocol
│   │   ├── lib/                # Compiled output
│   │   └── package.json
│   ├── arc-browser-app/        # Browser application
│   │   ├── src-gen/            # Generated Theia app
│   │   └── package.json
│   ├── arc-electron-app/       # Electron application (TODO)
│   └── arc-test-fixtures/      # Test utilities (TODO)
├── python/
│   ├── src/
│   │   ├── routes.py           # REST API endpoints
│   │   └── security_utils.py   # Security utilities
│   └── tests/                  # Python tests (TODO)
├── docs/                       # Documentation
│   ├── API.md                  # API documentation
│   ├── ARCHITECTURE.md         # This file
│   ├── DEVELOPMENT.md          # Development guide
│   ├── IMPLEMENTATION_DECISIONS.md
│   └── RESEARCH_NOTES.md
├── scripts/                    # Build and setup scripts
├── .arc/                       # Runtime data
│   └── traces/                 # Trace files
├── package.json                # Monorepo root
├── pnpm-workspace.yaml         # Workspace configuration
└── README.md                   # Project README
```

---

## Extension Points

### Adding New Workflow Types

To add support for a new workflow runtime:

1. **Update Protocol** (`arc-protocol.ts`)
   - Add new runtime type to `WorkflowInfo.type`

2. **Implement Detection** (`arc-backend-service.ts`)
   - Add detection logic in `detectWorkflows()`
   - Scan for runtime-specific files

3. **Implement Execution** (`arc-backend-service.ts`)
   - Add execution logic in `executeWorkflow()`
   - Handle runtime-specific CLI/API

4. **Update UI** (`arc-widget.tsx`)
   - Add runtime-specific controls
   - Handle runtime-specific visualization

### Adding New Event Types

To add a new trace event type:

1. **Update Protocol** (`arc-protocol.ts`)
   - Add new type to `TraceEvent.type` union

2. **Document Event** (`API.md`)
   - Add event type documentation
   - Specify data field schema

3. **Update Visualization** (`arc-widget.tsx`)
   - Add rendering logic for new event type

---

## Performance Considerations

### Current State (Phase 4)

- **Trace Loading:** Synchronous file reads (blocking)
- **Subprocess Execution:** No concurrency limits
- **Memory Usage:** Full trace files loaded into memory

### Planned Optimizations (Phase 5+)

- **Streaming Trace Parsing:** Read JSONL incrementally
- **Execution Queue:** Limit concurrent workflow executions
- **Trace Pagination:** Load events in chunks
- **Caching:** Cache parsed trace metadata

---

## Scalability

### Current Limits

- **Trace File Size:** Limited by available memory
- **Concurrent Executions:** No limit (can overwhelm system)
- **Workspace Size:** No limit on workflow detection

### Future Improvements

- **Large Trace Handling:** Stream processing for >100MB files
- **Execution Throttling:** Queue with configurable concurrency
- **Incremental Scanning:** Watch filesystem for workflow changes

---

## Testing Strategy

### Current State (Phase 4)

- ❌ No automated tests yet
- ✅ Manual testing via browser app
- ✅ SwarmGraph CLI integration tested

### Planned Testing (Phase 5+)

**Unit Tests:**
- Protocol interface contracts
- Backend service methods
- Security utilities
- Trace parsing logic

**Integration Tests:**
- End-to-end workflow execution
- Trace file generation and reading
- Workflow detection

**E2E Tests:**
- Full Theia application startup
- UI interactions
- Multi-step workflows

---

## Deployment

### Development

```bash
# Install dependencies
pnpm install

# Build all packages
pnpm build

# Start browser app
pnpm start:browser
```

### Production (Planned)

- **Browser App:** Static hosting (Vercel, Netlify)
- **Electron App:** Native installers (DMG, EXE, AppImage)
- **Python API:** Docker container or systemd service

---

## Known Issues

### Phase 4 (Current)

- ❌ Build fails with protocol interface errors
- ❌ Trace parsing not implemented
- ❌ Workflow detection incomplete (LangGraph)
- ❌ No error handling in UI
- ❌ No tests

### Technical Debt

- Synchronous file I/O (should be async)
- No input validation in frontend
- Hardcoded workspace paths
- No logging infrastructure

---

## Future Architecture

### Phase 5: Integration Fixes

- Complete trace parsing implementation
- Add LangGraph detection
- Implement error handling
- Add logging

### Phase 6: Alpha Acceptance

- Add authentication/authorization
- Implement rate limiting
- Add metrics and monitoring
- Complete test coverage

### Phase 7: Final Handover

- Production deployment configuration
- Performance optimization
- Documentation completion
- Handover to maintainers

---

## References

- [Eclipse Theia Documentation](https://theia-ide.org/docs/)
- [SwarmGraph Repository](https://github.com/Hansuqwer/SwarmGraph)
- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [Implementation Decisions](IMPLEMENTATION_DECISIONS.md)
- [API Documentation](API.md)
- [Development Guide](DEVELOPMENT.md)
