# ARC Studio — Security Audit Report

**Scope**: `theia-extensions/arc-core` (Theia TypeScript service layer) and `python/src/agent_runtime_cockpit` (CLI, daemon, adapters).
**Tree audited**: `main` at commit `f08ef52`.
**Date**: 2026-05-13.
**Status**: hardened; residual items tracked below.

This document describes the live code as of the commit above. Earlier audit drafts referenced files (`packages/arc-extension/src/node/arc-backend-service.ts`, `python/src/routes.py`) that did not exist in the live tree and have been archived under `docs/history/`.

## Threat Model

ARC Studio runs entirely on the developer's workstation. The Theia frontend (browser or Electron) talks to two backends:

1. The in-process TypeScript service `ArcServiceImpl` in `theia-extensions/arc-core/src/node/arc-service-impl.ts`, which spawns CLI subprocesses (`arc`, runtime adapters) on the local machine.
2. The Python daemon `agent_runtime_cockpit.web.server`, launched by `uv run arc serve`, which binds to `127.0.0.1:7777` by default and serves the JSON API consumed by the frontend.

Assumed adversaries: a malicious workflow file or trace file in the user's workspace; a malicious peer process on the same host (CORS, loopback binding); a malicious string crossing the frontend → service boundary. Network adversaries are out of scope because the daemon does not bind to non-loopback interfaces by default.

## Resolved Findings

Each finding below was remediated in or before commit `f08ef52`. CWE references are advisory.

### R-0. Workspace traversal bounded (pre-existing)

**Severity**: medium (CWE-400 resource exhaustion).
**File**: `python/src/agent_runtime_cockpit/workspace.py`, `iter_workspace_files()`.
**Status**: this control predates the current audit. It was listed as residual U-4 in an earlier draft of this report; investigation during Phase 5 found the bound was already in place. Documented here so the control is visible and tested.
**Control**: traversal caps at `max_files=1000` and `max_bytes=10 * 1024 * 1024` cumulative. Symlinks and non-files are skipped. The `IGNORED_DIRS` set excludes `.cache`, `.git`, `.mypy_cache`, `.pytest_cache`, `.ruff_cache`, `.venv`, `.venv2`, `__pycache__`, `dist`, `lib`, `node_modules`, `src-gen`. Per-adapter slices (e.g. `[:20]` in `adapters/langgraph.py`) provide tighter belt-and-braces caps on detection-stage scans.
**Verification**: `python/tests/test_workspace.py` (added in Phase 5).

### R-1. Paid-call gating was silently bypassed

**Severity**: high (CWE-840, business-logic).
**File**: `theia-extensions/arc-core/src/node/arc-service-impl.ts`, `startRun()`.
**Issue**: `StartRunRequest.allow_paid_calls` was defined in the protocol but never forwarded to the CLI. Runs that should have been gated proceeded regardless of the user's choice.
**Fix**: `startRun()` now appends `--allow-paid-calls` and sets `ARC_SWARMGRAPH_ALLOW_COSTS=true` only when `request.allow_paid_calls === true`. Non-boolean truthy values are rejected. Default behaviour is opt-in; the protocol JSDoc documents this.
**Verification**: `theia-extensions/arc-core/test/start-run-paid-calls.test.js`.

### R-2. `exportTraceToOTLP` accepted unvalidated `runId` and `endpoint`

**Severity**: high (CWE-22 path traversal, CWE-918 SSRF).
**File**: `theia-extensions/arc-core/src/node/arc-service-impl.ts`, `exportTraceToOTLP()`.
**Issue**: `runId` was concatenated into a filesystem path; `endpoint` was passed to an outbound HTTP client. A frontend caller could read arbitrary files via `runId="../../../etc/passwd"` or coerce the daemon to call internal services.
**Fix**: `validateRunId()` enforces `/^run-(sg|lg|ca|oa|ag2)-[a-f0-9]{6,64}$/`. `validateOtlpEndpoint()` requires `http(s)`, rejects credentialed URLs, and rejects private/loopback hosts unless `ARC_OTLP_ALLOW_PRIVATE=true` is set (development override for local Jaeger).

### R-3. `workspacePath()` returned unvalidated paths

**Severity**: critical (CWE-22).
**File**: `theia-extensions/arc-core/src/node/arc-service-impl.ts`.
**Issue**: derived paths used `path.join(workspacePath(), userInput)`, which permits traversal via `..` segments and accepts non-absolute or non-existent roots.
**Fix**: `resolveWorkspaceRoot()` normalises and stats the root; `safeJoinInsideWorkspace()` rejects any derived path whose relative form starts with `..` or is absolute. All call sites updated; `rg -n 'path\.join\(.*workspacePath' theia-extensions/arc-core/src` returns zero hits.

### R-4. Secret committed to repository

**Severity**: critical (CWE-798).
**File**: `.env` (now untracked).
**Issue**: a live `G4F_API_KEY` was committed.
**Fix**: file removed from tracking, key rotated, `.env.example` added, `scripts/check-pr.sh` extended with a generic secret-pattern scan and a hard refusal for any tracked `.env`. History scrub (BFG / `git filter-repo`) is recommended but not yet performed; see residual item U-1.

### R-5. CI swallowed failures

**Severity**: medium (CWE-754).
**File**: `.github/workflows/arc-roadmap-gate.yml`.
**Issue**: lint, type-check, and test steps ended in `|| true`.
**Fix**: suffixes removed; `pnpm install` now uses `--frozen-lockfile`; a `pnpm typecheck` step gates the pipeline via `tsconfig.check.json`.

## Residual Items

These items are accepted, deferred, or out of scope for the current release. They are tracked in the roadmap and should be reconsidered before any non-loopback deployment.

### U-1. `.env` is present in pre-`f08ef52` history (accepted risk)

A `G4F_API_KEY` (free GPT4Free service key) was committed in commit
`e5d1414` and later made unnecessary when the G4F provider switched
to a no-key endpoint. The key has been removed from tracking and
rotated. The value remains retrievable from prior commits. The
recommended remediation (`git filter-repo`) rewrites SHAs for every
collaborator; the project owner has accepted this risk for the alpha
release.

### U-2. No authentication on the local daemon (mitigated)

The daemon binds to `127.0.0.1:7777`. An optional bearer-token scheme
using `ARC_DAEMON_TOKEN` was added in this release. When set, all
requests except `/health` must carry `Authorization: Bearer <token>`.
When unset, the daemon remains open to localhost (backward-compatible
single-user default). The TypeScript client sends the token
automatically when the env var is present.

### U-3. No rate limiting on the daemon

The daemon does not rate-limit. A buggy frontend or a runaway loop can exhaust CPU. Acceptable for a single-user dev tool; revisit if the daemon is ever exposed beyond loopback.

### U-4. `runCli()` has no cancellation/tracking map

Long-running CLI invocations cannot be cancelled mid-flight from the frontend; users must wait for the spawn timeout. UX gap, not a security issue. Tracked for Phase 5.

### U-5. Theia build emits Node.js DEP0190

`@theia/cli` triggers Node 20's `DEP0190` warning. Upstream issue; not exploitable; will become a hard error in Node 22+. Node 20 is pinned via `.tool-versions` until Theia upstream fixes this.

## Verification Matrix

| Claim | Command |
|---|---|
| Paid-call gating works as documented | `pnpm --filter arc-core test` (suite includes `start-run-paid-calls`) |
| No `path.join` of `workspacePath()` remains | `rg -n 'path\.join\(.*workspacePath' theia-extensions/arc-core/src` |
| No tracked `.env` | `git ls-files | grep -E '^(.*/)?\.env$'` |
| Secret patterns blocked in PRs | `bash scripts/check-pr.sh` |
| TypeScript compiles strictly | `pnpm typecheck` |
| Frozen lockfile in CI | `pnpm install --frozen-lockfile` |
| Daemon binds loopback only | `rg -n '127\.0\.0\.1|localhost' theia-extensions/arc-core/src python/src` |

## Out-of-scope

Supply-chain auditing (transitive npm/PyPI deps), formal verification of subprocess spawn helpers, and review of Electron's own update channel are not covered by this report. The Electron auto-update path is not yet enabled; see CHANGELOG.
