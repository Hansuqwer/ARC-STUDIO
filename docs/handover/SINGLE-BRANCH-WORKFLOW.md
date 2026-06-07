# Single-Branch Workflow — `main` is the only trunk

**Effective 2026-06-07.** After the branch consolidation (see `CONSOLIDATION-2026-06-07.md`),
all work — ARC core and the mobile SDK — lives on **`main`**. This is the operating rule for
every session working in this clone.

## The rule

- **One trunk: `main`.** Do not create `mob/pr*`, `feat/*`, or per-task branches.
- **No PRs.** Commit directly to `main`.
- **One session writes at a time.** This clone is a single shared working copy. Concurrent
  sessions on different branches in the same clone is exactly what caused the breakage —
  don't do it. If another session is active, coordinate or wait.

## Every change — the loop

```bash
git switch main                 # always start on main
git pull --ff-only origin main  # sync before you work

# ...edit, then verify (see gates below)...

git add <specific files>        # stage explicitly; never `git add -A` (avoids arena/vendor noise)
git commit -m "type(scope): summary"
git pull --rebase origin main   # in case main advanced
git push origin main
```

If `pull --ff-only` fails, someone pushed — rebase your work (`git pull --rebase`) and
re-run the gates before pushing.

## Verification gates (run before every push)

Mobile work touches both stacks, so run what you changed:

```bash
# Python (mobile SDK lives here: src/agent_runtime_cockpit/mobile/, cli/mobile.py, tests/)
cd python && uv run ruff check src tests && uv run pytest tests/ -q

# TypeScript protocol (packages/arc-protocol-ts) — note the coverage gate
pnpm --filter @arc-studio/protocol test     # enforces coverage thresholds (jest.config.js)
pnpm typecheck                               # whole workspace
```

CI (`.github/workflows/node.yml`, `python.yml`) runs these on `main` — keep them green
locally so `main` never goes red.

## Mobile SDK specifics (learned the hard way)

- **`runtimes/` is gitignored.** New files there (e.g. `runtimes/mobile/spec/*.schema.json`)
  must be `git add -f`'d or tests that read them will fail only after a clean checkout.
  Confirm with `git status --ignored` if a test passes locally but not from a fresh clone.
- **`@arc-studio/protocol` has pinned coverage thresholds.** New `.ts` modules need tests in
  the same commit or `pnpm --filter @arc-studio/protocol test` fails the whole package.
- **`mobile trace <path>`** = inspect (leaf); **`mobile trace-verify <path>`** = chain verify
  (sibling). Don't reintroduce a `trace` sub-group — it shadows the leaf.
- **Types:** `MobileRuntimeEvent` / `MobilePolicyDecision` live in
  `packages/arc-protocol-ts/src/mobile-events.ts`; manifest/capability/action-plan types in
  `mobile-runtime.ts`. Import from the real source, not a sibling.
- **Never stage** the arena/opencode/vendor working-tree set; it is intentionally untracked
  churn, not part of the product.

## Canonical docs (CI-protected, update in place)

`docs/roadmap.md`, `docs/phases.md`, `AGENTS.md` — one of each, never fork. Mobile phases go
into the same `docs/phases.md`.
