# ARC Studio — Troubleshooting

## Browser App Won't Start

**Symptom:** `pnpm start:browser` fails or browser shows blank page.

**Fixes:**
1. Ensure `pnpm build` ran successfully first
2. Check Node.js version: `node --version` (must be 20+)
3. Clear build artifacts: `pnpm clean && pnpm install && pnpm build`
4. Check port 3000 is free: `lsof -i :3000`

## ARC Panel Shows Mock Data

**This is expected** when the Python daemon is not running.

**To connect real data:**
```bash
cd python
uv run arc serve
# ARC daemon running on http://localhost:7777
```

Then reload the browser (Theia will reconnect automatically).

## Python CLI Not Found

**Symptom:** `uv run arc --help` fails.

**Fix:**
```bash
cd python
uv sync --all-extras --dev
uv run arc --help
```

If `uv` is not installed:
```bash
pip install uv --user
# or
curl -LsSf https://astral.sh/uv/install.sh | sh
```

## Context7 Returns Mock Data

**Symptom:** Context pack shows "[MOCK — Context7 API key not set]"

**Fix:**
```bash
export ARC_CONTEXT7_API_KEY=your_key
uv run arc context pack --task "theia extension"
```

Get a key at https://context7.com/

## GitHub Search Returns Mock Data

```bash
export GITHUB_TOKEN=ghp_your_token
```

## Conformance Tests Fail

```bash
uv run arc adapter test swarmgraph --debug
uv run arc adapter test langgraph --debug
```

## Theia Build Fails (Native Modules)

For Electron, native modules must be rebuilt:

```bash
cd applications/electron
pnpm rebuild
```

## E2E Tests Fail

1. Ensure browser app is running: `pnpm start:browser`
2. Install Playwright browsers: `cd tests/e2e && pnpm install:browsers`
3. Run E2E: `pnpm test:e2e`

## Port 7777 Already in Use

```bash
lsof -i :7777
kill -9 <PID>
# or use a different port:
uv run arc serve --port 7778
```

## ARC Daemon Not Detected by Theia

Theia checks `localhost:7777/health` on startup. Ensure:
1. Daemon is running: `uv run arc serve`
2. No firewall blocking localhost
3. Check ARC settings: `arc.daemon.port` (default: 7777)
