# Handoff

## Current Status

This repo is a prototype prepared for GitHub handoff. Python core commands, Theia build, Node tests, and Playwright smoke coverage are verified locally on the handoff branch.

## Known Failures / Blockers

- Provider-backed SwarmGraph execution requires explicit approval before running paid/external calls.
- Real LangGraph runtime execution is not implemented beyond dynamic workflow export.
- Electron packaging/signing is not verified.

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
pnpm check:licenses
pnpm package:electron:dir
```

## Expected Results

- Python tests pass.
- Node fixture/protocol tests pass.
- `pnpm -r build` passes locally.
- Run Timeline E2E opens through `?arc-view=run-timeline`, executes a local stub-backed run, and verifies reload history through `arc runs`.
- Daemon integration tests cover run listing and SSE event replay.
- Electron packaging smoke creates an unsigned directory build only; signing remains blocked on credentials.

## Completion Plan

1. Keep CI passing Python tests and Node build/tests.
2. Extend SwarmGraph audit paths beyond JSONL run records.
3. Implement real LangGraph runtime execution or narrow capability claims further.
4. Expand daemon integration and E2E coverage for error paths.
5. Package signed Electron builds after credentials are available.

## Ownership Assumptions

- Runtime adapter owners implement real runtime behavior.
- IDE owner proves Theia build and removes scaffolding gaps.
- Release owner handles signing, update, and packaging.
