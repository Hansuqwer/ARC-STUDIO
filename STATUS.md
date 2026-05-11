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
- `pnpm build`, `pnpm -r test`, `pnpm check:pr`, and Playwright smoke tests pass locally.
- SwarmGraph runs execute through the real local CLI with default `stub` backend.
- Run Timeline supports prompt input, workspace refresh, trace path display, and explicit run status feedback.
- `arc runs --workspace <path>` lists workspace-scoped traces newest-first.
- `arc runs get <run-id> --workspace <path>` returns one stored run record or a truthful `NOT_FOUND` error.
- `arc runs trace <run-id> --workspace <path> --tail N` returns trace metadata and bounded tail lines.
- `arc runs prune --workspace <path> --keep N` dry-runs trace cleanup unless `--yes` is passed.
- Run Timeline can replay stored JSONL events and connect to the local daemon SSE stream.
- Run Timeline includes trace filtering, selected-event JSON inspection, trace JSON copy, and run JSON export.
- SwarmGraph provider-backed execution is gated by `ARC_SWARMGRAPH_ALLOW_COSTS=true`.
- LangGraph dynamic workflow export is available through `ARC_LANGGRAPH_EXPORT=module:function`.
- Daemon integration tests cover `/api/runs` and `/api/runs/{run_id}/events` SSE.
- Unsigned Electron directory packaging smoke passes with signing disabled.
- E2E workflow runs on push and pull requests.

## Mock/Demo-Only

- SwarmGraph fixture workflow/schema remain for tests and demos only.
- SwarmGraph demo run is available only as `demo_run_workflow()` in Python tests/manual demos.
- Context providers without credentials return mock/offline entries.
- Test fixtures live under `packages/arc-test-fixtures` and tests.

## Broken Or Not Verified

- Electron signing/notarization is not verified.
- E2E no longer relies on command-palette shortcuts; Run Timeline opens through `?arc-view=run-timeline`.

## Not Yet Implemented

- Real LangGraph runtime execution beyond dynamic workflow export.
- CrewAI, OpenAI Agents SDK, AG2 adapters.
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
