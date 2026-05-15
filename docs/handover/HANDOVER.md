# ARC Studio — Handover for Continued Implementation

**Generated:** 2026-05-15
**Previous commits:** 34 on main, latest `21e1061 fix: declare config YAML dependency and update status docs`
**Test count:** 435 passed, 6 skipped (Python), TS protocol + arc-extension builds clean

## Goal
Continue implementation beyond the first 23 recommended PRs from `docs/IMPLEMENTATION_PLAN.md` with green tests and builds, committing each green slice. All P1a execution core infrastructure is done. Next phases are P1b (remaining items), P2 (adoption integrations), and P3 (Theia UX).

## Constraints & Preferences
- Work in small vertical slices; after each slice run tests/lint/build, fix failures, commit only when green.
- No destructive git commands, no secret commits, preserve unrelated changes.
- Keep docs honest – never overclaim implemented features.
- Adoption scaffolds must fail closed: `NOT_RUNNABLE`, `RUN_FAILED`, `NotImplementedError`.
- LM Arena = stub-default with gated live path, excluded from v0.1 product claims.
- v0.1 scope = browser app + Python CLI/wheel only; Electron is post-v0.1.
- JSONL canonical, SQLite rebuildable index; event streams use bounded queues.
- Always read `docs/research/IMPLEMENTATION_RESEARCH.md` for scaffolds/guidance before each PR implementation.
- Before every new PR/slice, read: `docs/IMPLEMENTATION_PLAN.md`, `docs/research/IMPLEMENTATION_RESEARCH.md`, and relevant `docs/adr/*`.

## Progress

### Done
- PRs 1–23 fully implemented and committed.
- SQLite index beside JSONL (ADR-003): `IndexedTraceStore` wraps JSONL + SQLite with dual-write; `backfill_index()` for idempotent rebuild; 20 storage tests.
- Isolation provider interface (ADR-006): `isolation/` package with `IsolationProvider` base, `NoneIsolationProvider` (direct subprocess), `SubprocessIsolationProvider` (env-filtered); `arc isolation status/doctor/list` CLI; 16 tests.
- Run lifecycle CLI: `arc runs status/delete/export/backfill` commands added.
- Audit path on `RunRecord`: `audit_path` field added for trace-to-audit-chain linkage.
- Combo semantics: Already implemented via `ComboRuntimeAdapter`.
- Config model (ADR-001): `ArcConfig` Pydantic model, YAML loader, env/workspace/user/default precedence, `arc config init/show`; 14 tests.
- SwarmGraph import path spike: vendored `swarm_shared` and `hive-swarm` modules import from ARC Python venv; documented in `docs/SPIKE_SWARMGRAPH_IMPORT.md`.

### P1a Definition Of Done — All Met
- ✅ Capability API distinguishes standalone/adoption
- ✅ Event schema registry + versioning
- ✅ JSONL canonical + SQLite index (dual-write, backfill)
- ✅ Combo = `sequence`, not adoption
- ✅ Run records have `audit_path` field
- ✅ JobSupervisor + EventBroker (live, cancel, replay, orphan recovery)
- ✅ Workspace trust resolver (advisory, external DB)
- ✅ Isolation provider interface (`none`, `subprocess`, env-filtered, CLI)
- ✅ Run lifecycle CLI (`status/delete/export/backfill`)
- ✅ Config model + loader (ADR-001)
- ✅ Subprocess env allowlists (SwarmGraph adapter only; other adapters are in-process)

### P1b Items Still Open
- **Port run visualization shell pieces** — Extend `packages/arc-extension` by selectively porting UI from `theia-extensions/arc-adapters`, `arc-runs`, `arc-workflows`, `arc-event-stream`
- **Local prompt optimizer foundation** — Create `prompt_optimizer/` package with local-only prompt structuring, `arc prompt optimize` CLI, `arc prompt diff`

### In Progress
- (none)

### Blocked
- (none)

## Next Slices (ordered by impact + dependency)

### Slice A: Local Prompt Optimizer Foundation
**Why first:** Standalone Python module, no existing code to modify, tests can run without network.

**Files to create:**
- `python/src/agent_runtime_cockpit/prompt_optimizer/__init__.py`
- `python/src/agent_runtime_cockpit/prompt_optimizer/optimizer.py`
- `python/tests/prompt_optimizer/__init__.py`
- `python/tests/prompt_optimizer/test_optimizer.py`

**CLI commands to add:**
- `arc prompt optimize --file <path>` — structure a vague prompt
- `arc prompt optimize --mode off|local` — default to local mode
- `arc prompt diff <original> <optimized>` — show before/after

**Scaffolds in:** `docs/research/IMPLEMENTATION_RESEARCH.md` section 8 (prompt optimizer).

**Verification tests:** Unit tests with vague/broken-English prompts; no network tests.

### Slice B: Port Run Visualization Shell Pieces (Theia UI)
**Why second:** The most valuable UI work but depends on P1a backends being stable.

**Priority order:** `arc-adapters` > `arc-runs` > `arc-workflows` > `arc-event-stream`. Follow `docs/EXTENSION_MIGRATION.md`.

**Key constraint:** Protocol adaptation between duplicate widgets; static contract tests only (no jsdom/runtime).

### Slice C: LangGraph + SwarmGraph Adoption (First P2 Item)
**Why third:** Builds on P1b adoption skeleton + SwarmGraph import spike.

**Files to create/modify:**
- `python/src/agent_runtime_cockpit/adoption/langgraph.py` — adoption runner
- Tests with fake LangGraph graph

**Implementation notes:** "Convert LangGraph export into worker callable; SG queen assigns deliberation tasks; consensus signs result."

### Slice D: Wire SwarmGraph HMAC Audit Verify Path
**Dependencies:** SwarmGraph import spike (done), audit refs (partially done).

**Files to modify:**
- `audit/` — add audit service, verify endpoint
- `cli.py` — `arc audit verify/export` commands
- `web/routes.py` — verify endpoint

### Slice E: Enforce Workspace Trust Before Execution
**Dependencies:** P1a trust resolver (done), isolation provider interface (done).

**Change:** Flip P1a advisory mode → explicit approval/blocking mode in run/profile resolution.

## Critical Context

### Build Commands
```bash
# Python tests
cd python && uv run pytest -q                     # Full suite
cd python && uv run pytest tests/<path> -v        # Targeted

# TypeScript builds
pnpm --filter @arc-studio/protocol build
pnpm --filter arc-extension build

# Combined verification (run after each slice)
cd python && uv run pytest -q && pnpm --filter @arc-studio/protocol build && pnpm --filter arc-extension build
```

### Python venv
The Python venv is at `python/.venv`. Always use `uv run` to activate it, NOT `.venv/bin/python` (uv needs to manage the environment for dependency resolution).

**Dependencies:**
- `pydantic>=2.7` (config, schemas, protocol)
- `typer>=0.12` (CLI)
- `rich>=13.7` (CLI formatting)
- `aiohttp>=3.9` (daemon + SSE)
- `PyYAML>=6.0` (config loader)
- No `aiohttp-sse` dependency — manual `StreamResponse` used for SSE

### Key Files
| File | Purpose | Lines |
|------|---------|-------|
| `cli.py` | All CLI commands (1080+ lines) | Growing |
| `orchestration/supervisor.py` | Run lifecycle management | 189 |
| `orchestration/event_broker.py` | SSE pub/sub with bounded queues | 197 |
| `orchestration/runtime_router.py` | Runtime resolution + combo/adoption | 211 |
| `protocol/schemas.py` | `RunRecord`, `RunEvent`, `RunStatus` | 147 |
| `protocol/events.py` | Event registry (33 types), `create_event()` | — |
| `storage/indexed_store.py` | Dual-write JSONL + SQLite | 143 |
| `storage/sqlite.py` | SQLite index (ADR-003 schema) | 232 |
| `isolating/base.py` | IsolationProvider ABC | 64 |
| `isolating/none.py` | Direct subprocess provider | 70 |
| `isolating/subprocess.py` | Env-filtered subprocess provider | 100 |
| `config/model.py` | ArcConfig Pydantic model | 122 |
| `config/loader.py` | YAML config loader | 238 |
| `adoption/protocol.py` | Adoption Pydantic models | — |
| `adoption/registry.py` | Adoption registry + runner skeleton | — |
| `security/trust.py` | Workspace trust resolver (external DB) | — |

### Test Structure
Tests mirror the source structure but are flat under `python/tests/`:
- `tests/test_storage.py` — JSONL + SQLite + IndexedTraceStore (20 tests)
- `tests/test_config.py` — Config model + loader (14 tests)
- `tests/test_cli_runs.py` — CLI run commands (17 tests)
- `tests/isolation/test_isolation.py` — Isolation providers (16 tests)
- `tests/orchestration/test_supervisor.py` — JobSupervisor (9 tests)
- `tests/orchestration/test_event_broker.py` — EventBroker (13 tests)
- `tests/web/` — Web/daemon integration tests
- `tests/adapters/` — Per-adapter tests

### Do Not Overclaim
Avoid these claims unless tests prove them:
- "ARC supports SwarmGraph adoption for CrewAI/LangGraph/OpenAI Agents/AG2/LlamaIndex"
- "ARC has live streaming" if the endpoint only replays stored trace events
- "ARC has signed audit trails" unless using SwarmGraph HMAC audit
- "AG2 support" until registered and visible in `arc runtimes`
- "LM Arena live mode" as a v0.1 product feature
- "Production ready," "multi-user," or "tenant-isolated"

Safe language:
- "Standalone adapter exists"
- "Detection/static export only"
- "Stub-default with gated live path (not v0.1 scope)"
- "Planned SwarmGraph adoption mode"
- "Vendored SwarmGraph runtime includes HMAC audit, HITL, quota, and consensus"

### Git
- 34 commits ahead of `origin/main`
- Working tree has many deleted/untracked docs from historical cleanup — do not revert or stage them
- Only touch files needed for current slice
- Commit messages: `type: description` (e.g. `feat:`, `fix:`, `spike:`, `docs:`)

### ADR Status
| ADR | Status | Implemented |
|-----|--------|-------------|
| 000-execution-core-contract | Planning baseline | Partial |
| 001-config-model | **Done** | ✅ ArcConfig + loader + CLI |
| 002-run-lifecycle-state-machine | **Done** | ✅ JobSupervisor + cancel + orphan recovery |
| 003-storage-strategy | **Done** | ✅ IndexedTraceStore + backfill |
| 004-event-schema-versioning | **Done** | ✅ Event registry + create_event + validate |
| 005-audit-key-management | P2 target | Spike done, not wired |
| 006-workspace-trust-isolation | **Done** | ✅ Trust resolver + isolation providers |
| 007-provider-routing-unification | P1-P3 target | Partial |
| 008-daemon-bundling | P5 target | Not started |

## Relevant Files
- `docs/IMPLEMENTATION_PLAN.md` — Canonical PR list (23+ beyond)
- `docs/research/IMPLEMENTATION_RESEARCH.md` — Scaffolds and guidance (MUST READ before each PR)
- `docs/adr/` — ADR-000 through ADR-008
- `docs/SPIKE_KEYCHAIN_STORAGE.md` — Keychain platform validation report
- `docs/SPIKE_SWARMGRAPH_IMPORT.md` — SwarmGraph library import spike results
- `docs/EXTENSION_MIGRATION.md` — Port/archive/delete sequence for theia-extensions
- `AGENTS.md` — Full project context (updated frequently)
- `docs/RELEASE_CHECKLIST.md` — v0.1.0-alpha release checklist
