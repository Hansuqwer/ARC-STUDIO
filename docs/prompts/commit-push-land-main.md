# Prompt — Commit, Push, and Land on Main

## Pre-conditions (must all be true before committing)

1. `cd python && uv run ruff check src tests` → exit 0
2. `uv run pytest -q -p no:cacheprovider --ignore=tests/budget/test_persistence.py` → all pass
3. `bash scripts/check-banned-claims.sh docs/roadmap.md docs/phases.md AGENTS.md README.md` → "OK: No banned claims found."
4. Only the intended files are staged (`git diff --cached --name-only` — no `.arc/`, `snapshot_report.html`, `docs/reports/`, `docs/UX_AUDIT*.md`, `TOKEN_SAVING_PLAN*.md`)

## Staging rules

- **Never `git add .`** — always `git add <explicit file list>`
- Remove temp artefact before staging: `rm -f python/snapshot_report.html`
- The following are never committed: `python/.arc/*`, `python/snapshot_report.html`, `docs/reports/*`, `docs/UX_AUDIT*.md`, `TOKEN_SAVING_PLAN*.md`, `runtimes/Arc-Studio-Mobile-SDK/`

## Commit

Write the message to `.git/ARC_COMMIT_MSG.txt` (avoids shell quote-splitting on special chars):

```bash
cat > .git/ARC_COMMIT_MSG.txt << 'MSGEOF'
<type>(<scope>): <subject under 70 chars>

<body — what changed and why; reference R-item / Phase if applicable>

<test count line, e.g.: 5463 passed, 42 skipped, 5 xfailed>
MSGEOF
git commit -F .git/ARC_COMMIT_MSG.txt
rm -f .git/ARC_COMMIT_MSG.txt
```

Conventional commit types: `feat` / `fix` / `test` / `refactor` / `docs` / `chore`

## Push

```bash
git push origin main
```

This project commits directly to `main` (no PR branches unless explicitly requested).

## CI gate

Poll until all 6 required jobs are `completed success`:

```bash
SHA=$(git rev-parse --short HEAD)
gh run list --branch main --limit 6 --json status,conclusion,name,headSha \
  --jq ".[]|select(.headSha[:7]==\"$SHA\")|\"\\(.name): \\(.status) \\(.conclusion//\"-\")\""
```

Required jobs: `signing-preflight`, `perf (informational)`, `node`, `e2e`, `python`, `ARC Roadmap Gate`

- Poll every ~90–120 s; `ARC Roadmap Gate` is the long pole (~6–8 min).
- If `e2e` fails with `@vscode/ripgrep` HTTP 403, re-run it: `gh run rerun <id> --failed` — this is a known transient infra flake unrelated to code.
- Any other failure: diagnose before re-running.

## Done

When all 6 are `completed success`, the change is landed on `main`.
No separate merge step is needed — this repo does not use PRs for agent work.
