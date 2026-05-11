# Handoff

## Current Status

This repo is a prototype prepared for GitHub handoff. Python core commands, Theia build, Node tests, and Playwright smoke coverage are verified locally on the handoff branch.

## Known Failures / Blockers

- Provider-backed SwarmGraph execution requires explicit approval before running paid/external calls.
- Real LangGraph dynamic graph loading is not implemented.
- Electron packaging/signing is not verified.
- Run Timeline Playwright prompt-control coverage skips when Theia command service is not exposed to browser globals.

## Commands Run

```bash
git init
git checkout -b handoff/no-mockups-github-ready
cd python && uv sync --all-extras --dev
cd python && .venv/bin/python -m pytest
cd python && .venv/bin/arc --help
cd python && .venv/bin/arc inspect --json
cd python && .venv/bin/arc runtimes --json
cd python && .venv/bin/arc workflows --json
cd python && .venv/bin/arc schemas --json
cd python && .venv/bin/arc adapter test swarmgraph --json
cd python && .venv/bin/arc adapter test langgraph --json
node tests/unit/arc-protocol.test.js
node packages/arc-test-fixtures/src/index.js
bash scripts/check-artifacts.sh
pnpm -r build
pnpm -r test
pnpm check:pr
cd tests/e2e && pnpm exec playwright test
cd python && uv run pytest -q
cd python && uv run ruff check src tests
cd python && uv run arc runs get <run-id> --workspace <workspace> --json
cd python && uv run arc runs trace <run-id> --workspace <workspace> --tail 5 --json
cd python && uv run arc runs prune --workspace <workspace> --keep 20 --json
```

## Expected Results

- Python tests pass.
- Node fixture/protocol tests pass.
- `pnpm -r build` passes locally.
- E2E smoke currently passes with command-palette tests skipped.
- Run Timeline E2E opens through `?arc-view=run-timeline`, executes a local stub-backed run, and verifies reload history through `arc runs`.

## Completion Plan

1. Keep CI passing Python tests and Node build/tests.
2. Replace brittle command-palette E2E skips with stable Theia page objects.
3. Extend SwarmGraph trace/audit paths beyond JSONL run records.
4. Implement real LangGraph graph loading or narrow capability claims.
5. Add daemon integration tests and E2E tests.
6. Implement replay viewer and live event streaming.
7. Package unsigned Electron locally, then signed builds.

## Ownership Assumptions

- Runtime adapter owners implement real runtime behavior.
- IDE owner proves Theia build and removes scaffolding gaps.
- Release owner handles signing, update, and packaging.
