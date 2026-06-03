# Local Agent Flight Recorder

**ARC Studio — always-on, local-first, bounded, crash-safe forensic event log.**

---

## What Is the Flight Recorder?

The Local Agent Flight Recorder is a durable, append-only forensic event log for ARC Studio agent runs. Inspired by aircraft Flight Data Recorders (FDR/CVR), it records a continuous stream of run lifecycle events, IR compilation results, policy evaluations, HITL decisions, MCP manifest checks, and error/crash markers — without calling any external service, model, or tool.

Every event is:
- **Redacted before persistence** — secrets never reach disk.
- **Hash-linked** — each event's SHA-256 hash forms a tamper-evident chain.
- **Append-only** — written to immutable JSONL segment files.
- **Bounded** — retention policy enforced by size, age, and count limits.
- **Crash-safe** — metadata written atomically (temp → fsync → os.replace).

---

## What It Is Not

The Flight Recorder is **not**:

- A replacement for existing JSONL traces (`.arc/traces/`).
- A replacement for the audit chain (`audit/chain.py`).
- A database or query engine.
- A remote logging service.
- A model telemetry tool.
- A real-time streaming pipeline.

It extends existing storage by **storing references** to existing traces and audit receipts, adding compact flight-recorder-specific metadata (IR hash, policy risk, simulator report hash, etc.).

---

## Local-Only Safety Model

| Constraint | Enforcement |
|---|---|
| No network I/O | No `requests`, `httpx`, `aiohttp`, `socket`, `urlopen` in any module |
| No subprocess | No `subprocess`, `os.system`, `Popen` |
| No model calls | No LLM API calls — pure data recording |
| No MCP server startup | Registry/manifest referenced by ID only |
| No unauthenticated local server | No `listen()`, no `serve()` |
| No paid calls | Recorder has no billing surface |
| No secrets on disk | Redaction before every persistence operation |
| Fail closed | Malformed sensitive records dropped if `fail_closed=True` |

---

## Redaction Model

Redaction is performed by `flight_recorder/redaction.py`, which wraps the canonical `security/redaction.py` module (single source of truth for ARC secret patterns).

**Patterns detected and redacted:**
- Anthropic API keys (`sk-ant-...`)
- OpenAI API keys (`sk-...` ≥20 chars)
- AWS Access Keys (`AKIA...`)
- GitHub tokens (`ghp_`, `ghs_`, `gho_`, etc.)
- Bearer tokens (`Bearer <token>`)
- URL-embedded passwords (`user:password@host`)
- Generic API key assignments (`api_key = ...`)
- Auth token assignments
- Password fields
- Generic secret/token assignments

**Key-name-based redaction:** any dict key containing `key`, `token`, `password`, `secret`, `credential`, `auth`, `private`, `bearer`, or `signing` has its string value replaced with `[REDACTED]`.

**Test guarantee:** tests in `tests/flight_recorder/test_redaction.py` and `test_export.py` assert that no known secret pattern survives in any persisted file or tarball.

---

## Segment Model

```
.arc/flight/
  index.json                          ← master cross-run index (atomic writes)
  segments/
    <run-id>/
      segment-000000.events.jsonl     ← append-only event log
      segment-000000.meta.json        ← atomic segment metadata + hash
      segment-000001.events.jsonl
      segment-000001.meta.json
  exports/
    <bundle-id>.tar.gz                ← explicit export bundles
```

### Segment files

- **`.events.jsonl`** — one `FlightEvent` JSON object per line, `\n`-delimited.
  - Append-only; never overwritten.
  - `os.fsync()` after every write (crash-safe).
  - Partial/corrupt trailing lines (from crash mid-write) are tolerated during read and verify.

- **`.meta.json`** — `FlightSegment` model, written atomically.
  - Contains `segment_hash` (SHA-256 of all event hashes in order).
  - Contains `previous_segment_hash` for hash chain.

### Hash chain

```
GENESIS → segment_hash[0] → segment_hash[1] → ...
```

Each segment's `previous_segment_hash` is the previous segment's `segment_hash`. `arc flight verify` walks this chain to detect tampering or data loss.

---

## Retention Model

Configured via `FlightRecorderConfig`:

| Setting | Default | Description |
|---|---|---|
| `max_segment_bytes` | 5 MiB | Max size of a single segment before rotation |
| `max_segments` | 200 | Max total segments across all runs |
| `max_total_bytes` | 100 MiB | Max total size of all segment event files |
| `max_age_days` | 30 | Max age of a segment before it is eligible for pruning |

Rules:
- **Never delete an active (open) segment.**
- **Never delete audit receipts** (those live under `.arc/receipts/`, outside the segments directory).
- Oldest closed segments are deleted first (by creation time, ascending).
- Only segments whose files are inside `segments/` are eligible (path escape check).
- `arc flight prune --dry-run` shows what would be deleted without deleting.
- `arc flight prune --apply` executes deletion and updates the index.

---

## Export Bundle Model

`arc flight export --run-id <id> --out bundle.tar.gz` produces a self-contained forensic bundle:

```
bundle.tar.gz
  index.json           ← index filtered to this run
  manifest.json        ← FlightExportBundle (checksums, segment IDs, run IDs)
  segments/
    <run-id>/
      segment-000000.events.jsonl
      segment-000000.meta.json
      ...
```

- SHA-256 checksums for every included file.
- Secret check: if any event file contains detectable secrets, export aborts (fail closed) unless `--no-redact` is passed.
- Bundle is written to the caller-specified path only — no background sync.

---

## Relation to Existing Infrastructure

| Existing system | Flight Recorder relation |
|---|---|
| `.arc/traces/*.jsonl` | FR stores `trace_ref` pointing to run ID; does NOT duplicate trace data |
| `audit/chain.py` | FR stores `audit_ref` pointing to audit chain entry; does NOT replace the chain |
| `storage/jsonl.py` | FR uses its own segment files in `.arc/flight/segments/`; independent |
| `storage/atomic.py` | FR replicates the `write_text_atomic` pattern for crash-safe meta writes |
| `security/redaction.py` | FR wraps this as its canonical redactor |
| `swarmgraph_ir/` | IR compiler emits `ir.compiled` events with `ir_hash` payload |
| `security/policy_linter.py` | Policy linter emits `policy.evaluated` events with risk summary |
| `simulation/` | Simulator emits `simulation.generated` events with report hash |
| `mcp/manifests.py` + `mcp/registry.py` | MCP check events carry manifest hash + server ID (no secrets) |
| `evals/policy_recommend.py` | Eval recommendations referenced by ID, not duplicated |
| `audit/hitl.py` + `audit/hitl_store.py` | HITL events (`hitl.requested/approved/rejected`) stored by reference |

---

## Event Types

| Event type | When emitted |
|---|---|
| `run.started` | Run begins |
| `run.completed` | Run finishes successfully |
| `run.failed` | Run fails |
| `ir.compiled` | SwarmGraph IR compiler completes; payload includes `ir_hash`, node count |
| `policy.evaluated` | Policy linter runs; payload includes `risk_level`, `can_run`, issue count |
| `simulation.generated` | Action Simulator completes; payload includes `simulation_hash` |
| `mcp.manifest.checked` | MCP manifest pinning check; payload includes `server_id`, `manifest_hash`, `drift` |
| `mcp.tool.approved` | MCP tool allowlisted |
| `mcp.tool.blocked` | MCP tool blocked |
| `hitl.requested` | HITL approval requested |
| `hitl.approved` | HITL approved |
| `hitl.rejected` | HITL rejected |
| `consensus.selected` | Consensus protocol selected; payload includes `protocol` |
| `audit.receipt.created` | Audit receipt written; payload includes `receipt_id` |
| `eval.recommendation.generated` | Eval→policy recommendation; payload includes `recommendation_id` |
| `tool.call.planned` | Tool call planned (metadata ref only, no args) |
| `tool.call.completed` | Tool call completed (metadata ref only, no result) |
| `error.raised` | Exception caught; payload includes `error_type`, `message` |
| `crash.marker` | Crash detected; payload includes `reason` |
| `segment.opened` | New segment opened |
| `segment.closed` | Segment closed |
| `recorder.started` | Recorder process started |
| `recorder.stopped` | Recorder process stopped |

---

## CLI Reference

```bash
# Show recorder status and index summary
arc flight status [--workspace PATH] [--json]

# Verify segment integrity and hash chain
arc flight verify [--workspace PATH] [--json]

# Export a run bundle
arc flight export --run-id <id> --out /tmp/bundle.tar.gz [--workspace PATH] [--json]

# Retention: dry-run (default)
arc flight prune [--workspace PATH] [--json]

# Retention: apply
arc flight prune --apply [--workspace PATH] [--json]

# Inspect events for a run
arc flight inspect --run-id <id> [--limit 50] [--workspace PATH] [--json]

# [DEV ONLY] Inject a synthetic event
arc flight record --run-id <id> --event ir.compiled --json-payload '{"ir_hash":"abc"}'
```

### Example output

```bash
$ arc flight status --json
{
  "ok": true,
  "status": {
    "enabled": true,
    "base_dir": ".arc/flight",
    "active_runs": [],
    "total_segments": 12,
    "total_runs": 3,
    "total_bytes": 45234,
    "last_verified_at": "2026-06-03T09:00:00Z",
    "last_updated_at": "2026-06-03T10:00:00Z",
    "retention": {
      "max_segments": 200,
      "max_total_bytes": 104857600,
      "max_age_days": 30
    }
  }
}

$ arc flight verify --json
{
  "ok": true,
  "report": {
    "checked_segments": 12,
    "corrupt_segments": [],
    "missing_segments": [],
    "hash_chain_valid": true,
    "issues": []
  }
}
```

---

## Future Roadmap (Post-MVP)

| Feature | Status |
|---|---|
| Run Diff / Time Travel | Planned — compare two run's segment chains |
| Eval Autopsy Workbench | Planned — ingest flight events into eval harness |
| Action Simulator comparison | Planned — compare simulation report vs actual run events |
| OpenInference / OTel export | Planned — map flight events to OTel spans |
| Audit receipt signing | Planned — sign export bundles with local key |
| Crash recovery | Planned — resume from last known segment |
| Theia Flight Recorder panel | Planned — timeline view in IDE |
| Replay bundles | Planned — deterministic run replay from segment data |
| Signed export bundles | Planned — HMAC or GPG signed tarballs |

---

## Running Tests

```bash
cd python
uv run --extra dev python -m pytest tests/flight_recorder -q
uv run --extra dev ruff check src/agent_runtime_cockpit/flight_recorder tests/flight_recorder
```

## Safety Scan

```bash
grep -RIn "subprocess\|socket\|aiohttp\|requests\|httpx\|os\.system\|Popen\|urlopen\|listen\|serve" \
  python/src/agent_runtime_cockpit/flight_recorder \
  python/tests/flight_recorder
# Expected: no matches in runtime code; only in test_safety.py as string literals
```
