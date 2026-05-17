# ARC Studio Locked Execution Plan

Generated: 2026-05-17

Orchestrator: `cx/gpt-5.5 9router`

Model assignment policy:
- `qwen 3.6 max preview - alibaba`: heavy multi-file implementation, broad refactors, deep audits.
- `kimi 2.6 precision - crofai`: CLI/Python backend, security/trust, tests, precise fixes.
- `glm 5.1 precision - crofai`: Theia/React/IDE, protocol/UI contract tests, docs alignment.
- `cx/gpt-5.5 9router`: sequencing, conflict resolution, verification, commits, pushes.

This plan is locked for the next execution phase. Do not execute until reviewed.

## Track 1: CLI + Python Command Surface

### T1-01: CLI Truth And Help Matrix

Status: Partial.

Files likely touched: `python/src/agent_runtime_cockpit/cli.py`, `python/tests/cli/test_cli_discoverability.py`, `docs/IMPLEMENTATION_PLAN.md`, `docs/RELEASE_CHECKLIST.md`.

Tests required: CLI help/discoverability tests for all top-level groups and key subcommands.

Verification: `cd python && uv run pytest python/tests/cli/test_cli_discoverability.py -q`.

Risks: Docs may describe chat-first `arc-studio` not implemented by `arc`.

Owner model preference: `kimi 2.6 precision - crofai`.

Acceptance criteria: Current CLI surface has generated/help-backed matrix; missing targets are either implemented or explicitly deferred.

Priority: v0.1 blocker.

### T1-02: JSON Envelope And Workspace Consistency

Status: Partial.

Files likely touched: `python/src/agent_runtime_cockpit/cli.py`, `python/tests/cli/`, `packages/arc-extension/src/node/arc-backend-service.ts` if IDE args need adjustment.

Tests required: For all IDE-facing/user-facing commands with `--json`, parse envelope and assert stable `ok/error` shape plus workspace behavior.

Verification: `cd python && uv run pytest python/tests/cli -q`.

Risks: Changing CLI output can break IDE bridge tests.

Owner model preference: `kimi 2.6 precision - crofai`.

Acceptance criteria: `adapter list --json` exists or is documented deferred; `audit verify/export` support explicit workspace; JSON envelopes are consistent for key commands.

Priority: v0.1 blocker.

### T1-03: Run Index Correctness

Status: Partial.

Files likely touched: `python/src/agent_runtime_cockpit/cli.py`, `python/src/agent_runtime_cockpit/storage/*`, `python/tests/test_cli_runs.py`, `python/tests/test_storage*.py`.

Tests required: `arc run` creates run searchable by `arc runs search` without manual backfill.

Verification: `cd python && uv run pytest python/tests/test_cli_runs.py python/tests/test_storage.py -q`.

Risks: Storage dual-write can change existing run fixtures.

Owner model preference: `kimi 2.6 precision - crofai`.

Acceptance criteria: New run writes JSONL and SQLite index atomically enough for CLI search/status.

Priority: v0.1 blocker.

### T1-04: Provider/Profile UX Contract

Status: Partial.

Files likely touched: `python/src/agent_runtime_cockpit/cli.py`, `python/tests/test_cli_providers.py`, `python/tests/test_cli_profiles_workspace.py`, `python/tests/cli/test_cli_run_gating.py`, docs examples.

Tests required: `--profile` alias or docs fix; paid profile/key-ref behavior; provider proxy wording/flags; account env validation.

Verification: `cd python && uv run pytest python/tests/test_cli_providers.py python/tests/test_cli_profiles_workspace.py python/tests/cli/test_cli_run_gating.py -q`.

Risks: Provider docs can overclaim live calls.

Owner model preference: `kimi 2.6 precision - crofai`.

Acceptance criteria: Profile/provider flows are honest, test-covered, and do not imply ungated paid calls.

Priority: should-have.

### T1-05: Audit/HITL/Replay CLI Hardening

Status: Partial.

Files likely touched: `python/src/agent_runtime_cockpit/cli.py`, `python/src/agent_runtime_cockpit/audit/*`, `python/tests/test_audit*.py`, `python/tests/test_cli_runs.py`.

Tests required: Workspace-aware audit verify/export; no full audit key printed without explicit opt-in; HITL token output documented/tested; replay wording remains trace replay.

Verification: `cd python && uv run pytest python/tests/test_audit*.py python/tests/test_cli_runs.py -q`.

Risks: Audit key behavior can affect local setup instructions.

Owner model preference: `kimi 2.6 precision - crofai`.

Acceptance criteria: Audit/HITL/replay CLI behavior is secure enough for local alpha and docs avoid signed-all-runs/deterministic-replay claims.

Priority: v0.1 blocker.

### T1-06: Adapter Discoverability

Status: Partial.

Files likely touched: `python/src/agent_runtime_cockpit/cli.py`, runtime registry/capability files, `python/tests/cli/test_cli_discoverability.py`, `python/tests/cli/test_cli_runtimes_diff.py`.

Tests required: `adapter list --json`; optional `adapter detect <runtime> --json` or explicit deferral; registry-driven help.

Verification: `cd python && uv run pytest python/tests/cli/test_cli_discoverability.py python/tests/cli/test_cli_runtimes_diff.py -q`.

Risks: Runtime maturity can be overclaimed in capability output.

Owner model preference: `kimi 2.6 precision - crofai`.

Acceptance criteria: Adapter discoverability accurately reports supported/gated/fake/deferred status.

Priority: should-have.

## Track 2: Runtime / Adoption / Security Backend

### T2-01: Direct Run Trust Enforcement Proof

Status: Needs verification.

Files likely touched: `python/src/agent_runtime_cockpit/cli.py`, `python/src/agent_runtime_cockpit/orchestration/*`, `python/src/agent_runtime_cockpit/security/trust.py`, `python/tests/cli/test_cli_run_gating.py`.

Tests required: Untrusted workspace blocks before run record creation for direct CLI and supervisor/daemon paths.

Verification: `cd python && uv run pytest python/tests/cli/test_cli_run_gating.py python/tests/test_security*.py -q`.

Risks: Existing fixtures may assume trusted temp workspaces.

Owner model preference: `kimi 2.6 precision - crofai`.

Acceptance criteria: All execution entrypoints enforce trust consistently or explicitly document trusted-local exception.

Priority: v0.1 blocker.

### T2-02: Adoption Capability Truth

Status: Partial.

Files likely touched: `python/src/agent_runtime_cockpit/orchestration/runtime_router.py`, `python/src/agent_runtime_cockpit/protocol/capabilities.py`, adapter/adoption tests, docs.

Tests required: Capability JSON proves CrewAI+SwarmGraph fake/offline only; non-CrewAI adoption marked gated/scaffolded unless runnable.

Verification: `cd python && uv run arc runtimes --capabilities --json | python -m json.tool`; `cd python && uv run pytest python/tests/cli/test_cli_runtimes_diff.py python/tests/adapters -q`.

Risks: Product docs may overclaim adoption.

Owner model preference: `qwen 3.6 max preview - alibaba`.

Acceptance criteria: Runtime/adoption matrix is machine-readable and conservative.

Priority: v0.1 blocker.

### T2-03: Redaction And Raw Trace Boundary

Status: Needs verification.

Files likely touched: `python/src/agent_runtime_cockpit/security/redaction.py`, trace/export/bug-report code, CLI tests.

Tests required: Fake secrets in traces are redacted in bug reports and any release-facing exports, or raw-local commands are clearly documented.

Verification: `cd python && uv run pytest python/tests/test_security*.py python/tests/cli -q`.

Risks: Over-redaction can break forensic trace fidelity; under-redaction leaks secrets.

Owner model preference: `kimi 2.6 precision - crofai`.

Acceptance criteria: Secret handling policy is implemented and documented per command.

Priority: v0.1 blocker.

### T2-04: Event Broker / SSE Product Boundary

Status: Partial.

Files likely touched: `python/src/agent_runtime_cockpit/orchestration/event_broker.py`, `python/src/agent_runtime_cockpit/web/routes.py`, tests, docs.

Tests required: Broker/SSE replay and any live path are separately tested/labeled.

Verification: `cd python && uv run pytest python/tests/web python/tests/test_event* -q`.

Risks: Browser docs may claim active live run streaming before proof.

Owner model preference: `qwen 3.6 max preview - alibaba`.

Acceptance criteria: Release docs state exact tested SSE behavior.

Priority: should-have.

## Track 3: IDE + Browser UX

### T3-01: Browser Smoke Gate

Status: Needs verification.

Files likely touched: smoke scripts/docs only unless failure requires fix; `docs/RELEASE_CHECKLIST.md`.

Tests required: Browser prod build and bounded smoke proving canonical ARC widget/contribution loads.

Verification: `pnpm --filter @arc-studio/browser build`; `pnpm start:browser`; runtime smoke stronger than `grep arc-widget`.

Risks: Theia startup/native deps are platform-sensitive.

Owner model preference: `glm 5.1 precision - crofai`.

Acceptance criteria: Release checklist has reproducible browser smoke and current result.

Priority: v0.1 blocker.

### T3-02: Workspace Root Correctness

Status: Needs verification.

Files likely touched: `packages/arc-extension/src/node/arc-backend-service.ts`, frontend/backend DI modules, tests.

Tests required: Backend CLI bridge uses selected workspace/root arg, not accidental process cwd.

Verification: `pnpm --filter arc-extension test` plus targeted proxy/backend tests.

Risks: Theia workspace service injection can affect startup.

Owner model preference: `glm 5.1 precision - crofai`.

Acceptance criteria: IDE calls pass correct workspace for preflight/start/status/audit/replay/diff.

Priority: v0.1 blocker.

### T3-03: IDE Runtime UI Test Floor

Status: Partial.

Files likely touched: `packages/arc-extension/src/browser/__tests__/*`, Jest config if needed.

Tests required: Minimal runtime render/behavior tests for tabs or documented static-only coverage with smoke substitute.

Verification: `pnpm --filter arc-extension test`.

Risks: jsdom/Theia deps may be expensive; avoid broad rewrite.

Owner model preference: `glm 5.1 precision - crofai`.

Acceptance criteria: UI coverage limitation is explicit, and at least smoke/proxy tests cover critical paths.

Priority: should-have.

### T3-04: Extension Migration Truth

Status: Partial.

Files likely touched: `docs/EXTENSION_MIGRATION.md`, `docs/RELEASE_CHECKLIST.md`, possibly legacy package docs.

Tests required: Docs only unless package wiring changes.

Verification: `pnpm --filter @arc-studio/browser build`; banned claims check.

Risks: Deleting legacy dirs before smoke can remove salvageable code.

Owner model preference: `glm 5.1 precision - crofai`.

Acceptance criteria: Legacy dirs marked archival/parked/useful; browser app dependency truth is clear.

Priority: v0.1 blocker.

### T3-05: Async CLI Bridge Plan Or Minimal Fix

Status: Partial.

Files likely touched: `packages/arc-extension/src/node/arc-backend-service.ts`, tests.

Tests required: Long run does not block UI where feasible, or sync bridge is documented as alpha limitation.

Verification: `pnpm --filter arc-extension test`.

Risks: Async refactor broad; prefer smallest safe step.

Owner model preference: `glm 5.1 precision - crofai` or `qwen 3.6 max preview - alibaba` if broad.

Acceptance criteria: Alpha limitation is either fixed for long-running start or documented honestly.

Priority: should-have.

### T3-06: Park Or Port Schema/Context/Audit Standalone UX

Status: Deferred decision.

Files likely touched: docs first; code only if chosen.

Tests required: If porting, static/proxy tests; if parking, docs update.

Verification: `pnpm --filter arc-extension test`; browser build if code changes.

Risks: Scope creep.

Owner model preference: `glm 5.1 precision - crofai`.

Acceptance criteria: v0.1 explicitly parks or includes these UX surfaces.

Priority: deferred unless release owner upgrades.

## Track 4: Release / Docs / CI

### T4-01: Docs Truth Lock

Status: Partial.

Files likely touched: `docs/IMPLEMENTATION_PLAN.md`, `docs/RELEASE_CHECKLIST.md`, `docs/EXTENSION_MIGRATION.md`, `docs/handover/HANDOVER.md`, `README.md` if approved.

Tests required: Banned claims checker.

Verification: `bash scripts/check-banned-claims.sh README.md docs/IMPLEMENTATION_PLAN.md docs/REALITY_AUDIT.md docs/RELEASE_CHECKLIST.md` unless doc set is intentionally changed.

Risks: User has existing `README.md` modifications; preserve them.

Owner model preference: `glm 5.1 precision - crofai` for doc alignment; orchestrator for final review.

Acceptance criteria: Stale docs are bannered/archived or made current; active source-of-truth set is unambiguous.

Priority: v0.1 blocker.

### T4-02: Release Checklist Hardening

Status: Partial.

Files likely touched: `docs/RELEASE_CHECKLIST.md`, scripts if needed.

Tests required: Checklist commands copied exactly and run where feasible.

Verification: frozen install, builds, Python tests, extension tests, browser build/smoke, `uv build`, CLI help/capabilities, banned claims.

Risks: Full verification can be slow; CI may be red for unrelated reasons.

Owner model preference: `qwen 3.6 max preview - alibaba`.

Acceptance criteria: Checklist separates gates vs triggered/waived items and records current commit/date.

Priority: v0.1 blocker.

### T4-03: CI Truth

Status: Needs verification.

Files likely touched: docs only unless CI failure requires later fix.

Tests required: `gh` workflow/status inspection.

Verification: `gh run list`, current branch/main status, documented result.

Risks: Remote CI can fail outside local workspace.

Owner model preference: orchestrator `cx/gpt-5.5 9router`.

Acceptance criteria: Current CI status is recorded honestly with blockers/waivers.

Priority: v0.1 blocker.

### T4-04: Packaging Proof

Status: Partial.

Files likely touched: release docs; code only if package fails.

Tests required: `cd python && uv build`; clean venv install smoke; browser prod build.

Verification: `cd python && uv build`; `pnpm --filter @arc-studio/browser build`.

Risks: Native deps/platform issues.

Owner model preference: `qwen 3.6 max preview - alibaba`.

Acceptance criteria: Python wheel and browser artifact proof recorded; Electron explicitly excluded.

Priority: v0.1 blocker.

### T4-05: `.env` History Decision

Status: Deferred / release-blocking if required.

Files likely touched: `docs/ENV_HISTORY_SCRUB_PLAN.md`, `docs/RELEASE_CHECKLIST.md`.

Tests required: None until explicit destructive approval.

Verification: If approved later, follow scrub plan in isolated clone; no destructive action in normal execution.

Risks: History rewrite/force-push is disruptive.

Owner model preference: orchestrator only.

Acceptance criteria: Release owner decides: block release for scrub, or document waiver/rotation and defer.

Priority: v0.1 blocker decision, implementation deferred until approval.

## Track 5: Deferred / Post-v0.1

### T5-01: Broad Live SwarmGraph Adoption

Status: Deferred.

Files likely touched: adoption runners/router/adapters/audit/events/IDE.

Tests required: Real-runtime gated tests, audit trace proof, provider cost gates.

Verification: Opt-in real-runtime smoke and offline fake tests.

Risks: Overclaiming; paid calls; dependency drift.

Owner model preference: `qwen 3.6 max preview - alibaba`.

Acceptance criteria: Not part of v0.1 claims.

Priority: deferred.

### T5-02: Electron Packaging

Status: Deferred.

Files likely touched: `applications/electron`, packaging scripts/docs.

Tests required: Electron build/package smoke.

Verification: Later packaging workflow.

Risks: Native deps, legacy Theia deps.

Owner model preference: `glm 5.1 precision - crofai`.

Acceptance criteria: Explicitly excluded from v0.1.

Priority: deferred.

### T5-03: LM Arena Productization

Status: Deferred.

Files likely touched: arena backend/CLI/IDE/provider gateway.

Tests required: No-paid-call default, gated live smoke, provider safety tests.

Verification: Separate roadmap.

Risks: Paid/live provider calls.

Owner model preference: `qwen 3.6 max preview - alibaba`.

Acceptance criteria: Stub-default/gated live path only for v0.1.

Priority: deferred.

### T5-04: Multi-user / Tenant Isolation / Production Claims

Status: Deferred.

Files likely touched: auth, daemon, storage, tenancy, audit, docs.

Tests required: Full security model tests.

Verification: Future security review.

Risks: High.

Owner model preference: `qwen 3.6 max preview - alibaba`.

Acceptance criteria: No v0.1 claim.

Priority: deferred.
