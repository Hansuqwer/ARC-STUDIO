# ARC Studio — Phase 21 Handover: Streaming Audit Verification + HMAC Signing

**Generated:** 2026-05-22
**Source docs:** `docs/roadmap.md` (R14), `docs/phases.md` (Phase 21)
**Prior commits:** `bcf9489` — architecture review integration; `4b0f6b5` — v0.1 baseline complete

## Goal

Implement Phase 21: Streaming Audit Verification + HMAC Signing (R14). This is the **first post-v0.1 foundation phase** and the **critical path start** — audit credibility requires streaming (memory-bounded) verification for large traces.

## What to Read First

1. **`docs/roadmap.md`** — R14 section (full deliverables, acceptance, status)
2. **`docs/phases.md`** — Phase 21 section (implementation plan, verification commands)
3. **`ARC_STUDIO_1.0_ARCHITECTURE_AND_FEATURE_REVIEW.md`** — P0-1 finding that motivated this phase
4. **`python/src/agent_runtime_cockpit/audit/hmac_chain.py`** — existing verification code (needs streaming refactor)
5. **`docs/adr/`** — any relevant ADRs (check for audit-related decisions)

## Current State

- `audit/hmac_chain.py` has `verify_audit_signature()` and `verify_hmac_chain()` but both use `read_text().splitlines()` which loads entire files into memory
- This breaks on large traces (100 MB+) — the architecture review P0-1 finding
- SHA-256 verification exists as default; HMAC signing is modeled but not fully implemented across all run paths
- The rest of the codebase is v0.1 baseline complete

## What to Implement

### 1. StreamingAuditVerifier class

Create a memory-bounded verifier that processes audit files line-by-line (or in configurable chunks, default 8 MB) instead of loading the full file. Two verification modes:

- `verify_sha256(file_path)` — streaming SHA-256, keep existing hash format for backward compat
- `verify_hmac(file_path, key)` — streaming HMAC with explicit audit versioning and key availability status

### 2. CLI command

Add `arc audit verify <run-id> --mode sha256|hmac|auto --max-memory-mb 500`

- `auto` mode: detect whether trace has HMAC or SHA-256 signatures
- Stable JSON output: `{ ok, mode, records_checked, reason, duration_ms }`

### 3. HMAC signing support

Add HMAC signing to supported run paths (when key is available). Add signed `.audit.sig` or versioned record fields for new HMAC traces.

### 4. Tests

- 100 MB synthetic trace verification completes in <30s and <500 MB RSS
- Old SHA-256 traces verify without migration
- HMAC traces fail on content/chain/signature mutation
- Stable JSON output format
- All existing Phase 4/10 audit tests remain green

## Verification

```bash
cd python && uv run pytest tests/audit/ -q
cd python && uv run pytest -q
pnpm --filter @arc-studio/protocol build
pnpm --filter arc-extension build
bash scripts/check-pr.sh
bash scripts/check-banned-claims.sh docs/roadmap.md docs/phases.md
```

## Key Constraints

- SHA-256 default must be preserved for backward compatibility with existing traces
- HMAC is optional (key may not be available); SHA-256 always works
- When HMAC is enabled, verification must reject mutated content/chains/signatures
- If the trace is extremely large (>1 GB), document the boundary rather than trying to handle it
- Update `docs/phases.md` status for Phase 21 when complete
- No overclaims: this is streaming verification, not "audit chain complete for all use cases"

## Files to Modify

- `python/src/agent_runtime_cockpit/audit/hmac_chain.py` — main verification logic
- `python/src/agent_runtime_cockpit/audit/chain.py` — may need streaming support
- `python/src/agent_runtime_cockpit/cli.py` — `arc audit verify` command
- `tests/` — new audit verification tests
- `docs/phases.md` — update Phase 21 status when done

## Dependencies

- None — Phase 21 is standalone foundation work
- Does not block other phases until complete (but is the critical path start)
- Phase 30 (Consensus Escrow) depends on Phase 21 for audit chain recording
- Phase 32 (Event Notifications) depends on Phase 21 for audit events
