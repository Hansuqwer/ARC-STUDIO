# ARC Studio — Next Implementation Handover

Generated: 2026-05-17

## Current state

Latest local verification is green:

```bash
cd python && uv run pytest -q
# 782 passed, 14 skipped

pnpm --filter @arc-studio/protocol build
# pass

pnpm --filter arc-extension build
# pass

pnpm --filter @arc-studio/browser build && pnpm --filter @arc-studio/e2e-tests test
# 9 passed
```

Recent implemented slice:

- Release-facing docs refreshed to avoid stale adoption/audit/CI claims.
- e2e workflow stabilized locally.
- e2e tests now match canonical `packages/arc-extension` ported widgets.
- `arc-run-timeline` and `arc-event-stream` deep links now initialize via `FrontendApplicationContribution`.
- e2e workflow now ensures `tests/e2e/fixtures/swarmgraph-stub.sh` is executable.

Preserve unrelated worktree changes:

- `README.md` was already modified before this slice; do not overwrite/revert without inspection/approval.
- `.opencode/` is untracked; do not touch unless user asks.

No commit has been made for the latest changes.

## Working tree touched by latest slice

Expected modified files from latest slice:

- `.github/workflows/e2e.yml`
- `AGENTS.md`
- `docs/REALITY_AUDIT.md`
- `docs/RELEASE_CHECKLIST.md`
- `docs/handover/HANDOVER.md`
- `packages/arc-extension/src/browser/arc-extension-frontend-module.ts`
- `tests/e2e/arc-smoke.spec.ts`

Unrelated/pre-existing:

- `README.md`
- `.opencode/`

## Remaining ordered work

### 1. Confirm GitHub CI — partially done; final e2e requires commit/push

Goal: verify repo fixes pass on GitHub, not only locally.

Check workflows:

- `python`
- `node`
- `ARC Roadmap Gate`
- `signing-preflight`
- `e2e`
- `real-runtime-smoke` (manual/nightly; may require real deps and should not block offline PR gates unless release policy says so)

Use `gh` only for GitHub operations.

Suggested commands:

```bash
gh run list --limit 20
gh run view <run-id> --log-failed
```

Do not push/commit unless user explicitly asks.

### 2. Fix any GitHub-only CI failures — local e2e fix exists

Rules:

- Do not weaken tests with `skip`, `|| true`, or broad timeouts unless the test is explicitly out-of-scope and documented.
- Prefer fixing env/bootstrap/path mismatches.
- Keep release docs honest if a workflow remains non-blocking.

Likely CI areas:

- e2e Linux/Theia startup and workspace path behavior.
- Native dependencies for `native-keymap`/Theia packages.
- Browser app build cache/stale generated frontend.
- Python CLI path in e2e (`uv run arc` should now be used).

### 3. Theia extension migration Phase C — wiring cleanup done locally

Goal: finish cleanup of duplicate `theia-extensions/*` after confirming canonical `packages/arc-extension` contains needed UI. Current state: legacy packages are unwired from browser/electron apps, root typecheck, and pnpm workspace; source dirs are archived under `docs/archive/theia-extensions/` for rollback/history.

Start by reading:

- `docs/EXTENSION_MIGRATION.md`
- `applications/browser/package.json`
- `packages/arc-extension/src/browser/`
- archived `theia-extensions/*`

Constraints:

- Do not delete useful code until equivalent canonical behavior exists or is archived.
- Archive/stub/demo packages rather than present them as product.
- Static contract tests are acceptable for Theia UI; avoid unsupported runtime/jsdom assumptions.
- Keep `applications/browser` canonical; no new product work in old duplicate extension packages.

Suggested sub-slices:

1. Inventory archived `theia-extensions/*` and browser deps.
2. Identify any still-wired duplicates.
3. Port small missing UI-only pieces if needed.
4. Archive/remove stale packages only when tests/builds prove canonical app still works.
5. Update `docs/EXTENSION_MIGRATION.md`, `AGENTS.md`, and release docs.

### 4. Release checklist GitHub refresh

Goal: update release checklist with current local + GitHub evidence.

Files:

- `docs/RELEASE_CHECKLIST.md`
- `AGENTS.md`
- `docs/handover/HANDOVER.md`

Do not overclaim:

- No broad live/provider-backed SwarmGraph adoption.
- No adapter-wide keyed/HMAC audit claim unless specific run writes/verifies keyed audit material.
- No production/multi-user/tenant isolation claim.
- LM Arena remains stub-default/gated live path, not v0.1 product scope.
- Electron remains post-v0.1.

### 5. `.env` history scrub — gated only

Plan exists:

- `docs/ENV_HISTORY_SCRUB_PLAN.md`

Do not execute unless user explicitly approves release date + history rewrite/force-push plan.

### 6. Deferred product work

Not release blockers unless user reprioritizes:

- Broad live/provider-backed SwarmGraph adoption productization.
- Adapter-wide keyed audit population/verification.
- True live SSE wiring into active run lifecycle beyond replay/infra.
- SwarmGraph insight dashboards: consensus/voting, queen/worker topology, cost/token.
- Electron packaging.

## Required reading before next slice

Always read first:

```text
AGENTS.md
docs/handover/HANDOVER.md
docs/handover/NEXT_IMPLEMENTATION_HANDOVER.md
docs/LOCKED_REMAINING_ROADMAP.md
docs/LOCKED_PHASE_IMPLEMENTATION_PLAN.md
docs/research/IMPLEMENTATION_RESEARCH.md
relevant docs/adr/*.md
```

For migration work also read:

```text
docs/EXTENSION_MIGRATION.md
```

For audit/security work also read:

```text
docs/adr/005-audit-key-management.md
docs/adr/006-workspace-trust-isolation.md
```

## Subagent allocation

Use max parallel subagents:

- Orchestrator: `cx-gpt5.5 / 9router/cx-gpt-5.5`
  - Owns decisions, edits, verification, final summary.
- Heavy coding: `@kr-claude-sonnet`
  - Use for complex TS/Theia or Python integration changes.
- Fast exploration/fixes: `@kimi-k2.6`
  - Use for file discovery, CI log triage, quick patch options.
- Precise analysis/impl: `@kimi-k2.6-precision`
  - Use for CI root-cause, migration safety, protocol impacts.
- Context/reasoning/docs: `@glm-5.1-precision`
  - Use for release docs, claim review, ADR consistency.
- General coding: `@qwen-3.6-preview`
  - Use for straightforward tests, scripts, small implementation slices.

## Suggested next prompt

```text
Continue ARC Studio from current repo state using docs/handover/NEXT_IMPLEMENTATION_HANDOVER.md.

First read AGENTS.md, docs/LOCKED_REMAINING_ROADMAP.md, docs/LOCKED_PHASE_IMPLEMENTATION_PLAN.md, docs/research/IMPLEMENTATION_RESEARCH.md, docs/wiki/research-context/README.md, and relevant ADRs.

Identify the next ordered unfinished item. Use max parallel subagents:
- explore/kimi for repo + CI log discovery
- kimi-k2.6-precision for root-cause/impact analysis
- glm-5.1-precision for docs/claim safety
- kr-claude-sonnet for heavy coding if needed
- qwen for small tests/patches

Orchestrator owns final edits and verification. Preserve unrelated worktree changes (`README.md`, `.opencode/`). Do not commit unless explicitly asked.

Prefer the smallest correct vertical slice. Add/update tests. Run:
- cd python && uv run pytest -q
- pnpm --filter @arc-studio/protocol build
- pnpm --filter arc-extension build

For e2e/migration slices also run:
- pnpm --filter @arc-studio/browser build
- pnpm --filter @arc-studio/e2e-tests test

If green, continue to the next ordered item unless blocked by ambiguity, destructive action, secrets, paid/live calls, publishing, force-push/reset, or user asks to pause.
```

## Verification checklist for every slice

Minimum:

```bash
cd python && uv run pytest -q
pnpm --filter @arc-studio/protocol build
pnpm --filter arc-extension build
```

When release docs touched:

```bash
bash scripts/check-banned-claims.sh AGENTS.md README.md docs/LOCKED_REMAINING_ROADMAP.md docs/LOCKED_PHASE_IMPLEMENTATION_PLAN.md docs/REALITY_AUDIT.md docs/RELEASE_CHECKLIST.md docs/EXTENSION_MIGRATION.md docs/handover/HANDOVER.md
```

When browser/e2e touched:

```bash
pnpm --filter @arc-studio/browser build
pnpm --filter @arc-studio/e2e-tests test
```

Before final summary:

```bash
git status --short
```

## Safety rules

- Preserve unrelated user changes.
- No destructive git commands.
- No commits unless explicitly requested.
- No force-push/history rewrite unless explicitly approved.
- No paid/live provider calls unless explicitly approved.
- No broad product claims without tests.
- Keep scaffolds/not-wired behavior documented honestly.
