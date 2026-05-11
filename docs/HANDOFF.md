# Handoff

## Current Status

This repo is a prototype prepared for GitHub handoff. Python core commands and tests are verified. Theia build and Electron packaging are not verified in this environment because `pnpm` is unavailable.

## Known Failures / Blockers

- `pnpm -r build` cannot run here: `pnpm` command not found.
- Theia browser/electron apps need a machine with Node 20+ and pnpm 9+.
- Real SwarmGraph execution is not implemented.
- Real LangGraph dynamic graph loading is not implemented.
- E2E Playwright tests require a running browser app.

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
```

## Expected Results

- Python tests pass.
- Node fixture/protocol tests pass.
- `pnpm -r build` is blocked until pnpm is installed.

## Completion Plan

1. Install Node 20+ and pnpm 9+; prove Theia build.
2. Add CI passing Python tests and Node build/tests.
3. Implement real SwarmGraph run/trace/audit paths or keep `can_run=False`.
4. Implement real LangGraph graph loading or narrow capability claims.
5. Add daemon integration tests and E2E tests.
6. Implement replay viewer and live event streaming.
7. Package unsigned Electron locally, then signed builds.

## Ownership Assumptions

- Runtime adapter owners implement real runtime behavior.
- IDE owner proves Theia build and removes scaffolding gaps.
- Release owner handles signing, update, and packaging.
