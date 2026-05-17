# ADR-003: Storage Strategy — JSONL Traces + SQLite Index

## Status
Proposed

## Context

ARC Studio currently uses:
- **JSONL files** for trace storage (`.arc/traces/{run_id}.jsonl`) — one file per run, one JSON line per `RunRecord`
- **SQLite** (`SqliteStore` in `.arc/arc.db`) — schema exists for `runs` and `audit_log` tables but is NOT exported or wired into the trace store
- No search or indexing capabilities — traces listed by filesystem glob + mtime sort
- No full-text search, no filtering by status/runtime/date, no run aggregation

This works for small numbers of runs but breaks at scale:
- Listing 1000 runs requires reading 1000 JSONL files
- No way to search for runs by workflow name, status, or date range
- No way to aggregate metrics (success rate, avg duration, etc.)
- SQLite schema exists but is unused — dead code

## Decision

### Dual-Store Architecture

Adopt a **JSONL + SQLite** dual-store pattern:

| Store | Purpose | Data | Write Pattern |
|-------|---------|------|---------------|
| **JSONL** | Canonical trace data | Full `RunRecord` with all events | Append-only, one file per run |
| **SQLite** | Searchable index | Run metadata (no events) | Update on state transitions |

### JSONL Store (Unchanged)

JSONL remains the **canonical source of truth** for trace data:
- Location: `.arc/traces/{run_id}.jsonl`
- Format: Single JSON line containing full `RunRecord` (with events array)
- Streaming events: `.arc/traces/{run_id}-events.jsonl` (append-only event log)
- Advantages: Human-readable, git-friendly, portable, no lock-in, crash-resilient

No changes to JSONL format or storage location.

### SQLite Index Schema

Activate and extend the existing `SqliteStore` schema:

```sql
-- Run metadata index (no events stored here)
CREATE TABLE IF NOT EXISTS runs (
    id TEXT PRIMARY KEY,
    workflow_id TEXT NOT NULL,
    runtime TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    started_at TEXT NOT NULL,
    ended_at TEXT,
    duration_ms INTEGER,              -- Computed on completion
    profile_id TEXT DEFAULT 'stub',   -- Security profile used
    isolation TEXT DEFAULT 'none',    -- Isolation provider used
    supervisor_id TEXT,               -- Which supervisor ran this
    cancel_reason TEXT,               -- Why cancelled
    error_detail TEXT,                -- Redacted error message
    trace_path TEXT,                  -- Absolute path to JSONL file
    audit_path TEXT,                  -- Absolute path to audit chain
    metadata TEXT,                    -- JSON blob (non-searchable extras)
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_runs_status ON runs(status);
CREATE INDEX IF NOT EXISTS idx_runs_runtime ON runs(runtime);
CREATE INDEX IF NOT EXISTS idx_runs_workflow ON runs(workflow_id);
CREATE INDEX IF NOT EXISTS idx_runs_started ON runs(started_at);
CREATE INDEX IF NOT EXISTS idx_runs_supervisor ON runs(supervisor_id);

-- Audit log index (actual audit chains live in .arc/audit/)
CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    action TEXT NOT NULL,
    actor TEXT,
    details TEXT,
    verified BOOLEAN DEFAULT 0,
    FOREIGN KEY (run_id) REFERENCES runs(id)
);

CREATE INDEX IF NOT EXISTS idx_audit_run ON audit_log(run_id);

-- Schema version tracking
CREATE TABLE IF NOT EXISTS _schema_version (
    version INTEGER PRIMARY KEY,
    applied_at TEXT NOT NULL
);
```

### Write Strategy

**On run start:**
1. Write `RunRecord` to JSONL (`.arc/traces/{run_id}.jsonl`)
2. Insert metadata row into SQLite `runs` table

**On state transition:**
1. Update JSONL file (rewrite with new status/events)
2. Update SQLite row (status, ended_at, duration_ms, error_detail)

**On completion:**
1. Final JSONL write with all events
2. Final SQLite update with duration_ms, ended_at

**Atomicity:**
- JSONL writes use `mkstemp` + `os.replace()` (already implemented)
- SQLite writes use transactions (autocommit per statement)
- If SQLite write fails, JSONL is still valid (SQLite is a best-effort index)
- If JSONL write fails, run is considered corrupted (SQLite marks as `failed`)

### Read Strategy

**List runs (fast path):**
```sql
SELECT id, workflow_id, runtime, status, started_at, ended_at, duration_ms
FROM runs
WHERE status IN ('completed', 'failed', 'cancelled')
ORDER BY started_at DESC
LIMIT 50 OFFSET 0;
```

**Get run detail:**
1. Read JSONL file from `trace_path` (canonical data)
2. SQLite metadata is a cache, not the source of truth

**Search/filter:**
```sql
-- By status
SELECT * FROM runs WHERE status = 'failed' ORDER BY started_at DESC;

-- By runtime
SELECT * FROM runs WHERE runtime = 'swarmgraph' ORDER BY started_at DESC;

-- By date range
SELECT * FROM runs WHERE started_at >= '2026-05-01' AND started_at < '2026-06-01';

-- By workflow
SELECT * FROM runs WHERE workflow_id = 'my-agent' ORDER BY started_at DESC;

-- Aggregation
SELECT runtime, status, COUNT(*) as count, AVG(duration_ms) as avg_ms
FROM runs
WHERE started_at >= datetime('now', '-7 days')
GROUP BY runtime, status;
```

### Migration

**Phase 1: Activate SQLite index**
- Export `SqliteStore` from `storage/__init__.py`
- Wire into daemon startup (create tables if not exist)
- Insert/update on every run state transition

**Phase 2: Backfill existing traces**
- `arc runs index` CLI command scans `.arc/traces/*.jsonl` and populates SQLite
- Idempotent (skips already-indexed runs)

**Phase 3: Add search endpoints**
- `GET /api/runs?status=failed&runtime=swarmgraph&limit=20`
- `GET /api/runs/stats?since=7d` (aggregation)

**Phase 4: Deprecate pure-filesystem listing**
- `list_runs()` uses SQLite when available, falls back to glob if DB missing

### Full-Text Search (Future)

SQLite FTS5 extension can be added later for full-text search of:
- Workflow IDs
- Event data (output messages, error details)
- Metadata fields

This is deferred until search requirements are validated by usage.

## Consequences

### Positive
- Fast listing without reading hundreds of JSONL files
- Filtering by status, runtime, date, workflow
- Aggregation for dashboards (success rate, avg duration)
- SQLite is zero-dependency, embedded, and battle-tested
- JSONL remains canonical — no lock-in, always portable
- Backward compatible — existing traces work, backfill is optional

### Negative
- Dual-write complexity (must keep JSONL and SQLite in sync)
- SQLite file adds ~100KB-10MB to `.arc/` depending on run count
- Schema migrations needed as RunRecord evolves

### Neutral
- SQLite is an index, not the source of truth — JSONL always wins
- No vector search (that belongs in SwarmGraph gateway's semantic cache)
- No WAL mode needed (single-writer daemon, not concurrent access)

## References
- Current JSONL store: `python/src/agent_runtime_cockpit/storage/jsonl.py`
- Existing SQLite schema (unused): `python/src/agent_runtime_cockpit/storage/sqlite.py`
- Storage exports: `python/src/agent_runtime_cockpit/storage/__init__.py`
- Trace parser: `packages/arc-extension/src/node/services/trace-parser.ts`
