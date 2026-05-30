# ARC Studio — Deep Architecture Analysis & Improvement Report

**Generated:** 2026-05-27
**Methodology:** 8 parallel research agents covering protocol/storage, security/sandbox, SwarmGraph, IDE/frontend, CLI/REPL, memory/MCP/tools, adapters/providers, and web research on competitors/best practices.

---

## Executive Summary

ARC Studio has a **substantial, well-architected core** spanning 3000+ Python tests, 814+ TypeScript tests, 14 framework adapters, a native SwarmGraph runtime with cryptographic consensus, and a production-grade subprocess sandbox. The architecture is honest about its limitations — gated execution paths, labeled scaffolds, and banned-claims enforcement are rare virtues.

However, the audit reveals **5 critical issues**, **12 high-severity structural risks**, and significant gaps in cross-system integration. The most urgent: a MessageData protocol mismatch that breaks typed event parsing for the most common event type, a credential trust check that is a no-op, two disconnected event systems, and built-in tools that lack workspace boundary enforcement.

---

## 1. Architecture Debt Matrix

| Area | Debt Level | Risk | Effort | Priority |
|------|-----------|------|--------|----------|
| Protocol parity (MessageData, HitlTimeout) | **Critical** | Every MESSAGE/HITL_TIMEOUT event fails typed validation | Low (3 field fixes) | **P0** |
| Auth trust check no-op | **Critical** | Stored API keys accessible from any workspace | Low (wire to trust.py) | **P0** |
| Two disconnected event systems | **Critical** | EventBroker vs EventBus share no code/persistence | High (unify pipeline) | **P0** |
| Tools lack workspace boundary | **Critical** | ReadFileTool/ListDirectoryTool can read any file | Low (add path check) | **P0** |
| OAuth state uses `random` not `secrets` | **High** | CSRF token is not cryptographically secure | Trivial (delete 2 lines) | **P0** |
| SQLite no WAL mode + silent error swallowing | **High** | `database is locked` errors, silent data loss | Low (PRAGMA + raise) | **P1** |
| EventBroker purely in-memory | **High** | Daemon restart loses all live SSE state | Medium (persist ring buffer) | **P1** |
| Post-terminal events after RUN_COMPLETED | **High** | Consumers miss contract/receipt events | Low (reorder emission) | **P1** |
| SSE code duplicated 250 lines | **High** | arc-backend-service.ts vs run-lifecycle-service.ts | Medium (delete + delegate) | **P1** |
| Legacy ArcWidget still registered | **High** | Dead weight, confusion, doubled resources | Low (remove from module) | **P1** |
| No frontend code splitting | **High** | Monolithic bundle.js, slow initial load | Medium (webpack config) | **P1** |
| `gossip` consensus silent fallback | **High** | Requesting gossip silently gives majority | Trivial (remove or implement) | **P1** |
| Runner status bug (both branches = completed) | **High** | Incomplete swarms reported as completed | Trivial (fix else branch) | **P1** |
| Sandbox `run` lacks trust gate | **High** | Untrusted workspace can execute sandbox commands | Low (add ensure_trusted) | **P1** |
| Memory graph: JSON file, no locking, O(n) query | **Medium** | Won't scale, concurrent corruption | Medium (SQLite backend) | **P2** |
| No provider failover | **Medium** | Rate-limited calls just fail | Medium (circuit breaker) | **P2** |
| Pydantic AI not registered in default registry | **Medium** | Pydantic AI projects invisible to ARC | Trivial (add to registry) | **P1** |
| No cost extraction for OpenAI-compatible providers | **Medium** | Cost tracking is Anthropic-only | Medium (mirror anthrop_cost.py) | **P2** |
| Tab state lost on switch | **Medium** | Chat transcript disappears on tab change | Medium (lift state) | **P2** |
| Session bridge SSE no reconnect | **Medium** | Dropped session_changed events | Low (mirror active trace pattern) | **P2** |

---

## 2. Critical Findings (P0 — Fix Now)

### C1: MessageData Protocol Mismatch

- **File**: `python/src/agent_runtime_cockpit/protocol/typed_events.py:435-453`
- **Issue**: Python `MessageData` requires `message_id`, `role`, `content`. The TS type and Python event registry require `text`. Every MESSAGE event produced by the supervisor fails typed validation and falls back to `UnknownEvent`.
- **Impact**: The most frequently emitted event type is effectively broken in the typed union.
- **Fix**: Align Python typed model to registry: `text: str` required, `source/coalesced/node_id/message_id/tool_call_id/evidence_refs` optional. Remove `message_id`, `role`, `content` as required fields.

### C2: Auth Trust Check is a No-Op

- **File**: `python/src/agent_runtime_cockpit/auth/manager.py:46-53`
- **Issue**: `_is_workspace_trusted()` unconditionally returns `True`. Fernet-encrypted API keys at `~/.local/share/arc-studio/auth.json` are accessible from any workspace within the same user context.
- **Impact**: Stored credentials have no workspace isolation despite the API implying trust is checked.
- **Fix**: Wire `_is_workspace_trusted()` to `security/trust.py`'s `resolve_trust()` / `ensure_trusted()`.

### C3: Two Disconnected Event Systems

- **Files**: `orchestration/event_broker.py` vs `events/bus.py`
- **Issue**: EventBroker (per-run SSE, in-memory, raw dicts, no persistence) and EventBus (global notifications, typed Pydantic, JSONL-persisted) share no code, no event types, and no persistence path. A consumer wanting a unified event stream must subscribe to both.
- **Impact**: Architectural fragmentation. Event correlation across systems requires manual work. EventBroker loses all state on daemon restart.
- **Fix**: Unify into single event pipeline. EventBroker should persist ring buffer and subscribe to EventBus.

### C4: Built-in Tools Have No Workspace Boundary

- **File**: `python/src/agent_runtime_cockpit/tools/builtin.py:29-59`
- **Issue**: `ReadFileTool` and `ListDirectoryTool` resolve paths via `Path(args.path).resolve()` but never check workspace boundaries. Can read ANY file on the filesystem that the process has permission to access. No symlink traversal protection. No output redaction.
- **Impact**: Tools can exfiltrate secrets from outside the workspace.
- **Fix**: Add workspace root parameter and `path.is_relative_to(root)` check. Add symlink detection. Add output redaction via `Redactor().redact_string()`.

### C5: OAuth CSRF Token Uses `random` Instead of `secrets`

- **File**: `python/src/agent_runtime_cockpit/auth/oauth.py:143-144`
- **Issue**: Second `_generate_state()` definition shadows the first, using `random.choices()` instead of `secrets.token_urlsafe()`. The `random` module is not suitable for security-sensitive state parameters.
- **Impact**: OAuth CSRF protection is weakened.
- **Fix**: Delete lines 143-144 so the `secrets.token_urlsafe` version at line 117-119 is used.

---

## 3. High-Severity Findings (P1 — This Quarter)

### H1: SQLite No WAL Mode + Silent Error Swallowing

- **File**: `storage/sqlite.py:82-84,124-125`
- **Issue**: No `PRAGMA journal_mode=WAL`. Default DELETE mode causes readers to block writers. Every `SqliteStore` method catches all exceptions and logs warnings — a full disk or corrupted database silently loses data.
- **Fix**: Add `PRAGMA journal_mode=WAL; PRAGMA busy_timeout=5000;` in `init_db()`. Raise on `OperationalError`.

### H2: EventBroker Purely In-Memory

- **File**: `orchestration/event_broker.py:69-74`
- **Issue**: On daemon restart: `_active_runs` empty, `_ring_buffers` empty, `_subscribers` empty, `_event_ids` restart from 0. SSE clients get no replay of recent events.
- **Fix**: Persist ring buffer events to `.arc/events/event-log.jsonl`. Replay on restart.

### H3: Post-Terminal Events After RUN_COMPLETED

- **File**: `orchestration/supervisor.py:346-403`
- **Issue**: CONTRACT_FULFILLED/VIOLATED and RECEIPT_GENERATED events are emitted AFTER the run status is set to COMPLETED. Consumers treating terminal events as final will miss these.
- **Fix**: Emit contract/receipt events BEFORE the terminal status event.

### H4: 250 Lines SSE Code Duplicated

- **Files**: `arc-backend-service.ts:795-1045` vs `run-lifecycle-service.ts:435-795`
- **Issue**: `createActiveTraceIterable`, `streamLiveActiveTrace`, `parseSseEvent`, `resolvePythonDaemonBaseUrl`, and 8 other functions are copy-pasted between the facade and the service.
- **Fix**: Delete from `arc-backend-service.ts`, delegate to `RunLifecycleService`.

### H5: Legacy ArcWidget Still Registered

- **File**: `arc-extension-frontend-module.ts:53-61`
- **Issue**: Legacy `ArcWidget` (441 lines) is fully registered alongside `ArcStudioWidget` (219 lines). Both can be opened simultaneously. 7 components (~700 lines) are used only by the legacy widget.
- **Fix**: Remove from DI module. Delete 7 exclusive components.

### H6: No Frontend Code Splitting

- **File**: `gen-webpack.config.js`
- **Issue**: No `optimization.splitChunks` in frontend config. Entire Theia + ARC extension is a single monolithic `bundle.js`.
- **Fix**: Add split chunks with ARC-specific chunks. Lazy-load tabs.

### H7: `gossip` Consensus Silent Fallback

- **File**: `swarmgraph/consensus.py:235`
- **Issue**: `gossip` is defined in `ConsensusProtocol` enum but not in `CONSENSUS_FUNCS` dict. `run_consensus()` falls back to `majority_consensus` silently. Requesting gossip gives majority semantics with no warning.
- **Fix**: Remove `gossip` from enum or implement a gossip protocol function.

### H8: Runner Status Bug

- **File**: `swarmgraph/runner.py:130-134`
- **Issue**: Both branches of the if/else set `self.state.status = SwarmStatus.completed`. A swarm that exhausts its rounds without completing all tasks is still reported as completed.
- **Fix**: Set `SwarmStatus.failed` in the else branch with an error message.

### H9: Sandbox `run` Lacks Trust Gate

- **File**: `cli/sandbox.py:287-406`
- **Issue**: `sandbox_run()` evaluates sandbox policy and runs commands through isolation but never calls `ensure_trusted()` or `enforce_workspace_trust()`.
- **Fix**: Add `ensure_trusted(ws)` at the top of `sandbox_run()`.

### H10: Duplicate HITL Command Registrations

- **Files**: `cli/hitl.py:17` and `cli/mgmt.py:1197`
- **Issue**: Both register `hitl_pending` and `hitl_respond` on `hitl_app`. Typer registration collision.
- **Fix**: Remove duplicate in `mgmt.py` (lines 1194-1291).

### H11: Duplicate Eval Run Command

- **File**: `cli/mgmt.py:519,697`
- **Issue**: `eval_app.command("run")` registered twice. Second shadows first.
- **Fix**: Remove first `eval_run` (lines 519-622).

### H12: HitlTimeoutData Extra Required Field

- **File**: `protocol/typed_events.py:329-336`
- **Issue**: Python declares `step_id: str` as required. TS type does not have it. Supervisor does not emit it. Every HITL_TIMEOUT event fails typed validation.
- **Fix**: Make `step_id` optional or remove it.

---

## 4. Subsystem Analysis

### 4.1 Protocol & Storage

**20 issues found** (3 critical, 6 high, 8 medium, 3 low).

**What works well:**
- Discriminated RunEvent unions: 22 typed variants in TS, 29 in Python
- Event schema versioning: v1-to-v2 migration on both sides
- Cross-language fixture infrastructure: 31 fixture files, TS loader with round-trip testing
- Dual-write JSONL+SQLite: crash-safe JSONL with atomic temp-file + `os.replace` + `fsync`
- Advisory locking: POSIX `fcntl.flock` with spin-wait

**Key gaps:**
- No Python-side fixture round-trip tests
- No forward-compat handling in Python for `schema_version > CURRENT`
- `INSERT OR REPLACE` can lose status updates during backfill
- HMAC audit chain `_load_tail_state` reads entire file (memory-unbounded)
- No dual-write transaction between JSONL and SQLite
- No audit chain compaction or archival

### 4.2 Security & Sandbox

**15 findings** (2 critical, 2 high, 5 medium, 6 low).

**What is enforced:**
- Trust resolver: external DB at `~/.arc/trusted-workspaces.json`, `ensure_trusted()` raises for untrusted
- Enforcement layer: 4 gates (trust, paid-call, shell, network) with dry-run mode
- Subprocess hardening: env allowlist, 14 secret patterns, process group kill, bounded streaming, output redaction, no shell
- MCP: per-call trust re-check, audit events, output caps, redaction, ID validation

**What is NOT enforced:**
- Auth module trust check is a no-op (C2)
- Sandbox `run` command lacks trust gate (H9)
- Task executor `_execute_run()` has no trust check
- Provider action `run_provider_action()` has no workspace trust check
- `sed -i` classified as read_only (should be writes_workspace)
- Symlink guard only checks cwd, not command arguments
- Dangling symlinks pass path validation
- `NoneIsolationProvider` has no hardening or trust assertion
- Prompt injection scanner exists but is not wired to sandbox or MCP
- Two separate redaction pattern sets (security/redaction.py vs isolation/subprocess.py)

### 4.3 SwarmGraph Runtime

**8 structural risks, 7 scaffolded features, 10 recommendations.**

**What works:**
- Complete lifecycle: queen prepare/decompose/assign → worker execute → consensus/HITL → budget check → checkpoint
- 4 consensus protocols: majority, quorum, raft, bft — all implemented and tested
- Commit-reveal escrow: cryptographically sound SHA-256 with 5 adversarial scenarios
- Adaptive consensus: deterministic risk assessor, 100 fixtures, fail-closed
- CostRecord v3: full migration chain, Decimal arithmetic, component breakdown

**What is scaffolded (not functional):**
- `gossip` consensus protocol (dead code, silent fallback)
- `mesh` and `tree` topologies (incomplete graphs, dispatch-only)
- `sequential` and `hierarchical` strategies (defined, never referenced)
- `gated_local` and `provider_backed` execution modes (return error results)
- `judge` and `router` agent roles (defined, never used)
- `state_transition`, `error`, `audit` event kinds (no emit helpers)
- `SwarmFailureCause` enum (defined, never referenced)

**Structural risks:**
- Runner status bug (H8)
- Checkpoint `spec_map` not saved — restore can leave it inconsistent
- Escrow silent vote dropping on verification failure
- Substring false positives in risk signals ("read" in "already")
- Budget not enforced at adapter effect boundaries
- HITL-approved tasks stuck in pending (no re-processing)
- Worker timeout is non-functional (check after instantaneous fake execution)

### 4.4 IDE/Frontend

**34 risks identified (R1-R34).**

**What works well:**
- Service decomposition: 9 specialized services with clean domain separation
- Security posture: env allowlists, shell:false, input validation, path traversal guards
- Protocol coverage: all 42 RPC methods defined and implemented
- Typed event system in `arc-protocol-ts`: discriminated unions, type guards, schema versioning
- Active trace SSE: production-grade reconnect with exponential backoff and Last-Event-ID
- Session bridge: read/write/SSE with write mutex serialization

**Key gaps:**
- `arc-backend-service.ts` still has 1118 lines with residual business logic (HITL, audit, replay, diff)
- 22 `any` types in production CLI mapping code
- No interface-based DI bindings
- `WorkspaceRoot` from `process.cwd()` (fragile in production Theia)
- No symlink resolution in `validateFilePath()`
- No stdout/stderr cap in subprocess executor
- No process group kill on timeout
- Tab state lost on switch (unmounts on tab change)
- VirtualizedEventList used in only 1 of 4+ event-rendering views
- Dual protocol definitions (`arc-protocol.ts` vs `arc-protocol-types.ts`) risk type drift

### 4.5 CLI/Interactive Shell

**3 critical issues, 4 moderate, 4 minor.**

**What works:**
- 26 CLI modules (8,053 lines) + 11 REPL modules (4,860 lines)
- 30 slash commands with 16 subcommand groups
- Three-layer error boundary (outer, inner, runner)
- Approval UX for NETWORK/INSTALL/UNKNOWN with injectable confirm_fn
- DESTRUCTIVE/PRIVILEGED hard-denied at three layers
- Session schema v4 with migration from v1-v3
- Advisory locking on all write paths
- Batch mode with sandbox-gated deterministic execution
- Session export/import with SHA-256 integrity and secret scanning

**Key gaps:**
- Duplicate HITL command registrations (H10)
- Duplicate eval run command (H11)
- `providers_catalog` double-outputs (human text + JSON envelope)
- `mgmt.py` oversized at 1,629 lines
- Pipe operator is argument injection, not stdin pipe
- No `/diff`, `/apply`, `/test` slash commands
- Alias expansion requires explicit `/alias run`, no auto-expand
- `cmd_version` returns hardcoded string instead of `__version__`

### 4.6 Memory Graph

**Research prototype with significant scaling and quality gaps.**

**What works:**
- Memory schema: nodes (concept/decision/pattern/risk/outcome) + edges (derived_from/supports/contradicts/co_occurs)
- JSON file store at `.arc/memory/graph.json`
- Redaction-before-extraction via `Redactor().redact_dict()`
- Evidence evaluation with proceed/no_go/insufficient_evidence gate
- CLI: extract, query, show, forget-run, evaluate, evidence create/evaluate/show

**Key gaps:**
- Full-file JSON read/write on every operation (won't scale)
- No concurrent access protection (no file locking)
- Naive keyword extraction produces low-quality memories (every token ≥ 4 chars becomes a concept)
- Query is O(n) full scan (no inverted index)
- Only `co_occurs` edges ever created (other edge types declared but unused)
- No semantic search (token intersection only)
- No graph traversal (BFS/DFS/path finding)
- No memory decay or expiration
- No encryption at rest
- `forget_run` does not guarantee complete erasure (shared memories persist)

### 4.7 MCP Server

**Production-quality local control plane with minor gaps.**

**What works:**
- 11 tools + 3 resources, all with per-call trust re-check
- Audit events at `.arc/audit/mcp.events.jsonl` with redacted args, timing, decision
- Output caps (1MB), redaction, ID validation, path escape guard
- Stable `ok()`/`err()` envelopes
- 42 tests (27 unit + 15 full MCP protocol stack)

**Key gaps:**
- Resources do not emit their own audit events (invisible as distinct from tool calls)
- No execution timeouts per tool
- No rate limiting
- No request correlation ID
- Audit JSONL file has no rotation or size limits
- `arc_task_create` accepts arbitrary operation strings and params JSON

### 4.8 Tools System

**Working scaffold with critical security gap.**

**What works:**
- Tool protocol: `ToolResult` with trust overrides, `ToolHandler` protocol
- 3 built-in tools: ReadFile, ListDirectory, GetCurrentTime
- Tool registry with duplicate rejection
- Trust wrapping (XML envelope with trust level)

**Critical gap:**
- **No workspace boundary enforcement** (C4)
- No symlink traversal protection
- No output redaction
- `mixed` trust level raises `NotImplementedError`
- No tool execution audit trail
- No timeout enforcement
- No sandbox integration
- No bridge to MCP tools

### 4.9 Adapters & Providers

**12 structural risks.**

**What works:**
- 14 adapters registered, 5 with T3 runtime (SwarmGraph, LangGraph, LangChain, CrewAI, OpenAI Agents)
- ProviderClient protocol: Anthropic + OpenAI-compatible (6 vendors)
- Cost estimation: Anthropic-only with SDK count_tokens + tiktoken approximation
- Cache control breakpoints for Anthropic
- Conformance test suite (8 tests)

**Key gaps:**
- Pydantic AI not registered in default registry
- Two conflicting `ProviderClient` protocols (`base.py` vs `client.py`)
- No provider failover mechanism
- No cost extraction for OpenAI-compatible providers
- Static/outdated model lists
- `max_context_tokens` hardcoded to 128K for all OpenAI-compatible vendors
- AST detection has no version-specific handling
- LangChain `capability_report` contradicts `capabilities()`
- Fernet key stored alongside encrypted data
- Keyring integration exists but is not wired into main flow

---

## 5. What Is Real vs. Labeled

| Claim | Reality |
|-------|---------|
| Workspace trust enforcement | **Real** for web routes, supervisor, MCP. **Not enforced** in sandbox CLI, task executor, auth module |
| Three-layer provider gate | **Real** — env + paid + confirmation all checked |
| Subprocess hardening | **Real** — env allowlist, secret stripping, process group kill, bounded pipes |
| Container sandbox | **Real** but gated behind `ARC_ENABLE_CONTAINER_SANDBOX=1`. Never active by default |
| MicroVM preflight | **Real** — thorough doctor/preflight for Firecracker/Cloud Hypervisor/Lima |
| MicroVM execution | **Not real** — `execute()` raises `NotImplementedError`. Correctly labeled |
| Fernet-encrypted credentials | **Real** encryption. **Trust gate is labeled but not enforced** (always returns True) |
| MCP per-call trust re-check | **Real** for tools. **Fragile** for resources (relies on delegation) |
| Native SwarmGraph runtime | **Real** for `fake_offline`. `gated_local`/`provider_backed` are stubs |
| 14 adapters | **Real** detection + export. Only 5 have T3 runtime |
| Adaptive consensus | **Real** — deterministic, 100 fixtures, fail-closed |
| Memory graph | **Real** research prototype. No semantic search, no scaling, no runtime integration |
| Audit hash-chain | **Real** — SHA-256 chain with HMAC mirror |
| Command classification | **Real** but has gaps (`sed -i`, dangling symlinks) |

---

## 6. Competitive Position

| Capability | ARC Studio | LangSmith | Arize Phoenix | CrewAI | Codex CLI | Claude Code |
|-----------|-----------|-----------|---------------|--------|-----------|-------------|
| Multi-agent consensus | **Unique** | No | No | Sequential only | No | No |
| OS-level sandbox | Subprocess | N/A (cloud) | N/A | No | **Seatbelt+Landlock** | Permission-based |
| Local-first IDE | Theia | No (cloud) | Local+cloud | No | Terminal | Terminal |
| Framework adapters | 14 (5 runnable) | LangChain only | 20+ integrations | CrewAI only | N/A | N/A |
| Trust enforcement | **Yes** | No | No | No | **Yes** | Partial |
| MCP server | stdio-only | No | **Yes** | No | **Yes** | **Yes** |
| Audit chain | **HMAC-signed** | Basic | OTel traces | No | No | No |
| Memory graph | Research prototype | No | No | No | No | No |
| Cost tracking | Anthropic only | **Full** | **Full** | No | No | No |

**ARC Studio's unique moat**: Multi-agent consensus with commit-reveal escrow + adaptive risk-based protocol selection. No competitor has this.

**ARC Studio's biggest gap**: OS-level sandbox (Seatbelt/Landlock) and MCP ecosystem integration.

---

## 7. Top 10 Improvement Recommendations

### 1. Implement OS-Level Sandbox (Seatbelt + Landlock)
**Impact: Very High | Effort: Medium**

Following Codex CLI's proven pattern:
- **macOS**: Seatbelt `.sb` profiles restricting filesystem to workspace + temp, blocking network by default
- **Linux**: Landlock ABI v4+ for filesystem, seccomp-bpf for syscall filtering, network namespaces for isolation
- Integrate with existing `IsolationProvider` as a new `seatbelt` / `landlock` provider
- This is the single highest-impact security improvement — moves from process-level to OS-kernel-level isolation

### 2. Unify Event Systems
**Impact: Very High | Effort: High**

Merge EventBroker and EventBus into a single typed event pipeline:
- Single persistence layer (JSONL)
- Single ring buffer with disk backing
- Single subscriber model
- Daemon restart replays recent events for SSE clients
- Eliminates the most significant architectural fragmentation

### 3. Add MCP HTTP+SSE Transport
**Impact: High | Effort: Medium**

Current stdio-only limits integration. Add Streamable HTTP transport per MCP spec 2025-03-26:
- Session management via `Mcp-Session-Id` header
- Resumability via `Last-Event-ID`
- Localhost-only binding with token authentication
- Enables remote MCP clients (Cursor, Claude Code, Continue.dev) to connect to ARC

### 4. Bridge Tool Registry to MCP
**Impact: High | Effort: Low**

The 3 built-in tools and 11 MCP tools are completely disconnected. Bridge them:
- Register built-in tools as MCP tools
- Add workspace boundary enforcement to built-in tools
- Add output redaction
- Unified tool discovery across CLI REPL, MCP, and runtime

### 5. Upgrade Memory Graph to SQLite + Semantic Search
**Impact: High | Effort: Medium**

Current JSON file store won't scale. Migrate to:
- SQLite backend with FTS5 for full-text search
- Optional vector embeddings via `sentence-transformers` (local, no provider calls)
- Memory decay (confidence reduction over time)
- Inverted index for O(log n) queries
- File locking for concurrent access

### 6. Add Provider Failover + Cost Extraction for All Providers
**Impact: High | Effort: Medium**

- Circuit breaker pattern: health checks, latency-based selection, cost-aware routing
- Mirror `anthropic_cost.py` pattern for OpenAI-compatible providers
- Dynamic model catalog from provider APIs

### 7. Remove Legacy ArcWidget + Consolidate Components
**Impact: Medium | Effort: Low**

- Remove legacy `ArcWidget` from DI module
- Delete 7 exclusive components (~700 lines)
- Migrate any unique functionality to `ArcStudioWidget`
- Reduces bundle size and eliminates confusion

### 8. Add Frontend Code Splitting
**Impact: Medium | Effort: Medium**

- Webpack `splitChunks` for ARC-specific chunks
- Lazy-load tabs (Chat, Runs, Config, etc.)
- Bundle analysis via `webpack-bundle-analyzer`
- Target: reduce initial load by 40%+

### 9. Implement Letta-Style Memory Blocks for Agent Context
**Impact: Medium | Effort: Medium**

- Structured memory blocks (persona, human, custom labels)
- Archival memory (long-term) + recall memory (conversation history)
- RAG-based context injection into agent prompts
- Tree-sitter based code chunking for codebase context

### 10. Expand SwarmGraph Worker Specialization
**Impact: Medium | Effort: High**

Current workers are homogeneous. Add:
- Role-specialized workers (coder, reviewer, architect) with different model/prompt/tool configs
- Dynamic worker scaling based on task complexity
- Cross-run learning via memory graph integration
- Expand adversarial test suite from 5 to 20+ scenarios

---

## 8. Recommended Next 5 PRs

### PR 1: Protocol Parity Fix (1 day)
Fix MessageData, HitlTimeoutData, NodeStartedData mismatches. Register denial events in EVENT_TYPES and both KnownRunEvent unions. Add Python-side fixture round-trip tests. Add forward-compat handling in Python RunEvent.

**Files affected:**
- `python/src/agent_runtime_cockpit/protocol/typed_events.py`
- `python/src/agent_runtime_cockpit/protocol/denial_events.py`
- `python/src/agent_runtime_cockpit/protocol/events.py`
- `packages/arc-protocol-ts/src/run-events.ts`
- `protocol/fixtures/run-event-registry.json`

### PR 2: Security Gate Closure (1 day)
Wire auth trust check to `security/trust.py`. Add `ensure_trusted()` to sandbox CLI `run` command and task executor `_execute_run()`. Fix OAuth `_generate_state()` shadowing. Add trust check to `run_provider_action()`.

**Files affected:**
- `python/src/agent_runtime_cockpit/auth/manager.py`
- `python/src/agent_runtime_cockpit/auth/oauth.py`
- `python/src/agent_runtime_cockpit/cli/sandbox.py`
- `python/src/agent_runtime_cockpit/tasks/executor.py`
- `python/src/agent_runtime_cockpit/provider_action.py`

### PR 3: Tool Workspace Boundary (1 day)
Add workspace root parameter to `ReadFileTool` and `ListDirectoryTool`. Add `path.is_relative_to(root)` check. Add symlink detection (`path.is_symlink()` before resolve). Add output redaction via `Redactor().redact_string()`. Add `is_error: bool` field to `ToolResult`.

**Files affected:**
- `python/src/agent_runtime_cockpit/tools/builtin.py`
- `python/src/agent_runtime_cockpit/tools/protocol.py`
- `python/src/agent_runtime_cockpit/tools/registry.py`

### PR 4: SwarmGraph Correctness (1 day)
Fix runner status bug (else branch → `SwarmStatus.failed`). Remove `gossip` from `ConsensusProtocol` enum. Add `spec_map` to `SwarmCheckpoint`. Raise `VoteVerificationError` on escrow verification failure instead of silently dropping votes. Add word-boundary matching for risk signals (`re.search(r'\b' + re.escape(signal) + r'\b', normalized)`).

**Files affected:**
- `python/src/agent_runtime_cockpit/swarmgraph/runner.py`
- `python/src/agent_runtime_cockpit/swarmgraph/config.py`
- `python/src/agent_runtime_cockpit/swarmgraph/consensus.py`
- `python/src/agent_runtime_cockpit/swarmgraph/state.py`
- `python/src/agent_runtime_cockpit/swarmgraph/risk_assessment.py`
- `python/src/agent_runtime_cockpit/swarmgraph/nodes/consensus.py`

### PR 5: Storage Hardening (2 days)
Enable SQLite WAL mode + busy_timeout. Propagate critical `OperationalError` instead of swallowing. Add EventBroker ring buffer persistence to `.arc/events/`. Add concurrent run limit via `asyncio.Semaphore`. Persist HITL state to disk. Add stale RUNNING task recovery on startup. Register Pydantic AI in default adapter registry.

**Files affected:**
- `python/src/agent_runtime_cockpit/storage/sqlite.py`
- `python/src/agent_runtime_cockpit/orchestration/event_broker.py`
- `python/src/agent_runtime_cockpit/orchestration/supervisor.py`
- `python/src/agent_runtime_cockpit/tasks/executor.py`
- `python/src/agent_runtime_cockpit/adapters/registry.py`

---

## 9. Research Sources

### Sandbox & Security
- **Codex CLI** (github.com/openai/codex): Seatbelt profiles, Landlock, seccomp, three-tier approval policy
- **Linux Landlock ABI v4+**: Kernel-native filesystem restriction, no root required
- **Firecracker** (github.com/firecracker-microvm/firecracker): Linux-only, KVM required, ~125ms boot
- **Lima** (github.com/lima-vm/lima): macOS Virtualization.framework, 10-30s boot, session-based

### MCP Ecosystem
- **MCP Specification** (modelcontextprotocol.io/specification/2025-03-26): Streamable HTTP transport, sampling, session management
- **Arize Phoenix MCP** (@arizeai/phoenix-mcp): Observability via MCP

### Memory Systems
- **Letta/MemGPT** (github.com/letta-ai/letta): Memory blocks, archival/recall memory, stateful agents
- **Chroma**: Python-native embedded vector database for local-first

### Competitors
- **LangSmith**: Cloud-hosted observability, Fleet visual agent builder
- **Arize Phoenix**: OTel-based, 20+ integrations, MCP-enabled
- **CrewAI**: Role-based agents, Crews + Flows, 52k stars
- **AutoGen**: Maintenance mode, successor is Microsoft Agent Framework
- **Claude Code**: 127k stars, terminal-native, plugin system
- **Cursor**: VS Code fork, permission-based sandbox, excellent UX polish
- **Continue.dev**: CI/CD AI checks, source-controlled policies

### IDE Architecture
- **Eclipse Theia**: Independent from VS Code, InversifyJS DI, Contribution pattern
- **Theia AI**: Built-in AI integration framework (chat, completion, agents)
