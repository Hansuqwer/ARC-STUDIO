# Changelog

All notable changes to ARC Studio are recorded here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Versions follow [SemVer](https://semver.org/spec/v2.0.0.html); pre-release identifiers (`-alpha`, `-alphaN`) precede a stable `1.0.0`.

There are no git tags yet. The "Unreleased" section below describes what is currently on `main`. The first tag will be cut once the items under "Required before tagging" are resolved.

## [Unreleased]

### Added

- Input validators in `theia-extensions/arc-core/src/node/arc-service-impl.ts`: `validateRunId`, `validateOtlpEndpoint`, `resolveWorkspaceRoot`, `safeJoinInsideWorkspace`.
- `theia-extensions/arc-core/test/start-run-paid-calls.test.js` covering paid-call gating and traversal validators.
- Root `tsconfig.check.json` + `pnpm typecheck` script.
- `.env.example` template; `.tool-versions` pinning Node 20.18.0, pnpm 9.12.0, Python 3.11.10.
- `docs/SECURITY_AUDIT_REPORT.md` describing the live tree.
- `scripts/apply-phase3.sh` for one-shot cleanup tasks.
- `python/tests/web/` — daemon auth tests (`test_daemon_auth.py`), protocol contract tests (`test_protocol_contract.py`), health endpoint test (`test_health.py`), SSE replay tests (`test_runs_sse.py`).
- `ARC_DAEMON_TOKEN` bearer-token middleware in `python/src/agent_runtime_cockpit/web/server.py` (optional, U-2).
- `GET /api/runs?runtime=` filter parameter on the daemon runs endpoint.
- `ArcService.cancelRun(runId)` protocol method + implementation in `ArcServiceImpl` (coarse kill-all-running-procs for alpha).
- `arc-frontend-service.ts` passes `allowPaidCalls` from `runtimeCapabilities.requires_paid_calls` to `startRun()`.
- `arc-run-timeline-widget.tsx` reads `runtimeCapabilities` and passes `paid ? true : undefined` to `startRun()`.
- `scripts/generate-runtime-table.sh` and `scripts/generate-runtime-table.py` — auto-generate the runtime capabilities table in `README.md` between `<!-- RUNTIMES:START/END -->` markers.

### Changed

- `theia-extensions/arc-core/src/node/arc-service-impl.ts`: `startRun()` now forwards `--allow-paid-calls` and `ARC_SWARMGRAPH_ALLOW_COSTS=true` **only** when `request.allow_paid_calls === true`. Non-boolean truthy values are ignored. `exportTraceToOTLP()` validates both arguments. `workspacePath()` is normalised and validated; all derived paths use `safeJoinInsideWorkspace()`. `runCli()` tracks spawned processes in `runningProcs` Map. Added `cancelRun()` method.
- `theia-extensions/arc-core/src/common/arc-protocol.ts`: `StartRunRequest.allow_paid_calls` JSDoc documents opt-in default. Added `cancelRun(runId)` to `ArcService` interface.
- `applications/browser/package.json`, `applications/electron/package.json`: workspace dependencies retargeted to the real `theia-extensions/arc-*` packages.
- `.github/workflows/arc-roadmap-gate.yml`: removed `|| true`, enforced `pnpm install --frozen-lockfile`, added `pnpm typecheck`.
- `applications/electron/electron-builder.release.yml`: ships a pre-built Python wheel under `arc-python/` rather than raw sources.
- `scripts/start-browser-arc.mjs`, `scripts/start-browser-stub.mjs`: explicit env allow-list, no `process.env` spread.
- `scripts/check-pr.sh`: extended secret-pattern scan; rejects any tracked `.env`. Added exclusions for test fixture files and auth middleware docstrings to eliminate false positives.
- `scripts/check-artifacts.sh`: excluded `.env.example` from generated-artifact detection.
- `README.md`: runtime table now auto-generated via `scripts/generate-runtime-table.sh` between `<!-- RUNTIMES:START/END -->` markers.
- `python/src/agent_runtime_cockpit/web/routes.py`: `GET /api/runs` accepts optional `runtime` query parameter for filtering.
- `theia-extensions/arc-core/src/browser/arc-frontend-service.ts`: `startRun()` accepts optional `allowPaidCalls` parameter and forwards it to backend.

### Removed

- Tracked `.env` (free G4F key, rotated, risk accepted; see `docs/SECURITY_AUDIT_REPORT.md` U-1).
- Unused backup/debris files targeted by `scripts/apply-phase3.sh`.

### Moved

- `docs/FINAL_STATUS.md`, `docs/HANDOFF.md`, `docs/ORCHESTRATOR_HANDOVER_PROMPT.md` → `docs/history/`.

### Required before tagging

- Decide a first version: `0.1.0-alpha1` or `0.2.0-alpha` depending on whether the runtime hardening counts as additive or breaking.
- Verify U-1 (`.env` in git history) documented risk acceptance is acknowledged by the release owner.
