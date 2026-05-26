# CLI Session Sharing Protocol Design

## Status

Design-only for Phase 41.6. No IDE daemon, shared server, tenant sync, or cross-device claims are implemented here.

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
| Transport | Local filesystem only for P0. No socket daemon in this phase. |
| Root | `ARC_STUDIO_SESSIONS_DIR` if set, else `~/.arc/sessions`. |
| Record | `<session_id>/session.json`. |
| Schema | `version: 4` required; readers may migrate older versions through `ChatSession.model_validate`. |
| Writes | Atomic temp-file write plus rename in future IDE bridge. Current CLI `save()` remains unchanged. |
| Locking | Future `session.lock` advisory lock before concurrent IDE/CLI writes. |
| Trust | Session content is user-local state, not workspace trust. Execution still requires normal trust/sandbox gates. |
| Secrets | Session JSON must not contain raw provider keys or tokens. |
| Identity | `id`, `created_at`, `updated_at` remain source of truth. |

## Implemented In This Phase

- `/sessions resume <session_id>` loads an existing local session into the active REPL session.
- `/sessions search <query>` searches saved local session messages.
- `/history search <query>` searches active-session history.

## Explicit Non-Goals

- No IDE daemon.
- No remote sync.
- No shared-server or multi-tenant coordination.
- No bypass of run/sandbox/HITL policy.

## Next Steps

1. Add atomic session write helper and tests.
2. Add advisory lock semantics for IDE/CLI concurrent writes.
3. Define session change event envelope for IDE UI refresh.
4. Implement IDE read-only session browser first.
