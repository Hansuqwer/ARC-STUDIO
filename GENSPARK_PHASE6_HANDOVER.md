# Genspark Handover — ARC Studio Remaining Fixes (UPDATED)

## Context

Repo: `arc-theia-studio`
Branch: `feature/security-and-mapper-fixes`
Latest pushed commits:
- `f08ef52 fix: harden runtime security gates`
- `9af27b8 docs: reconcile audit and protocol test coverage`

Current verified state:
- `pnpm install --frozen-lockfile` passes.
- `pnpm typecheck` passes.
- `pnpm -r build` passes, with known Theia `DEP0190` warning.
- `cd python && uv run pytest` passes: `185 passed, 6 skipped, 4 warnings`.
- `pnpm --filter arc-core test` passes: `106 passed`.
- `bash scripts/check-pr.sh` passes.
- Docs now reflect live tree facts: `README.md`, `CHANGELOG.md`, `docs/SECURITY_AUDIT_REPORT.md`.
- `STATUS.md` was removed to avoid drift.

Important repo fact:
- Live Theia extension tree is `theia-extensions/*`, especially `theia-extensions/arc-core`.
- `packages/arc-extension` is not the live implementation.

## Working Rules

Audit first, implement second.

For each item:
1. Confirm whether the behavior is documented, implemented, tested, or speculative.
2. Decide bug vs feature vs risk acceptance.
3. Make the smallest correct code change.
4. Add/update tests.
5. Run focused verification.
6. Run broad verification before final handoff.
7. Do not rewrite git history unless explicitly approved by the repo owner.

Do not change unrelated untracked local prompt/planning docs unless asked.

## Items Status Summary

| # | Item | Status | Notes |
|---|------|--------|-------|
| 1 | U-1: leaked `.env` in git history | ✅ Done | Option A (document + accept); audit report updated |
| 2 | U-2: daemon auth | ✅ Done | Optional `ARC_DAEMON_TOKEN` bearer-token middleware; 6 Python tests |
| 3 | `/api/runs?runtime=` filter | ✅ Done | Added `runtime` query param; `test_filter_by_runtime` passes with strict assertions |
| 4 | Protocol-contract tests | ✅ Done | `python/tests/web/test_protocol_contract.py` — envelope shape, RunRecord validation, health, error-envelope |
| 5 | Frontend `allow_paid_calls` | ✅ Done | `arc-frontend-service.ts` accepts optional param; widget passes from `runtimeCapabilities` |
| 6 | `cancelRun` tracking map | ✅ Done | `ArcService.cancelRun()` protocol + `ArcServiceImpl` kills all tracked procs (coarse for alpha) |
| 7 | README runtime-table generator | ✅ Done | `scripts/generate-runtime-table.sh` + `.py`; `<!-- RUNTIMES:START/END -->` markers; `--check` mode for CI |

### 1. Pre-tag gate U-1: leaked `.env` remains in git history

**Status: ✅ Resolved — Option A (document + accept)**

- `.env` is no longer tracked.
- Secret scanning rejects tracked `.env` and common secret patterns.
- Historical commits contain the leaked key; accepted risk documented in `docs/SECURITY_AUDIT_REPORT.md` and `CHANGELOG.md`.
- No history rewrite.

### 2. Pre-tag gate U-2: local daemon has no authentication

**Status: ✅ Implemented — Optional bearer token**

- `python/src/agent_runtime_cockpit/web/server.py`: `bearer_token_middleware` added.
- When `ARC_DAEMON_TOKEN` env var is set, all requests except `/health` require `Authorization: Bearer <token>`.
- `/health` stays open for liveness probes.
- Token comparison uses `hmac.compare_digest` (constant-time).
- When env var is unset, pass-through (backward compatible).
- TypeScript `ArcServiceImpl.daemonAuthHeaders()` sends header when `ARC_DAEMON_TOKEN` is set.
- Tests: `python/tests/web/test_daemon_auth.py` — 6 tests covering all auth scenarios.

### 3. `/api/runs?runtime=...` filter

**Status: ✅ Implemented**

- `python/src/agent_runtime_cockpit/web/routes.py`: `list_runs()` accepts optional `runtime` query parameter.
- Filter applied post-load: `[r for r in runs if r.runtime == runtime]`.
- No TypeScript protocol change needed (frontend doesn't send it).
- Test: `test_filter_by_runtime` upgraded from skip to strict assertion.

### 4. Protocol-contract drift detection

**Status: ✅ Done — Python contract tests added**

- `python/tests/web/test_protocol_contract.py` — tests:
  - `test_list_runs_envelope_shape`: asserts `/api/runs` response has `version`, `ok`, `data`, `error`, `meta`.
  - `test_list_runs_data_are_valid_run_records`: validates every run record via `RunRecord.model_validate(item)`.
  - `test_health_returns_status_object`: validates `/health` response.
  - `test_envelope_error_shape`: validates error envelope structure.
- TS/Python generated schema remains future work (noted in CHANGELOG).

### 5. Frontend `allow_paid_calls` propagation

**Status: ✅ Implemented**

- `theia-extensions/arc-core/src/browser/arc-frontend-service.ts`: `startRun()` now accepts optional `allowPaidCalls?: boolean` parameter.
- `theia-extensions/arc-runs/src/browser/arc-run-timeline-widget.tsx`: reads `runtimeCapabilities.requires_paid_calls`, passes `paid ? true : undefined` to `startRun()`.
- Default is omitted/`undefined` (no paid calls allowed).
- Backend gates strictly on `allow_paid_calls === true`.

### 6. `cancelRun` tracking map

**Status: ✅ Implemented (coarse for alpha)**

- `ArcService` protocol extended with `cancelRun(runId: string): Promise<ArcEnvelope<{ cancelled: boolean }>>`.
- `ArcServiceImpl` maintains `runningProcs` Map keyed by internal counter (runId is only known after CLI exits).
- `runCli()` registers process on spawn, deletes on `close`/`error`.
- `cancelRun()` iterates all tracked processes, sends `SIGTERM`, and returns `{cancelled: true/false}`.
- No UI wiring (Cancel button deferred).

### 7. README runtime-table generator

**Status: ✅ Implemented**

- `<!-- RUNTIMES:START -->` and `<!-- RUNTIMES:END -->` markers added to `README.md`.
- `scripts/generate-runtime-table.sh` — shell script that runs `uv run arc runtimes --capabilities --json` and pipes into the Python generator.
- `scripts/generate-runtime-table.py` — Python script that parses the JSON, builds a Markdown table, and rewrites content between markers.
- `--check` mode for CI: detects staleness without modifying README.
- Running the generator refreshes the table in place.

## Final Verification Results

```bash
# All pass:
pnpm install --frozen-lockfile
pnpm typecheck
pnpm -r build
pnpm --filter arc-core test        # 106 passed
cd python && uv run pytest         # 185 passed, 6 skipped, 4 warnings
bash scripts/check-pr.sh           # clean
bash scripts/generate-runtime-table.sh --check  # up to date
```

## Remaining Work for Future Phases

- **Cancel button in UI**: Wire `cancelRun` to a button in `arc-run-timeline-widget.tsx`.
- **TS/Python generated schema**: Codegen shared protocol types.
- **Release tagging**: Decide version (`0.1.0-alpha1` vs `0.2.0-alpha`).
- **History scrub (U-1)**: Only if release owner changes decision from Option A to Option B.

## Deliverables

For each item implemented:
- ✅ Audit note included above.
- ✅ Code patch applied (see `git log` for individual commits after `9af27b8`).
- ✅ Tests proving the behavior.
- ✅ Verification output included.
- ✅ Deferred decisions documented.
