# ARC Studio — Next Steps

## Immediate (Alpha → Beta)

### 1. Run the verified checks

```bash
pnpm build
pnpm -r test
cd python && uv run pytest -q
cd python && uv run ruff check src tests
cd tests/e2e && pnpm exec playwright test
pnpm check:pr
```

### 2. Start the browser IDE

```bash
ARC_WORKSPACE_PATH=/path/to/swarmgraph/workspace \
ARC_SWARMGRAPH_CLI=/path/to/swarmgraph \
pnpm start:browser:stub
```

### 3. Inspect local run history

```bash
cd python
uv run arc runs --workspace /path/to/swarmgraph/workspace --json
uv run arc runs trace <run-id> --workspace /path/to/swarmgraph/workspace --tail 5 --json
uv run arc runs prune --workspace /path/to/swarmgraph/workspace --keep 20 --json
```

### 4. Enable live context providers

```bash
export ARC_CONTEXT7_API_KEY=<key>
export GITHUB_TOKEN=<token>
uv run arc context pack --task "build theia extension"
```

## Short Term (Beta)

- [x] Add timeline replay controls for stored JSONL events
- [x] Connect Theia run timeline to local daemon SSE stream
- [x] Add daemon integration test coverage for `/api/runs` and SSE events
- [x] Add trace filtering, event detail inspection, trace copy, and run JSON export
- [x] Add LangGraph dynamic export hook via `ARC_LANGGRAPH_EXPORT=module:function`
- [x] Add LangGraph real run path via explicit `ARC_LANGGRAPH_EXPORT`
- [x] Add provider-backed SwarmGraph execution behind `ARC_SWARMGRAPH_ALLOW_COSTS=true`
- [x] Add unsigned Electron packaging smoke
- [ ] Add more Open VSX extensions (JSON, Python, YAML viewers)
- [ ] Add LangGraph streaming/event support

## Medium Term

- [ ] Add CrewAI adapter
- [ ] Add OpenAI Agents SDK adapter
- [ ] Add AG2 adapter
- [ ] Implement A2UI v1.0 renderer (when spec stable)
- [ ] Add Flutter project extension (enable via settings)
- [x] Upload Playwright traces/screenshots from E2E CI failures
- [x] Add package/plugin license policy check
- [ ] Auto-update (electron-updater)

## Production Criteria

- [ ] Signed installers (Mac, Windows, Linux)
- [ ] Auto-update endpoint
- [ ] Privacy policy (if telemetry added)
- [ ] Crash/error reporting (Sentry or similar)
- [ ] License audit of all bundled extensions
- [ ] Compatibility matrix (OS versions, Node, Python)
- [ ] Real user validation of all core workflows
- [ ] Security review by external party
