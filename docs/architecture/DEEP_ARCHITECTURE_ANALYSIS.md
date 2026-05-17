# ARC Studio Deep Architecture Analysis

Generated: 2026-05-17

Orchestrator: `cx/gpt-5.5 9router`

Subagent roles:
- Subagent A, `qwen 3.6 max preview - alibaba`: full architecture matrix; CLI/IDE priority.
- Subagent B, `kimi 2.6 precision - crofai`: CLI/Python/backend/security.
- Subagent C, `glm 5.1 precision - crofai`: IDE/Theia/browser.
- Subagent D, `qwen 3.6 max preview - alibaba`: docs/release truth.

## Executive Verdict

ARC Studio has a substantial implemented core: Python CLI/backend, JSONL+SQLite storage, runtime router, standalone adapters, fake/gated adoption scaffolds, audit/HITL/replay/eval/storage/isolation commands, and canonical Theia browser app wiring through `packages/arc-extension`.

The remaining risk is not lack of breadth. It is truth, proof, and productization:
- Docs over/understate current behavior in multiple places.
- CLI command surface is broad but inconsistent around JSON/workspace/discoverability.
- IDE has canonical widgets and static tests, but runtime browser smoke/e2e proof is thin.
- Adoption support must remain described as fake/offline/gated/scaffolded except where tests prove otherwise.
- Release readiness still needs CI truth, browser smoke, packaging proof, and `.env` history decision.

## CLI + Python Command Surface

Owner audit: Subagent B, `kimi 2.6 precision - crofai`; cross-checked by Subagent A.

Implemented:
- Top-level CLI includes `version`, `health`, `status`, `inspect`, `runtimes`, `workflows`, `schemas`, `serve`, `run`, `bug-report`.
- Command groups include `context`, `adapter`, `doctor`, `workspace`, `isolation`, `config`, `hitl`, `storage`, `runs`, `eval`, `providers`, `receipt`, `audit`, `profiles`, `prompt`.
- Run lifecycle commands cover stored-run management: list/get/status/delete/export/import/replay/backfill/search/prune/diff.
- Provider commands cover catalog/status/diagnostics/proxy, key refs, accounts, quotas, routing.
- Workspace/profile/config commands exist with tests.
- Audit/HITL/replay/eval/storage/isolation command families exist.

Partial / gaps:
- Current CLI is command-first `arc`, not the planned chat-first `arc-studio` REPL.
- `adapter detect` target is not implemented; `adapter list` lacks `--json`.
- JSON envelope consistency is incomplete across all commands.
- `audit verify/export` need workspace consistency for IDE/non-cwd calls.
- `arc run` indexing must be verified: new runs should be searchable without manual backfill.
- `runs stream`, `runs tail --follow`, and `runs cancel` are not proven implemented.
- `--profile-id` differs from docs/examples that use `--profile`.
- Provider proxy wording suggests live behavior, but implementation appears dry-run/gated.
- `audit key init` fallback behavior needs review to avoid secret-like key leakage in logs.

Recommended next CLI slices:
- Normalize JSON/workspace contracts.
- Fix run indexing split-brain.
- Add `--profile` alias or update docs.
- Add/park `adapter detect` explicitly.
- Harden provider/profile/audit-key security edge cases.

## IDE + Browser Architecture

Owner audit: Subagent C, `glm 5.1 precision - crofai`; cross-checked by Subagent A.

Implemented:
- `applications/browser` depends on canonical `arc-extension` only for ARC product surface.
- `packages/arc-extension` exposes canonical frontend/backend modules.
- Primary `ArcStudioWidget` provides Chat/Runs/Workflows/Config tabs.
- Canonical widgets exist for adapters, workflow graph, run timeline, event stream, health, welcome, safe prefs, status bar.
- Protocol and backend bridge include runtime capability, preflight/start, run status/detail/link, HITL, audit, replay, diff, capability diff methods.
- Static contract/proxy/protocol tests cover many UI and service surfaces.

Partial / gaps:
- Legacy `ArcWidget` remains registered for compatibility.
- Widgets are ported but not fully consolidated into tab UX.
- Chat launch is fake/offline oriented and uses hardcoded workflow defaults.
- Runs UX is useful but basic: replay is list-only, HITL is manual, audit display is minimal.
- Event stream is not proven as active live run UI.
- Backend bridge uses synchronous CLI calls and depends on `arc` on PATH.
- Workspace root handling needs proof for non-repo cwd / selected Theia workspace.
- Browser smoke/e2e proof is missing or too weak.
- Schema/context/audit standalone UX remains parked in legacy dirs.

Recommended next IDE slices:
- Browser smoke gate that proves canonical widget load.
- Fix `docs/EXTENSION_MIGRATION.md` current-state contradictions.
- Workspace-root correctness for backend bridge.
- Minimal runtime UI tests beyond source-pattern contract checks.
- Async bridge for long CLI calls.
- Explicitly park or port schema/context/audit standalone UX.

## Python Runtime / Backend Architecture

Owner audit: Subagent B, `kimi 2.6 precision - crofai`; Subagent A broad-check.

Implemented:
- Runtime router and capability reporting exist.
- JSONL canonical traces plus SQLite index exist.
- EventBroker, Supervisor, web/SSE routes exist.
- Trust resolver uses external workspace DB.
- Redaction, profiles, paid-call gates, env filtering, subprocess and Docker-compatible isolation exist.
- Audit/HMAC, HITL, eval, replay, storage management exist.
- CrewAI + SwarmGraph fake/offline path exists.
- Adoption runner scaffolds exist for LangGraph, AG2, CrewAI, OpenAI Agents, LlamaIndex.

Partial / gaps:
- Broad SwarmGraph adoption is not a release claim.
- CrewAI+SwarmGraph is fake/offline for product-safe claims.
- Other adoption runners are gated/scaffolded unless router/tests prove runnable flow.
- Trust enforcement must be verified for direct CLI `arc run`, not just supervisor path.
- Adapter-wide isolation/redaction enforcement varies by runtime path.
- HMAC audit should be claimed only where audit material exists.
- Deterministic replay is not proven; trace replay is implemented.

## Docs / Plan Truth

Owner audit: Subagent D, `qwen 3.6 max preview - alibaba`.

Current enough to drive work:
- `AGENTS.md`, after commit `docs: require roadmap updates after commits`.
- `docs/RELEASE_CHECKLIST.md`, but needs release gating cleanup.
- `docs/EXTENSION_MIGRATION.md`, but needs table/current-state reconciliation.
- This analysis set under `docs/architecture/` and `docs/roadmap/LOCKED_EXECUTION_PLAN.md`.

Stale or historical:
- `docs/REALITY_AUDIT.md`: stale severe; contains old claims around AG2, HMAC, adoption, SSE, LM Arena.
- `docs/PLAN_COMPLETION_AUDIT.md`: stale severe; pre-implementation gaps now completed.
- `docs/CLI_IDE_GAP_ANALYSIS.md`: stale severe; many missing CLI/IDE items now exist.
- `docs/handover/HANDOVER.md`: stale medium/high; old test counts, old next slices, old git state.
- `docs/IMPLEMENTATION_PLAN.md`: useful target architecture, stale current-baseline/status sections.

Docs risks:
- Release checklist includes stale docs in banned-claims check.
- Browser smoke command greps `arc-widget`; canonical primary widget is `arc-studio-widget`, and HTML grep is not enough.
- `.env` scrub is both “required” and “deferred”; release gate must choose one.
- README link/status wording should be rechecked before tag.

## Release Readiness

Implemented / reported green:
- Python tests reported: `782 passed, 14 skipped`.
- arc-extension tests reported: `581 passed` by current state summary; older docs say `563`.
- Browser build reported passing.
- Browser app no longer uses legacy ARC Theia deps.

Needs verification before release:
- Remote CI status on main.
- Browser smoke that proves canonical ARC widget loads.
- Python wheel build plus clean install smoke.
- `arc --help` and `arc runtimes --capabilities --json` current outputs.
- Real-runtime smoke last run status.
- Banned claims check after docs lock.
- `.env` history scrub decision: block release or explicitly defer with waiver/rotation.
- Electron explicitly out of v0.1; no packaging claim.

## Locked Direction

Start execution with Track 1 and Track 3:
- Track 1: CLI/Python command surface correctness, JSON/workspace contracts, run indexing, provider/profile/audit security edges.
- Track 3: IDE/browser runtime proof, workspace-root correctness, extension migration truth, basic runtime UI tests.

Do not begin implementation until `docs/roadmap/LOCKED_EXECUTION_PLAN.md` is reviewed/approved.
