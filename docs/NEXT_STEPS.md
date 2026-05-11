# ARC Studio — Next Steps

## Immediate (Alpha → Beta)

### 1. Run the Theia build locally (30 min)

```bash
# Requires Node.js 20+, pnpm 9+
pnpm install        # ~5 min (downloads Theia packages)
pnpm build          # ~15 min (compiles extensions)
pnpm start:browser  # starts on http://localhost:3000
```

### 2. Connect the Python daemon

```bash
cd python
uv run arc serve
# ARC panel in browser IDE will show live data
```

### 3. Run E2E tests

```bash
pnpm test:e2e
# Requires: pnpm start:browser running in another terminal
```

### 4. Enable live context providers

```bash
export ARC_CONTEXT7_API_KEY=<key>
export GITHUB_TOKEN=<token>
uv run arc context pack --task "build theia extension"
```

## Short Term (Beta)

- [ ] Wire `arc-workflows` graph widget to real workflow data via Theia ↔ Python IPC
- [ ] Implement real-time event streaming (SSE → Theia widget)
- [ ] Add Theia ↔ Python integration test (spawn real daemon)
- [ ] Implement replay viewer (JSONL playback)
- [ ] Add LangGraph live execution (install `langgraph`)
- [ ] Add SwarmGraph live execution (install from GitHub)
- [ ] Electron packaging (set signing certs)
- [ ] Add more Open VSX extensions (JSON, Python, YAML viewers)

## Medium Term

- [ ] Add CrewAI adapter
- [ ] Add OpenAI Agents SDK adapter
- [ ] Add AG2 adapter
- [ ] Implement A2UI v1.0 renderer (when spec stable)
- [ ] Add Flutter project extension (enable via settings)
- [ ] CI/CD pipeline (GitHub Actions)
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
