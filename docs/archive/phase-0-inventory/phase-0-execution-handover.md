# Phase 0 Execution Handover

Status: ready for Phase 0 completion work.
Scope: finish inventory evidence only. No code changes, docs moves, renames, deletions, or Phase 1 consolidation.

## Guardrails

- Preserve unrelated dirty work, especially `docs/ENV_HISTORY_SCRUB_PLAN.md`.
- Do not claim native SwarmGraph provider-backed execution.
- Do not claim CLI/IDE parity, production readiness, EU AI Act compliance, or prompt-injection resistance.
- Do not create Phase 1 canonical docs until Phase 0 acceptance is complete.
- Keep `arc-studio` wording as supported alias/shim target, not deprecated.
- Treat Python capability reports and event envelopes as the semantic source of truth.

## Current Baseline

- Latest pushed implementation before this docs package: `d44037b feat: add native SwarmGraph runtime path`.
- Native SwarmGraph fake/offline path exists and is tested.
- Native SwarmGraph provider-backed path is absent.
- External `ARC_SWARMGRAPH_CLI` delegation path exists but does not prove native provider-backed completeness.
- `arc` currently shows help on no args; bare TUI is target behavior only.
- `arc studio chat` and `arc-studio` are separate implementations.
- IDE runtime dropdowns consume capability reports but have fallback lists that can drift.

## Phase 0 Files To Finish

1. `docs/archive/phase-0-inventory/cli-commands.md`
2. `docs/archive/phase-0-inventory/sessions.md`
3. `docs/archive/phase-0-inventory/slash-commands.md`
4. `docs/archive/phase-0-inventory/runtime-matrix.md`
5. `docs/archive/phase-0-inventory/ide-tabs.md`
6. `docs/archive/phase-0-inventory/docs-move-map.md`
7. `docs/archive/phase-0-inventory/test-status.md`
8. `docs/archive/phase-0-inventory/claims-audit.md`
9. `docs/archive/phase-0-inventory/swarmgraph-design.md`

## Required Next Work

1. Make `docs-move-map.md` exhaustive for ARC-owned docs, or explicitly classify vendored/runtime docs out of scope.
2. Fill remaining placeholder rows in `cli-commands.md` with concrete symbols from `python/src/agent_runtime_cockpit/cli.py`.
3. Audit `AssuranceTab.tsx` and `WorkflowsTab.tsx` line-by-line, then replace remaining `unknown`/source-contract notes in `ide-tabs.md`.
4. Grep banned claims outside `docs/archive/` and fill `claims-audit.md` hits table.
5. Re-run verification and update `test-status.md` counts/failures.
6. Review ADR-011 through ADR-015 for exact text requirements; current versions are condensed.

## Known Verification State

- `bash scripts/check-pr.sh` passed on 2026-05-19.
- `pnpm --filter arc-extension test` passed: 16 suites, 762 tests.
- `cd python && uv run pytest -q` failed: 1 failed, 990 passed, 19 skipped.
- Failure: `tests/test_cli_providers.py::test_providers_action_all_gates_pass_closed_smoke` attempted live OpenAI-compatible call with invalid `sk-test` key and received HTTP 401.
- Previously reported `tests/test_trust_resolver.py::TestTrustCLI::test_untrust` passed in latest run.

## Phase 0 Acceptance

- All inventory docs have no `<fill>`, `<add row>`, or `Unknown` cells except explicitly justified source-contract placeholders.
- `docs-move-map.md` enumerates every in-scope markdown file.
- `claims-audit.md` has grep results for every banned claim.
- `test-status.md` reflects latest verification output.
- No Phase 1 file moves or canonical-doc replacements have been performed.
