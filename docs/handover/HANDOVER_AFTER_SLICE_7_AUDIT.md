# ARC Studio Handover After Slice 7 Audit

Generated: 2026-05-16

## Current Status

Slices 1-7 are implemented and audit-patched. Verification is green locally.

Completed slices:
- Slice 1: CLI profiles + run preflight
- Slice 2: CrewAI + SwarmGraph fake/offline runtime
- Slice 3: IDE preflight/run protocol + surface
- Slice 4: IDE capability-driven disabled reasons
- Slice 5: CrewAI real-runtime smoke gated by `ARC_REAL_RUNTIME_SMOKE=1`
- Slice 6: IDE run result linked to Runs tab
- Slice 7: HITL/audit/replay UX hardening

## Audit Findings And Patches

Finding 1: HITL IDE responses could not work because Python CLI requires a single-use token.
Patch: `HitlPromptInfo` now carries `token`; `HitlRespondRequest` requires `token`; `RunsTab` passes token to `respondHitlPrompt()`; backend calls `arc hitl respond ... --token ...`.

Finding 2: HITL prompt mapping used wrong Python fields.
Patch: backend maps `hitl_id` -> `promptId`, `prompt_text` -> `prompt`, plus existing camelCase fallbacks.

Finding 3: audit verify backend call used `auditPath` as the run ID.
Patch: backend now calls `arc audit verify <runId> --chain <auditPath> --json`.

Finding 4: audit verification boolean fallback was wrong.
Patch: replaced `!!data.chain_verified ?? !!data.verified` with `Boolean(data.chain_verified ?? data.verified)`.

Finding 5: `arc audit verify --json` had a Python shadowing bug.
Patch: renamed local `ok` boolean to `verified`, avoiding collision with the JSON envelope helper.

Finding 6: HITL/replay/status CLI calls missed `--workspace`.
Patch: backend now passes `--workspace this.workspaceRoot` for `hitl pending`, `hitl respond`, `runs status`, and `runs replay`.

Finding 7: docs and status counts were stale.
Patch: updated `AGENTS.md`, `docs/RELEASE_CHECKLIST.md`, and `docs/roadmap/ARC_IDE_CLI_KEYS_AND_CREWAI_SWARMGRAPH_ROADMAP.md` with current counts and honest replay/audit/HITL status.

## Verification Results

Commands run:
- `cd python && uv run pytest -q -W error`
- `pnpm --filter @arc-studio/protocol build`
- `pnpm --filter arc-extension build`
- `pnpm --filter arc-extension test`

Results:
- Python: `782 passed, 14 skipped`
- Protocol build: clean
- arc-extension build: clean
- arc-extension tests: `563 passed, 9 suites`

Known test note:
- Jest still prints the pre-existing open-handle notice after successful completion.

## Known Limitations

Still not claimed:
- No broad live SwarmGraph adoption claim.
- No real provider-backed CrewAI + SwarmGraph adoption, except opt-in smoke scaffolding behind `ARC_REAL_RUNTIME_SMOKE=1`.
- No production-ready, multi-user, or tenant-isolated claim.
- No deterministic runtime replay claim; IDE replay is stored trace replay only.
- No signed audit claim for fake/offline adoption runs; audit verification exists only where a real audit path + key are present.
- No live progress stream in Runs/Chat; current IDE replay is not live event delivery.

## Remaining Slices

Slice 8: Theia extension migration Phase C.

Scope:
- Continue `docs/EXTENSION_MIGRATION.md` Phase C.
- Port only useful UI-only/product-relevant pieces from `theia-extensions/*` into `packages/arc-extension`.
- Archive or remove duplicate/stub/static extensions only when canonical replacements exist or docs clearly say why they are parked.
- Preserve `applications/browser` compatibility; do not break current browser package wiring without a build/smoke proof.

Primary files:
- `docs/EXTENSION_MIGRATION.md`
- `applications/browser/package.json`
- `packages/arc-extension/src/browser/`
- `theia-extensions/*`

Suggested verification:
- `pnpm --filter @arc-studio/protocol build`
- `pnpm --filter arc-extension build`
- `pnpm --filter arc-extension test`
- Browser app build/smoke if package wiring changes.

Slice 9: Docs/release truth finalization.

Scope:
- Align `README.md`, `AGENTS.md`, `docs/RELEASE_CHECKLIST.md`, `docs/roadmap/*`, and current handovers.
- Run banned-claim checker on release-facing docs.
- Keep historical/archive docs out of product claims unless explicitly scoped.
- Update exact test counts only after final verification.

Suggested verification:
- `bash scripts/check-banned-claims.sh README.md docs/IMPLEMENTATION_PLAN.md docs/REALITY_AUDIT.md docs/RELEASE_CHECKLIST.md`
- `cd python && uv run pytest -q -W error`
- `pnpm --filter @arc-studio/protocol build`
- `pnpm --filter arc-extension build`
- `pnpm --filter arc-extension test`

## Guardrails

- Preserve unrelated worktree changes.
- Do not use destructive git commands.
- Do not commit unless explicitly asked.
- Do not run paid/provider calls.
- Do not overclaim live streaming, signed audit, real adoption, deterministic replay, production readiness, multi-user support, or tenant isolation.
- Keep CrewAI + SwarmGraph labeled fake/offline unless explicitly inside `ARC_REAL_RUNTIME_SMOKE=1` gated smoke.

## Resume Prompt

```text
Continue with Slice 8: Theia extension migration Phase C. First read AGENTS.md, docs/handover/HANDOVER_AFTER_SLICE_7_AUDIT.md, docs/EXTENSION_MIGRATION.md, docs/IMPLEMENTATION_PLAN.md, and docs/research/IMPLEMENTATION_RESEARCH.md. Preserve unrelated worktree changes. Port/archive only the smallest correct Theia extension migration slice, avoid product overclaims, add/update static contract tests, run pnpm --filter @arc-studio/protocol build && pnpm --filter arc-extension build && pnpm --filter arc-extension test, and run browser build/smoke if package wiring changes. Do not commit unless explicitly asked.
```
