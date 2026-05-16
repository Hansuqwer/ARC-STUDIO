# Sessions / Daemon Review

## Current ARC Spec

ARC Studio specifies a shared session lifecycle and explicit daemon state machine as first-class v0.1 features. Both CLI and IDE attach to the same workspace session by default, with a background daemon managing run execution, event brokering, and crash recovery.

### Session Lifecycle (§7.14.1)

- **Session ID**: ULID (26 characters, lexicographically sortable, time-ordered), separate from `run_id`
- **Storage**: Per-platform session root directories:
  - Linux: `~/.local/share/arc-studio/sessions/<session_id>/`
  - macOS: `~/Library/Application Support/arc-studio/sessions/<session_id>/`
  - Windows: `%LOCALAPPDATA%\arc-studio\sessions\<session_id>\`
- **Per-session files**: `metadata.yaml`, `transcript.jsonl`, `runs.jsonl`, future `audit.log`
- **Transcript journal**: Every assistant turn is journaled to `transcript.jsonl` before rendering
- **Crash recovery**: If journal has incomplete/unrendered turns, next launch offers automatic `/resume`
- **Multi-client attach**: CLI and IDE attach to the same workspace session by default; both surfaces show `{N} clients attached`
- **Concurrent writes**: Serialized by daemon session lock
- **Session commands**: `/new` creates new session, `/clear` starts fresh (previous transcript saved), `/compact` summarizes context, `/resume` resumes previous session, `/exit` saves and quits
- **Status line**: Shows session ID as a segment, middle-elided when space constrained

### Daemon Lifecycle (§7.14.2)

ARC Studio defines an 8-state daemon state machine with explicit recovery actions:

| State | CLI Startup | IDE Startup | `/status` | `/doctor` | Recovery |
|---|---|---|---|---|---|
| `not-installed` | error before chat | setup banner | unavailable | fail | install package / run bootstrap |
| `stopped` | auto-start allowed | auto-start allowed | stopped | warning | start daemon |
| `starting` | progress row | loading badge | starting | pending | wait/retry |
| `running` | normal | normal | running + version | pass | none |
| `stale` | prompt before replace | prompt before replace | stale pid | warning | confirm replace |
| `port-conflict` | do not kill process | do not kill process | conflict | fail | choose port or stop other process |
| `unreachable` | chat read-only | disconnected banner | unreachable | fail | restart daemon |
| `version-mismatch` | show client/daemon versions | show banner | mismatch | fail | upgrade matching package |

**Key daemon rules** (§7.14.2):
- `arc-studio` may auto-start daemon only from `stopped` state
- Must NOT kill another process on `port-conflict`
- Must prompt before replacing stale daemon
- Version mismatch reports exact client and daemon versions

### DaemonStatusBadge Component (§9)

```ts
interface DaemonStatusBadgeProps {
  state: 'not-installed' | 'stopped' | 'starting' | 'running' | 'stale' | 'port-conflict' | 'unreachable' | 'version-mismatch';
  version?: string;
  port?: number;
  recoveryAction?: string;
}
```

State-to-tone mapping:
- `running` → `state.success`
- `starting` → `state.running`
- `stale` / `port-conflict` / `version-mismatch` → `state.warning`
- `unreachable` / `not-installed` → `state.danger`

### Daemon Bundling (ADR-008)

- **Current**: Standalone pip package, manual start via `uv run arc serve` or `arc serve`, connects at `127.0.0.1:7777`
- **Target for Electron**: Embedded Python bundled in app resources, auto-started by Electron main process
- **Phased approach**:
  - Phase 1: Packaging spike (compare PyInstaller, embedded Python, uv-managed venv)
  - Phase 2: Selected bundling implementation
  - Phase 3: Update/bootstrap refinement
- **Auto-start**: Controlled by `arc.daemon.autoStart` preference (default `false` in dev, `true` in bundled mode)
- **Version management**: Daemon version verified on startup; mismatch throws explicit error
- **Token auth**: `ARC_DAEMON_TOKEN` auto-generated per session via `crypto.randomBytes(32)`

### Session/CLI Integration (CLI_IDE_REDESIGN_PLAN §2.2, §2.5, §4.5)

- `arc-studio -c` — continue last session
- `arc-studio -r <session-id>` — resume specific session
- `arc-studio "query"` — launch with initial prompt (creates or continues session)
- Session state stored as JSON with: id, workspace, runtime, model, mode, messages, runs, timestamps
- `~/.arc/sessions/` with `latest` symlink to most recent session

### Backend Infrastructure (IMPLEMENTATION_PLAN P1a)

- **JobSupervisor**: Run lifecycle management, cancellation, orphan recovery
- **EventBroker**: Bounded queue pub/sub, SSE streaming, replay fallback
- **SQLite index**: JSONL remains source of truth; SQLite is rebuildable index for run listing/status/search
- **Workspace trust**: External store at `~/.arc/trusted-workspaces.json`; default untrusted until explicit approval

---

## Comparable Products / Research

| Feature | Claude Code | OpenCode (archived → Crush) | Codex CLI (OpenAI) | Aider | VS Code Copilot | LangGraph Studio | ARC Studio (spec) |
|---|---|---|---|---|---|---|---|
| **Session ID format** | Internal (not exposed) | SQLite auto-increment | Internal thread ID | None (single session) | Conversation ID (internal) | Thread ID (LangGraph checkpoint) | **ULID** (explicit, user-visible) |
| **Session storage** | Cloud (Anthropic-managed) + local cache | SQLite (`~/.opencode/`) | Cloud (OpenAI-managed) | In-memory + git commits | Cloud (Microsoft-managed) | Checkpoint saver (SQLite/Postgres) | **JSONL + metadata.yaml per session dir** |
| **Session resume** | `-c` (continue), `-r` (resume), `--resume`, `--teleport` (cross-device) | `-c` (cwd), `-s` (session), `Ctrl+A` switch session, share links | `resume`, `fork` (create branch from session) | `--restore-chat-history` (limited) | Conversation history panel | Thread/conversation checkpoint restore | **`/resume`, `/clear`, auto-resume on crash** |
| **Multi-client attach** | ✅ Cloud sessions accessible from CLI, IDE, desktop, web, iOS | ❌ Single process | ✅ App + CLI + IDE share cloud threads | ❌ Single process | ✅ VS Code + web share conversations | ✅ Studio + deployed agent share threads | **CLI + IDE share same workspace session** |
| **Crash recovery** | ✅ Cloud persists all state | ✅ SQLite persists messages | ✅ Cloud persists all state | ❌ Loses context on crash | ✅ Cloud persists | ✅ Checkpoint-based recovery | **JSONL journal + auto-resume on incomplete turns** |
| **Session history browse** | ✅ Full searchable history | ✅ `Ctrl+A` session switcher | ✅ Thread list in app/desktop | ❌ No history browsing | ✅ Chat history panel | ✅ Thread list in Studio | **Resume only — no history browser specified** |
| **Session fork/branch** | ❌ | ❌ | ✅ `fork` creates session branch | ❌ | ❌ | ✅ Checkpoint replay creates new thread | **Not specified** |
| **Session compacting** | ✅ Auto-compaction with skill carry-forward | ✅ `/compact` manual + auto-compact at 95% context | ✅ Auto-compaction via Chronicle memory | ❌ | ✅ Context management | ❌ (developer responsibility) | **`/compact` specified (no implementation details)** |
| **Session export/share** | ✅ `/share` creates shareable link | ✅ Share links | ❌ | ❌ | ❌ | ✅ Trace export | **Not specified** |
| **Daemon architecture** | Cloud-only (no local daemon) | Single process (no daemon) | Cloud + local CLI (no daemon) | Single process (no daemon) | Cloud (VS Code extension proxies) | LangGraph Server (separate deployment) | **Local loopback daemon at 127.0.0.1:7777** |
| **Daemon state machine** | N/A (cloud) | N/A (single process) | N/A (cloud) | N/A (single process) | N/A (cloud) | N/A (server-managed) | **8-state explicit machine with recovery** |
| **Auto-start daemon** | N/A | N/A | N/A | N/A | N/A | Manual server start | **Auto-start from `stopped` state** |
| **Version mismatch handling** | N/A | N/A | N/A | N/A | N/A | N/A | **Explicit banner with client/daemon versions** |
| **Port conflict handling** | N/A | N/A | N/A | N/A | N/A | N/A | **Never kill other process; prompt user** |
| **Stale detection** | N/A | N/A | N/A | N/A | N/A | N/A | **PID check + prompt before replace** |
| **Session locks** | Cloud-managed concurrency | SQLite write locking | Cloud-managed | File-based git locking | Cloud-managed | Checkpoint write locking | **Daemon session lock for concurrent writes** |

### Key Observations

1. **ARC is unique in specifying a local daemon with an explicit state machine.** Every comparable product either uses cloud-managed sessions (Claude Code, Codex, VS Code Copilot) or runs as a single process (Aider, OpenCode). LangGraph Studio uses a separate server but doesn't expose a state machine to the user.

2. **ULID session IDs are unusual.** Most products use internal opaque IDs or auto-increment integers. ULID gives ARC time-ordered, user-inspectable session identifiers — a good choice for high-assurance workflows.

3. **Multi-client attach is rare among local tools.** Claude Code achieves this via cloud sync. ARC's local approach (CLI + IDE sharing a session via daemon) is novel but harder to implement correctly.

4. **No competitor exposes daemon lifecycle to users.** The 8-state machine is thorough but may be overkill for v0.1. Most users expect "it just works" — the state machine should be internal, with user-facing messages simplified.

5. **Session history browsing is table stakes.** Every product with session support allows browsing past sessions, not just resuming the latest. ARC's `/resume` without a session list is a gap.

6. **Crash recovery via JSONL journal is solid.** This is more robust than in-memory approaches (Aider) and comparable to SQLite-based recovery (OpenCode). The append-only journal with incomplete-turn detection is a good design.

---

## Gaps

### G1: No Session History Browser
The spec defines `/resume` and `-r <session-id>` but provides no way to list, search, or browse past sessions. Users must know the ULID to resume a specific session. Every competitor with session support has a session list or switcher.

### G2: Session Lock Implementation Not Specified
The spec says "concurrent writes are serialized by daemon session lock" but doesn't define the lock mechanism. File-based locks (`.lock` files), SQLite advisory locks, or in-process mutex all have different failure modes. Without a spec, implementations will diverge.

### G3: No Session Fork/Branch
Codex CLI supports `fork` to create a session branch from a checkpoint. ARC's session model is linear — `/new` creates a fresh session, `/clear` saves the old one. Forking would let users explore alternative approaches from a shared starting point.

### G4: Session Export/Share Not Defined
No mechanism exists to export a session transcript, share it with teammates, or import it into another workspace. Claude Code has `/share`, OpenCode has share links. ARC's audit focus makes export even more important (for review/compliance).

### G5: Compacting Implementation Missing
`/compact` is specified as "summarise context to free tokens" but no implementation details exist. What model does the summarization? What context is preserved? How does compact interact with the transcript journal? OpenCode has auto-compact at 95% context with session continuation — ARC should match this.

### G6: Daemon Auth Is Underdefined
ADR-008 mentions `ARC_DAEMON_TOKEN` auto-generated per session, but the spec doesn't define:
- Token rotation policy
- How CLI authenticates to daemon when IDE started it
- What happens when token expires mid-session
- Whether token is stored in session metadata or ephemeral

### G7: No Session TTL or Cleanup
Sessions accumulate indefinitely in `~/.local/share/arc-studio/sessions/`. No TTL, no max-count, no cleanup policy. OpenCode uses SQLite with configurable retention. ARC needs `arc runs prune` equivalent for sessions.

### G8: Daemon Port Is Hardcoded
`127.0.0.1:7777` is hardcoded throughout. The spec mentions "choose port" as recovery for `port-conflict` but doesn't define how to configure an alternative port. This should be a config option (`daemon.port`).

### G9: Cross-Workspace Session Behavior Undefined
The spec says CLI and IDE attach to "the same workspace session by default" but doesn't define:
- What happens when the user switches workspaces in the IDE
- Whether sessions are workspace-scoped or global
- How a session's workspace binding is validated on resume

### G10: No Session Metadata Schema
`metadata.yaml` is mentioned but no schema is defined. What fields are required? What's the versioning strategy? How does metadata evolve across ARC versions?

### G11: Daemon Crash Mid-Run Not Addressed
The spec covers daemon states but not what happens to an in-progress run when the daemon crashes. Does the run fail? Can it be resumed? What events are lost? The JobSupervisor handles orphan recovery (P1a) but the user-facing behavior isn't specified.

### G12: No Session Encryption
Session transcripts may contain sensitive code, API responses, and provider keys (redacted, but still). No encryption at rest is specified. For high-assurance workflows, this matters.

---

## Improvement Proposals

| Proposal | Why | v0.1/v0.2/v0.3 | Risk | Spec edits |
|---|---|---|---|---|
| **P1: Session list command** | Users need to browse past sessions, not just resume latest. `/sessions` lists recent sessions with workspace, runtime, last activity, and run count. | v0.1 | Low — just a listing over existing session dirs | Add `/sessions` to §10.4 help text; add session list CLI command |
| **P2: Session metadata schema** | Without a schema, `metadata.yaml` will drift and break across versions. Define required fields, versioning, and migration strategy. | v0.1 | Low — schema definition only | Add §7.14.3 "Session Metadata Schema" with required fields and version |
| **P3: Session lock mechanism** | Concurrent CLI+IDE writes need a defined lock strategy. Use file-based lock (`.lock` with PID + timestamp) with stale-lock detection. | v0.1 | Medium — lock bugs cause hangs | Add lock mechanism to §7.14.1; define stale-lock timeout (30s) |
| **P4: Daemon port config** | Hardcoded port 7777 will conflict. Add `daemon.port` config option with fallback scanning (7777-7787). | v0.1 | Low — config change only | Add `daemon.port` to config model; update §7.14.2 port-conflict recovery |
| **P5: Session TTL and cleanup** | Sessions accumulate forever. Add `session.max_age_days` (default 30) and `session.max_count` (default 50). Auto-prune on launch. | v0.2 | Low — cleanup logic | Add session retention config; add `arc sessions prune` CLI |
| **P6: Auto-compact on context overflow** | Long sessions hit context limits. Auto-trigger summarization at 90% context usage, create compacted continuation session. | v0.2 | Medium — LLM summarization quality | Add auto-compact behavior to §7.14.1; define compaction model selection |
| **P7: Session fork** | Users want to explore alternatives from a checkpoint. `/fork` creates a new session with the same transcript up to current point. | v0.2 | Low — copy + new ULID | Add `/fork` to §10.4; define fork semantics (transcript copy, new ULID, parent ref) |
| **P8: Session export/import** | Audit/compliance requires session export. `arc sessions export <id>` produces a portable archive. `arc sessions import` restores. | v0.2 | Medium — portable format design | Add export/import commands; define archive format (tar.gz with metadata + transcript + runs) |
| **P9: Daemon crash run recovery** | When daemon crashes mid-run, the run should be recoverable or explicitly marked as orphaned. Supervisor should checkpoint run state. | v0.1 | High — race conditions, state consistency | Add run recovery behavior to §7.14.2; define orphan state and user-facing recovery |
| **P10: Session workspace binding** | Sessions should be workspace-scoped by default. Resuming a session in a different workspace should warn and require confirmation. | v0.1 | Low — validation check | Add workspace binding to metadata schema; add cross-workspace resume warning |
| **P11: Daemon auth token lifecycle** | Token generation, rotation, and sharing between CLI and IDE need definition. Store token in session metadata for multi-client access. | v0.1 | Medium — security implications | Add token lifecycle to ADR-008; define token storage in session metadata |
| **P12: Session encryption at rest** | For high-assurance workflows, session transcripts should be encrypted. Use workspace-local key derived from trust store. | v0.3 | High — key management, recovery | Add encryption section to §7.14.1; define key derivation and recovery |
| **P13: Session share link** | Quick sharing of session transcripts for collaboration. Upload to ephemeral storage or generate local HTML export. | v0.3 | Medium — hosting/privacy decisions | Add `/share` to §10.4; define share scope and expiry |
| **P14: Daemon health ping interval** | Define how often CLI/IDE ping the daemon for health checks. Current spec implies continuous checking but no interval defined. | v0.1 | Low — timing config | Add `daemon.health_interval_ms` (default 2000ms) to config |
| **P15: Session attach indicator** | When CLI and IDE share a session, both should show a clear indicator. Spec mentions `{N} clients attached` but doesn't define how client count is tracked. | v0.1 | Low — reference counting | Add client tracking mechanism to §7.14.1; define attach/detach events |

---

## Recommended Decisions

### D1: Sessions are per-workspace by default
**Decision**: Each session binds to a specific workspace path. Resuming a session in a different workspace shows a warning: `Session 01H... was created in /other/workspace. Resume here? Context may not apply.`

**Rationale**: Agent workflows are workspace-specific. File references, run traces, and tool outputs assume a workspace context. Cross-workspace resume should be explicit, not silent.

**Spec edit**: Add workspace binding to §7.14.1 metadata schema; add cross-workspace resume flow to §7.14.1.

### D2: Daemon owns all session writes
**Decision**: The daemon is the sole writer to session files. CLI and IDE send write requests to the daemon via RPC/SSE. Direct file writes from CLI or IDE are prohibited.

**Rationale**: Multi-client attach requires a single source of truth. If CLI and IDE both write to `transcript.jsonl` directly, race conditions are inevitable. The daemon's session lock is the correct serialization point.

**Spec edit**: Update §7.14.1 to explicitly state daemon-owned writes; add write RPC protocol to backend spec.

### D3: CLI and IDE attach to same session by default
**Decision**: When both CLI and IDE are open for the same workspace, they share the active session. No manual session selection needed.

**Rationale**: This is the spec's current position and it's correct. Users expect continuity between CLI and IDE interactions with the same workspace. The `{N} clients attached` indicator provides visibility.

**Spec edit**: No change needed — already specified in §7.14.1. Add implementation note about attach/detach events.

### D4: Daemon crash mid-run marks run as orphaned
**Decision**: When the daemon crashes during an active run, the run is marked as `orphaned` in the SQLite index. On daemon restart, the supervisor checks for orphaned runs and offers recovery: `Run 01H... was interrupted. Retry or mark as failed?`

**Rationale**: Silent failure is worse than explicit orphan status. The JobSupervisor (P1a) already handles orphan recovery — the user-facing behavior just needs specification.

**Spec edit**: Add `orphaned` status to run states; add daemon crash recovery flow to §7.14.2; add orphan recovery prompt to §7.12 error states.

### D5: Keep ULID for session IDs
**Decision**: ULID remains the session ID format. No change.

**Rationale**: ULID is time-ordered, lexicographically sortable, and has sufficient entropy for collision resistance. It's superior to UUID v4 for session IDs where temporal ordering matters (session listing, resume). No competitor uses ULID, but that's a reason to keep it, not change.

**Spec edit**: No change needed.

### D6: Session lock uses file-based locking with stale detection
**Decision**: Use a `.lock` file in the session directory containing PID and timestamp. Lock is acquired before writing to `transcript.jsonl`. Stale locks (PID no longer exists, or timestamp > 30s old) are automatically cleared.

**Rationale**: File-based locks work across processes (CLI daemon, IDE extension host) and survive process restarts. SQLite advisory locks are an alternative but add dependency on SQLite for lock semantics. In-process mutex doesn't work for multi-client scenarios.

**Spec edit**: Add lock mechanism to §7.14.1.

### D7: Daemon port is configurable with fallback range
**Decision**: Default port 7777. Configurable via `daemon.port`. If the configured port is in use, scan 7777-7787 before failing. Port is written to a well-known file (`~/.local/share/arc-studio/daemon-port`) for client discovery.

**Rationale**: Hardcoded ports are fragile. Port scanning provides resilience for common conflicts. The port file enables client discovery without requiring a service registry.

**Spec edit**: Add `daemon.port` config; update §7.14.2 port-conflict recovery.

### D8: Session history browser is v0.1 scope
**Decision**: Add `/sessions` command and `-l`/`--list` CLI flag for session listing. Shows workspace, last activity, run count, and allows selection for resume.

**Rationale**: Session resume without a session list is a significant UX gap. Every competitor has this. The implementation is straightforward (enumerate session dirs, read metadata.yaml, sort by timestamp).

**Spec edit**: Add `/sessions` to §10.4 help text; add session list UI to §7.11 runs section or new §7.14.4.

---

## Specific Spec Edits

### §7.14.1 Session Lifecycle Contract

**Add after current content:**

```
#### Session Metadata Schema

`metadata.yaml` uses this schema:

```yaml
schema_version: 1
session_id: "01J..."          # ULID
workspace: "/path/to/workspace" # Canonical resolved path
created_at: "2026-05-16T14:30:00Z"
updated_at: "2026-05-16T14:35:00Z"
runtime: "swarmgraph"          # Active runtime at session end
model: "claude-sonnet-4-5"     # Active model at session end
mode: "build"                  # Active mode at session end
run_count: 3                   # Number of runs in this session
client_count: 1                # Currently attached clients
parent_session: null           # ULID of parent session (if forked)
daemon_port: 7777              # Port daemon is listening on
daemon_token_file: ".token"    # Relative path to auth token file
```

Unknown `schema_version` major is rejected. Minor version additions are tolerated.

#### Session Lock Mechanism

Concurrent writes are serialized by a file-based lock:

1. Lock file: `<session_dir>/.lock`
2. Lock content: `{pid: N, timestamp: "ISO8601"}`
3. Acquire: Write lock file atomically (write to `.lock.tmp`, rename to `.lock`)
4. Release: Delete lock file
5. Stale detection: If lock PID no longer exists OR timestamp is > 30s old, lock is stale and may be cleared
6. Retry: Failed acquisition retries 3 times with 500ms backoff before reporting error

The daemon owns the lock. CLI and IDE request writes via the daemon.

#### Session Workspace Binding

Sessions bind to the workspace path recorded in `metadata.yaml`. On resume:
- If current workspace matches `metadata.yaml.workspace`: resume normally
- If current workspace differs: show warning and require confirmation:
  `Session 01J... was created in /other/workspace. Resume here? File references and run context may not apply.`
- Symlinked paths resolve before comparison

#### Session Retention

Sessions are retained for 30 days by default. Configurable via `session.max_age_days`. Auto-prune runs on each launch: sessions older than `max_age_days` are archived (moved to `<session_root>/archived/`) then deleted after 7 more days. Maximum session count: 50 (configurable via `session.max_count`). Oldest sessions are pruned first when limit is exceeded.
```

### §7.14.2 Daemon Lifecycle Contract

**Add to recovery column for `stopped` state:**

```
Auto-start only permitted from `stopped`. Daemon port discovery:
1. Check `daemon.port` config (default 7777)
2. If port in use by non-ARC process → `port-conflict`
3. If port in use by ARC daemon with matching version → connect
4. If port in use by ARC daemon with mismatched version → `version-mismatch`
5. If port free → start daemon, write port to `<data_dir>/daemon-port`
6. If configured port unavailable, scan 7777-7787 before failing
```

**Add new row to state table:**

```
| `orphaned-run` | show orphaned runs | show orphaned runs banner | orphaned runs listed | warning | retry or mark failed |
```

**Add after current content:**

```
#### Daemon Crash Recovery

When the daemon crashes during an active run:
1. Run status transitions to `orphaned` in SQLite index
2. On daemon restart, JobSupervisor scans for orphaned runs
3. User is notified: `Run 01J... was interrupted by daemon crash. [Retry] [Mark as failed] [Open trace]`
4. Retry re-executes the run with the same prompt and config
5. Mark as failed sets status to `failed` with reason `daemon_crash`
6. Orphaned runs older than 1 hour are auto-marked as failed

#### Daemon Auth Token Lifecycle

1. Token generated on daemon start: `crypto.randomBytes(32).toString('hex')`
2. Token written to `<session_dir>/.token` (mode 0600)
3. CLI reads token from session directory when attaching
4. Token rotated on daemon restart
5. Token is NOT valid across daemon restarts (clients must re-read)
6. Token file deleted on daemon graceful shutdown
```

### §7.14.3 Session History (new section)

```
### 7.14.3 Session History

`/sessions` lists recent sessions for the current workspace:

```text
┌──────────────────────────────────────── /sessions ───────────────────────────────────────────────┐
│ Session        Workspace          Runtime      Runs  Last activity     Status                    │
│ 01J... (now)   ~/my-project       SwarmGraph   3     2 min ago         active (2 clients)       │
│ 01H...         ~/my-project       SwarmGraph   1     1 hour ago        completed                 │
│ 01G...         ~/other-project    LangGraph    5     3 days ago        completed                 │
│                                                                                                  │
│ [Resume selected] [Delete] [Export] [New session]                                                │
└──────────────────────────────────────────────────────────────────────────────────────────────────┘
```

CLI equivalent: `arc-studio -l` or `arc sessions list --workspace <path>`

Sessions sorted by `updated_at` descending. Active session marked with `(now)`. Multi-client sessions show client count.

Keyboard: arrows navigate, Enter resumes, `d` deletes, `e` exports, `n` creates new session.
```

### §9 DaemonStatusBadge

**Add to props:**

```ts
interface DaemonStatusBadgeProps {
  state: 'not-installed' | 'stopped' | 'starting' | 'running' | 'stale' | 'port-conflict' | 'unreachable' | 'version-mismatch' | 'orphaned-run';
  version?: string;
  port?: number;
  recoveryAction?: string;
  orphanedRunCount?: number;  // New: count of orphaned runs
}
```

**Add state:**
- `orphaned-run` → `state.warning` with recovery action "Review orphaned runs"

### §10.4 Help Text

**Add to Session section:**

```
Session
  /clear      start fresh; previous transcript saved
  /compact    summarise context to free tokens
  /resume     resume a previous session
  /sessions   list recent sessions
  /fork       fork current session from checkpoint
  /exit       save and quit
```

### §7.12 Error States

**Add new row:**

| Error | Exact text | Recovery |
|---|---|---|
| Daemon crash mid-run | `Run 01J... was interrupted by daemon crash.` | `[Retry] [Mark as failed] [Open trace]` |
| Port conflict | `Port 7777 is in use by another process (PID 12345).` | `Choose a different port in /config or stop the other process.` |
| Cross-workspace resume | `Session 01J... was created in /other/workspace. Resume here?` | `[Resume anyway] [Create new session]` |

---

## Acceptance Criteria

### Session Management
- [ ] Session ID uses ULID format (26 characters, time-ordered)
- [ ] Sessions stored in per-platform directories (§7.14.1)
- [ ] `metadata.yaml` follows defined schema with `schema_version`
- [ ] `transcript.jsonl` journals every assistant turn before rendering
- [ ] Incomplete journal entries detected on launch and offered for resume
- [ ] `/sessions` lists recent sessions with workspace, runtime, runs, last activity
- [ ] `/resume` resumes a specific session by ULID
- [ ] `/new` creates a new session
- [ ] `/clear` starts fresh, preserving previous transcript
- [ ] `/compact` summarizes context (manual trigger in v0.1)
- [ ] `/fork` creates a session branch from current checkpoint (v0.2)
- [ ] Session retention: auto-prune after 30 days, max 50 sessions
- [ ] Session export produces portable archive (v0.2)
- [ ] Cross-workspace resume shows warning and requires confirmation

### Multi-Client Attach
- [ ] CLI and IDE attach to same workspace session by default
- [ ] `{N} clients attached` indicator shown when multiple clients connected
- [ ] Concurrent writes serialized by file-based lock with stale detection
- [ ] Daemon owns all session writes; CLI/IDE use RPC
- [ ] Client count tracked in `metadata.yaml`
- [ ] Attach/detach events emitted for real-time client count updates

### Daemon Lifecycle
- [ ] 8-state daemon state machine implemented (§7.14.2)
- [ ] Auto-start only from `stopped` state
- [ ] Never kills another process on `port-conflict`
- [ ] Prompts before replacing stale daemon
- [ ] Version mismatch reports exact client and daemon versions
- [ ] Port configurable via `daemon.port` with fallback scanning (7777-7787)
- [ ] Port written to well-known file for client discovery
- [ ] Auth token generated per session, stored in `.token` file (mode 0600)
- [ ] Token rotated on daemon restart, invalidated on shutdown
- [ ] Health ping interval configurable (default 2000ms)

### Crash Recovery
- [ ] Daemon crash mid-run marks run as `orphaned`
- [ ] Orphaned runs detected on daemon restart
- [ ] User prompted to retry or mark orphaned runs as failed
- [ ] Orphaned runs auto-marked as failed after 1 hour
- [ ] JSONL journal survives daemon crash (append-only writes)
- [ ] Stale session locks auto-cleared after 30s

### DaemonStatusBadge
- [ ] All 8+1 states rendered with correct tones
- [ ] Recovery action shown for each non-running state
- [ ] Version and port displayed when available
- [ ] Orphaned run count shown when applicable
- [ ] Clickable recovery actions (start daemon, choose port, etc.)

### Tests
- [ ] Session creation, resume, clear, new — all tested
- [ ] Concurrent write serialization tested (2 clients)
- [ ] Stale lock detection tested (dead PID, expired timestamp)
- [ ] Cross-workspace resume warning tested
- [ ] Session retention prune tested (age and count limits)
- [ ] All 8 daemon states tested with correct recovery
- [ ] Port conflict detection and fallback scanning tested
- [ ] Daemon crash mid-run → orphaned → recovery flow tested
- [ ] Auth token lifecycle tested (generation, rotation, invalidation)
- [ ] Session metadata schema validation tested
- [ ] Session list sorted correctly, active session marked

---

## Reject / Do Not Build

### R1: Cloud-synced sessions
**Rejected for v0.1.** Cloud sync (like Claude Code's cross-device sessions) requires authentication, storage infrastructure, and privacy review. ARC is local-first. Cloud sync can be added later as an optional feature, but it should not block v0.1 release.

### R2: Real-time collaborative sessions
**Rejected.** Multiple users editing the same session simultaneously is a different product (like Google Docs for agent workflows). The complexity of CRDTs, conflict resolution, and presence indicators is not justified for v0.1. Multi-client attach (CLI + IDE for the same user) is sufficient.

### R3: Session encryption at rest in v0.1
**Deferred to v0.3.** Encryption requires key management, recovery procedures, and platform-specific keychain integration. The current trust model (workspace trust + local-only daemon) provides adequate protection for v0.1. Encryption becomes important when sessions are exported or shared.

### R4: Session share links in v0.1
**Deferred to v0.2.** Share links require either a hosted service (privacy implications) or local file export (less useful). The export/import mechanism (P8) is a better v0.2 starting point. Share links can build on top of export.

### R5: Daemon as a system service (systemd/launchd)
**Rejected for v0.1.** Running the daemon as a persistent system service adds installation complexity and changes the security model (always-on loopback server). The current approach (auto-start on demand) is simpler and matches user expectations for a dev tool. System service can be an advanced option later.

### R6: Session branching with merge
**Rejected.** Git-style session branching and merging is interesting but premature. Fork (P7) is sufficient for v0.2. Merge semantics for agent conversations are undefined and would require significant design work.

### R7: Multiple daemons per machine
**Rejected.** One daemon per workspace is the correct model. Multiple daemons would complicate port management, session discovery, and resource allocation. If a user needs parallel workspaces, each workspace gets its daemon on a different port (handled by fallback scanning).

### R8: Session replay as live re-execution
**Deferred.** True session replay (re-executing every tool call and LLM response deterministically) requires deterministic LLM outputs, tool idempotency, and environment snapshotting. Trace replay (`arc runs replay`) is sufficient for v0.1. Live re-execution is a v0.3+ feature at best.

### R9: Session-level undo/redo
**Rejected.** Undo/redo at the session level is ambiguous — does it undo tool calls? File edits? LLM responses? Git-level undo (`/undo` → git revert) is the correct approach for file changes. Session-level undo is not well-defined enough to implement.

### R10: WebSocket instead of SSE for daemon communication
**Rejected.** SSE is simpler, works well with Theia's HTTP infrastructure, and supports replay fallback. WebSocket would add complexity (connection management, heartbeat, reconnection) without clear benefit for the current use case. The event broker (P1a) already uses SSE.
