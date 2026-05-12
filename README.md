# ARC Studio

ARC Studio is an early prototype for an Eclipse Theia based IDE plus Python ARC daemon/CLI for inspecting agent runtime projects.

Current state: handoff-ready prototype, not production-ready. See `STATUS.md` and `docs/HANDOFF.md` for verified results and blockers.

## What Works

- Python ARC package installs with `uv`.
- Python tests pass after dev dependency sync.
- CLI inspection, runtime detection, workflow/schema export, and adapter conformance commands run.
- Node fixture/protocol bootstrap tests pass without installing Theia.

## What Does Not Work Yet

- Electron smoke packaging is local-only; release packaging requires signing credentials.
- Live/provider-backed SwarmGraph execution requires explicit approval before running external calls.
- LangGraph real runtime execution is not implemented.

## Setup

```bash
cd arc-theia-studio

# Python
cd python
uv sync --all-extras --dev
.venv/bin/python -m pytest
.venv/bin/arc --help

# Node/Theia, requires Node 20+ and pnpm 9+
cd ..
pnpm install
pnpm build
pnpm start:browser
```

## SwarmGraph Stub Run Quickstart

Default SwarmGraph runs use the local `stub` backend and do not call paid/provider services.
Provider-backed runs require explicit opt-in with `ARC_SWARMGRAPH_RUN_BACKEND=<backend>` and `ARC_SWARMGRAPH_ALLOW_COSTS=true`; otherwise ARC adds `--no-cost`.
ARC does not install SwarmGraph as a Python extra yet; set `ARC_SWARMGRAPH_CLI` or open a workspace that contains an executable `swarmgraph` launcher.

```bash
cd python
uv run arc run wf-swarmgraph-001 \
  --workspace /path/to/swarmgraph/workspace \
  --prompt "ARC local stub smoke run" \
  --json

uv run arc runs --workspace /path/to/swarmgraph/workspace --json
uv run arc runs get <run-id> --workspace /path/to/swarmgraph/workspace --json
uv run arc runs trace <run-id> --workspace /path/to/swarmgraph/workspace --tail 5 --json
uv run arc runs prune --workspace /path/to/swarmgraph/workspace --keep 20 --json
uv run arc runs prune --workspace /path/to/swarmgraph/workspace --keep 20 --yes --json
```

Open the Run Timeline directly in Theia:

```text
http://127.0.0.1:3000/?arc-view=run-timeline
```

LangGraph dynamic export can load a workspace symbol when the library is installed:

```bash
ARC_LANGGRAPH_EXPORT=graph_module:export_graph uv run arc workflows --workspace /path/to/langgraph/project --runtime langgraph --json
```

PR hygiene:

```bash
pnpm check:pr
```

## Verified Python Commands

```bash
cd python
uv sync --all-extras --dev
.venv/bin/python -m pytest
.venv/bin/arc --help
.venv/bin/arc inspect --json
.venv/bin/arc runtimes --json
.venv/bin/arc workflows --json
.venv/bin/arc schemas --json
.venv/bin/arc adapter test swarmgraph --json
.venv/bin/arc adapter test langgraph --json
```

## Verified Node Bootstrap Commands

```bash
node tests/unit/arc-protocol.test.js
node packages/arc-test-fixtures/src/index.js
```

## Runtime Status

| Runtime | Current support | Missing |
| --- | --- | --- |
| SwarmGraph | Detection, AST workflow/schema export heuristics, local/gateway execution, JSONL trace replay/export | Audit integrations |
| LangGraph | Detection, AST workflow heuristics, dynamic export hook, fixture schema | Real runtime execution |
| CrewAI | Not implemented | Adapter |
| OpenAI Agents SDK | Not implemented | Adapter |
| AG2 | Not implemented | Adapter |

## Docs

- `STATUS.md`: evidence-based current status.
- `docs/HANDOFF.md`: commands run, known failures, completion plan.
- `docs/ROADMAP.md`: prioritized work list.
- `docs/MOCK_POLICY.md`: mock/demo rules.
- `docs/SECURITY.md`: trust boundaries, secrets, daemon, and release security notes.
- `CONTRIBUTING.md`: setup and definition of done.

## License

Apache-2.0. See `LICENSE`.
