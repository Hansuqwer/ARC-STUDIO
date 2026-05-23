---
date: 2026-05-22
head: 51673b2
phases_completed:
  - Phase 21: Streaming Audit Verification + HMAC Signing
  - Phase 22: Discriminated RunEvent Unions
  - Phase 23: Typed Denial Events + Enforcement (Baseline Complete)
  - Phase 24: Trace Viewer Virtualization + Daemon Resilience (Baseline Complete)
  - Phase 25: CLI Decomposition (In Progress — PR 25.1-25.3 done)
phases_remaining:
  - Phase 25 PR 25.4: Extract runs, audit, receipt, profiles commands
  - Phase 25 PR 25.5: Extract remaining groups (providers, eval, hitl, studio, workspace, isolation, storage, config, prompt, adapter, context)
  - Phase 25 PR 25.6: Add JSON schema snapshots and snapshot tests
  - Phase 25.5: Shared test harness + ProviderClient interface (needed for adapter phases)
  - Phase 26-35: Adapter phases (LangChain, Anthropic, OpenAI-compatible, etc.)
next_phase: Phase 25 PR 25.4
---

# Session Handover — 2026-05-22

## Current State

**HEAD:** `51673b2`  
**Tests:** 1,519 Python passed, 21 skipped, 3 xfailed, 1 xpassed  
**TypeScript:** 6 pre-existing failures in `services.unit.test.ts` (WorkflowExecutor mock tests)  
**Audit script:** 0 violations (28 syscall sites annotated)

### Files changed in this session

| Phase | Commit | Files |
|-------|--------|-------|
| 23.1 | `fca4bf2` | `security/context.py`, `security/enforcement.py`, `cli.py`, tests |
| 23.2 | `5a9df47` | `scripts/audit-enforcement-surfaces.sh`, `docs/security/enforcement-surfaces.md`, 28 syscall annotations |
| 23.3 | `09bfbb8` | `context.py` (correlation_id), `routes.py` (retry endpoint), `DenialModal.tsx`, `useDenialHandler.ts`, e2e tests |
| 24 | `7365191` | `VirtualizedEventList.tsx` (@tanstack/react-virtual), `run-lifecycle-service.ts` (SSE reconnect), `event_broker.py` (RingBuffer) |
| 25.1 | `3171171` | `cli/` package (`_app.py`, `_helpers.py`), `_legacy_cli.py` (renamed from cli.py) |
| 25.2 | `ca5e3ca` | `cli/info.py` (version, health, status, inspect, bug-report) |
| 25.3 | `51673b2` | `cli/discover.py` (runtimes, workflows, schemas), `cli/exec.py` (serve, run) |

### Docs created

- `docs/research/adapter-priorities.md` — top-10 ranked adapters
- `docs/research/adapter-roadmap.md` — Phases 26-35 implementation plan
- `docs/research/phase-22.1-landing-pr.md` — ADR-0022.1 implementation skeleton
- `docs/research/phase-35-mcp-prompt.md` — MCP adapter implementation prompt
- `docs/audit/phases-23-24-audit.md` — Phase 23-24 audit findings
- `docs/release/v0.2-release-notes.md` — draft release notes

## CLI Package Structure

```
python/src/agent_runtime_cockpit/
├── cli/                    # Decomposed CLI (Phase 25)
│   ├── __init__.py         # Re-exports app, imports all command modules
│   ├── _app.py             # Root Typer app, callback, EnforcementContext, main()
│   ├── _helpers.py         # Shared utilities (_workspace, _out, _run_preflight, etc.)
│   ├── info.py             # version, health, status, inspect, bug-report
│   ├── discover.py         # runtimes, workflows, schemas
│   └── exec.py             # serve, run
├── _legacy_cli.py          # Remaining legacy commands (3359 lines, being extracted)
```

## What remains in `_legacy_cli.py`

Still to extract (PR 25.4-25.5):
- `runs_app` group (15 subcommands: runs, prune, get, diff, trace, status, delete, export, import, replay, backfill, search, fork, links, contract, budget, autopsy)
- `audit_app` group (verify, export) + `key_app` sub-group (init, show, delete)
- `receipt_app` group (show, export, verify)
- `profiles_app` group (list, show, create)
- `eval_app` group (run, save, delete, report, list)
- `doctor_app` group (swarmgraph, all, env, network, storage)
- `providers_app` group (list, catalog, status, diagnostics, proxy, action) + accounts/key/quota/routing sub-groups
- `hitl_app` group (pending, respond, approve, reject)
- `studio_app` group (chat, sessions) + `studio_sessions_app`
- `workspace_app` group (trust-status, trust, untrust, init, info, config)
- `isolation_app` group (status, doctor, list, setup, test)
- `storage_app` group (vacuum, status)
- `config_app` group (init, show)
- `prompt_app` group (optimize, diff)
- `context_app` group (pack)
- `adapter_app` group (test, list)

## Adapter Roadmap (Phases 26-35)

See `docs/research/adapter-roadmap.md`. First adapter is LangChain (Phase 26), requires Phase 25.5 (shared test harness + ProviderClient) first.

## Key Decisions This Session

1. **Phase 23 completed** — 3 PRs delivering EnforcementContext, CLI flags, audit infrastructure, DenialModal, correlation IDs, retry endpoint. All 28 syscall sites annotated.
2. **Phase 24 completed** — @tanstack/react-virtual for event list virtualization, RingBuffer for SSE replay, client-side reconnect with exponential backoff + Last-Event-ID.
3. **Phase 25 structure** — `cli.py` renamed to `_legacy_cli.py` (file shadower conflicted with new `cli/` package). Legacy file goes from 4,225→3,359 lines across 3 PRs with zero regressions.
4. **ADR-0022.1 designed** but not landed — `POLICY_BYPASS_WARNING` event variant for cases where enforcement cannot prove a gate is applied (requires Phase 22.1 landing PR).
5. **Research docs drafted** — top-10 adapter priorities, phased roadmap, MCP implementation prompt. These are placeholders requiring reconciliation against fresh grep.app/context7 research.

## Next Phase: PR 25.4

Extract `runs`, `audit`, `receipt`, `profiles` commands into `cli/runs.py`, `cli/audit.py`, `cli/receipt.py`, `cli/profiles.py`.

## Verification Commands

```bash
cd python && uv run pytest -q              # Full Python suite
cd python && uv run pytest tests/security/ -q  # Enforcement tests
bash scripts/audit-enforcement-surfaces.sh     # Audit script
cd python && uv run pytest tests/test_sse_resilience.py -v  # SSE tests
pnpm --filter arc-extension build              # TypeScript build
pnpm --filter arc-extension test               # TypeScript tests
```

## Known Issues

1. **6 pre-existing TypeScript failures** — `services.unit.test.ts` WorkflowExecutor mock tests (unrelated to CLI changes)
2. **4 xfail Python tests** — edge cases in `test_cli_doctor.py` (2) and `test_cli_runs.py` (2) — exit code/JSON formatting differences
3. **Research docs need reconciliation** — `docs/research/adapter-priorities.md` scores are placeholders; need fresh grep.app/context7 research
4. **ADR-0022.1 not landed** — Phase 22.1 PR skeleton exists at `docs/research/phase-22.1-landing-pr.md`
