# CLI Session Sharing Protocol Design

## Status

Phase 43 + Phase 46 + Phase 47: Advisory locking implemented for all session and alias writes. IDE reads local sessions via the CLI bridge. IDE writes now use a daemon-first HTTP path when the local Python daemon is available and fall back to the Phase 46 CLI bridge when it is unavailable. No shared server, tenant sync, or cross-device claims are implemented here.

## Goal

Allow ARC CLI and IDE surfaces to share local chat session state safely without inventing a network service or weakening workspace trust boundaries.

## Current Local Format

Source: `python/src/agent_runtime_cockpit/cli_repl/session.py`

Learned:
- Canonical sessions are stored under `~/.arc/sessions/<session_id>/session.json` by default.
- `ARC_STUDIO_SESSIONS_DIR` can redirect session storage for tests or local override.
- Current schema version is `4`.
- `ChatSession.load()` and `ChatSession.list_sessions()` already migrate/read legacy flat session JSON.

Implementation consequence:
- CLI session resume/search should reuse `ChatSession.load()` and `ChatSession.list_sessions()`.
- IDE bridge should consume the same canonical JSON only after a lock/version protocol exists.

Confidence: high.

Unresolved questions:
- Whether IDE should keep an in-memory mirror or read-on-demand.
- Whether session writes need atomic file locking on all target OSes.

## Proposed Protocol

| Field | Requirement |
| --- | --- |
| Transport | Local filesystem + local daemon HTTP for IDE writes. CLI fallback remains available. |
| Root | `ARC_STUDIO_SESSIONS_DIR` if set, else `~/.arc/sessions`. |
| Record | `<session_id>/session.json`. |
| Schema | `version: 4` required; readers may migrate older versions through `ChatSession.model_validate`. |
| Writes | CLI session writes use atomic temp-file write plus rename. |
| Locking | `session.json.lock` advisory lock (`fcntl.flock` on POSIX; documented no-op on Windows single-writer assumption). Implemented for `ChatSession.save()` and `_write_aliases()`. |
| Trust | Session content is user-local state, not workspace trust. Execution still requires normal trust/sandbox gates. |
| Secrets | Session JSON must not contain raw provider keys or tokens. |
| Identity | `id`, `created_at`, `updated_at` remain source of truth. |

## Implemented In This Phase

- `/sessions resume <session_id>` loads an existing local session into the active REPL session.
- `/sessions search <query>` searches saved local session messages.
- `/history search <query>` searches active-session history.
- `arc studio sessions show <id>` reads a redacted local session.
- `arc studio sessions export <id> --output <path>` writes a redacted `arc.session.bundle` v1.
- `arc studio sessions import <path>` validates schema, version, integrity, ID safety, and secret-looking content before atomic write.

## Explicit Non-Goals

- No IDE daemon.
- No remote sync.
- No shared-server or multi-tenant coordination.
- No bypass of run/sandbox/HITL policy.

## Implemented In Phase 43

- `storage/advisory_lock.py`: POSIX `fcntl.flock` advisory lock with spin-wait; Windows documented no-op.
- `ChatSession.save()` and `_write_aliases()` use `lock=True` via `write_text_atomic`.
- `SessionBridgeService` (TypeScript, read-only): `listChatSessions()` and `getChatSession(id)` via `arc studio sessions --json` / `show`. No shell=true.
- `ArcService` protocol: `listChatSessions()` and `getChatSession()` methods added.

## Implemented In Phase 46 (IDE Write Bridge)

### Write Path Contract

| Layer | Component | Role |
| --- | --- | --- |
| Python advisory lock | `storage/advisory_lock.py` `fcntl.flock` | Authoritative data-safety lock |
| Python CLI write cmds | `arc studio sessions write/delete/update` | Atomic writes under advisory lock + trust gate |
| TypeScript TS mutex | `SessionBridgeService._serializedWrite()` | Second-layer defense; serializes TS-side write calls |
| TypeScript bridge | `SessionBridgeService.importSession/deleteSession/updateSessionField()` | argv-only; no shell=True; env allowlist |
| ArcService protocol | `arc-protocol.ts` | TypeScript interface for all session write methods |

### Lock layers

1. **Python `fcntl.flock` (POSIX)** — authoritative. Acquires exclusive lock on `session.json.lock` before temp-write + rename. Spins up to 5000ms; raises `AdvisoryLockUnavailable` on timeout → `LOCK_CONTENTION` err envelope.
2. **TypeScript `_serializedWrite()` mutex** — second-layer defense. One pending write at a time; rejects with `LOCK_CONTENTION` if `pendingWriteCount >= 1`. Reduces contention against Python lock; not a replacement for it.
3. **Windows** — Python advisory lock is a documented no-op. TypeScript mutex still applies. Single-writer IDE assumption documented.

### Error codes

| Code | When | Python source | TypeScript source |
| --- | --- | --- | --- |
| `LOCK_CONTENTION` | Advisory lock timeout or TS mutex queue full | `AdvisoryLockUnavailable` → `err(ArcErrorCode.LOCK_CONTENTION)` | `ArcError(ArcErrorCode.LOCK_CONTENTION)` |
| `PERMISSION_DENIED` | Workspace untrusted | `TrustEnforcementError` → `err(ArcErrorCode.PERMISSION_DENIED)` | Re-thrown from parsed CLI err envelope |
| `INVALID_INPUT` | Unsafe ID / bad field / secret value | Validation before lock | `SESSION_ID_RE` or field allowlist check |
| `RUN_NOT_FOUND` | Session doesn't exist (delete/update) | `err(ArcErrorCode.RUN_NOT_FOUND)` | Re-thrown from parsed CLI err envelope |

### Session ID validation

`SESSION_ID_RE = /^[A-Za-z0-9_-]{1,80}$/` — shared pattern enforced in both:
- Python: `cli_repl/session.py:SESSION_ID_RE`
- TypeScript: `session-bridge-service.ts:SESSION_ID_RE`

### Allowed update fields (from IDE)

Only `mode`, `runtime_mode`, `profile_id`, `isolation_id` — no history mutation, no secret fields.

### Payload limits

- History: capped at 200 entries (TypeScript truncates before sending; Python also enforces)
- Payload size: 512 KB cap enforced by Python `arc studio sessions write`

## Implemented In Phase 47 (Daemon HTTP Write Protocol)

### Daemon Endpoints

| Method | Path | Behavior |
| --- | --- | --- |
| `POST` | `/api/sessions/write` | Validate ChatSession JSON, reject secrets, cap history at 200, cap payload at 512 KB, trust gate, advisory lock, write session. |
| `DELETE` | `/api/sessions/{session_id}` | Validate ID, trust gate, advisory lock, delete session file and empty directory. |
| `PATCH` | `/api/sessions/{session_id}` | Validate ID, allowlist field update (`mode`, `runtime_mode`, `profile_id`, `isolation_id`), reject secrets, trust gate, advisory lock. |

All endpoints return ARC `ok(...)` / `err(...)` envelopes. HTTP status mapping:

| HTTP | Error code | Meaning |
| --- | --- | --- |
| `400` | `INVALID_INPUT` | invalid JSON, unsafe ID, secret-looking content, bad field, payload too large |
| `403` | `PERMISSION_DENIED` | workspace trust enforcement denied |
| `404` | `RUN_NOT_FOUND` | session not found for delete/update |
| `429` | `LOCK_CONTENTION` | advisory lock timeout |
| `500` | `INTERNAL_ERROR` | unexpected failure |

### TypeScript Fallback Contract

`SessionBridgeService` tries daemon HTTP first for writes when `ARC_PYTHON_DAEMON_URL` is set or the default loopback daemon (`http://127.0.0.1:7777`) is discoverable. Daemon URL discovery is cached for 30 seconds.

Fallback to CLI happens only when the daemon is unavailable:
- no daemon URL
- network error / refused connection / abort
- daemon returns `503` or `504`

No CLI fallback occurs for daemon `400`, `403`, `404`, or `429`; those are surfaced as typed `ArcError` values.

### Session Changed Event

Daemon writes emit an in-memory `session_changed` event through the existing event bus:

```json
{
  "event_type": "session_changed",
  "session_id": "s-...",
  "operation": "write|delete|update",
  "workspace": "/path/to/workspace",
  "coverage_class": "session_lifecycle_ephemeral",
  "audit_persistence": "excluded",
  "exclusion_reason": "in-memory event bus only; not part of per-run audit chain"
}
```

The event is ephemeral and not persisted. TypeScript `SessionBridgeService.onSessionChanged` fires only after successful daemon writes, not after CLI fallback. Phase 48 explicitly classifies these daemon session mutation notifications as audit-excluded; if a future run path embeds one inside an audit chain record, `arc audit verify` may verify the surrounding chain envelope, but this phase does not add persisted session-event audit coverage.

### Windows Decision

ADR-025 keeps Windows as a documented single-writer best-effort target for Phase 47. No `LockFileEx` native binding is implemented. POSIX `fcntl.flock` remains authoritative for macOS/Linux. TypeScript mutex remains a second-layer IDE defense, not a replacement for OS locking.

## Deferred After Phase 47

1. WebSocket/IPC push protocol for live IDE auto-refresh.
2. Persisted session event replay.
3. Windows native `LockFileEx` if Windows becomes a supported multi-writer target.
4. Cross-device or multi-session concurrent write support.

## Next Steps

1. Design WebSocket/IPC push protocol for session auto-refresh.
2. Decide whether session_changed events need persistence.
3. Windows lock parity: evaluate `LockFileEx` via native addon if needed.
