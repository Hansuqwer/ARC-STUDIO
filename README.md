# ARC Studio

ARC Studio is a local developer tool for inspecting, running, and debugging agent workflows. It ships as a Python CLI and loopback daemon plus an Eclipse Theia shell. The canonical Theia extension is `packages/arc-extension`.

ARC Studio runs entirely on your workstation. No telemetry is sent. No data leaves the loopback interface.

## Status

Pre-release (`v0.1.0-alpha`, tagged 2026-05-14). Pin against tags or commit SHAs; the public API surface may still change. See [CHANGELOG.md](./CHANGELOG.md) and [docs/SECURITY_AUDIT_REPORT.md](./docs/SECURITY_AUDIT_REPORT.md) for what changed recently and what is still outstanding.

ARC Studio currently supports these standalone runtime surfaces:
- **SwarmGraph** - In-repo runtime with queen/worker orchestration, consensus, HITL, audit, provider gateway, and CLI execution (`runtimes/swarmgraph/`). ARC calls it through a configured CLI launcher.
- **LangGraph** - Detection, workflow inspection, explicit export/run via `ARC_LANGGRAPH_EXPORT`, and persisted node-update events when `.stream()` is available.
- **CrewAI** - Detection and exported crew execution via `ARC_CREWAI_EXPORT`, gated as potentially paid provider calls.
- **OpenAI Agents SDK** - Partial adapter. Detection and SDK-backed execution exist, but project entrypoint/export wiring is not complete.
- **LlamaIndex** - Detection/static workflow export only. No run path.
- **Trace Visualization** - Stored run/event inspection in the Theia shell.

ARC does **not** yet compose CrewAI, LangGraph, OpenAI Agents, AG2, or LlamaIndex inside SwarmGraph. “Runtime + SwarmGraph” orchestration is planned work, not current product behavior.

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
│   ├── arc-ag-ui/           # AG-UI helpers/tests
│   ├── arc-protocol-ts/     # TypeScript protocol types
│   └── arc-test-fixtures/   # Test fixtures
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

### Electron shell (post-v0.1)

```bash
pnpm start:electron
```

To produce an unsigned installer for local testing:

```bash
pnpm package:electron:dir
```

Electron packaging is a post-v0.1 spike. The commands above are development/proof paths, not the v0.1 release target. The v0.1 release scope is the browser app plus Python CLI/wheel.

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

| Runtime | Current standalone support | Missing / limitation |
| --- | --- | --- |
| SwarmGraph | CLI/subprocess runner via `ARC_SWARMGRAPH_CLI`; detects SwarmGraph projects; exports heuristic workflow/schema data | ARC does not expose full vendored SwarmGraph audit/replay/HITL UX; SSE trace replay is available, active-run streaming is planned |
| LangGraph | Detection, AST workflow heuristics, dynamic export/run hook via `ARC_LANGGRAPH_EXPORT`, `.invoke()` and `.stream()` support when available | No live token stream UI; persisted traces keep coalesced node updates only |
| CrewAI | Detection and real exported crew execution via `ARC_CREWAI_EXPORT` with paid-call gating | Static workflow export only; no rich graph extraction or provider-side cancellation |
| OpenAI Agents SDK | Detection and SDK-backed execution when `agents` is installed and OpenAI cost gates are configured | User project entrypoint/export target is not complete; current run path uses an internal test agent |
| AG2 | Registered standalone adapter with detection/run scaffolding under `python/src/agent_runtime_cockpit/adapters/ag2/` | Real dependency/runtime path is gated; availability depends on project deps and config |
| LlamaIndex | Detection and static workflow export only | No run path |
| LM Arena | Stub/offline battle/direct/code/agent-preview responses | No live model calls |

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

"Detected" means the adapter found runtime evidence or an importable dependency. "Can run" means the adapter plus its required configuration are both present. "Paid" means a successful run may make billable API calls; such runs are gated behind explicit cost flags and are opt-in.

CrewAI, LangGraph, OpenAI Agents, AG2, LlamaIndex, and LM Arena are ARC adapter surfaces, not SwarmGraph backends. ARC can run supported standalone adapters beside SwarmGraph from the same cockpit, but it does not currently compose them inside a SwarmGraph queen/worker/consensus/HITL/audit graph unless user code implements that composition.

## SwarmGraph Adoption Layer Status

The intended product direction is runtime-agnostic execution with optional SwarmGraph adoption mode. In that future mode, external runtimes such as CrewAI, LangGraph, OpenAI Agents SDK, AG2, and LlamaIndex would be wrapped by SwarmGraph queen/worker decomposition, votes, consensus, HITL approval, deterministic orchestration, and signed audit records.

That adoption layer is **not implemented yet**. Current code has standalone adapters plus a sequential combo adapter; it is not SwarmGraph composition.

## Security

ARC Studio is designed as a single-user, loopback-only tool. The daemon binds to `127.0.0.1` and does not currently require authentication; any process running as your user on the same host can reach it. This is acceptable for a personal developer workstation; it is not acceptable on multi-tenant hosts, shared dev containers, or anywhere a non-trusted process can open a localhost socket.

For the full threat model, resolved findings, and residual items, see [docs/SECURITY_AUDIT_REPORT.md](./docs/SECURITY_AUDIT_REPORT.md).

To report a security issue, please open a private security advisory on GitHub rather than a public issue.

## Project Layout

```text
applications/             Theia app shells (browser, electron)
packages/arc-extension/   Canonical ARC Theia extension
theia-extensions/         Secondary/experimental Theia extensions; not the canonical shell path
python/                   Python CLI, daemon, and adapters
  src/agent_runtime_cockpit/
docs/                     Documentation; see docs/history/ for older working notes
scripts/                  Build, lint, and dev-loop helpers
```

Historical docs may still refer to `theia-extensions/arc-core` as the live extension. Treat `packages/arc-extension` as canonical unless that architecture is explicitly changed.

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
