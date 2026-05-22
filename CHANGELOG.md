# Changelog

All notable changes to ARC Studio are recorded here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Versions follow [SemVer](https://semver.org/spec/v2.0.0.html); pre-release identifiers (`-alpha`, `-alphaN`) precede a stable `1.0.0`.

## [Unreleased]

### Added

- ADR-023 error-code sync: Python and TypeScript now share the 16 canonical `ArcErrorCode` values.
- `PERMISSION_DENIED` and `UNKNOWN` in Python `ArcErrorCode`.
- `canonicalErrorCode()` in TypeScript and `ArcErrorCode.from_legacy()` in Python for read-path legacy normalization.
- `protocol/fixtures/error-codes/` cross-language fixtures and `docs/guides/error-code-migration.md`.

### Deprecated

- TypeScript `ArcErrorCode.TRACE_NOT_FOUND`; use `RUN_NOT_FOUND`.
- TypeScript `ArcErrorCode.EXECUTION_FAILED`; use `RUN_FAILED`.
- TypeScript `ArcErrorCode.PARSE_ERROR`; use `INVALID_INPUT`.
- TypeScript `ArcErrorCode.WORKFLOW_NOT_FOUND`; use `WORKSPACE_NOT_FOUND`.

These deprecated members keep their original wire strings until removal in v0.3.0.

## [0.1.0-alpha] - 2026-05-21

### Added

- `RuntimeMode` enum with canonical `fake`, `gated_local`, and `provider_backed` values plus legacy migration warnings for prior runtime-mode strings.
- `RuntimeCapability` schema v2 with deterministic v1-to-v2 migration and preserved v1/v2 contract fixtures.
- Event envelope schema v2 migration in Python plus synced TypeScript protocol parsing defaults for legacy v1 events.
- `ChatSession` schema v2 runtime/profile/isolation/paid-call fields with v1 read migration.
- Minimal `RuntimeRegistry` for canonical runtime capability introspection.
- `/runtime` and `/mode` slash commands, plus capability-aware `/run` gating metadata.
- `cli_repl/commands/` — declarative slash command registry (`CommandRegistry`, `CommandDef`), single source of truth for all slash commands.
- `arc studio sessions migrate` CLI command for converting legacy flat `StudioSession` JSON files to canonical `ChatSession` dir-per-session format (idempotent).
- Bare `arc` CLI launches ARC Studio interactive REPL when invoked without subcommand in a TTY (respects `ARC_NO_TUI=1` to show help instead).
- `ChatSession.version` field (schema v1) for forward-compatible session serialization.
- Legacy `StudioSession` flat JSON reader via `ChatSession.load()` fallback with workspace-trust metadata for legacy file content.
- ADR-016 documents the bounded Phase 2 CLI consolidation subset and defers full slash/session inventory items to dependent phases.
- 38 new tests covering: merged slash commands (plan/build/auto/status/doctor/runs), command registry contract, cancellation primitives, `/run` gate/cancel integration, legacy session detection/migration, `sessions migrate` CLI (no-legacy/with-legacy/idempotent/deprecated-alias), bare `arc` TTY behavior.

### Changed

- `arc run --runtime-mode` accepts canonical runtime-mode values while preserving legacy CLI aliases for existing adoption/router paths.
- `/status` includes canonical runtime-mode context from the session.
- CLI consolidation: `cli_studio.py` rewritten as thin shim (≤30 active lines) delegating to `cli_repl/chat_repl.py`. Slash commands from both implementations unified in the declarative registry. `cli_studio.py`'s legacy `StudioSession` class removed — canonical `ChatSession` is the only write target; legacy sessions are readable via fallback.
- `cli_repl/slash_commands.py` refactored: `SlashCommandHandler` now uses the declarative `CommandRegistry`; merged commands from `cli_studio.py` (`/plan`, `/build`, `/auto`, `/status`, `/doctor`, `/runs`); registered commands now carry explicit gate/mode/trust/privilege/render/event metadata.
- `cli_repl/session.py`: `ChatSession` now includes `version`, `mode`, `set_mode()`; added `_detect_legacy_sessions()`, `_read_legacy_session()`, `_list_legacy_session_ids()`, `migrate_legacy_session()`, `migrate_all_legacy_sessions()`. `list_sessions()` scans the canonical sessions dir for both subdirectory-based and flat-file sessions, skipping the `latest` symlink. `save()` creates a `latest` symlink for backward compatibility.
- `tests/test_cli_studio.py` refactored: imports from `cli_repl.session` instead of removed `cli_studio.StudioSession`; covers ChatSession persistence, mode tracking, and legacy compat.
- `tests/test_cli_repl.py` expanded from 22 to 52 tests with merged commands, registry, migration, sessions-migrate alias, and bare-arc test classes.

### Deprecated

- `arc studio sessions-migrate` remains as a compatibility alias and prints a deprecation warning. Use `arc studio sessions migrate`.

- `docs/audits/audit-2026-05-14-55b9c25.md` — full 6-dimension health audit (accessibility, architecture, code quality, performance, security, test/CI integrity).
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

- `pnpm-lock.yaml` regenerated (was broken: empty `specifiers: {}` for `packages/arc-extension`). `pnpm install --frozen-lockfile` now works on clean clones.
- `.tool-versions`: pnpm pinned to `9.15.9` (was `9.12.0`).
- `pnpm-workspace.yaml`: `!theia-extensions/arc-arena` exclusion added (TS build has 5 Theia API drift errors; source retained for revival).
- `applications/electron/package.json`: removed `arc-arena` dependency.
- `README.md`: status now references `v0.1.0-alpha` tag; CLI command table includes `eval` (was missing, 12 total); pnpm troubleshooting version synced.
- `scripts/check-artifacts.sh`: allowlists `packages/arc-browser-app/src-gen/` and `*.env.example` (were falsely flagged as generated artifacts).
- `scripts/check-pr.sh`: excludes `runtimes/swarmgraph/` from secret scan (vendored project has test fixtures with fake keys).
- `.github/workflows/node.yml`: steps reordered (install before hygiene), `--frozen-lockfile` restored (was `=false`), pnpm cache added.
- `.github/workflows/arc-roadmap-gate.yml`: added `pnpm/action-setup@v4` (was missing, causing `pnpm: command not found`), bumped `setup-uv` to v5.
- `python/pyproject.toml`: registered `needs` pytest marker (was causing `-W error` CI failure); ruff ignores `E701`/`E702`/`E741` (intentional project style patterns).
- `docs/SECURITY_AUDIT_REPORT.md`: U-1 marked resolved (`.env` untracked, key rotated), R-4 updated.
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

- Tracked `.env` (free G4F key, rotated, untracked via `git rm --cached`; see `docs/SECURITY_AUDIT_REPORT.md` U-1).
- G4F (GPT4Free) provider definitions — 5 entries removed from both `python/src/agent_runtime_cockpit/providers.py` and `theia-extensions/arc-core/src/node/arc-service-impl.ts`. **Breaking**: configs referencing `g4f-*` provider IDs will now get a runtime error. Migrate to direct provider entries (OpenAI, Anthropic, etc.).
- `python/tests/test_routes_execute.py` (159 lines, stale FastAPI test, `fastapi` not a dependency).
- `console.log()` call in `packages/arc-extension/src/node/services/trace-parser.ts` (replaced with breadcrumb comment).
- Unused `typing.Iterable` import in `ag_ui/__init__.py`, unused `sys` import in `workspace/__init__.py`, unused `traces_dir` assignment in `src/routes.py` and `tests/web/test_protocol_contract.py`.
- Unused backup/debris files targeted by `scripts/apply-phase3.sh`.

### Moved

- `docs/FINAL_STATUS.md`, `docs/HANDOFF.md`, `docs/ORCHESTRATOR_HANDOVER_PROMPT.md` → `docs/history/`.

### Added (Phase 4)

- `ProviderClient` runtime-checkable protocol with `complete()`, `stream()`, `cancel()` methods and associated types (`ProviderRequest`, `ProviderResponse`, `UsageRecord`, `StreamChunk`, `ProviderCapability`, `CostRates`, error taxonomy).
- `BudgetEnforcer`, `BudgetConfig`, `BudgetState` in `budget/schema.py` — Decimal-based budget enforcement with AND-combined scope caps, first-launch confirmation gate.
- Heuristic injection-pattern scanner in `security/injection_patterns.py` with 5 locked ADR-014 patterns (prompt-injection, code-exec, data-exfil, role-play, override) and `--bypass-injection-scan` flag.
- `CancellationToken` with thread-safe cancel/reason/timestamp propagation, parent-child linkage, and `never_cancelled()` singleton.
- Mocked `AnthropicClient` skeleton with lazy SDK import, dependency-injected SDK factory, error mapping, and both `complete()`/`stream()` paths (6 tests).
- Package rename: `providers.py` → `provider_action.py`, `provider_clients/` → `providers/` to unblock provider-backed runtime package layout.
- `CostRecord` v2 Pydantic schema in `protocol/cost_record.py` with `Decimal` cost arithmetic (ROUND_HALF_EVEN, 8-decimal quantization), v1→v2 migration function, and 4 fixture pairs under `tests/contract/fixtures/cost-record/`.
- `extract_cost()` in `providers/anthropic_cost.py` — per-provider cost extraction from `ProviderResponse` + `ProviderCapability.cost_rates`, with measured and estimated (degraded) paths.
- 56 new tests across Phase 4: provider protocol contract, budget schema, injection patterns, Anthropic client, cost record migration (42), and Anthropic cost extraction (12).

### Added (Phase 20 — Streaming, Tool Use, and Multi-Turn Sessions)

- `AnthropicClient.stream()` async generator yielding `StreamChunk` with incremental text deltas, usage, and stop reasons.
- `ToolRegistry` and `ToolHandler` protocol with ADR-019 `output_trust_level` declarations (`trusted`, `untrusted`, `mixed`).
- Built-in read-only tools: `read_file`, `list_directory`, `get_current_time` with trust declarations and output byte limits.
- `ChatSession` v3→v4 schema with `tools_enabled`, `max_tool_iterations`, and `available_tools` fields plus v3→v4 migration.
- `TurnManager` for provider-backed multi-turn conversations with sequential tool execution loops, iteration caps, and trust-tagged history.
- `CostRecord` v2→v3 schema with `cost_components` field for per-call cost breakdown and parent-sum invariant enforcement.
- `/tools list`, `/tools enable`, `/tools disable` slash commands for session-level tool management.
- Structured injection scanner (`scan_structured()`) for nested dict/list/string payloads with tool-result attack patterns.
- Provider-backed `/run` routed through `TurnManager` with streaming chunks, tool calls, and turn events; fake/gated-local modes remain on existing SwarmGraph path.
- 273 new tests across Phase 20: streaming, tool registry/trust, built-in tools, ChatSession v4 migration, TurnManager single/multi-turn, cost components, /tools commands, structured scanner.

### Added (Phase 5.1 — Runtime Cleanup Follow-ups)

- `migrate_cost_record_to_latest()` canonical migration helper that chains v1→v2→v3, v2→v3, and v3 no-op migrations with clear errors for unsupported versions.
- `_run_coro_sync()` async-safe wrapper for provider-backed `/run` that detects running event loops and uses worker threads when called from async contexts, avoiding nested event loop errors.
- 5 new tests: CostRecord latest migration (v1→v3, v2→v3, v3 no-op, unsupported version), async-safe /run in both sync and async contexts.

### Changed

- `provider_clients/` package renamed to `providers/`; `providers.py` module renamed to `provider_action.py`. All imports updated.

### Known CI gaps / pre-existing failures

- **Node/E2E** ([#19](https://github.com/Hansuqwer/arc-theia-studio/issues/19)): webpack `Aborted (core dump)` exit code 134 during `packages/arc-browser-app prepare` on Ubuntu CI runner. V8 crash during JSON stringification in Theia's webpack pipeline. Workaround: set `NODE_OPTIONS=--max-old-space-size=8192` in CI, or pin Node to a version compatible with this Theia release.
- **Python** ([#20](https://github.com/Hansuqwer/arc-theia-studio/issues/20)): 52 web/daemon tests return HTTP 500 on Python 3.12/Ubuntu (all pass on Python 3.11/macOS). Suspect asyncio event-loop compatibility (`asyncio.get_event_loop()` vs `asyncio.get_running_loop()` on 3.12). Check `pytest-asyncio` version pin and `asyncio_mode` config.
- **Python** (pre-existing, unmitigated): `test_providers_action_all_gates_pass_closed_smoke` makes a real HTTP call to OpenAI with a fake API key (`sk-test-*`) and fails with HTTP 401. The test was designed to exercise the full gated live-action path but was never mocked. Present on `phase-3-complete` tag; unchanged in Phase 4. Fix: mock `urllib.request.urlopen` like the other live-action tests. Tracked for Phase 4.x.
- **Python** (transient, resolved): `test_langgraph_swarmgraph_local_real_routes_when_env_set` showed a one-off `ModuleNotFoundError: No module named 'swarm'` during initial Phase 4 package install. Test passes cleanly on re-run and on `phase-3-complete` tag. No code change needed; likely module-resolution race during editable install.
