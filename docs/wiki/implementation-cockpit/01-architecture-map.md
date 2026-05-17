# 01 — Architecture Map

## System Layers

```
┌─────────────────────────────────────────────────────────────────┐
│                     Python Backend (daemon + CLI)                 │
│                                                                   │
│  CLI:     cli.py (2426) — typer app, 79+ commands               │
│                                                                   │
│  Web:     web/server.py — aiohttp daemon                        │
│           web/routes.py (637) — 33 route handlers               │
│                                                                   │
│  Core:    orchestration/event_broker.py — EventBroker (196)     │
│           orchestration/supervisor.py — JobSupervisor (277)     │
│           orchestration/runtime_router.py — RuntimeRouter (214) │
│                                                                   │
│  Store:   storage/jsonl.py — JsonlTraceStore (94)               │
│           storage/sqlite.py — SqliteStore (240, ADR-003)        │
│           storage/indexed_store.py — IndexedTraceStore (139)     │
│                                                                   │
│  Security: security/trust.py — TrustResolver (191)              │
│            security/redaction.py — Redactor (53)                 │
│            security/profiles.py — RunProfile (78)               │
│            security/validation.py — input validation (39)       │
│                                                                   │
│  Audit:   audit/hmac_chain.py — HmacAuditChainWriter (92)      │
│           audit/key_manager.py — AuditKeyManager (121)          │
│           audit/hitl.py — HitlPrompt/HitlResponse (51)           │
│           audit/hitl_store.py — HITL persistence (127)          │
│           audit/permissions.py — permission logging (43)        │
│                                                                   │
│  Config:  config/model.py — ArcConfig (122, ADR-001)           │
│           config/loader.py — load_config() (238)                │
│                                                                   │
│  Isolation: isolation/base.py — IsolationProvider ABC (64)     │
│             isolation/none.py — NoneIsolationProvider (70)      │
│             isolation/subprocess.py — SubprocessIsol. (154)     │
│             isolation/docker_provider.py — DockerIsol. (163)    │
│                                                                   │
│  Adapters: adapters/base.py — RuntimeAdapter ABC (140)          │
│            adapters/registry.py — AdapterRegistry (110)          │
│            adapters/swarmgraph.py + langgraph.py + crewai.py    │
│            adapters/openai_agents.py + ag2_adapter.py           │
│            adapters/llamaindex.py + lmarena.py                   │
│                                                                   │
│  Protocol: protocol/schemas.py — RunRecord, RunEvent (148)      │
│            protocol/events.py — EVENT_TYPES registry (237)      │
│            protocol/capabilities.py — RuntimeCapabilities (83)  │
│            protocol/envelope.py — ArcEnvelope, ok(), err() (63) │
│            protocol/errors.py — ArcErrorCode (19)               │
│                                                                   │
│  Eval:     evals/golden.py (116), evals/diff.py (80)           │
│  Context:  context/engine.py, pack.py, cache.py, ranker.py      │
│  Tracing:  tracing/jsonl_writer.py                              │
│  Extensions: extensions/base.py, registry.py                   │
└──────────────────────┬──────────────────────────────────────────┘
                       │ SSE + HTTP (aiohttp, port 9876)
┌──────────────────────▼──────────────────────────────────────────┐
│              TypeScript Theia Backend (Node.js)                   │
│                                                                   │
│  packages/arc-extension/src/node/:                               │
│    arc-backend-service.ts (374) — ArcBackendService              │
│    services/workflow-executor.ts (475) — WorkflowExecutor        │
│    services/trace-parser.ts (325) — TraceParser                  │
│    services/workflow-detector.ts (293) — WorkflowDetector        │
│    services/file-manager.ts (134) — FileManager                  │
│    security-utils.ts (156) — sanitization/validation             │
│    health-endpoint.ts (75) — ArcHealthEndpoint                   │
│    metrics-endpoint.ts (29) — ArcMetricsEndpoint                 │
│    arc-extension-backend-module.ts (38) — DI bindings            │
│                                                                   │
│  theia-extensions/arc-core/src/node/:                            │
│    arc-service-impl.ts — ArcServiceImpl                          │
│                                                                   │
│  theia-extensions/arc-core/src/common/:                          │
│    arc-protocol.ts (276) — ArcEnvelope, ArcService interface     │
│                                                                   │
│  packages/arc-protocol-ts/src/:                                  │
│    arc-protocol-types.ts (163) — standalone protocol types       │
└──────────────────────┬──────────────────────────────────────────┘
                       │ JSON-RPC (Theia IPC)
┌──────────────────────▼──────────────────────────────────────────┐
│              TypeScript Theia Frontend (React)                    │
│                                                                   │
│  packages/arc-extension/src/browser/:                            │
│    arc-widget.tsx (554) — ArcWidget (main cockpit widget)        │
│    arc-widget-contribution.ts (123) — ArcWidgetContribution      │
│    arc-keybinding-contribution.ts (46) — keybindings             │
│    arc-adapters-widget.tsx (245) — runtime adapters status       │
│    arc-event-stream-widget.tsx (183) — trace-backed event viewer │
│    arc-run-timeline-widget.tsx (168) — timeline visualization    │
│    arc-workflow-graph-widget.tsx (225) — SVG graph viz           │
│    components/ (8 files) — ProgressBar, ToastContainer,          │
│      ShortcutsModal, ExecutionSteps, ErrorBanner,                │
│      WorkflowExecutionSection, TraceViewerSection,               │
│      WorkflowDetectionSection                                    │
│    arc-extension-frontend-module.ts (76) — DI bindings            │
│                                                                   │
│  theia-extensions/ (11 extension dirs):                          │
│    arc-adapters, arc-arena, arc-audit, arc-context,              │
│    arc-event-stream, arc-health, arc-product, arc-runs,          │
│    arc-schemas, arc-settings, arc-workflows                      │
│                                                                   │
│  packages/arc-ag-ui/src/:                                        │
│    event-types.ts (40) — AGUIEventType enum (34 types)           │
│    mapper.ts (56) — RuntimeEventMapper, REGISTRY                 │
│    redaction.ts (49) — secret redaction + payload capping        │
│    mapping/swarmgraph.ts (54) — SwarmGraphMapper                 │
│    mapping/langgraph.ts (57) — LangGraphMapper                   │
└──────────────────────────────────────────────────────────────────┘
```

## 1. Run Records

### Python — `protocol/schemas.py:118-128`

```python
class RunRecord(BaseModel):
    id: str
    workflow_id: str
    runtime: str
    status: RunStatus  # PENDING/RUNNING/COMPLETED/FAILED/CANCELLED
    started_at: str    # ISO-8601
    ended_at: Optional[str]
    events: list[RunEvent]
    metadata: dict[str, Any]
    audit_path: Optional[str]  # path to HMAC chain file
```

- **RunRecord** is the **canonical** data model. JSONL store persists it as single-line JSON.
- **RunStatus** enum: `PENDING → RUNNING → COMPLETED` (or `FAILED`, `CANCELLED`)
- `RunEvent` at `schemas.py:109-116`: `schema_version`, `type`, `timestamp`, `run_id`, `sequence`, `data`

### TypeScript — `arc-protocol.ts:137-146`

```typescript
interface RunRecord {
  id: string; workflow_id: string; runtime: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';
  started_at: string; ended_at?: string;
  events: RunEvent[]; metadata: Record<string, unknown>;
}
```

### Persistence flow:
1. `JobSupervisor.start_run()` — creates `RunRecord`, calls `jsonl.save()`
2. Adapter's `run_workflow()` — returns completed `RunRecord`
3. `IndexedTraceStore.save()` — atomic JSONL write + SQLite best-effort

### Tests:
- `python/tests/test_storage.py` — 20 storage tests
- `python/tests/test_cli_storage.py` — 5 CLI storage tests
- `packages/arc-extension/src/node/__tests__/arc-service.integration.test.ts` — 839 lines

---

## 2. JSONL Trace Store

**File:** `python/src/agent_runtime_cockpit/storage/jsonl.py` (94 lines)

### `JsonlTraceStore` class
| Method | Line | Description |
|--------|------|-------------|
| `__init__(base_dir)` | 18 | Default: `.arc/traces/` |
| `save(run)` | 29 | Thread-safe, single-line `run.model_dump_json()` |
| `load(run_id)` | 41 | Reads first line, validates via `RunRecord.model_validate()` |
| `list_runs()` | 53 | Globs `*.jsonl`, sorted by mtime descending |
| `prune(keep, dry_run, older_than_days)` | 60 | Deletes oldest beyond `keep` |
| `append_event(run_id, event)` | 86 | Streaming mode: appends to `{run_id}-events.jsonl` |
| `trace_path(run_id)` | 25 | Returns `base_dir / {run_id}.jsonl` |

**Storage format:** One JSON line per file: `{"id":"run-abc", "workflow_id":"...", ...}`

### Thread safety:
- `threading.Lock` for `save()` and `append_event()`
- `IndexedTraceStore.save()` uses temp-file + fsync + `os.replace()` for atomicity

### Extension points:
- `base_dir` is configurable per-workspace
- JSONL is the **canonical** store; SQLite is disposable index

---

## 3. SQLite Index

**File:** `python/src/agent_runtime_cockpit/storage/sqlite.py` (240 lines)

### `SqliteStore` class — Schema (ADR-003)

**Table: `runs`**
```
id TEXT PK, workflow_id, runtime, status, started_at, ended_at,
duration_ms, profile_id, isolation, supervisor_id, cancel_reason,
error_detail, trace_path, audit_path, metadata (JSON),
created_at, updated_at
```
Indices: `status`, `runtime`, `workflow_id`, `started_at`, `supervisor_id`

**Table: `audit_log`**
```
id PK, run_id FK, timestamp, action, actor, details, verified
```

**Table: `_schema_version`** — migration tracking

### Key methods:
| Method | Line | Description |
|--------|------|-------------|
| `init_db()` | 67 | Idempotent table creation |
| `insert_run(...)` | 86 | INSERT OR REPLACE |
| `update_run_status(...)` | 127 | Status + ended_at + duration |
| `update_run_audit_path(...)` | 150 | Set audit_path after completion |
| `get_run(run_id)` | 170 | Returns dict row |
| `list_runs(status?, runtime?, workflow_id?, limit, offset)` | 184 | Filtered listing |
| `delete_run(run_id)` | 161 | Cascade deletes audit_log |
| `count_runs()` | 220 | Total count |
| `run_exists(run_id)` | 230 | Existence check |
| `insert_audit_log(...)` | — | Not yet exposed (called from `indexed_store.py`?) |

### Risk: SQLite is best-effort only; all failures logged but not raised. JSONL is canonical.

### Tests: via `test_storage.py` (20 tests)

---

## 4. Event Broker / SSE

**File:** `python/src/agent_runtime_cockpit/orchestration/event_broker.py` (196 lines)

### `EventBroker` class
| Method | Line | Description |
|--------|------|-------------|
| `publish(run_id, event) → event_id` | 37 | Pub to queues; drop-oldest on QueueFull |
| `subscribe(run_id) → Queue` | 54 | maxsize=1000 |
| `unsubscribe(run_id, queue)` | 60 | |
| `end_run(run_id)` | 66 | Push `None` to all subscribers |
| `stream_live(run_id, last_event_id)` | 71 | Replay missed + subscribe live |
| `sse_handler(request) → StreamResponse` | 125 | HTTP SSE, `mode=live|replay` |
| `_send_heartbeats(response)` | 188 | 15-second heartbeat interval |

### Internal state:
- `_subscribers: dict[str, list[Queue]]`
- `_event_ids: dict[str, int]` — monotonic per-run event counter

### SSE format:
```
event: RUN_STARTED
id: 1
data: {"type":"RUN_STARTED",...}
```

### 30 event type registry (`protocol/events.py:36-184`):
Lifecycle: `RUN_STARTED`, `RUN_COMPLETED`, `RUN_FAILED`, `RUN_CANCELLED`
Steps: `STEP_STARTED`, `STEP_COMPLETED`, `STEP_FAILED`
Agents: `AGENT_START`, `AGENT_END`
Tools: `TOOL_CALL`, `TOOL_CALL_START/ARGS/END/RESULT/ERROR`, `TOOL_END`
Handoffs: `HANDOFF`
Messages: `MESSAGE`, `MESSAGE_CHUNK`, `TEXT_MESSAGE_START/CONTENT/END/CHUNK`
State: `STATE_SNAPSHOT`
HITL: `HITL_PROMPT`, `HITL_RESPONSE`, `HITL_TIMEOUT`
Node: `NODE_STARTED`, `NODE_UPDATE`, `NODE_FAILED`
Fallback: `RAW`, `CUSTOM`

### Web routes serving SSE:
- `routes.py:398` — `/api/runs/{run_id}/events` — replay stored events as SSE
- `routes.py:352` — `/api/sse/proof` — manual SSE proof endpoint

### Tests:
- `python/tests/orchestration/test_event_broker.py`
- `python/tests/web/test_sse_proof.py`
- `python/tests/web/test_runs_sse.py`
- `python/tests/test_sse_resilience.py`

---

## 5. Supervisor

**File:** `python/src/agent_runtime_cockpit/orchestration/supervisor.py` (277 lines)

### `RunRequest` model (line 29):
```
workflow_id, runtime?, inputs, prompt?, profile_id, timeout_seconds,
metadata, workspace_root?, workspace_trust_db?
```

### `ActiveRun` dataclass (line 48):
```
run_id, task (asyncio.Task), cancelled (bool)
```

### `JobSupervisor` class (line 64):
| Method | Line | Description |
|--------|------|-------------|
| `__init__(store, broker?)` | 71 | Takes JsonlTraceStore |
| `start_run(request, executor_fn) → RunRecord` | 82 | Creates run, enforces trust, spawns task |
| `_execute_run(run_id, request, executor_fn)` | 124 | Emits lifecycle events via broker |
| `cancel_run(run_id) → bool` | 188 | Cancels asyncio task |
| `recover_orphans() → int` | 201 | Marks RUNNING → FAILED (supervisor restart) |
| `get_active_run(run_id)` | 214 | |
| `request_hitl(prompt)` | 218 | Emits HITL_PROMPT, waits with timeout |
| `respond_hitl(response)` | 250 | Resolves pending Future |
| `pending_hitl(run_id?)` | 265 | List pending HITL |

### Internal state:
- `_active_runs: dict[str, ActiveRun]`
- `_sequence_counters: dict[str, int]`
- `_pending_hitl: dict[str, Future[HitlResponse]]`

### Risks:
- No persistence of active runs across daemon restart (recover_orphans only marks FAILED)
- `executor_fn` is injected — no lifecycle hooks for RunContract/EvidenceRef

### Tests: `python/tests/orchestration/test_supervisor.py`

---

## 6. HITL

### Models — `audit/hitl.py` (51 lines)

| Model | Line | Fields |
|-------|------|--------|
| `HitlDecision` (enum) | 11 | `APPROVE`, `REJECT`, `MODIFY`, `SKIP` |
| `HitlPrompt` | 18 | `hitl_id, run_id, step_id, prompt_text, context, options, timeout_seconds, created_at` |
| `HitlResponse` | 30 | `hitl_id, run_id, decision, operator_id, modified_data, notes, responded_at` |
| `HitlResponse.to_audit_event()` | 40 | Converts to audit-signable dict |

### Persistence — `audit/hitl_store.py` (127 lines)

| Function | Line | Description |
|----------|------|-------------|
| `save_prompt(workspace, prompt, expiry)` | 28 | Saves with UUID token + expiry |
| `list_prompts(workspace, include_expired)` | 43 | Lists non-responded prompts |
| `respond(workspace, hitl_id, decision, token, notes)` | 78 | Single-use token validation |
| `get_token(workspace, hitl_id)` | 107 | Return token for pending prompt |
| `prune_expired(workspace)` | 115 | Remove expired |

### Storage layout:
- `.arc/hitl/pending/{hitl_id}.json`
- `.arc/hitl/responded/{hitl_id}.json`

### Events in registry: `HITL_PROMPT`, `HITL_RESPONSE`, `HITL_TIMEOUT`

### CLI commands:
- `arc hitl pending` — list pending prompts
- `arc hitl respond --decision --token` — respond with single-use token
- `arc hitl approve --token` / `arc hitl reject --token`

### Risks:
- Single-use tokens only protect against replay in the same session
- No web UI for HITL response yet (CLI only)

### Tests: `python/tests/audit/test_hitl.py` (6 tests)

---

## 7. Audit / HMAC

### HMAC Chain — `audit/hmac_chain.py` (92 lines)

| Class/Function | Line | Description |
|----------------|------|-------------|
| `HmacAuditChainWriter` | 16 | Append-only HMAC-authenticated chain |
| `__init__(path, key_manager)` | 24 | Loads tail state from existing file |
| `append(event) → record` | 40 | Signs with HMAC-SHA256, writes record |
| `verify_hmac_chain(chain_path, key)` | 63 | Walks chain, verifies each signature |

### Record format:
```json
{"seq":0,"event":{...},"prev_hash":"GENESIS","record_hash":"sha256","signature":"hmac","key_source":"keychain"}
```

### Key Manager — `audit/key_manager.py` (121 lines)

| Method | Line | Description |
|--------|------|-------------|
| `get_key() → (bytes, AuditKeyStatus)` | 36 | Keychain → env fallback |
| `set_key(key)` | 61 | Store in keychain |
| `delete_key()` | 73 | Delete from keychain |
| `generate_key()` | 85 | 32 random bytes, hex-encoded |
| `sign_audit_record(data, key, prev_hash)` | 101 | SHA-256(JSON) + HMAC-SHA256 |
| `verify_audit_signature(data, sig, key, prev_hash)` | 116 | Constant-time compare |

### Permission audit — `audit/permissions.py` (43 lines)
- `log_permission_decision()` — appends to `permissions.audit.jsonl`

### CLI:
- `arc audit verify <run_id>` — verify HMAC chain
- `arc audit export <run_id>` — export audit records
- `arc audit key init/show/delete`

### Tests: `python/tests/audit/test_hmac_chain.py`

---

## 8. Trust Resolver

**File:** `python/src/agent_runtime_cockpit/security/trust.py` (191 lines)

### Key functions:
| Function | Line | Description |
|----------|------|-------------|
| `resolve_trust(workspace, trust_db)` | 60 | Advisory check → `TrustResolution` |
| `trust_workspace(workspace, note, trust_db)` | 96 | Add to external DB |
| `untrust_workspace(workspace, trust_db)` | 128 | Remove from DB |
| `list_trusted(trust_db)` | 151 | List all trusted |
| `ensure_trusted(workspace, trust_db, allow_if_no_db)` | 159 | Raises `WorkspaceUntrusted` |

### Models:
- `TrustLevel`: `UNTRUSTED`, `PARTIAL`, `TRUSTED`
- `TrustResolution`: `level, reason, marker_path, warning`
- `WorkspaceUntrusted(Exception)` with `workspace_path` and `reason`

### External DB: `~/.arc/trusted-workspaces.json`

### Enforcement point:
- Called by `JobSupervisor.start_run()` at line 96 before execution

### Tests: `python/tests/test_trust_resolver.py`

---

## 9. Config / Policy

### Config Model — `config/model.py` (122 lines)

`ArcConfig` (line 87) contains:
| Sub-model | Line | Purpose |
|-----------|------|---------|
| `WorkspaceConfig` | 9 | `name, trust_level` |
| `RuntimeConfig` | 15 | `default, auto_detect, fallback` |
| `ExecutionConfig` | 22 | `isolation, default_profile, timeout_seconds, allow_paid_calls, background` |
| `ProviderConfig` | 31 | `default_provider, default_model, routing_mode, dry_run, accounts` |
| `SwarmGraphConfig` | 40 | `provider, base_url, run_backend, cli_path` |
| `LangGraphConfig` | 48 | `export` |
| `CrewAIConfig` | 53 | `export` |
| `ContextConfig` | 58 | `search_provider, context7_api_key_env, github_token_env` |
| `TelemetryConfig` | 65 | `otel_endpoint, otel_genai_experimental` |
| `UIConfig` | 71 | `show_mock_warnings, compact_sidebar, auto_open_sidebar` |
| `SecurityConfig` | 78 | `redact_secrets, audit_enabled, audit_secret_env, allowed_paths, allowed_hosts` |

### Config Loader — `config/loader.py` (238 lines)

**Precedence (highest wins):**
1. CLI arguments (caller overrides)
2. Environment variables (`ARC_*`)
3. Workspace config (`.arc/config.yaml`)
4. User config (`~/.arc/config.yaml`)
5. Built-in defaults

### Run Profiles — `security/profiles.py` (78 lines)

| Built-in | Backend | Network | Paid |
|----------|---------|---------|------|
| `stub` | STUB | ✗ | ✗ |
| `local-safe` | STUB | ✓ | ✗ |
| `local-paid` | LOCAL | ✓ | ✓ |
| `gateway` | GATEWAY | ✓ | ✓ |

`enforce_profile()` gated by `require_dual_gate()` which checks `ARC_<RUNTIME>_ALLOW_COSTS`.

### Tests:
- `python/tests/test_config.py` — 14 config tests
- `python/tests/security/test_profiles.py`

---

## 10. CLI Command Structure

**File:** `python/src/agent_runtime_cockpit/cli.py` (2426 lines)

Built with `typer`. Complete tree:

```
arc
├── version              Print version
├── health               Daemon + env health
├── status               Workspace + runtime status
├── inspect              Inspect workspace
├── runtimes             List runtimes (--capabilities)
├── workflows            List workflows
├── schemas              List schemas
├── serve                Start daemon
├── run                  Execute workflow
├── bug-report           Collect diagnostics
├── runs
│   ├── (list)           List stored runs
│   ├── prune            Delete old traces
│   ├── get              Load one run
│   ├── diff             Compare two runs
│   ├── trace            Inspect trace file
│   ├── status           Show run status
│   ├── delete           Delete run + trace
│   ├── export           Export as JSON
│   ├── import           Import JSON
│   ├── replay           Replay stored events
│   ├── backfill         SQLite from JSONL
│   └── search           SQLite search
├── eval
│   ├── run              Evaluate vs golden (--batch)
│   ├── save             Save golden trace
│   ├── delete           Delete golden
│   ├── report           Golden inventory
│   └── list             List goldens
├── providers
│   ├── list             List definitions
│   ├── status           Env presence
│   ├── diagnostics      Redacted diagnostics
│   ├── proxy            Dry-run proxy
│   ├── accounts list/add/disable/delete
│   ├── quota show/reset
│   └── routing get/set
├── doctor
│   ├── swarmgraph       Check SwarmGraph CLI
│   ├── all              All diagnostic checks
│   ├── env              Environment vars
│   ├── network          Network connectivity
│   └── storage          Storage health
├── workspace
│   ├── trust-status     Show trust status
│   ├── trust            Mark trusted
│   ├── untrust          Remove trust
│   ├── init             Init ARC config
│   ├── info             Show workspace info
│   └── config           Show/update config
├── isolation
│   ├── status           Provider health
│   ├── doctor           Diagnostics
│   ├── list             List providers
│   ├── setup            Setup (docker)
│   └── test             Test with echo
├── config
│   ├── init             Generate config
│   └── show             Show resolved config
├── hitl
│   ├── pending          List pending
│   ├── respond          Respond with token
│   ├── approve          Approve shortcut
│   └── reject           Reject shortcut
├── storage
│   ├── vacuum           Vacuum SQLite
│   └── status           Usage stats
├── audit
│   ├── verify           Verify HMAC chain
│   ├── export           Export audit records
│   ├── key init         Generate + store key
│   ├── key show         Show key status
│   └── key delete       Delete key
├── context
│   └── pack             Generate context pack
├── adapter
│   ├── test             Run conformance
│   └── list             List adapters
├── profiles
│   ├── list             List profiles
│   └── show             Show profile detail
└── prompt
    ├── optimize          Rule-based optimization
    └── diff              Compare two prompts
```

### Tests:
- `python/tests/cli/test_cli_smoke.py`
- `python/tests/cli/test_cli_runs.py`
- `python/tests/cli/test_cli_discoverability.py`
- `python/tests/cli/test_cli_error_paths.py`
- `python/tests/cli/test_cli_eval.py`
- `python/tests/test_cli_storage.py`
- `python/tests/test_cli_doctor.py`
- `python/tests/test_cli_providers.py`
- `python/tests/test_cli_profiles_workspace.py`
- `python/tests/test_cli_run_gating.py`

---

## 11. Theia Frontend Widgets / Services

### Main Widget — `arc-widget.tsx` (554 lines)
- `ArcWidget` (line 53): `@injectable`, extends `ReactWidget`
- `ArcWidgetState` (lines 24-50): `isExecuting, executionStatus, executionProgress, executionSteps, traceFilter, toasts, isCollapsed, showShortcutsHelp`
- Methods: `handleExecuteWorkflow()` (239), `handleLoadTraces()` (340), `handleScanWorkspace()` (392)

### Specialized widgets (ported from legacy extensions):

| Widget | File | Lines | ID | Description |
|--------|------|-------|----|-------------|
| `ArcAdaptersWidget` | `arc-adapters-widget.tsx` | 245 | `arc:adapters-status` | Runtime readiness cards |
| `ArcEventStreamWidget` | `arc-event-stream-widget.tsx` | 183 | `arc:event-stream` | Trace-backed event viewer (NOT live SSE) |
| `ArcRunTimelineWidget` | `arc-run-timeline-widget.tsx` | 168 | `arc:run-timeline` | Timeline viz with vertical event bars |
| `ArcWorkflowGraphWidget` | `arc-workflow-graph-widget.tsx` | 225 | `arc:workflow-graph` | SVG-based workflow graph |

### Reusable components (`components/`):
| Component | File | Lines |
|-----------|------|-------|
| `ProgressBar` | `ProgressBar.tsx` | 23 |
| `ToastContainer` | `ToastContainer.tsx` | 49 |
| `ShortcutsModal` | `ShortcutsModal.tsx` | 83 |
| `ExecutionSteps` | `ExecutionSteps.tsx` | 44 |
| `ErrorBanner` | `ErrorBanner.tsx` | 49 |
| `WorkflowExecutionSection` | `WorkflowExecutionSection.tsx` | 142 |
| `TraceViewerSection` | `TraceViewerSection.tsx` | 154 |
| `WorkflowDetectionSection` | `WorkflowDetectionSection.tsx` | 100 |

### Frontend DI (arc-extension-frontend-module.ts — 76 lines):

| Binding | Strategy |
|---------|----------|
| `ArcService` → WebSocket proxy | `toDynamicValue` |
| `ArcWidget` | `toSelf` + `WidgetFactory` |
| `ArcAdaptersWidget` | `toSelf` + `WidgetFactory` |
| `ArcWorkflowGraphWidget` | `toSelf` + `WidgetFactory` |
| `ArcRunTimelineWidget` | `toSelf` + `WidgetFactory` |
| `ArcEventStreamWidget` | `toSelf` + `WidgetFactory` |

### Backend DI (arc-extension-backend-module.ts — 38 lines):

| Binding | Strategy |
|---------|----------|
| `WorkflowExecutor` | `toSelf` singleton |
| `TraceParser` | `toSelf` singleton |
| `WorkflowDetector` | `toSelf` singleton |
| `FileManager` | `toSelf` singleton |
| `ArcBackendService` | `toDynamicValue` (explicit DI) |

### Theia extensions (legacy, being ported):

| Extension | Widget | Contribution |
|-----------|--------|-------------|
| `arc-adapters` | (ported) | `ArcAdaptersContribution` |
| `arc-arena` | Arena widget | `ArcArenaContribution` |
| `arc-audit` | Audit view | `ArcAuditContribution` |
| `arc-context` | Context panel | `ArcContextContribution` |
| `arc-event-stream` | (ported) | `ArcEventStreamContribution` |
| `arc-health` | Health dashboard | (contribution) |
| `arc-runs` | (ported) | `ArcRunsContribution` |
| `arc-schemas` | Schema inspector | `ArcSchemasContribution` |
| `arc-workflows` | (ported) | `ArcWorkflowContribution` |
| `arc-core` | Welcome page, commands, status bar | `ArcFrontendService` |

### AG-UI package (`packages/arc-ag-ui/`):
- `event-types.ts`: 34 event types including chunked variants
- `mapper.ts`: `RuntimeEventMapper` interface + registry
- `mapping/swarmgraph.ts`: SwarmGraph → AG-UI event mapping
- `mapping/langgraph.ts`: LangGraph → AG-UI event mapping
- `redaction.ts`: Secret redaction + payload capping (64KB max)

### Tests:
- `packages/arc-extension/src/node/__tests__/services.unit.test.ts` — 588 lines
- `packages/arc-extension/src/node/__tests__/security-utils.test.ts` — 206 lines
- `packages/arc-extension/src/node/__tests__/arc-service.integration.test.ts` — 839 lines
- `packages/arc-extension/src/browser/__tests__/arc-service.proxy.test.ts` — 294 lines
- `packages/arc-extension/src/browser/__tests__/arc-widget.integration.test.ts` — 621 lines
- `packages/arc-extension/src/browser/__tests__/ui-components.contract.test.ts` — 495 lines
- `packages/arc-ag-ui/test/mapping.test.js` — 54 lines
- `packages/arc-ag-ui/test/redaction.test.js` — 31 lines
- `packages/arc-ag-ui/test/performance.test.js` — 99 lines

---

## 12. Implementation Hooks for Cockpit Primitive Types

### 12.1 — RunContract

**Purpose:** Pre-execution contract between ARC and a runtime — declares what the run expects, what it can access, and what guarantees it offers.

**Where to add:**
- **New file:** `python/src/agent_runtime_cockpit/protocol/run_contract.py`

**Exact hook points:**
| Hook | File | Line | How to wire |
|------|------|------|-------------|
| Create RunContract before execution | `supervisor.py` | 82-122 | In `start_run()`, before creating RunRecord, build RunContract from `RunRequest` + resolved `RunProfile` + workspace trust |
| Attach to RunRecord.metadata | `supervisor.py` | 105-112 | Store `RunContract.model_dump()` in `run.metadata["contract"]` |
| Profile enforcement feeds contract | `profiles.py` | 52-78 | `RunProfile` fields → `RunContract.permissions` |
| Trust resolution feeds contract | `trust.py` | 60-93 | `TrustResolution.level` → `RunContract.trust_level` |
| Runtime capabilities feed contract | `capabilities.py` | 40-83 | `RuntimeCapabilities` → `RunContract.capability_assertions` |
| TS mirror type | `arc-protocol-types.ts` | — | Add `RunContract` interface + `RunContractSchema` |

**Fields to model:**
```python
class RunContract(BaseModel):
    run_id: str
    workflow_id: str
    runtime: str
    profile_id: str
    trust_level: TrustLevel
    capability_assertions: RuntimeCapabilities
    isolation_provider: str
    max_timeout_seconds: int
    allow_paid_calls: bool
    allow_network: bool
    allow_secrets: bool
    env_allowlist: list[str]
    signed_at: str
```

**Tests to write:** 3-4 contract creation + enforcement tests in `tests/protocol/test_run_contract.py`

---

### 12.2 — RunReceipt

**Purpose:** Post-execution receipt summarizing what happened — output, cost, duration, audit trail link, evidence refs.

**Where to add:**
- **New file:** `python/src/agent_runtime_cockpit/protocol/run_receipt.py`

**Exact hook points:**
| Hook | File | Line | How to wire |
|------|------|------|-------------|
| Build receipt after run completes | `supervisor.py` | 144-150 | In `_execute_run` after `RUN_COMPLETED`, collect metrics from events |
| Build receipt after run fails | `supervisor.py` | 160-170 | Same hook, different status |
| Attach to RunRecord.metadata | `supervisor.py` | 105-112 | Store receipt in `run.metadata["receipt"]` |
| CLI export | `cli.py` | 1167 (runs_export) | Include receipt in export |
| Web route return | `routes.py` | 237-247 (start_run) | Return receipt alongside RunRecord |
| Audit path linkage | `sqlite.py` | 150-159 | `update_run_audit_path()` after audit chain written |
| HTTP GET run response | `routes.py` | 252-257 | Include receipt in `get_run` envelope response |
| TS mirror type | `arc-protocol-types.ts` | — | Add `RunReceipt` interface |

**Fields to model:**
```python
class RunReceipt(BaseModel):
    run_id: str
    contract_id: str  # hash of RunContract
    status: RunStatus
    started_at: str
    ended_at: Optional[str]
    duration_ms: Optional[int]
    event_count: int
    step_count: int
    tool_call_count: int
    agent_handoff_count: int
    total_tokens: Optional[int]  # if reported
    audit_path: Optional[str]
    audit_verified: Optional[bool]
    evidence_refs: list[str]  # EvidenceRef IDs
    error_summary: Optional[str]
```

**Tests to write:** 3-4 receipt construction + serialization tests

---

### 12.3 — FailureAutopsy

**Purpose:** Structured failure analysis — captures error type, stack trace fragment, which step/agent/tool failed, recovery suggestion.

**Where to add:**
- **New file:** `python/src/agent_runtime_cockpit/protocol/failure_autopsy.py`

**Exact hook points:**
| Hook | File | Line | How to wire |
|------|------|------|-------------|
| Capture on RUN_FAILED | `supervisor.py` | 160-170 | In `handle_exception`, extract error info from events |
| Parse last N events for context | `supervisor.py` | 160-170 | Read `run.events[-10:]` to find last successful step |
| Suggest recovery from error type | `supervisor.py` | 160-170 | Classify: timeout→retry, env→check config, etc. |
| Store in RunRecord.metadata | `supervisor.py` | 168-170 | `run.metadata["failure_autopsy"]` |
| CLI show | `cli.py` | 1107 (runs_status) | Include autopsy in status output |
| TS mirror type | `arc-protocol-types.ts` | — | Add `FailureAutopsy` interface |

**Fields to model:**
```python
class FailureCategory(str, Enum):
    TIMEOUT = "timeout"
    ADAPTER_ERROR = "adapter_error"
    PROVIDER_ERROR = "provider_error"
    INVALID_INPUT = "invalid_input"
    PERMISSION_DENIED = "permission_denied"
    INTERNAL_ERROR = "internal_error"
    UNKNOWN = "unknown"

class FailureAutopsy(BaseModel):
    run_id: str
    category: FailureCategory
    error_type: str  # Python exception class name
    error_message: str
    last_successful_step: Optional[str]
    failed_step_id: Optional[str]
    failed_agent: Optional[str]
    failed_tool_call: Optional[str]
    last_events_before_failure: list[dict]  # last 5 events
    suggested_action: str  # human-readable recovery hint
    retryable: bool
```

**Tests to write:** 4-5 autopsy extraction tests (timeout, adapter error, provider error, permission)

---

### 12.4 — EvidenceRef

**Purpose:** Reference to external evidence that this run actually happened — audit chain path, trace file path, workflow source, CLI invocation, environment snapshot.

**Where to add:**
- **New file:** `python/src/agent_runtime_cockpit/protocol/evidence_refs.py`

**Exact hook points:**
| Hook | File | Line | How to wire |
|------|------|------|-------------|
| Generate on run creation | `supervisor.py` | 103-112 | Create EvidenceRef for trace path, CLI command |
| Generate on run completion | `supervisor.py` | 144-150 | Create EvidenceRef for audit path, event count hash |
| Generate on audit write | `hmac_chain.py` | 40-60 | EvidenceRef for chain file path + last record hash |
| Store in RunRecord.metadata | `supervisor.py` | 105-112 | `run.metadata["evidence_refs"]` |
| Validate on load | `indexed_store.py` | 84-86 | Check all refs still resolve |
| TS mirror type | `arc-protocol-types.ts` | — | Add `EvidenceRef` interface |
| Web route return | `routes.py` | 252-257 | Include in `get_run` |

**Fields to model:**
```python
class EvidenceCategory(str, Enum):
    TRACE_FILE = "trace_file"
    AUDIT_CHAIN = "audit_chain"
    WORKFLOW_SOURCE = "workflow_source"
    CLI_INVOCATION = "cli_invocation"
    ENV_SNAPSHOT = "env_snapshot"
    LOG_FILE = "log_file"

class EvidenceRef(BaseModel):
    ref_id: str
    category: EvidenceCategory
    description: str
    path: str
    mime_type: str  # "application/jsonl", "text/plain", etc.
    size_bytes: Optional[int]
    hash_sha256: Optional[str]
    created_at: str
    valid: bool = True  # set to False if target no longer exists
```

**Tests to write:** 3-4 evidence ref creation + validation tests

---

### 12.5 — TrustDiff

**Purpose:** Before/after comparison of trust policy — what changed between runs, which permissions were escalated, what profiles were used.

**Where to add:**
- **New file:** `python/src/agent_runtime_cockpit/protocol/trust_diff.py`

**Exact hook points:**
| Hook | File | Line | How to wire |
|------|------|------|-------------|
| Compare trust across two runs | `supervisor.py` | 82-122 | Snapshot trust + profile at start vs at end |
| Feed from diff of RunContracts | `protocol/run_contract.py` | — | Compare two RunContract model dumps |
| Check profile changes | `profiles.py` | 45-50 | Diff `profile_id` → resolved `RunProfile` |
| Check trust level changes | `trust.py` | 60-93 | Diff `TrustResolution.level` |
| CLI diff command | `cli.py` | 1056 (runs_diff) | Extend existing diff with trust section |
| Web route | `routes.py` | 464-476 (runs_diff) | Add trust comparison to diff response |
| TS mirror type | `arc-protocol-types.ts` | — | Add `TrustDiff` interface |

**Fields to model:**
```python
class TrustDiffItem(BaseModel):
    field: str
    before: Any
    after: Any
    changed: bool
    severity: Literal["info", "warning", "critical"]

class TrustDiff(BaseModel):
    run_a_id: str
    run_b_id: str
    profile_changed: bool
    profile_before: str
    profile_after: str
    trust_level_changed: bool
    trust_before: Optional[TrustLevel]
    trust_after: Optional[TrustLevel]
    isolation_changed: bool
    isolation_before: str
    isolation_after: str
    paid_calls_changed: bool
    paid_calls_before: bool
    paid_calls_after: bool
    changes: list[TrustDiffItem]
```

**Tests to write:** 3-4 trust diff tests (same profile, different profile, trust level change)

---

### 12.6 — Runtime Capability Snapshot

**Purpose:** Point-in-time freeze of what a runtime adapter claimed it could do — captured before execution for audit trail.

**Where to add:**
- **New file:** `python/src/agent_runtime_cockpit/protocol/capability_snapshot.py`

**Exact hook points:**
| Hook | File | Line | How to wire |
|------|------|------|-------------|
| Snapshot before run starts | `supervisor.py` | 82-122 | In `start_run()`, call `adapter.capabilities()` and save |
| Snapshot after run ends | `supervisor.py` | 144-150 | Re-check capabilities (some adapters may change availability) |
| Include in RunContract | `protocol/run_contract.py` | — | Embed `capability_assertions: RuntimeCapabilities` |
| CLI display | `cli.py` | 316 (runtimes) | Extend `--capabilities` flag to accept `--snapshot` |
| TS mirror type | `arc-protocol-types.ts` | — | Already has `RuntimeCapabilities` — use as-is |
| Web route | `routes.py` | 134-141 | Extend `/api/runtimes/capabilities` with timestamp |

**Fields to model:**
```python
class CapabilitySnapshot(BaseModel):
    runtime_id: str
    adapter_version: Optional[str]
    schema_version: int
    capabilities: RuntimeCapabilities
    snapshot_timestamp: str
    works_with_workspace: bool  # false if detection failed
```

**Tests to write:** 2-3 snapshot tests

---

### 12.7 — Graph/Chat Cross-Links

**Purpose:** Bidirectional links between workflow graph nodes and chat messages — enables clicking a graph node to scroll to the relevant conversation turn, and clicking a message to highlight the corresponding graph node.

**Where to add:**
- **New file (Python):** `python/src/agent_runtime_cockpit/protocol/cross_links.py`
- **New file (TS):** Not needed — existing widget state can hold links

**Exact hook points:**
| Hook | File | Line | How to wire |
|------|------|------|-------------|
| Build links during execution | `adapters/base.py` | 125-132 | Adapters emit `NODE_STARTED` / `HANDOFF` events with `step_id` + `agent_name` |
| Emit CROSS_LINK event | `protocol/events.py` | 184 | Register new event type `CROSS_LINK` in EVENT_TYPES dict |
| Parse links from events | `trace-parser.ts` | 31-67 | Build node↔message index from event sequence |
| Theia widget state | `arc-widget.tsx` | 24-50 | Add `graphChatLinks: CrossLink[]` to `ArcWidgetState` |
| Event stream widget | `arc-event-stream-widget.tsx` | 149-155 | Add click handler to highlight graph node |
| Workflow graph widget | `arc-workflow-graph-widget.tsx` | 100-130 | Add click handler to scroll chat to first linked message |

**Fields to model:**
```python
class CrossLink(BaseModel):
    run_id: str
    node_id: str
    node_label: str
    event_sequence: int  # sequence number of the linked event
    event_type: str       # AGENT_START, TOOL_CALL, HANDOFF, MESSAGE, etc.
    direction: Literal["node_to_event", "event_to_node"]
```

**Event registry addition** (`protocol/events.py`):
```python
"CROSS_LINK": EventTypeDef(
    required_fields={"node_id", "event_sequence", "direction"},
    optional_fields={"node_label", "event_type"},
)
```

**Tests to write:**
- 2-3 Python cross-link generation + event emission tests
- 2-3 TS widget state cross-link integration tests

---

## 13. Complete Test Inventory

| Test file | Lines | What it covers |
|-----------|-------|----------------|
| `python/tests/test_storage.py` | — | 20 storage tests (Jsonl + Sqlite + Indexed) |
| `python/tests/test_cli_storage.py` | — | 5 storage CLI tests |
| `python/tests/test_config.py` | — | 14 config tests |
| `python/tests/test_trust_resolver.py` | — | Trust resolver tests |
| `python/tests/security/test_profiles.py` | — | Profile tests |
| `python/tests/test_sse_resilience.py` | — | SSE resilience |
| `python/tests/test_runtime_router.py` | — | Runtime router |
| `python/tests/test_cli_smoke.py` | — | CLI smoke tests |
| `python/tests/test_cli_runs.py` | — | CLI run tests |
| `python/tests/test_cli_discoverability.py` | — | CLI discoverability |
| `python/tests/test_cli_error_paths.py` | — | CLI error paths |
| `python/tests/test_cli_eval.py` | — | CLI eval tests |
| `python/tests/test_cli_doctor.py` | — | CLI doctor tests |
| `python/tests/test_cli_providers.py` | — | CLI provider tests |
| `python/tests/test_cli_profiles_workspace.py` | — | CLI profile + workspace |
| `python/tests/test_cli_run_gating.py` | — | CLI run gating |
| `python/tests/orchestration/test_supervisor.py` | — | Supervisor tests |
| `python/tests/orchestration/test_event_broker.py` | — | Event broker tests |
| `python/tests/web/test_sse_proof.py` | — | SSE proof tests |
| `python/tests/web/test_runs_sse.py` | — | Run SSE tests |
| `python/tests/audit/test_hmac_chain.py` | — | HMAC chain tests |
| `python/tests/audit/test_hitl.py` | — | 6 HITL tests |
| `python/tests/isolation/test_isolation.py` | — | 11 isolation tests |
| `python/tests/isolation/test_docker_provider.py` | — | 13 Docker tests |
| `packages/arc-extension/src/node/__tests__/services.unit.test.ts` | 588 | WorkflowExecutor, TraceParser, FileManager, Detector |
| `packages/arc-extension/src/node/__tests__/security-utils.test.ts` | 206 | Sanitization + validation |
| `packages/arc-extension/src/node/__tests__/arc-service.integration.test.ts` | 839 | Full integration |
| `packages/arc-extension/src/browser/__tests__/arc-service.proxy.test.ts` | 294 | Protocol contract tests |
| `packages/arc-extension/src/browser/__tests__/arc-widget.integration.test.ts` | 621 | Widget structure |
| `packages/arc-extension/src/browser/__tests__/ui-components.contract.test.ts` | 495 | Component contracts |
| `packages/arc-ag-ui/test/mapping.test.js` | 54 | AG-UI mapping |
| `packages/arc-ag-ui/test/redaction.test.js` | 31 | Secret redaction |
| `packages/arc-ag-ui/test/performance.test.js` | 99 | Throughput benchmarks |

---

## 14. Key Risks

1. **SQLite is best-effort, JSONL is canonical** — all primitives must first persist to JSONL, then SQLite. Any new field in RunRecord must be added to both.

2. **Event schema versioning** — `CURRENT_SCHEMA_VERSION = 1`. When adding new event types (CROSS_LINK, etc.), increment version and handle N-1 backward compat.

3. **SSE heartbeat drift** — `HEARTBEAT_INTERVAL = 15.0`. Long-lived connections must handle interim heartbeats.

4. **HITL token replay** — Single-use tokens only protect within same session. Cross-session protection requires additional state.

5. **EvidenceRef stale targets** — After load, validate all paths still resolve. Strip invalid refs silently.

6. **TrustDiff blocker order** — Policy check (`enforce_profile`) runs BEFORE run start in `routes.py` (line 228). Trust diff generation must NOT block execution.

7. **No live SSE in Theia frontend** — `ArcEventStreamWidget` is trace-backed only. Live SSE requires wiring into `EventBroker.sse_handler()` via the daemon.

8. **RunContract not persisted** — Must save alongside RunRecord in JSONL. Currently no explicit contract persistence.

9. **No cross-link storage** — Cross-links must be stored in events or as separate metadata, not derived on-the-fly from full event replay.

10. **CLI ↔ Daemon parity** — Some CLI commands read storage directly (`cli.py`), others call the daemon (`web/routes.py`). Primitive CLI commands must work in both modes.
