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

### Changed

- `theia-extensions/arc-core/src/node/arc-service-impl.ts`: `startRun()` now forwards `--allow-paid-calls` and `ARC_SWARMGRAPH_ALLOW_COSTS=true` **only** when `request.allow_paid_calls === true`. Non-boolean truthy values are ignored. `exportTraceToOTLP()` validates both arguments. `workspacePath()` is normalised and validated; all derived paths use `safeJoinInsideWorkspace()`.
- `theia-extensions/arc-core/src/common/arc-protocol.ts`: `StartRunRequest.allow_paid_calls` JSDoc documents opt-in default.
- `applications/browser/package.json`, `applications/electron/package.json`: workspace dependencies retargeted to the real `theia-extensions/arc-*` packages.
- `.github/workflows/arc-roadmap-gate.yml`: removed `|| true`, enforced `pnpm install --frozen-lockfile`, added `pnpm typecheck`.
- `applications/electron/electron-builder.release.yml`: ships a pre-built Python wheel under `arc-python/` rather than raw sources.
- `scripts/start-browser-arc.mjs`, `scripts/start-browser-stub.mjs`: explicit env allow-list, no `process.env` spread.
- `scripts/check-pr.sh`: extended secret-pattern scan; rejects any tracked `.env`.

### Removed

- Tracked `.env` (key rotated; see `docs/SECURITY_AUDIT_REPORT.md` U-1 for history-scrub status).
- Unused backup/debris files targeted by `scripts/apply-phase3.sh`.

### Moved

- `docs/FINAL_STATUS.md`, `docs/HANDOFF.md`, `docs/ORCHESTRATOR_HANDOVER_PROMPT.md` → `docs/history/`.

### Required before tagging

- Resolve residual item U-1 (history scrub of the leaked key) or publish an explicit accept-the-risk decision.
- Add a daemon-side authentication scheme (residual U-2) **or** document the single-user-loopback threat model in the README's Security section.
- Decide a first version: `0.1.0-alpha1` or `0.2.0-alpha` depending on whether the runtime hardening counts as additive or breaking.
