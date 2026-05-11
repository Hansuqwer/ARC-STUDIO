# ARC Studio Status

Generated during GitHub handoff prep.

## Verified Working

- `cd python && uv sync --all-extras --dev` installs Python deps.
- `cd python && .venv/bin/python -m pytest` passes: `82 passed` after handoff fixes.
- `.venv/bin/arc --help` displays CLI commands.
- `.venv/bin/arc inspect --json` returns ARC envelope JSON.
- `.venv/bin/arc adapter test swarmgraph --json` passes conformance with real run skipped/unsupported.
- `.venv/bin/arc adapter test langgraph --json` passes conformance.
- `node tests/unit/arc-protocol.test.js` passes bootstrap protocol tests.
- `node packages/arc-test-fixtures/src/index.js` passes fixture self-test.
- `bash scripts/check-artifacts.sh` fails if venvs, caches, node modules, generated builds, or trace JSONL files are tracked.

## Mock/Demo-Only

- SwarmGraph fixture workflow/schema remain for tests and demos only.
- SwarmGraph demo run is available only as `demo_run_workflow()` in Python tests/manual demos.
- Context providers without credentials return mock/offline entries.
- Test fixtures live under `packages/arc-test-fixtures` and tests.

## Broken Or Not Verified

- `pnpm` is missing in this environment, so Theia install/build/start is not verified.
- Electron packaging/signing is not verified.
- E2E Playwright tests are present but not verified.
- `uv run pytest` may use the wrong system Python in this environment; direct `.venv/bin/python -m pytest` is verified.

## Not Yet Implemented

- Real SwarmGraph workflow execution.
- Real LangGraph dynamic graph export/execution.
- Replay viewer.
- SSE event streaming wired into Theia UI.
- CrewAI, OpenAI Agents SDK, AG2 adapters.
- CI-backed Theia build/e2e proof.
- Signed Electron installers and auto-update.

## Requires Credentials

- `ARC_CONTEXT7_API_KEY` for live Context7 docs.
- `GITHUB_TOKEN` for GitHub code search.
- `ARC_SEARCH_API_KEY` and `ARC_SEARCH_PROVIDER` for web search.
- Electron/macOS signing env vars for distribution builds.

## Requires Local Tooling

- Node.js 20+.
- pnpm 9+.
- uv.
- Python 3.11+.
