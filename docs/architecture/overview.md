# ARC Studio Architecture Overview

## Three-Layer Model

ARC Studio is built in three layers that communicate over JSON-RPC and HTTP:

```
┌──────────────────────────────────────────────────────────┐
│                   BROWSER APP                             │
│  applications/browser/                                    │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────┐ │
│  │ Chat Tab │ │ Runs Tab │ │Workflows │ │ Config Tab   │ │
│  │          │ │          │ │ Tab      │ │              │ │
│  └──────────┘ └──────────┘ └──────────┘ └──────────────┘ │
│  ┌──────────┐ ┌──────────────┐ ┌──────────────────────┐  │
│  │ Timeline │ │ Event Stream │ │ Graph / Adapters /.. │  │
│  └──────────┘ └──────────────┘ └──────────────────────┘  │
└──────────────────────┬───────────────────────────────────┘
                       │ JSON-RPC (Theia connection)
┌──────────────────────▼───────────────────────────────────┐
│               THEIA EXTENSION                              │
│  packages/arc-extension/                                   │
│  ┌──────────────────┐  ┌────────────────────────────────┐ │
│  │ Frontend Widgets │  │ Backend Services               │ │
│  │ ArcStudioWidget  │  │ arc-backend-service.ts         │ │
│  │ ArcWidget (leg.) │  │ workflow-executor.ts           │ │
│  │ Components (13)  │  │ trace-parser.ts                │ │
│  │ Tabs (4)         │  │ run-lifecycle-service.ts       │ │
│  └──────────────────┘  │ audit-bridge-service.ts        │ │
│                        └──────────┬─────────────────────┘ │
└───────────────────────────────────┬───────────────────────┘
                                    │ HTTP / CLI spawn
┌───────────────────────────────────▼───────────────────────┐
│               PYTHON BACKEND                               │
│  python/src/agent_runtime_cockpit/                         │
│  ┌────────────┐ ┌──────────────┐ ┌──────────────────────┐ │
│  │ CLI (arc)  │ │ Daemon (arc  │ │ Orchestration        │ │
│  │            │ │ serve) + SSE │ │ EventBroker          │ │
│  │ health     │ │ /api/runs    │ │ JobSupervisor        │ │
│  │ status     │ │ /api/audit   │ │ RuntimeRouter        │ │
│  │ run        │ │ /api/hitl    │ └──────────────────────┘ │
│  │ audit      │ └──────────────┘ ┌──────────────────────┐ │
│  │ replay     │                  │ Storage              │ │
│  │ eval       │                  │ JsonlTraceStore      │ │
│  │ runs       │                  │ SqliteStore          │ │
│  └────────────┘                  │ IndexedTraceStore    │ │
│                                  └──────────────────────┘ │
│  ┌────────────┐ ┌──────────────┐ ┌──────────────────────┐ │
│  │ Security   │ │ Adapte┴s     │ │ Config / Profiles    │ │
│  │ Trust      │ │ SwarmGraph   │ │ YAML loader          │ │
│  │ Redaction  │ │ LangGraph    │ │ 4-level precedence   │ │
│  │ Isolation  │ │ CrewAI, etc. │ └──────────────────────┘ │
│  └────────────┘ └──────────────┘                          │
└───────────────────────────────────────────────────────────┘
```

## Data Flow

1. **User input** enters through the CLI (`arc run`) or the browser IDE (Chat/Runs tabs).
2. **Theia extension** receives the request via JSON-RPC and delegates to the Python CLI via `execFileSync` or spawn.
3. **RuntimeRouter** selects the appropriate adapter (SwarmGraph, LangGraph, etc.) based on workspace detection.
4. **Adapter** executes the workflow. Events flow through **EventBroker** (bounded queue, pub/sub, SSE).
5. **Events** are dual-written: canonical JSONL trace files (`.arc/traces/<run_id>.jsonl`) and SQLite metadata index (ADR-003).
6. **Frontend** receives events via SSE or replay, updating the run timeline, event stream, and graph views in real time.

## Key Subsystems

### Storage Strategy (ADR-003)

Dual-write architecture: JSONL files are the canonical trace storage (human-readable, append-only). A SQLite index provides fast metadata search, run listing, and status queries. The `IndexedTraceStore` coordinates both.

### Run Lifecycle State Machine (ADR-002)

Runs progress through `queued → running → completed/failed/cancelled`. Lifecycle is managed by `JobSupervisor`, which handles cancel, orphan recovery, and timeout.

### Event Schema Versioning (ADR-004)

All events carry a `schema_version` field (currently v2). Additive changes do not increment the version. Breaking changes increment, and readers must support N and N-1. Old traces retain their original version.

### Audit Chain Architecture (ADR-021)

Audit chains support memory-bounded SHA-256 verification and optional HMAC-SHA256 verification where a run path writes keyed audit material. Stored as JSONL per run in `~/.arc/audit/<run_id>.audit.jsonl`. Each covered record is linked to the previous record. Verification is via `arc audit verify <run_id>`. ARC does not claim adapter-wide keyed audit coverage.

### Security Model

Workspace trust resolver (external DB at `~/.arc/trusted-workspaces.json`), secret redaction in adapter outputs, paid-call gating via `RunProfile`, and subprocess/Docker isolation providers.

### Provider Routing

`RuntimeRouter` supports combo routing (multiple adapters) and adoption routing (scaffolding for non-native runtimes). Provider configuration uses 4-level precedence: environment > workspace > user > defaults.

## Protocol Boundary

Frontend and backend communicate via **JSON-RPC** over Theia's connection infrastructure (JSON-RPC channel). Protocol types are defined in TypeScript at `packages/arc-extension/src/common/arc-protocol.ts` and mirrored in Python at `python/src/agent_runtime_cockpit/protocol/`. The `packages/arc-protocol-ts/` package provides standalone TypeScript types for use outside Theia.

## Python Daemon Communication

The Python daemon listens on configurable host/port and provides REST API endpoints.

### Default Configuration
- **Host:** `localhost` (127.0.0.1)
- **Port:** `7777`
- **Workspace:** Current working directory (or `--workspace` flag)

### Fallback Chain

The Theia backend connects to the daemon using the following priority:

1. **Explicit `ARC_PYTHON_DAEMON_URL` environment variable**
2. **Auto-probe `http://127.0.0.1:7777`** (default port)
3. **Manual configuration** in IDE Config tab

### API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/health` | GET | Health check |
| `/api/inspect` | GET | Workspace inspection |
| `/api/runtimes` | GET | List detected runtimes |
| `/api/workflows` | GET | Export workflows |
| `/api/schemas` | GET | Export schemas |
| `/api/runs/start` | POST/GET | Start a run |
| `/api/runs/{id}` | GET | Get run details |
| `/api/runs/{id}/events` | GET | SSE stream events |

See `python/src/agent_runtime_cockpit/web/routes.py` for full API documentation.

## Related Docs

- [Deep Architecture Analysis](./DEEP_ARCHITECTURE_ANALYSIS.md) — detailed audit of all subsystems
- [Product Layout](./product-lock.md) — desktop-first product architecture
- [ADR-000: Execution Core Contract](../adr/000-execution-core-contract.md)
- [ADR-001: Config Model](../adr/001-config-model.md)
- [ADR-002: Run Lifecycle State Machine](../adr/002-run-lifecycle-state-machine.md)
- [ADR-003: Storage Strategy](../adr/003-storage-strategy.md)
- [ADR-004: Event Schema Versioning](../adr/004-event-schema-versioning.md)
- [ADR-014: Security Architecture](../adr/ADR-014-security-architecture.md)
- [ADR-018: Protocol Package as Canonical Schema Home](../adr/ADR-018-protocol-package-as-canonical-schema-home.md)
- [ADR-021: Audit Chain Architecture](../adr/021-audit-chain-architecture.md)
- [DEVELOPMENT.md](../DEVELOPMENT.md) — build, test, and contribution guide
# Sandbox Architecture

The execution isolation model is now layered:

```text
IsolationProvider
├── none
├── subprocess
├── container     # gated Docker/Podman fallback
└── microvm       # Linux/Firecracker gated scaffold, host-unproven; macOS preflight/harness only
```

The CLI sandbox path separates policy from execution:

```text
argv -> CommandClassification -> SandboxDecision -> IsolationProvider -> SandboxResult/audit event -> local event-log mirror
```

`subprocess` is the default real execution provider. It uses argv lists, filtered env, bounded stdout/stderr capture, process-group timeout kill, workspace cwd checks, and defaults to `workspace_root` as cwd when a direct caller omits `cwd`. `container` is a gated fallback. `microvm` has a Linux/Firecracker gated scaffold behind `ARC_MICROVM_EXEC_ENABLED=1`, `ARC_MICROVM_INTEGRATION=1`, `ARC_FC_REAL_EXEC=1`, Linux/KVM, Firecracker, kernel/rootfs, and workspace snapshot tooling. It is host-unproven until an eligible Linux/KVM host boots/runs/tears down a VM and tests pass. macOS remains blocked for strict public execution because Lima/VZ networking is network-present and no direct Apple VZ no-NIC helper exists.

MicroVM doctor/preflight output separates runtime preflight readiness from public execution readiness. Real microVM execution has not been proven on this macOS host; release docs must keep Linux/Firecracker labeled gated scaffold, host-unproven until live proof exists.

Firecracker proof and execution artifact generation are available as local CLI utilities. They do not boot a VM; eligible Linux/KVM hosts must run the opt-in smoke test to prove real execution.
