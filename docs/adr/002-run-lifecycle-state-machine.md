# ADR-002: Run Lifecycle State Machine and Background Job Supervisor

## Status
Proposed

## Context

ARC Studio's current run lifecycle has critical gaps:
- `RunStatus` enum defines 5 states (`pending`, `running`, `completed`, `failed`, `cancelled`) but `RUNNING` is never persisted
- Runs transition synchronously from `PENDING` → `COMPLETED`/`FAILED` in storage
- No background job supervisor exists — runs are either awaited (Python daemon) or tracked in-memory (Node.js `runningProcesses` map)
- Cancellation is coarse-grained (kills all processes, not specific run IDs)
- No run state survives process restart
- No live event streaming — SSE endpoint replays stored JSONL after completion
- Run IDs in Node.js are tentative until CLI exits with definitive ID

This prevents background runs, reliable cancellation, crash recovery, and live progress monitoring.

## Decision

### Run Lifecycle State Machine

Define a formal state machine with explicit public run states and internal supervisor phases:

```
                    ┌─────────┐
                    │ PENDING │
                    └────┬────┘
                         │ start()
                         ▼
                    ┌─────────┐
              ┌─────│ RUNNING │─────┐
              │     └────┬────┘     │
              │          │          │
     cancel() │    error()│    complete()
              │          │          │
              ▼          ▼          ▼
        ┌──────────┐ ┌─────────┐ ┌──────────┐
        │CANCELLED │ │ FAILED  │ │COMPLETED │
        └──────────┘ └─────────┘ └──────────┘
             ▲           ▲
        phase│      phase│
     cancelling     failing
```

**States:**

| State | Description | Persisted | Terminal |
|-------|-------------|-----------|----------|
| `PENDING` | Run request accepted, not yet started | Yes | No |
| `RUNNING` | Execution in progress | Yes | No |
| `COMPLETED` | Finished successfully | Yes | Yes |
| `FAILED` | Execution failed | Yes | Yes |
| `CANCELLED` | Cancelled by user or timeout | Yes | Yes |
| `CANCELLING` | Internal supervisor phase, not public `RunStatus` | Metadata only | No |
| `FAILING` | Internal supervisor phase, not public `RunStatus` | Metadata only | No |

**Transitional supervisor phases** (`cancelling`, `failing`) exist to ensure:
- Cancellation is observable (user sees "cancelling..." not stuck "running")
- Failure diagnostics are captured before final state
- Crash recovery can distinguish "was cancelling" from "was running"

### RunRecord Schema Update

Extend `RunRecord` with supervisor fields:

```python
class RunRecord(BaseModel):
    id: str
    workflow_id: str
    runtime: str
    status: RunStatus
    started_at: str
    ended_at: Optional[str] = None
    events: list[RunEvent] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    
    # New supervisor fields
    pid: Optional[int] = None              # Subprocess PID (for cancellation)
    isolation: str = "none"                # Isolation provider used
    profile_id: str = "stub"               # Security profile
    trace_path: Optional[str] = None       # Absolute path to trace file
    audit_path: Optional[str] = None       # Absolute path to audit chain
    cancel_reason: Optional[str] = None    # Why cancelled (user/timeout/crash)
    error_detail: Optional[str] = None     # Failure diagnostics (redacted)
    supervisor_id: Optional[str] = None    # Which supervisor owns this run
    heartbeat_at: Optional[str] = None     # Last supervisor heartbeat
    supervisor_phase: Optional[str] = None # cancelling/failing/etc.; not public status
```

### Background Job Supervisor

Create a `JobSupervisor` that manages background runs:

```python
class JobSupervisor:
    """Manages background run execution with persistence and recovery."""
    
    def __init__(self, store: SqliteStore, trace_store: JsonlTraceStore):
        self.store = store
        self.trace_store = trace_store
        self.running: dict[str, asyncio.Task] = {}
    
    async def start_run(self, request: RunRequest) -> RunRecord:
        """Start a run in the background, return immediately with PENDING record."""
        run = RunRecord(
            id=generate_run_id(request.runtime),
            status=RunStatus.PENDING,
            workflow_id=request.workflow_id,
            runtime=request.runtime,
            started_at=now(),
            supervisor_id=self.supervisor_id,
        )
        self.trace_store.save(run)
        self.store.insert_run(run)
        
        task = asyncio.create_task(self._execute_run(run, request))
        self.running[run.id] = task
        
        return run
    
    async def _execute_run(self, run: RunRecord, request: RunRequest):
        """Execute run, updating state at each transition."""
        # PENDING → RUNNING
        run.status = RunStatus.RUNNING
        run.heartbeat_at = now()
        self.trace_store.save(run)
        self.store.update_run_status(run.id, RunStatus.RUNNING)
        
        try:
            # Execute via isolation provider
            result = await self._run_with_isolation(run, request)
            
            # RUNNING → COMPLETED
            run.status = RunStatus.COMPLETED
            run.ended_at = now()
            run.events = result.events
            self.trace_store.save(run)
            self.store.update_run_status(run.id, RunStatus.COMPLETED)
            
        except asyncio.CancelledError:
            # RUNNING → CANCELLED, with internal cancelling phase
            run.supervisor_phase = "cancelling"
            self.trace_store.save(run)
            
            # Kill subprocess
            if run.pid:
                await self._kill_process(run.pid)
            
            run.status = RunStatus.CANCELLED
            run.ended_at = now()
            run.cancel_reason = request.cancel_reason or "user_requested"
            self.trace_store.save(run)
            self.store.update_run_status(run.id, RunStatus.CANCELLED)
            
        except Exception as e:
            # RUNNING → FAILED, with internal failing phase
            run.supervisor_phase = "failing"
            self.trace_store.save(run)
            
            run.status = RunStatus.FAILED
            run.ended_at = now()
            run.error_detail = redact_error(str(e))
            self.trace_store.save(run)
            self.store.update_run_status(run.id, RunStatus.FAILED)
            
        finally:
            self.running.pop(run.id, None)
    
    async def cancel_run(self, run_id: str, reason: str = "user_requested") -> bool:
        """Cancel a specific run by ID."""
        task = self.running.get(run_id)
        if not task:
            return False
        
        task.cancel()  # Triggers CancelledError in _execute_run
        return True
    
    async def recover_orphaned_runs(self):
        """On startup, find RUNNING runs with no active supervisor and mark FAILED."""
        orphaned = self.store.get_runs_by_status(RunStatus.RUNNING)
        for run in orphaned:
            if run.supervisor_id != self.supervisor_id:
                run.status = RunStatus.FAILED
                run.error_detail = "supervisor_crash"
                run.ended_at = now()
                self.trace_store.save(run)
                self.store.update_run_status(run.id, RunStatus.FAILED)
```

### Cancellation Semantics

1. **User cancellation**: `POST /api/runs/{id}/cancel` → supervisor sends SIGTERM → waits 5s → SIGKILL → state: `CANCELLED`
2. **Timeout cancellation**: Supervisor timer fires → same as user cancellation → `cancel_reason: "timeout"`
3. **Supervisor crash**: On restart, `recover_orphaned_runs()` marks orphaned `RUNNING` runs as `FAILED` with `error_detail: "supervisor_crash"`
4. **Graceful shutdown**: Supervisor cancels all running tasks, waits for cleanup, then exits

### Live Event Streaming

Replace replay-only SSE with a live event broker:

```python
class EventBroker:
    """Streams events live during execution, falls back to replay for completed runs."""
    
    def __init__(self):
        self.subscribers: dict[str, list[asyncio.Queue]] = {}
    
    def subscribe(self, run_id: str) -> asyncio.Queue:
        """Subscribe to live events for a run. Returns queue of events."""
        queue = asyncio.Queue()
        self.subscribers.setdefault(run_id, []).append(queue)
        return queue
    
    def publish(self, run_id: str, event: RunEvent):
        """Publish event to all subscribers."""
        for queue in self.subscribers.get(run_id, []):
            queue.put_nowait(event)
    
    def unsubscribe(self, run_id: str, queue: asyncio.Queue):
        """Remove subscriber."""
        if run_id in self.subscribers:
            self.subscribers[run_id].remove(queue)
```

SSE endpoint checks run status:
- `RUNNING` → subscribe to EventBroker, stream live events
- `COMPLETED`/`FAILED`/`CANCELLED` → replay from JSONL (current behavior)

### Node.js Integration

The TypeScript `WorkflowExecutor` will:
1. Call `POST /api/runs/start` (daemon path) for background execution
2. Receive `PENDING` run record immediately
3. Subscribe to SSE for live events
4. Use `POST /api/runs/{id}/cancel` for targeted cancellation

The in-memory `runningProcesses` map is retained only for the direct subprocess fallback path (no daemon).

## Consequences

### Positive
- Runs survive process restarts (orphaned runs detected and marked failed)
- Targeted cancellation by run ID (not kill-all)
- Live event streaming enables real-time progress monitoring
- Clear state machine prevents ambiguous states
- Background execution enables long-running workflows

### Negative
- Adds complexity (supervisor, event broker, state persistence)
- SQLite writes on every state transition (minor I/O overhead)
- Transitional states require careful error handling

### Neutral
- Synchronous CLI path still works (daemon wraps it in supervisor)
- JSONL remains the canonical trace store; SQLite is an index
- Event broker is in-memory only (not persisted across restarts)

## References
- Current RunStatus: `python/src/agent_runtime_cockpit/protocol/schemas.py:101-106`
- Current RunRecord: `python/src/agent_runtime_cockpit/protocol/schemas.py:117-125`
- Node.js process tracking: `packages/arc-extension/src/node/services/workflow-executor.ts:49`
- SSE replay: `python/src/agent_runtime_cockpit/web/routes.py:352-381`
- Current cancellation: `packages/arc-extension/src/node/services/workflow-executor.ts:157-184`
