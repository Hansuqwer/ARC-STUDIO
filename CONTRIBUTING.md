# Contributing

## Setup

```bash
cd python
uv sync --all-extras --dev
.venv/bin/python -m pytest

cd ..
pnpm install
pnpm build
```

## Test Commands

```bash
cd python
.venv/bin/python -m pytest
.venv/bin/arc inspect --json
.venv/bin/arc adapter test swarmgraph --json
.venv/bin/arc adapter test langgraph --json

cd ..
node tests/unit/arc-protocol.test.js
node packages/arc-test-fixtures/src/index.js
pnpm -r test
```

## Mock Policy

- Normal product paths must not silently return mock success.
- Test fixtures and demo helpers are allowed only when clearly named and marked.
- Runtime capabilities must describe real product behavior, not fixture behavior.
- If a dependency, daemon, or runtime is unavailable, return an explicit error.

## Definition Of Done

- Tests added or updated.
- Python tests pass.
- Node/Theia build checked when tooling is available.
- Docs updated with verified command output.
- No venvs, caches, node modules, generated build output, or secrets committed.
