# ARC Studio

**Agent Runtime Cockpit** — your local command center for running, inspecting, and debugging AI agent workflows.

ARC Studio combines a Python CLI and loopback daemon with an Eclipse Theia browser interface, giving you a complete local environment for agent runtime experiments, trace inspection, human-in-the-loop workflows, audit verification, replay debugging, and workflow diagnostics. Everything runs on your machine. Your project data stays with you.

**Current Release:** `v0.1.0-alpha`

This is an alpha release. Core functionality is stable and ready for development use, but APIs, UI components, and runtime adapters will continue to evolve as we move toward v1.0 stable. We recommend pinning to a specific version tag or commit SHA for production experiments.

See [CONTRIBUTING.md](./CONTRIBUTING.md) for development setup, commit conventions, and the PR checklist.

## Features

**Local-First Execution**  
Run agent workflows entirely on your machine using the `arc` CLI and loopback daemon. No cloud dependencies, no data leaving your workstation.

**Browser-Based IDE**  
A full Eclipse Theia environment with dedicated views for workflows, runs, traces, adapters, human-in-the-loop prompts, audit chains, and replay debugging.

**Multi-Runtime Support**  
Automatic detection and adapter scaffolding for SwarmGraph, LangGraph, CrewAI, OpenAI Agents SDK, AG2, LlamaIndex, and LM Arena. Run multiple agent frameworks from a single cockpit.

**Persistent Trace Storage**  
JSONL trace files with SQLite metadata indexing. Search, export, import, replay, and maintain your run history with full lifecycle commands.

**Human-in-the-Loop Workflows**  
Capture HITL prompts with approval/rejection flows. Integrate with your IDE or use the CLI for interactive agent supervision.

**Audit & Verification**  
Built-in audit chain verification and export for runs that generate audit material. Track agent decisions and validate compliance requirements.

**Security & Isolation**  
Workspace trust checks, output redaction, paid-call gating, and subprocess/Docker isolation providers keep your experiments safe and controlled.

**Evaluation Tooling**  
Save golden traces and run batch evaluations to measure agent performance over time.

## What's Ready in 0.1 Alpha

ARC Studio 0.1 alpha is ready for development use. Core features are functional and tested, but expect continued refinement as we move toward a stable release.

| Component | Status |
| --- | --- |
| Python CLI and daemon | Production-ready for local development |
| Browser application | Primary interface, fully functional |
| Electron application | Experimental, available for testing |
| Runtime adapters | Varying maturity: some fully runnable, others detection/export only |
| SwarmGraph integration | Offline/fake mode by default; limited local execution path available |
| Security model | Single-user loopback workstation tool |

**What This Means:**  
The Python backend and browser interface are stable enough for daily use. Runtime adapter support varies by framework—some offer full execution, others provide detection and scaffolding. The Electron build is available but not the primary target for this release.

See [CHANGELOG.md](./CHANGELOG.md) for release notes, [docs/release/checklist.md](./docs/release/checklist.md) for verification steps, and [docs/SECURITY.md](./docs/SECURITY.md) for the security model and known limitations.

## Architecture

ARC Studio is built in three layers that work together to give you a complete agent development environment:

- **Python backend**: The `arc` CLI, daemon server, runtime adapters, trace storage, audit verification, HITL handling, configuration management, workspace trust, isolation providers, and evaluation tooling.
- **Theia extension**: TypeScript JSON-RPC service layer and custom ARC Studio widgets in `packages/arc-extension`.
- **Applications**: The browser interface in `applications/browser` is the primary target. Electron support in `applications/electron` is available for experimentation.

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

ARC Studio requires specific tool versions for consistent builds and reproducible environments. All versions are pinned in [`.tool-versions`](./.tool-versions):

- **Node.js** `20.18.0`
- **pnpm** `9.15.9`
- **Python** `3.11.10`
- **uv** — Python dependency manager ([installation guide](https://github.com/astral-sh/uv))

Using these exact versions ensures you have the same environment as CI and other contributors.

## Quick Start

Get ARC Studio running in three steps:

```bash
git clone https://github.com/Hansuqwer/arc-theia-studio.git
cd arc-theia-studio
pnpm install --frozen-lockfile
bash scripts/bootstrap-dev.sh
```

**Launch the browser interface with full backend:**

```bash
pnpm start:browser:arc
```

Open your browser to `http://127.0.0.1:3000` and you're ready to go.

**UI development without agent execution:**

If you're working on the interface and don't need real agent runs, use the stub backend:

```bash
pnpm start:browser:stub
```

## Python CLI

The `arc` CLI is your command-line interface to the ARC Studio backend. It handles workflow execution, trace management, runtime detection, HITL flows, audit verification, and evaluation.

For the interactive coding-agent REPL, use the dedicated launcher:

```bash
cd python
uv sync --all-extras --dev
uv run arch-studio-cli
uv run arch-studio-cli "/help"
```

Provider-backed agent runs use `/agent <task>` and keep tool execution behind workspace trust and sandbox policy gates. Example 9router/OpenAI-compatible smoke setup:

```bash
export ARC_DEFAULT_PROVIDER=9router
export ARC_9ROUTER_DEFAULT_MODEL=ag/gemini-3.5-flash-extra-low
export NINEROUTER_API_KEY=...
uv run --extra arena arch-studio-cli "/agent Create hello.py and run it"
```

Running workspace Python scripts through the agent `bash` tool is denied by default as dynamic interpreter execution. For an explicit local smoke only, set `ARC_AGENT_ALLOW_WORKSPACE_INTERPRETER=1`; the script path must still resolve inside the trusted workspace.

ARC also registers a compact `models.dev`-backed OpenAI-compatible provider catalog without live network fetches at startup. Current bundled catalog providers are `alibaba`, `deepseek`, `github-models`, `moonshotai`, and `zai`; ARC also has explicit OpenAI-compatible registrations for local/gated providers such as `9router` and `crofai`. Select them with the relevant provider ID and configure the documented key env var. Default models can be overridden with sanitized provider IDs, for example `ARC_DEEPSEEK_DEFAULT_MODEL=deepseek-chat` or `ARC_GITHUB_MODELS_DEFAULT_MODEL=ai21-labs/ai21-jamba-1.5-large`. models.dev is used only as model/provider metadata, never as a secret source.

**Set up the Python environment:**

```bash
cd python
uv sync --all-extras --dev
uv run arc --help
uv run arc runtimes --capabilities --json
```

**Common commands:**

```bash
# Start the daemon (binds to 127.0.0.1:7777 by default)
uv run arc serve

# List available workflows and runtimes
uv run arc workflows
uv run arc runtimes

# Execute and manage runs
uv run arc run --help
uv run arc runs search
uv run arc runs replay <run-id>

# Audit and HITL workflows
uv run arc audit verify <run-id>
uv run arc hitl pending

# Evaluation
uv run arc eval run --batch
```

The daemon binds to `127.0.0.1:7777` by default. The browser application connects to this loopback endpoint to communicate with the backend.

## Runtime Support

ARC Studio detects and adapts to multiple agent frameworks. Runtime availability depends on your installed dependencies, project structure, environment configuration, and paid-call gates.

### Current Runtime Adapters

| Runtime | Support Level | Key Limitations |
| --- | --- | --- |
| **SwarmGraph** | CLI/subprocess execution via `ARC_SWARMGRAPH_CLI`; detection and workflow export | Full composition UX still maturing |
| **LangGraph** | Detection, AST-based workflow analysis, export/run hooks via `ARC_LANGGRAPH_EXPORT`; supports `.invoke()` and `.stream()` | No live token streaming in UI; traces show coalesced node updates |
| **CrewAI** | Detection and crew execution via `ARC_CREWAI_EXPORT` with paid-call gating | Static export only; limited graph extraction |
| **OpenAI Agents SDK** | Detection and SDK-backed execution when configured | Entrypoint wiring incomplete |
| **AG2** | Registered adapter with detection and run scaffolding | Real execution path gated |
| **LlamaIndex** | Detection and static workflow export | No execution path yet |
| **LM Arena** | Stub/offline responses for battle/direct/code/agent modes | No live model calls |

**Check your current runtime status:**

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

**Understanding the table:**
- **Detected**: The adapter found runtime evidence or an importable dependency in your environment
- **Can run**: The adapter and required configuration are ready for execution
- **Paid**: Successful runs may make billable API calls; these paths require explicit opt-in

**Multi-runtime architecture:**  
ARC Studio can run multiple supported frameworks from the same cockpit. Each runtime adapter operates independently. ARC does not currently compose CrewAI, LangGraph, OpenAI Agents, AG2, LlamaIndex, or LM Arena inside a SwarmGraph workflow unless your code implements that composition.

## Configuration

**Environment setup:**

Start by copying the example environment file:

```bash
cp .env.example .env
```

Configure the runtimes you want to use:

```bash
ARC_SWARMGRAPH_CLI=/path/to/swarmgraph
ARC_LANGGRAPH_EXPORT=module:function
ARC_CREWAI_EXPORT=module:function
OPENAI_API_KEY=...
```

**Important:** Never commit real API keys or secrets to version control. Provider-backed and paid-call paths are gated by default—enable them deliberately when you're ready.

**CLI-based configuration:**

You can also manage ARC configuration through the command line:

```bash
cd python
uv run arc config init
uv run arc config show
uv run arc profiles list
uv run arc workspace info
```

## Development

### JavaScript/TypeScript

Build, test, and lint the frontend:

```bash
pnpm build
pnpm test
pnpm lint
pnpm check:pr
```

Build specific packages:

```bash
pnpm --filter @arc-studio/protocol build
pnpm --filter arc-extension build
pnpm --filter arc-extension test
```

### Python

Run tests and checks:

```bash
cd python
uv run pytest -q
uv run pytest tests/web/
uv run ruff check src tests
uv run mypy src
```

### Running the Applications

**Browser (primary target):**

```bash
pnpm start:browser:arc      # Full backend
pnpm start:browser:stub     # UI-only, no agent execution
pnpm --filter @arc-studio/browser build
```

**Electron (experimental):**

```bash
pnpm start:electron
pnpm package:electron:dir
```

Note: Electron support is available for experimentation but is not the primary target for v0.1 alpha.

## Security

**Threat Model:**  
ARC Studio is designed for a single trusted user on a local workstation. The daemon binds to `127.0.0.1` and does not require authentication. Any process running as your user on the same machine can reach the loopback service.

**What this means:**
- ✅ Safe for single-user local development
- ✅ Safe on trusted personal workstations
- ❌ Not safe on multi-tenant hosts
- ❌ Not safe in shared dev containers
- ❌ Not safe on untrusted networks

**Reporting security issues:**  
If you discover a security vulnerability, please report it through a private GitHub security advisory. Do not open a public issue.

**Full security documentation:**  
See [docs/SECURITY.md](./docs/SECURITY.md) for the complete threat model, audit status, and detailed security considerations.

## Troubleshooting

### Lockfile errors during `pnpm install`

Make sure you're using pnpm `9.15.9` as specified in [`.tool-versions`](./.tool-versions). CI runs with `--frozen-lockfile` and expects this exact version.

### Runtime shows `can_run=false`

This is expected on a fresh install. ARC Studio needs you to configure which runtimes you want to use. Set the appropriate environment variables in `.env` and install any required runtime dependencies.

### `arc doctor` reports "Missing command"

`arc doctor` is a command group, not a standalone command. Use a specific subcommand:

```bash
cd python
uv run arc doctor swarmgraph
```

### Browser app loads but shows no workflows

ARC Studio scans the workspace currently open in Theia. By default, this is the repository root. If you need to scan a different directory, use **File > Open Workspace** to switch.

### Build shows Node.js `DEP0190` warning

This is a known warning from `@theia/cli`. The build will still succeed—you can safely ignore it.

## Contributing

We welcome contributions to ARC Studio! Whether you're fixing bugs, adding features, improving documentation, or suggesting enhancements, your help makes this project better.

**Before submitting a pull request:**

1. Branch from `main`
2. Run the full test suite:

```bash
pnpm check:pr
cd python && uv run pytest -q
```

**Contribution guidelines:**
- New features and bug fixes should include tests
- Public API changes should include a CHANGELOG entry
- Keep README and documentation aligned with actual behavior
- Follow the existing code style and conventions

**Questions or ideas?**  
Open an issue to discuss your proposal before investing significant time in implementation. We're happy to provide guidance and feedback.

## License

Apache-2.0. See [LICENSE](./LICENSE).
