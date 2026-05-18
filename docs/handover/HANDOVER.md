# ARC Studio — Handover for Continued Implementation

**Generated:** 2026-05-15; release-truth refresh 2026-05-18
**Previous commits:** historical value omitted; check `git status`/`git log` before work.
**Test count:** Python 782 passed / 14 skipped; TS protocol + arc-extension builds clean; arc-extension test suite 581 tests / 9 suites.

## Goal
Continue remaining ARC Studio product work from `docs/LOCKED_REMAINING_ROADMAP.md` and `docs/LOCKED_PHASE_IMPLEMENTATION_PLAN.md` with green tests and builds. Those two locked docs are authoritative. Current v0.2 planning selects Option A: IDE productization of existing/gated capabilities, while effect-boundary replay/fork and adapter-wide real-time budget interrupts are deferred. Commit only if explicitly requested.

## Constraints & Preferences
- Work in larger coherent phase chunks when safe; after each chunk run tests/lint/build, fix failures, commit only when green.
- No destructive git commands, no secret commits, preserve unrelated changes.
- Keep docs honest – never overclaim implemented features.
- Adoption scaffolds must fail closed: `NOT_RUNNABLE`, `RUN_FAILED`, `NotImplementedError`.
- LM Arena = stub-default with gated live path, excluded from v0.1 product claims.
- v0.1 scope = browser app + Python CLI/wheel only; Electron is post-v0.1.
- JSONL canonical, SQLite rebuildable index; event streams use bounded queues.
- Always read `docs/LOCKED_REMAINING_ROADMAP.md` and `docs/LOCKED_PHASE_IMPLEMENTATION_PLAN.md` before each implementation chunk.
- Use `docs/research/IMPLEMENTATION_RESEARCH.md` and `docs/wiki/research-context/` for supporting context only; they are not status sources.
- Before every new slice, read relevant `docs/adr/*`.

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

### P1b–P5 Items Still Open
- (none as a broad implementation phase; see `AGENTS.md` current status for completed prompt optimizer, adoption skeleton/runners, Theia port notes, and release caveats.)

### In Progress
- (none)

### Blocked
- (none)

## Next Slices

Use `docs/LOCKED_PHASE_IMPLEMENTATION_PLAN.md` as the ordered execution plan. Current planned v0.2 Option A slices are:

- Phase 8: live stream productization to a configured Python daemon/local runtime stream.
- Phase 9: BudgetVector post-hoc accounting/reporting and IDE gauges.
- Phase 10: Assurance tab HITL/audit polish.
- Phase 11: daemon/CLI parity, `arc doctor all` coverage, and truth-alignment audits.

Release operations and `.env` history scrub remain governed by R7/Phase 7. Do not run destructive history rewrite or force-push without explicit approval.

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
| `isolation/base.py` | IsolationProvider ABC | approx |
| `isolation/none.py` | Direct subprocess provider | approx |
| `isolation/subprocess.py` | Env-filtered subprocess provider | approx |
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
- "ARC supports broad live/provider-backed SwarmGraph adoption for CrewAI/LangGraph/OpenAI Agents/AG2/LlamaIndex"
- "ARC has live streaming" if the endpoint only replays stored trace events
- "ARC has adapter-wide keyed audit trails" unless the specific run writes keyed audit material
- "Ungated/live AG2 support"; AG2 is registered/gated, real dependency/runtime path remains gated
- "LM Arena live mode" as a v0.1 product feature
- "Production ready," "multi-user," or "tenant-isolated"

Safe language:
- "Standalone adapter exists"
- "Detection/static export only"
- "Stub-default with gated live path (not v0.1 scope)"
- "Fake-tested/gated adoption runners exist; only `crewai+swarmgraph` is currently routed through CLI fake/offline path"
- "Vendored SwarmGraph runtime includes HMAC audit, HITL, quota, and consensus"

### Git
- Check current branch/status before each slice; preserve unrelated changes.
- Do not revert or stage user/unrelated worktree changes.
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
| 005-audit-key-management | Partial | ✅ key manager + hmac_chain + audit verify/export/key; adapter-wide keyed audit population still needs verification |
| 006-workspace-trust-isolation | **Done** | ✅ Trust resolver + isolation providers |
| 007-provider-routing-unification | P1-P3 target | Partial |
| 008-daemon-bundling | P5/post-v0.1 | Smoke workflow/scaffold exists; Electron bundling remains post-v0.1 |

## Relevant Files
- `docs/LOCKED_REMAINING_ROADMAP.md` — Locked remaining roadmap/status
- `docs/LOCKED_PHASE_IMPLEMENTATION_PLAN.md` — Locked ordered phase/slice plan
- `docs/research/IMPLEMENTATION_RESEARCH.md` — Scaffolds and guidance (MUST READ before each PR)
- `docs/adr/` — ADR-000 through ADR-008
- `docs/SPIKE_KEYCHAIN_STORAGE.md` — Keychain platform validation report
- `docs/SPIKE_SWARMGRAPH_IMPORT.md` — SwarmGraph library import spike results
- `docs/EXTENSION_MIGRATION.md` — Port/archive/delete sequence for theia-extensions
- `AGENTS.md` — Full project context (updated frequently)
- `docs/RELEASE_CHECKLIST.md` — v0.1.0-alpha release checklist
