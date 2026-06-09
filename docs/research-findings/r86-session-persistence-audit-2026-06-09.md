# R86 ARC Continuum — Session Persistence Audit

Date: 2026-06-09
Auditor: Agentic Auditor
Repository: Hansuqwer/ARC-STUDIO @ e2526c3
Scope: Audit every piece of session state lost on process exit. Design minimal SQLite schema
for `~/.arc/sessions/{id}/state.db` covering only the gaps. Reuse `auth/manager.py` Fernet
key for encryption.

---

## 1. State Inventory — What Exists vs. What Survives

| State | Location | Survives Restart? | Evidence |
|---|---|---|---|
| Chat history (messages) | `cli_repl/session.py` → `~/.arc/sessions/{id}/session.json` | ✅ Yes | `ChatSession.save()` writes atomic JSON |
| Session ID | `cli_repl/session.py` → `session.json` | ✅ Yes | `id` field |
| Mode (plan/build/auto) | `cli_repl/session.py` → `session.json` | ✅ Yes | `mode` field |
| Runtime mode | `cli_repl/session.py` → `session.json` | ✅ Yes | `runtime_mode` field |
| Profile ID | `cli_repl/session.py` → `session.json` | ✅ Yes | `profile_id` field |
| Isolation ID | `cli_repl/session.py` → `session.json` | ✅ Yes | `isolation_id` field |
| Allow paid calls | `cli_repl/session.py` → `session.json` | ✅ Yes | `allow_paid_calls` field |
| Tools enabled | `cli_repl/session.py` → `session.json` | ✅ Yes | `tools_enabled` field |
| Max tool iterations | `cli_repl/session.py` → `session.json` | ✅ Yes | `max_tool_iterations` field |
| Available tools | `cli_repl/session.py` → `session.json` | ✅ Yes | `available_tools` field |
| Created/updated timestamps | `cli_repl/session.py` → `session.json` | ✅ Yes | `created_at`, `updated_at` |
| Metadata | `cli_repl/session.py` → `session.json` | ✅ Yes | `metadata` dict |
| Session spend (budget) | `budget/storage.py` → SQLite WAL | ✅ Yes | `budget_spend` table, SESSION scope |
| Provider day spend | `budget/storage.py` → SQLite WAL | ✅ Yes | `budget_spend` table, PROVIDER_DAY scope |
| Run traces | `storage/indexed_store.py` → `~/.arc/traces/{run_id}.jsonl` | ✅ Yes | Atomic temp-file + replace |
| Run receipts | `storage/indexed_store.py` | ✅ Yes | JSONL store |
| Audit chain | `audit/session.py` → `~/.arc/audit/audit_chain.jsonl` | ✅ Yes | Append-only JSONL |
| HITL decisions | `mcp/session.py` → `hitl_store.db` | ✅ Yes | SQLite store |

---

## 2. State Inventory — What Is Lost

| State | Location | Survives? | Impact |
|---|---|---|---|
| TUI transcript | `tui/screen.py` → `self.data` (DataStore) | ❌ Lost | All chat history in TUI session is ephemeral |
| TUI scroll position | `tui/screen.py` → Transcript widget | ❌ Lost | User loses reading position |
| Current provider | `tui/screen.py` → DataStore | ❌ Lost | Provider selection resets to default |
| Current model | `tui/screen.py` → DataStore | ❌ Lost | Model selection resets |
| Active run context | `tui/screen.py` → `_session` (lazy) | ❌ Lost | If a run is in progress, context is lost |
| Command palette MRU | `tui/screen.py` → SlashMenu | ❌ Lost | MRU ordering resets |
| Daemon connection state | `tui/screen.py` → `_daemon_was_online` | ❌ Lost | Reconnection detection resets |
| Theme selection | `tui/theme.py` → ThemeManager | ⚠️ Partial | May be saved elsewhere; needs verification |
| Activity tray visibility | `tui/screen.py` → ActivityTray | ❌ Lost | Toggle state resets |
| Toaster notifications | `tui/screen.py` → Toaster | ❌ Lost | Ephemeral by design — acceptable |

---

## 3. Gap Analysis

The canonical `ChatSession` persists the core chat metadata. The gap is:

1. **TUI runtime state** — `DataStore` in `tui/screen.py` is purely in-memory. The `Transcript`
   widget rebuilds from `self.data.entries` which are not saved.
2. **Active run context** — If a run is interrupted by process exit, the partial run state is
   lost (traces up to that point ARE written to JSONL incrementally).
3. **IDE-side state** — Theia has its own workspace state; ARC extension does not persist
   run-specific UI state.

---

## 4. Minimal Schema for `~/.arc/sessions/{id}/state.db`

Reuse the existing Fernet key from `auth/manager.py` for encryption of sensitive fields.

```sql
-- Schema: session_state v1
-- File: ~/.arc/sessions/{session_id}/state.db

PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS session_meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS transcript_entries (
    seq_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp   TEXT NOT NULL,
    role        TEXT NOT NULL,   -- user | assistant | system | tool
    content     TEXT NOT NULL,   -- encrypted with Fernet
    metadata    TEXT             -- JSON, encrypted
);

CREATE TABLE IF NOT EXISTS ui_state (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL  -- JSON (non-sensitive, not encrypted)
);

CREATE TABLE IF NOT EXISTS run_context (
    run_id          TEXT PRIMARY KEY,
    status          TEXT NOT NULL,   -- running | paused | completed | failed
    started_at      TEXT NOT NULL,
    last_event_id   INTEGER,
    provider_id     TEXT,
    model_id        TEXT,
    context_budget  INTEGER,
    context_used    INTEGER,
    metadata        TEXT             -- JSON
);

CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY
);
INSERT OR IGNORE INTO schema_version (version) VALUES (1);
```

---

## 5. Implementation Plan — `arc continuum` CLI

```bash
arc continuum list              # List resumable sessions (id, name, updated_at, run_status)
arc continuum resume <id>       # Resume session (TUI or IDE)
arc continuum snapshot <id>     # Force snapshot of current state
arc continuum delete <id>       # Delete session + traces
arc continuum import <path>     # Import legacy flat .json session
```

**File to create:** `python/src/agent_runtime_cockpit/continuum/store.py`
**Stub already written at:** `python/src/agent_runtime_cockpit/continuum/store.py`

Key wire points:

| File | Change | Description |
|---|---|---|
| `tui/screen.py` | `on_mount()` → `restore_session()` | Check for `state.db`; restore transcript + UI state |
| `tui/screen.py` | After every submitted message → `append_transcript_entry()` | Incremental append |
| `cli_repl/session.py` | `ChatSession.save()` also calls `SessionStore.save_meta()` | Sync canonical JSON with continuum DB |
| `budget/storage.py` | No change | Already persisted |
| `storage/indexed_store.py` | No change | Already persisted |

---

## 6. Resume Flow

```
User runs: arc continuum resume s-abc123

1. Read ~/.arc/sessions/s-abc123/session.json (canonical ChatSession)
   → Load mode, provider, history, metadata

2. Read ~/.arc/sessions/s-abc123/state.db (continuum store)
   → Load transcript entries (if more recent than session.json)
   → Load UI state (scroll position, theme, activity tray visibility)
   → Load run_context (if a run was interrupted)

3. If run_context.status == "running":
   → Check if run_id still active in EventBroker
   → If yes: reconnect to SSE stream (R87 dependency)
   → If no: mark as "paused", offer user to restart or autopsy

4. Start TUI with restored state
```

**Dependency:** Step 3 requires R87. Steps 1–2 and 4 are independent of R87.

---

## 7. Encryption Plan

```python
from agent_runtime_cockpit.auth.manager import FernetKeyManager

key_manager = FernetKeyManager()
fernet_key = key_manager.get_or_create_key()  # Returns 32-byte Fernet key
store = SessionStore(session_id, fernet_key)
```

- **Encrypt:** `transcript_entries.content`, `transcript_entries.metadata`
- **Do NOT encrypt:** `ui_state` (non-sensitive), `session_meta`, timestamps, `run_id`, `status`

---

## 8. Kiro Session Prompt

> Implement `python/src/agent_runtime_cockpit/continuum/store.py` using the stub at that path.
> The store must use `auth/manager.py` `FernetKeyManager` for encryption. Implement
> `save_transcript`, `load_transcript`, `save_ui_state`, `load_ui_state`, `save_run_context`,
> `load_run_context`. Add `arc continuum list` and `arc continuum resume` CLI commands to
> `cli_repl/session.py`. The resume command must restore the TUI transcript from the continuum
> store if it is more recent than the canonical `session.json`. All existing tests must pass
> (`pytest tests/cli tests/tui -q`).
