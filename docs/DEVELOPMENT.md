# ARC Studio — Development Guide

## Prerequisites

| Tool | Version | Required For |
|------|---------|--------------|
| Node.js | 20+ | Theia extensions |
| pnpm | 9+ | Package management |
| Python | 3.11+ | ARC daemon/CLI |
| uv | 0.4+ | Python env management |

## Setup

```bash
# Clone and bootstrap
git clone https://github.com/your-org/arc-theia-studio
cd arc-theia-studio
bash scripts/bootstrap.sh

# Or manually:
pnpm install
cd python && uv sync --all-extras --dev
```

## Running in Development

### Browser IDE
```bash
pnpm build           # compile all extensions
pnpm start:browser   # http://localhost:3000
```

### Python Daemon
```bash
cd python
uv run arc serve             # http://localhost:7777
uv run arc serve --debug     # with debug logging
```

### Watch Mode (Extension Development)
```bash
# Terminal 1: watch extension
cd theia-extensions/arc-core && pnpm watch

# Terminal 2: browser app
pnpm start:browser
# Then reload browser tab after extension changes
```

## Adding a New Extension

1. Create `theia-extensions/my-ext/`
2. Add `package.json` with `theiaExtensions` entry
3. Add `tsconfig.json` extending `../../tsconfig.base.json`
4. Create `src/browser/my-ext-frontend-module.ts`
5. Add to `applications/browser/package.json` dependencies
6. Run `pnpm install && pnpm build`

## Adding a New Runtime Adapter

1. Create `python/src/agent_runtime_cockpit/adapters/myadapter.py`
2. Extend `RuntimeAdapter` base class
3. Implement `detect()`, `capabilities()`, `export_workflow()`, `export_schemas()`
4. Register in `adapters/registry.py::AdapterRegistry.build_default()`
5. Add tests in `python/tests/test_adapters.py`
6. Run conformance: `uv run arc adapter test myadapter`

## Environment Variables

| Variable | Description |
|----------|-------------|
| `ARC_DEBUG=1` | Enable debug logging |
| `ARC_USE_FIXTURE_RUNTIME=1` | Force fixture data even with real adapters |
| `ARC_MOCK_CONTEXT7=1` | Force Context7 mock provider |
| `ARC_CONTEXT7_API_KEY` | Context7 API key |
| `GITHUB_TOKEN` | GitHub code search token |
| `ARC_SEARCH_API_KEY` | Web search API key (Brave, etc.) |
| `ARC_SEARCH_PROVIDER` | Search provider: `brave`, `serpapi`, `tavily` |

## Project Structure

See [README.md](../README.md) for the full monorepo layout.

## Code Style

- TypeScript: ESLint + Prettier (configured in root)
- Python: Ruff (configured in `pyproject.toml`)
- All mocks must include the standard metadata block (see ADR-0004)
