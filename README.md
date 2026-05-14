# ARC Studio

ARC Studio is a local developer tool for inspecting, running, and debugging agent workflows built on SwarmGraph, LangGraph, CrewAI, OpenAI Agents SDK, and (partial) LlamaIndex. It ships as a Python CLI and daemon plus an Eclipse Theia IDE shell available as a browser app or an Electron desktop app.

ARC Studio runs entirely on your workstation. No telemetry is sent. No data leaves the loopback interface.

## Status

Pre-release (`v0.1.0-alpha`, tagged 2026-05-14). Pin against tags or commit SHAs; the public API surface may still change. See [CHANGELOG.md](./CHANGELOG.md) and [docs/SECURITY_AUDIT_REPORT.md](./docs/SECURITY_AUDIT_REPORT.md) for what changed recently and what is still outstanding.

ARC Studio supports the following runtimes:
- **SwarmGraph** - In-repo canonical runtime for AI provider routing and quota management (`runtimes/swarmgraph/`)
- **LangGraph** - Stateful agent orchestration
- **Trace Visualization** - Real-time execution monitoring
- **Workflow Detection** - Automatic workflow discovery

## Prerequisites

The toolchain versions are pinned in [`.tool-versions`](./.tool-versions). If you use `asdf` or `mise` they will be picked up automatically; otherwise install manually:

- Node.js 20.18.0
- pnpm 9.15.9
- Python 3.11.10
- [`uv`](https://github.com/astral-sh/uv) for Python dependency management

## Quick Start

```bash
# 1. Clone and install JS deps
git clone <this-repo>
cd arc-theia-studio
pnpm install --frozen-lockfile

# 2. Bootstrap development environment
bash scripts/bootstrap-dev.sh
```

Visit http://localhost:3000 to access ARC Studio.

## Development

### Project Structure

```
arc-theia-studio/
├── packages/
│   ├── arc-extension/       # Main Theia extension
│   ├── arc-browser-app/     # Browser application
│   ├── arc-electron-app/    # Electron application (TODO)
│   └── arc-test-fixtures/   # Test utilities (TODO)
├── runtimes/
│   └── swarmgraph/          # Vendored SwarmGraph runtime sub-project
├── python/
│   ├── src/                 # Python backend
│   └── tests/               # Python tests
├── docs/                    # Documentation
└── scripts/                 # Build and setup scripts
```

### Available Commands

```bash
# Development
pnpm install              # Install dependencies
pnpm build               # Build all packages
pnpm watch               # Watch mode for development
pnpm clean               # Clean build artifacts

# Running
pnpm start:browser       # Start browser app (port 3000)
pnpm start:electron      # Start Electron app (TODO)

# Testing
pnpm test                # Run all tests
pnpm test:e2e            # Run E2E tests (TODO)
pnpm lint                # Lint code
```

Then set up Python:

```bash
cd python
uv sync --all-extras --dev
cd ..

# 3. Build everything
pnpm -r build

# 4. Verify your install
cd python
uv run arc --help
uv run arc runtimes --capabilities --json
cd ..
```

If the commands above fail, see Troubleshooting below.

## Running

### Browser shell (recommended for development)

```bash
# Real backend (requires runtimes configured; see "Runtime Support")
pnpm start:browser:arc

# Stub backend (no real agents; useful for UI work)
pnpm start:browser:stub
```

The browser shell listens on `http://127.0.0.1:3000` and talks to the ARC daemon at `http://127.0.0.1:7777`. CORS is restricted to the browser shell's origin.

### Electron shell

```bash
pnpm start:electron
```

To produce an unsigned installer for local testing:

```bash
pnpm package:electron:dir
```

The unsigned build writes to `applications/electron/dist/`. A signed release build (`pnpm package:electron`) requires the macOS signing environment variables described in `.env.example`.

### Daemon only (headless)

```bash
cd python
uv run arc serve
uv run arc serve --help
```

The daemon binds `127.0.0.1:7777` by default.

## CLI

The `arc` CLI is the canonical surface; the Theia shell is a thin UI over it. Available commands:

```text
arc inspect       Inspect a workflow file's structure
arc runtimes      List detected runtimes and their capabilities
arc workflows     Enumerate workflows in the current workspace
arc schemas       Print or validate workflow schemas
arc serve         Start the local daemon
arc run           Execute a workflow
arc context       Manage context providers
arc adapter       Manage and test runtime adapters
arc doctor        Runtime-specific diagnostics
arc eval          Evaluate runs against golden traces
arc runs          Inspect past runs and traces
arc providers     Manage credential providers
```

| Runtime | Current support | Missing |
| --- | --- | --- |
| SwarmGraph | Source lives in `runtimes/swarmgraph/`; ARC Studio talks to it through the existing CLI/subprocess contract | Audit integrations |
| LangGraph | Detection, AST workflow heuristics, dynamic export/run hook, fixture schema | Streaming/events; see `docs/RUNTIMES.md` |
| CrewAI | Not implemented | Adapter |
| OpenAI Agents SDK | Not implemented | Adapter |
| AG2 | Not implemented | Adapter |

Run `uv run arc <command> --help` for the flags on any subcommand.

## Runtime Support

The table below is auto-generated. To refresh it, run:

```bash
bash scripts/generate-runtime-table.sh
```

<!-- RUNTIMES:START -->
| Runtime       | Detected | Can run | Paid | Notes                                              |
|:--------------|--------:|-------:|----:|:---------------------------------------------------|
| swarmgraph    | yes      | no      | no   | install missing; set `ARC_SWARMGRAPH_CLI`          |
| langgraph     | yes      | no      | no   | requires export target; set `ARC_LANGGRAPH_EXPORT` |
| crewai        | yes      | no      | yes  | install missing; set `ARC_CREWAI_EXPORT`           |
| openai-agents | no       | no      | yes  | not detected; set `OPENAI_API_KEY`                 |
| llamaindex    | no       | no      | no   | not detected                                       |
<!-- RUNTIMES:END -->

"Detected" means the adapter is importable. "Can run" means the adapter plus its required configuration are both present. "Paid" means a successful run will make billable API calls; such runs are gated behind the `allow_paid_calls` flag and are opt-in.

## Security

ARC Studio is designed as a single-user, loopback-only tool. The daemon binds to `127.0.0.1` and does not currently require authentication; any process running as your user on the same host can reach it. This is acceptable for a personal developer workstation; it is not acceptable on multi-tenant hosts, shared dev containers, or anywhere a non-trusted process can open a localhost socket.

For the full threat model, resolved findings, and residual items, see [docs/SECURITY_AUDIT_REPORT.md](./docs/SECURITY_AUDIT_REPORT.md).

To report a security issue, please open a private security advisory on GitHub rather than a public issue.

## Project Layout

```text
applications/             Theia app shells (browser, electron)
theia-extensions/         Theia extensions (arc-core is the live one)
python/                   Python CLI, daemon, and adapters
  src/agent_runtime_cockpit/
docs/                     Documentation; see docs/history/ for older working notes
scripts/                  Build, lint, and dev-loop helpers
```

The `packages/arc-extension/` tree present in older drafts of the repository is not used; the live extension is `theia-extensions/arc-core`.

## Troubleshooting

### `pnpm install` fails with a lockfile error

Make sure you are on pnpm 9.15.9 (`pnpm --version`). The version is pinned in `.tool-versions`. The CI uses `--frozen-lockfile` and so should you.

### `arc runtimes` shows `can_run=false` for everything

This is expected on a fresh install. Each runtime has a required env var (see the table above). Set the one(s) you need in your `.env` (copy from `.env.example`).

### `arc doctor` says "Missing command"

`arc doctor` is a command group. Use a concrete subcommand such as `cd python && uv run arc doctor swarmgraph`.

### The browser shell loads but shows no workflows

ARC Studio scans the workspace you open in Theia. The default workspace is the repo root; switch via File → Open Workspace.

### Build emits a Node.js DEP0190 warning

Known issue in `@theia/cli`. Build succeeds. Will be tracked upstream; not a regression in ARC.

## Contributing

Branch from `main`. Run `pnpm check:pr` before opening a PR; this runs the secret scan, type-check, and tests. New behaviour needs a test; new public APIs need a CHANGELOG entry.

## License

Apache-2.0. See [LICENSE](./LICENSE).
