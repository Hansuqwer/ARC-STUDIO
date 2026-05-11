# ARC Studio

ARC Studio is an early prototype for an Eclipse Theia based IDE plus Python ARC daemon/CLI for inspecting agent runtime projects.

Current state: handoff-ready prototype, not production-ready. See `STATUS.md` and `docs/HANDOFF.md` for verified results and blockers.

## What Works

- Python ARC package installs with `uv`.
- Python tests pass after dev dependency sync.
- CLI inspection, runtime detection, workflow/schema export, and adapter conformance commands run.
- Node fixture/protocol bootstrap tests pass without installing Theia.

## What Does Not Work Yet

- Theia browser/electron build is not verified in this environment because `pnpm` is missing.
- Normal product paths no longer silently return mock success when backend/runtime execution is unavailable.
- SwarmGraph and LangGraph real runtime execution are not implemented.
- Electron packaging/signing and E2E tests are not verified.

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
| SwarmGraph | Detection, AST workflow/schema export heuristics | Real execution, real trace/audit/replay |
| LangGraph | Detection, AST workflow heuristics, fixture schema | Dynamic graph loading, real execution |
| CrewAI | Not implemented | Adapter |
| OpenAI Agents SDK | Not implemented | Adapter |
| AG2 | Not implemented | Adapter |

## Docs

- `STATUS.md`: evidence-based current status.
- `docs/HANDOFF.md`: commands run, known failures, completion plan.
- `docs/ROADMAP.md`: prioritized work list.
- `docs/MOCK_POLICY.md`: mock/demo rules.
- `CONTRIBUTING.md`: setup and definition of done.

## License

Apache-2.0. See `LICENSE`.
