# ADR-025 — Windows Session Lock Posture for Phase 47

## Status

Accepted — Phase 47 keeps Windows as documented single-writer best-effort.

## Context

Phase 43 added `storage/advisory_lock.py` with POSIX `fcntl.flock` locking and a documented Windows no-op. Phase 46 added IDE session writes through the TypeScript CLI bridge. Phase 47 adds daemon HTTP write routes and daemon-first TypeScript writes.

The current product scope remains macOS/Linux first. Windows is not a supported multi-writer target for session mutation in this phase.

## Decision

Do not implement a Windows `LockFileEx` native binding in Phase 47.

Windows session writes remain:
- Atomic temp-file replace via `write_text_atomic`.
- Best-effort single-writer semantics.
- Protected in the TypeScript IDE path by a per-instance write mutex.
- Not protected by an OS-level interprocess advisory lock.

## Rationale

- Phase 47 is a daemon protocol slice, not a cross-platform native-locking slice.
- POSIX `fcntl.flock` already covers the current macOS/Linux target.
- Windows support would require a native layer, packaging, CI coverage, and failure-mode tests.
- The TypeScript mutex reduces IDE-origin contention but is not a substitute for a Windows OS lock.

## Consequences

- Docs must continue to say Windows locking is a no-op / single-writer assumption.
- No production/shared-server/concurrent-user claim may be made from Phase 47.
- If Windows becomes a supported multi-writer target, a future phase must implement and test `LockFileEx` or an equivalent native lock.

## Unblock Criteria for Windows Native Lock

1. Explicit product decision to support Windows IDE session writes beyond single-writer use.
2. Native lock implementation with timeout semantics matching POSIX behavior.
3. Tests proving lock contention, timeout, cleanup, and atomic replace behavior on Windows CI.
4. Packaging path for the native binding.
