# Execution Core Contract Specification

## Status
Proposed

## Context

ARC Studio's biggest hidden risk is that the **execution core contract is underspecified**. There is no formal definition of how a run request flows from the IDE through the daemon, isolation provider, adapter, event broker, trace store, and audit store. Each component was built independently, leading to:

- Inconsistent state management (Node.js tentative IDs vs Python definitive IDs)
- No formal handoff boundaries between components
- Missing error propagation paths
- No guarantee that events, traces, and audit chains are consistent
- No specification for what happens when components fail mid-execution

This document defines the **execution core contract** — the formal specification that all components must follow.

## Overview

```
┌────────────────────────────────────────────────────────────────────────────┐
│                          EXECUTION CORE CONTRACT                           │
│                                                                            │
│  Run Request ──► Config Resolution ──► Workspace Trust ──► Isolation       │
│       │              │                     │                   │            │
│       ▼              ▼                     ▼                   ▼            │
│  Job Supervisor ──► Adapter ──► Event Broker ──► Trace Store               │
│       │              │              │                  │                    │
│       ▼              ▼              ▼                  ▼                    │
│  Audit Store ◄── HITL/Replay ◄── Cancel ◄── Final RunRecord                │
└────────────────────────────────────────────────────────────────────────────┘
```

## 1. Run Request

### Definition

A run request is the entry point for all executions. It is created by the IDE or CLI and submitted to the daemon.

```python
class RunRequest(BaseModel):
    workflow_id: str                      # Workflow identifier
    runtime: Optional[str] = None         # Explicit runtime (None = auto-detect)
    inputs: dict[str, Any] = {}           # Workflow inputs
    prompt: Optional[str] = None          # Prompt input (for SwarmGraph)
    profile_id: str = "stub"              # Security profile
    provider: Optional[str] = None        # Explicit provider (None = use routing policy)
    model: Optional[str] = None           # Explicit model (None = use routing policy)
    allow_paid_calls: bool = False        # Dual-gate override
    background: bool = False              # Background execution
    timeout_seconds: int = 300            # Execution timeout
    metadata: dict[str, Any] = {}         # Arbitrary metadata
```

### Validation

The daemon validates the run request before processing:

1. `workflow_id` matches `^[\w\-\.]{1,128}$`
2. `profile_id` is a known profile
3. `timeout_seconds` is between 1 and 3600
4. `inputs` is a flat dict (no nested objects > 3 levels deep)
5. `prompt` is sanitized (no control chars, no shell metacharacters, max 10K chars)

### Submission

Run requests are submitted via:
- **HTTP**: `POST /api/runs/start` (daemon)
- **CLI**: `arc run <workflow> --runtime <runtime> --prompt <prompt> --json`
- **IDE**: `ArcFrontendService.executeWorkflow(request)`

## 2. Config Resolution

### Process

Before execution begins, the daemon resolves configuration:

```
1. Load workspace config (.arc/config.yaml)
2. Load user config (~/.arc/config.yaml)
3. Apply environment variable overrides
4. Apply CLI argument overrides
5. Resolve runtime (explicit or auto-detect)
6. Resolve provider (explicit or routing policy)
7. Resolve security profile
8. Resolve isolation provider (based on profile + trust)
9. Build final execution config
```

### Output

```python
class ResolvedConfig(BaseModel):
    run_id: str                           # Generated run ID
    workflow_id: str
    runtime: str                          # Resolved runtime
    provider: str                         # Resolved provider
    model: str                            # Resolved model
    profile: RunProfile                   # Resolved profile
    isolation: str                        # Isolation provider name
    trust_level: TrustLevel              # Workspace trust level
    timeout_seconds: int
    allow_paid_calls: bool
    filesystem_policy: FilesystemPolicy
    network_policy: NetworkPolicy
    resource_limits: ResourceLimits
    audit_enabled: bool
    trace_path: str                       # Absolute path for trace file
    audit_path: Optional[str] = None      # Absolute path for audit chain
```

## 3. Workspace Trust

### Resolution

```python
def resolve_trust(workspace: Path, config: Config) -> TrustLevel:
    """Resolve workspace trust level."""
    # 1. Explicit config override
    if config.workspace.trust_level != "auto":
        return TrustLevel(config.workspace.trust_level)
    
    # 2. Trust marker file
    if (workspace / ".arc" / "trusted").exists():
        return TrustLevel.TRUSTED
    
    # 3. Default: untrusted. A home-directory path is not trust evidence.
    return TrustLevel.UNTRUSTED
```

`PARTIAL` trust is reserved for explicit user approval or future Theia trust integration. A path being under the user's home directory is not sufficient trust evidence.

### Enforcement

Trust level determines minimum isolation:

| Trust Level | Minimum Isolation | Network Mode | Filesystem Access |
|-------------|------------------|--------------|-------------------|
| `UNTRUSTED` | `subprocess` | `none` | Workspace only |
| `PARTIAL` | `subprocess` | `restricted` | Workspace + ~/.arc/ |
| `TRUSTED` | `none` | `full` | All user-accessible |

If the resolved profile requires more trust than the workspace has, the run is rejected with `GatingError`.

## 4. Isolation Provider

### Selection

The isolation provider is selected based on:
1. Profile requirement (`profile.isolation`)
2. Workspace trust level (minimum isolation)
3. Config override (`config.execution.isolation`)
4. Availability (health check)

```python
async def select_isolation_provider(
    profile: RunProfile,
    trust: TrustLevel,
    config: Config,
    providers: dict[str, IsolationProvider],
) -> IsolationProvider:
    """Select isolation provider based on policy and availability."""
    # Config override takes priority
    requested = config.execution.isolation
    if requested and requested != "none":
        provider = providers.get(requested)
        if provider and await provider.health_check():
            return provider
    
    # Profile requirement
    provider = providers.get(profile.isolation)
    if provider and await provider.health_check():
        return provider
    
    # Fallback to subprocess
    return providers["subprocess"]
```

### Execution Contract

The isolation provider guarantees:

1. **Process isolation**: The command runs in an isolated environment
2. **Environment filtering**: Only allowlisted env vars are passed
3. **Filesystem policy**: Access is restricted per policy
4. **Network policy**: Network access is restricted per policy
5. **Resource limits**: CPU, memory, and disk limits are enforced
6. **Clean termination**: Process is killed on timeout or cancellation
7. **Output capture**: stdout and stderr are captured and returned

```python
class SubprocessResult(BaseModel):
    exit_code: int
    stdout: str
    stderr: str
    duration_ms: int
    pid: int
    killed: bool = False
    kill_reason: Optional[str] = None
```

## 5. Job Supervisor

### Lifecycle Management

The job supervisor owns the run lifecycle:

```
1. Receive RunRequest
2. Resolve config, trust, isolation
3. Create RunRecord (status: PENDING)
4. Persist to trace store + SQLite
5. Spawn execution task (status: RUNNING)
6. Stream events via EventBroker
7. On completion: persist final RunRecord
8. On error: persist error detail
9. On cancel: kill process, persist cancellation
```

### Guarantees

The supervisor guarantees:

1. **State persistence**: Every state transition is persisted before proceeding
2. **Orphan recovery**: On restart, orphaned RUNNING runs are marked FAILED
3. **Targeted cancellation**: Specific runs can be cancelled by ID
4. **Timeout enforcement**: Runs exceeding timeout are killed
5. **Event ordering**: Events are emitted with monotonically increasing sequence numbers
6. **Heartbeat**: Running runs have heartbeat timestamps for liveness detection

### Crash Recovery

On supervisor startup:

```python
async def recover_orphaned_runs(self):
    """Find and recover orphaned runs from previous supervisor."""
    orphaned = self.store.get_runs_by_status(RunStatus.RUNNING)
    
    for run in orphaned:
        if run.supervisor_id != self.supervisor_id:
            # This run belongs to a dead supervisor
            run.status = RunStatus.FAILED
            run.error_detail = "supervisor_crash"
            run.ended_at = now()
            self.trace_store.save(run)
            self.store.update_run_status(run.id, RunStatus.FAILED)
```

## 6. Adapter/Adoption Runner

### Contract

Adapters convert run requests into runtime-specific execution:

```python
class Adapter(Protocol):
    """Interface for runtime adapters."""
    
    @property
    def runtime_id(self) -> str:
        """Runtime identifier (swarmgraph, langgraph, crewai, etc.)."""
        ...
    
    @property
    def capabilities(self) -> AdapterCapabilities:
        """What this adapter supports."""
        ...
    
    async def run(
        self,
        run_id: str,
        workflow_id: str,
        inputs: dict[str, Any],
        config: ResolvedConfig,
        event_emitter: EventEmitter,
    ) -> AdapterResult:
        """Execute workflow, emitting events."""
        ...
    
    async def test(self, workspace: Path) -> AdapterTestResult:
        """Test if adapter is available and functional."""
        ...
```

### Event Emission

Adapters MUST emit events in this order:

1. `RUN_STARTED` (seq 0) — before any execution
2. `STEP_STARTED` (seq N) — before each step
3. `STEP_COMPLETED` or `STEP_FAILED` (seq N+1) — after each step
4. `TEXT_MESSAGE_*` or `TOOL_CALL_*` — during step execution
5. `STATE_SNAPSHOT` — at meaningful state checkpoints
6. `RUN_COMPLETED` or `RUN_FAILED` — final event

### Error Handling

Adapters MUST:
- Catch all exceptions and emit `RUN_FAILED` with redacted error
- Never propagate exceptions to the supervisor
- Redact secrets from all output before returning
- Return structured `AdapterResult` (not raw exceptions)

```python
class AdapterResult(BaseModel):
    success: bool
    output: Optional[str] = None
    error: Optional[str] = None          # Redacted
    error_detail: Optional[str] = None   # Redacted
    events: list[RunEvent] = Field(default_factory=list)
    duration_ms: int = 0
```

## 7. Event Broker

### Contract

The event broker provides live event streaming and replay:

```python
class EventBroker:
    """Streams events live during execution, replays for completed runs."""
    
    def subscribe(self, run_id: str) -> EventSubscription:
        """Subscribe to events for a run."""
        ...
    
    def publish(self, run_id: str, event: RunEvent):
        """Publish event to all subscribers."""
        ...
    
    def close(self, run_id: str):
        """Signal end of events for a run."""
        ...
    
    async def replay(self, run_id: str) -> AsyncIterator[RunEvent]:
        """Replay events from stored trace."""
        ...
```

### Guarantees

1. **Ordering**: Events are delivered in sequence order
2. **Delivery**: All published events are delivered to all subscribers (best-effort)
3. **Completion**: `STREAM_END` is sent when no more events will arrive
4. **Replay**: Completed runs can be replayed from trace store
5. **No persistence**: The broker is in-memory only; events are persisted by the supervisor

### SSE Protocol

```
GET /api/runs/{run_id}/events

data: {"schema_version":1,"type":"RUN_STARTED","timestamp":"...","run_id":"...","sequence":0,"data":{...}}

data: {"schema_version":1,"type":"STEP_STARTED","timestamp":"...","run_id":"...","sequence":1,"data":{...}}

data: {"schema_version":1,"type":"RUN_COMPLETED","timestamp":"...","run_id":"...","sequence":5,"data":{...}}

data: {"type":"STREAM_END"}
```

## 8. Trace Store

### Contract

The trace store persists run records and events:

```python
class TraceStore(Protocol):
    """Interface for trace persistence."""
    
    def save(self, run: RunRecord) -> None:
        """Save or update a run record."""
        ...
    
    def load(self, run_id: str) -> Optional[RunRecord]:
        """Load a run record by ID."""
        ...
    
    def list_runs(
        self,
        status: Optional[RunStatus] = None,
        runtime: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[RunRecord]:
        """List run records with filtering."""
        ...
    
    def append_event(self, run_id: str, event: RunEvent) -> None:
        """Append event to streaming event log."""
        ...
    
    def delete(self, run_id: str) -> None:
        """Delete a run record and its trace file."""
        ...
```

### Dual-Write Guarantee

Every save operation writes to both:
1. **JSONL file**: `.arc/traces/{run_id}.jsonl` (canonical)
2. **SQLite index**: `.arc/arc.db` runs table (search index)

If SQLite write fails, JSONL is still valid. If JSONL write fails, the run is considered corrupted.

### Atomicity

JSONL writes use atomic rename:
```python
def save(self, run: RunRecord) -> None:
    path = self.trace_dir / f"{run.id}.jsonl"
    fd, tmp_path = tempfile.mkstemp(dir=self.trace_dir, suffix='.tmp')
    try:
        with os.fdopen(fd, 'w') as f:
            f.write(run.model_dump_json() + '\n')
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, path)
    except:
        os.unlink(tmp_path)
        raise
```

## 9. Audit Store

### Contract

The audit store persists HMAC-signed audit chains:

```python
class AuditStore(Protocol):
    """Interface for audit chain persistence."""
    
    def sign_and_append(
        self,
        run_id: str,
        action: str,
        data: dict,
        secret: str,
    ) -> AuditRecord:
        """Sign and append audit record to chain."""
        ...
    
    def verify_chain(self, run_id: str, secret: str) -> ChainVerificationResult:
        """Verify entire audit chain integrity."""
        ...
    
    def get_head_hash(self, run_id: str) -> Optional[str]:
        """Get current chain head hash."""
        ...
    
    def get_chain(self, run_id: str) -> list[AuditRecord]:
        """Get full audit chain."""
        ...
```

### Audit Points

Audit records are created at these points:

1. **Run start**: `action: "run_started"`, data: `{workflow_id, runtime, profile}`
2. **State transitions**: `action: "state_change"`, data: `{from, to}`
3. **Cancellation**: `action: "cancelled"`, data: `{reason}`
4. **Completion**: `action: "completed"`, data: `{duration_ms, output_hash}`
5. **Failure**: `action: "failed"`, data: `{error_hash}`
6. **HITL approval**: `action: "hitl_approved"`, data: `{reviewer, decision}`
7. **Verification**: `action: "verified"`, data: `{head_hash, record_count}`

## 10. HITL/Replay/Cancel

### HITL (Human-in-the-Loop)

```
1. Adapter emits HITL request event
2. Supervisor pauses execution
3. Event broker notifies IDE subscribers
4. IDE shows approval UI
5. User approves/denies
6. IDE sends decision to daemon
7. Daemon validates decision token
8. Supervisor resumes or aborts execution
9. Audit store records decision
```

### Replay

```
1. User selects run to replay
2. IDE requests replay from daemon
3. Daemon loads trace from store
4. Event broker replays events at original timing (or instant)
5. IDE renders events as they arrive
6. Checkpoint time-travel available for SwarmGraph runs
```

### Cancel

```
1. User requests cancellation
2. IDE sends POST /api/runs/{id}/cancel
3. Supervisor finds running task
4. Supervisor sends SIGTERM to subprocess
5. Supervisor waits 5 seconds
6. If still running, sends SIGKILL
7. Supervisor updates state: RUNNING → CANCELLING → CANCELLED
8. Event broker emits RUN_CANCELLED + STREAM_END
9. Audit store records cancellation
```

## Error Model

### Error Classification

| Category | Examples | Handling |
|----------|---------|----------|
| **InputError** | Invalid workflow_id, missing required input | Reject at validation, 400 response |
| **GatingError** | Paid calls not allowed, trust insufficient | Reject at gating, 403 response |
| **AdapterError** | Runtime not installed, CLI not found | Fail run, redacted error in trace |
| **ExecutionError** | Subprocess exit code != 0 | Fail run, capture stderr (redacted) |
| **TimeoutError** | Run exceeds timeout | Kill process, cancel run |
| **StoreError** | Disk full, permission denied | Fail run, log diagnostic |
| **SupervisorCrash** | Daemon killed mid-execution | Recover on restart, mark FAILED |

### Error Propagation

```
Adapter ──► AdapterResult (success=false, error=redacted)
    │
    ▼
Supervisor ──► RunRecord (status=FAILED, error_detail=redacted)
    │
    ▼
EventBroker ──► RUN_FAILED event (data.error=redacted)
    │
    ▼
IDE ──► Error display (user-safe message)
```

## Compatibility Matrix

### Version Compatibility

| Component | Version Contract | Breaking Change Policy |
|-----------|-----------------|----------------------|
| RunRequest | Schema version in metadata | Additive only; new fields optional |
| RunRecord | Schema version in metadata | N-1 compatibility |
| RunEvent | `schema_version` field | N-1 compatibility |
| AuditRecord | Part of SwarmGraph audit | SwarmGraph versioning |
| Config | `version` field in YAML | Backward compatible |
| SQLite schema | `_schema_version` table | Migration scripts |

### Adapter Compatibility

| Adapter | Runtime | Min Version | Max Version | Status |
|---------|---------|-------------|-------------|--------|
| SwarmGraph | swarmgraph | 0.8.0 | 0.9.x | Active |
| LangGraph | langgraph | 0.2.0 | TBD | Planned |
| CrewAI | crewai | 0.80.0 | TBD | Planned |
| AG2 | ag2 | 0.1.0 | TBD | Stub |
| OpenAI Agents | openai-agents | TBD | TBD | Stub |

## Implementation Priority

### Phase 0: Core Contract Foundation
1. Define RunRequest, ResolvedConfig, RunRecord schemas
2. Implement config loader (ADR-001)
3. Implement state machine transitions (ADR-002)
4. Wire SQLite index (ADR-003)
5. Add event schema versioning (ADR-004)

### Phase 1: Supervisor + Event Broker
1. Implement JobSupervisor
2. Implement EventBroker
3. Wire live SSE streaming
4. Implement orphan recovery
5. Implement targeted cancellation

### Phase 2: Isolation + Trust
1. Implement FilesystemPolicy
2. Implement NetworkPolicy
3. Implement IsolationProvider interface
4. Implement workspace trust resolution
5. Wire audit key management (ADR-005)

### Phase 3: Audit + HITL
1. Wire SwarmGraph audit chain to ARC
2. Implement audit verification endpoints
3. Implement HITL persistence
4. Implement replay with checkpoint support
5. IDE audit widget integration

## References
- All ADRs: `docs/adr/001-*.md` through `docs/adr/008-*.md`
- Current schemas: `python/src/agent_runtime_cockpit/protocol/schemas.py`
- Current adapters: `python/src/agent_runtime_cockpit/adapters/`
- Current storage: `python/src/agent_runtime_cockpit/storage/`
- Current security: `python/src/agent_runtime_cockpit/security/`
- Current gating: `python/src/agent_runtime_cockpit/gating.py`
- Node.js executor: `packages/arc-extension/src/node/services/workflow-executor.ts`
- Node.js trace parser: `packages/arc-extension/src/node/services/trace-parser.ts`
