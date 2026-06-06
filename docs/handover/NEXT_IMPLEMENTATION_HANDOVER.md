# ARC Studio — Next Implementation Handover

**Generated:** 2026-05-18  
**Status:** Thin pointer. Not a roadmap/status source of truth.

## Authority

Use these files for current ordered work:

- `docs/roadmap.md`
- `docs/LOCKED_PHASE_IMPLEMENTATION_PLAN.md`

Do not treat this file as a competing plan. If this file conflicts with the locked docs, the locked docs win.

## Current Planning Decision

v0.2 uses Option A:

- Productize live streaming against configured Python daemon/local runtime paths.
- Add BudgetVector post-hoc accounting/reporting and IDE gauges.
- Polish the existing Assurance tab for HITL/audit workflows.
- Run daemon/CLI parity, `arc doctor all` coverage, and truth-alignment audits.

Deferred from v0.2 unless the locked docs are explicitly changed:

- Effect-boundary deterministic replay and journal-backed fork/resume.
- Adapter-wide real-time budget interrupts at model/tool-call boundaries.
- New adapters or adapter status upgrades without corresponding IDE views.
- Live LM Arena and Electron release packaging.

## Required Reading

Before implementation:

- `AGENTS.md`
- `docs/roadmap.md`
- `docs/LOCKED_PHASE_IMPLEMENTATION_PLAN.md`
- `docs/research/IMPLEMENTATION_RESEARCH.md`
- Relevant `docs/adr/*.md`

## Verification

Minimum for implementation slices:

```bash
cd python && uv run pytest -q
pnpm --filter @arc-studio/protocol build
pnpm --filter arc-extension build
bash scripts/check-pr.sh
```

If browser/IDE touched:

```bash
pnpm --filter @arc-studio/browser build
pnpm --filter @arc-studio/e2e-tests test
```

If release-facing docs touched:

```bash
bash scripts/check-banned-claims.sh AGENTS.md README.md docs/roadmap.md docs/LOCKED_PHASE_IMPLEMENTATION_PLAN.md docs/REALITY_AUDIT.md docs/RELEASE_CHECKLIST.md docs/EXTENSION_MIGRATION.md docs/handover/HANDOVER.md
```

## Safety

- Preserve unrelated worktree changes.
- No destructive git commands.
- No commits unless explicitly requested.
- No force-push/history rewrite unless explicitly approved.
- No paid/live provider calls unless explicitly approved.
- No broad product claims without tests.
