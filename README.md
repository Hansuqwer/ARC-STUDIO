# ARC Studio

Agent Runtime Cockpit for running, inspecting, and debugging AI agent workflows locally.

ARC Studio combines a Python CLI and loopback daemon with an Eclipse Theia browser shell. It is built for developers who need a local cockpit for agent runtime experiments, trace inspection, HITL flows, audit checks, replay, and workflow diagnostics without sending project data to a remote service.

ARC Studio is currently pre-release software (`v0.1.0-alpha`). Public APIs, UI surfaces, and runtime adapters may change before a stable release.

## Features

- Local-first workflow execution via the `arc` CLI and loopback daemon.
- Eclipse Theia browser app for workflow, run, trace, adapter, HITL, audit, and replay surfaces.
- Runtime detection and adapter scaffolding for SwarmGraph, LangGraph, CrewAI, OpenAI Agents SDK, AG2, LlamaIndex, and LM Arena (stub/gated).
- JSONL trace storage with a SQLite metadata index.
- Run lifecycle commands for status, search, export, import, replay, delete, backfill, prune, and storage maintenance.
- HITL prompt persistence with approval/rejection CLI and IDE integration.
- Audit-chain verification/export commands where audit material exists.
- Workspace trust checks, output redaction, paid-call gating, and subprocess/Docker isolation providers.
- Evaluation tooling for saved golden traces and batch reports.

## Status

ARC Studio is an alpha developer tool. Pin usage to a tag or commit SHA.

| Area | Status |
| --- | --- |
| Python CLI and daemon | Active primary surface |
| Browser app | Primary UI target |
| Electron app | Development/proof path, post-v0.1 release target |
| Runtime adapters | Mixed: some runnable, some detection/export/scaffold only |
| SwarmGraph adoption layer | Fake/offline default; narrow gated local-real path exists; no provider-backed execution |
| Security model | Single-user, loopback-only workstation tool |

See [CHANGELOG.md](./CHANGELOG.md), [docs/RELEASE_CHECKLIST.md](./docs/RELEASE_CHECKLIST.md), and [docs/SECURITY.md](./docs/SECURITY.md) for current release notes, verification, and residual risks.

## Architecture

ARC Studio has three main layers:

- **Python backend**: CLI, daemon, runtime adapters, trace storage, audit, HITL, config, trust, isolation, and eval tooling.
- **Theia extension**: TypeScript JSON-RPC service contract plus ARC Studio widgets in `packages/arc-extension`.
- **Applications**: The canonical browser shell in `applications/browser`; Electron remains a development path.

```text
arc-theia-studio/
├── applications/
│   ├── browser/             # Canonical Theia browser app
│   └── electron/            # Electron development/proof path
├── packages/
│   ├── arc-extension/       # Main ARC Theia extension
│   ├── arc-ag-ui/           # AG-UI helpers/tests
│   ├── arc-protocol-ts/     # TypeScript protocol types
│   └── arc-test-fixtures/   # Test fixtures
├── python/
│   ├── src/agent_runtime_cockpit/
│   └── tests/
├── runtimes/swarmgraph/     # Vendored SwarmGraph runtime project
├── docs/                    # ADRs, release docs, research, audits
└── scripts/                 # Build, bootstrap, verification helpers
```

`packages/arc-extension` is the canonical Theia extension. Some older docs may mention historical `theia-extensions/*` packages; treat those as migration/legacy context unless explicitly wired into the current app.

## Prerequisites

Tool versions are pinned in [`.tool-versions`](./.tool-versions):

- Node.js `20.18.0`
- pnpm `9.15.9`
- Python `3.11.10`
- [`uv`](https://github.com/astral-sh/uv) for Python dependency management

## Quick Start

```bash
git clone <this-repo>
cd arc-theia-studio
pnpm install --frozen-lockfile
bash scripts/bootstrap-dev.sh
```

Start the browser app with the real ARC backend:

```bash
pnpm start:browser:arc
```

Open `http://127.0.0.1:3000`.

For UI-only work without real agents:

```bash
pnpm start:browser:stub
```

## Python CLI

Set up the Python environment:

```bash
cd python
uv sync --all-extras --dev
uv run arc --help
uv run arc runtimes --capabilities --json
```

Common commands:

```bash
uv run arc serve
uv run arc workflows
uv run arc runtimes
uv run arc run --help
uv run arc runs search
uv run arc runs replay <run-id>
uv run arc audit verify <run-id>
uv run arc hitl pending
uv run arc eval run --batch
```

The daemon binds `127.0.0.1:7777` by default. The browser app talks to this loopback endpoint.

## Runtime Support

Runtime availability depends on installed dependencies, project contents, environment variables, and paid-call gates.

| Runtime | Current support | Limitations |
| --- | --- | --- |
| SwarmGraph | CLI/subprocess runner via `ARC_SWARMGRAPH_CLI`; detection and heuristic workflow/schema export | Full SwarmGraph composition UX is still maturing |
| LangGraph | Detection, AST workflow heuristics, export/run hook via `ARC_LANGGRAPH_EXPORT`, `.invoke()`/`.stream()` support when available | No live token stream UI; traces persist coalesced node updates |
| CrewAI | Detection and exported crew execution via `ARC_CREWAI_EXPORT` with paid-call gating | Static export only; no rich graph extraction or provider-side cancellation |
| OpenAI Agents SDK | Detection and SDK-backed execution when dependencies and gates are configured | Project entrypoint/export wiring is incomplete |
| AG2 | Registered adapter with detection/run scaffolding | Real dependency/runtime path is gated |
| LlamaIndex | Detection and static workflow export | No run path |
| LM Arena | Stub/offline battle/direct/code/agent-preview responses | No live model calls |

Refresh the generated runtime table when adapter state changes:

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

`Detected` means the adapter found runtime evidence or an importable dependency. `Can run` means the adapter and required configuration are available. `Paid` means a successful run may make billable provider calls; those paths require explicit opt-in.

ARC can run supported standalone adapters beside SwarmGraph from the same cockpit. It does not currently compose CrewAI, LangGraph, OpenAI Agents, AG2, LlamaIndex, or LM Arena inside a SwarmGraph queen/worker/consensus/HITL/audit graph unless user code implements that composition.

## Configuration

Start from the example environment file:

```bash
cp .env.example .env
```

Common runtime variables:

```bash
ARC_SWARMGRAPH_CLI=/path/to/swarmgraph
ARC_LANGGRAPH_EXPORT=module:function
ARC_CREWAI_EXPORT=module:function
OPENAI_API_KEY=...
```

Do not commit real secrets. Provider-backed or paid-call paths are gated and should be enabled deliberately.

ARC config can also be managed through the CLI:

```bash
cd python
uv run arc config init
uv run arc config show
uv run arc profiles list
uv run arc workspace info
```

## Development

JavaScript/TypeScript commands:

```bash
pnpm build
pnpm --filter @arc-studio/protocol build
pnpm --filter arc-extension build
pnpm test
pnpm --filter arc-extension test
pnpm lint
pnpm check:pr
```

Python commands:

```bash
cd python
uv run pytest -q
uv run pytest tests/web/
uv run ruff check src tests
uv run mypy src
```

Browser app commands:

```bash
pnpm start:browser:arc
pnpm start:browser:stub
pnpm --filter @arc-studio/browser build
```

Electron commands are available for development, but Electron is not the v0.1 release target:

```bash
pnpm start:electron
pnpm package:electron:dir
```

## Security

ARC Studio is designed for a single trusted user on a local workstation. The daemon binds to `127.0.0.1` and does not currently require authentication. Any process running as the same user on the same host may be able to reach the loopback service.

Do not expose ARC Studio on multi-tenant hosts, shared dev containers, or untrusted networks. Report security issues through a private GitHub security advisory, not a public issue.

See [docs/SECURITY.md](./docs/SECURITY.md) for the full threat model and audit status.

## Troubleshooting

### `pnpm install` fails with a lockfile error

Use pnpm `9.15.9`, matching [`.tool-versions`](./.tool-versions). CI uses `--frozen-lockfile`.

### `arc runtimes` shows `can_run=false`

This is expected on a fresh install. Configure the runtime you want to use in `.env` and install any required runtime dependencies.

### `arc doctor` says `Missing command`

`arc doctor` is a command group. Use a concrete subcommand, for example:

```bash
cd python
uv run arc doctor swarmgraph
```

### Browser app loads but shows no workflows

ARC Studio scans the workspace opened in Theia. The default workspace is the repository root; switch via **File > Open Workspace**.

### Build emits a Node.js `DEP0190` warning

This is a known `@theia/cli` warning. The build can still succeed.

## Contributing

Branch from `main`. Before opening a PR:

```bash
pnpm check:pr
cd python && uv run pytest -q
```

New behavior should include tests. Public API changes should include a CHANGELOG entry. Keep README and docs claims aligned with implemented behavior.

## License

Apache-2.0. See [LICENSE](./LICENSE).
