# Contributing to ARC Studio

Thank you for considering a contribution. ARC Studio is Apache-2.0 licensed.

## Quick start

```bash
# Python backend
cd python && uv sync
uv run pytest -q

# TypeScript / Theia extension
pnpm install --frozen-lockfile
pnpm --filter @arc-studio/protocol build
pnpm --filter arc-extension build
pnpm check:pr
```

## Branching

- `main` is the integration branch.
- Feature branches: `feat/<short-slug>` · fixes: `fix/<short-slug>` · docs: `docs/<short-slug>` · chores: `chore/<short-slug>`.

## Commit messages — Conventional Commits 1.0

Format: `<type>(<scope>)!: <subject>`

Allowed types: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `build`, `ci`, `chore`, `revert`.

The `!` marker (or a `BREAKING CHANGE:` footer) signals a breaking change and triggers ADR-022's deprecation flow.

Examples:
- `feat(audit): add HMAC chain verification CLI`
- `fix(arc-ag-ui): render HITL_REQUESTED events in trace widget`
- `refactor(arc-extension)!: split arc-backend-service into config + run-lifecycle`

## PR checklist

- [ ] `uv run pytest -q` → 1428 passed, 20 skipped (no regressions)
- [ ] `uv run ruff check src tests` clean on touched files
- [ ] `pnpm check:pr` green
- [ ] New behavior covered by tests (Python and/or Jest)
- [ ] If schema changed: fixture added under `protocol/fixtures/` AND both loaders pass
- [ ] If architectural: ADR added under `docs/adr/`
- [ ] If breaking: deprecation alias + `@deprecated` JSDoc / `DeprecationWarning` per ADR-022
- [ ] Docs updated (tutorial / how-to / reference / explanation as appropriate)

## Code review expectations

Reviewers look for: contract preservation (wire format, public API), test coverage of the *behavior* (not the lines), ADR alignment, and clear commit messages. First-time contributors get extra patience — flag yourself as new in the PR description.

## Pre-commit hooks

Pre-commit hooks run automatically after `pnpm install`. To bypass in an emergency:

```bash
git commit --no-verify -m "wip: ..."
HUSKY=0 git commit -m "..."   # disable for the whole shell session
```

## Reporting issues

Security issues: see `SECURITY.md`. Everything else: open a GitHub issue with a minimal reproduction.
