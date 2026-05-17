# ARC Studio Implementation Status Matrix

Generated: 2026-05-17

Orchestrator: `cx/gpt-5.5 9router`

Subagent evidence:
- Subagent A, `qwen 3.6 max preview - alibaba`: full repo architecture/status matrix, CLI/IDE priority.
- Subagent B, `kimi 2.6 precision - crofai`: CLI/Python/backend/security audit.
- Subagent C, `glm 5.1 precision - crofai`: IDE/Theia/browser audit.
- Subagent D, `qwen 3.6 max preview - alibaba`: docs/release truth audit.

This matrix is conservative. If evidence was static-only or docs conflicted, status is `Partial` or `Needs verification`.

## Summary

| Area | Status | Evidence | Gaps / caveats |
|---|---|---|---|
| Canonical browser app | Implemented | `applications/browser/package.json` depends on `arc-extension`; legacy browser deps removed | Browser runtime smoke still required before archival cleanup |
| Canonical Theia extension | Implemented | `packages/arc-extension`, frontend/backend modules, tabbed `ArcStudioWidget` | Legacy `ArcWidget` still registered; UX split across separate widgets |
| IDE static coverage | Implemented | `packages/arc-extension/src/browser/__tests__/*contract*.test.ts`, proxy/protocol tests | Static contract tests are not runtime UI tests |
| IDE runtime/browser smoke | Partial | Browser build reported passing | Need widget-load smoke/e2e evidence, not HTML grep only |
| IDE Chat launch | Partial | `ChatTab.tsx`, backend `preflightRun`/`startRun` | Hardcoded workflow defaults; no live streaming/progress |
| IDE Runs UX | Partial | `RunsTab.tsx` has diff, HITL, replay, audit actions | Replay list-only; HITL manual refresh; audit display basic |
| IDE workflow graph/timeline/event stream/adapters | Implemented, static-tested | Canonical widgets in `packages/arc-extension/src/browser` | Separate commands/widgets; not fully integrated into tabs |
| IDE schema/context/audit standalone UX | Not implemented / parked | Remaining `theia-extensions/arc-schemas`, `arc-context`, `arc-audit` | Explicitly park or port later |
| Legacy `theia-extensions/*` source | Parked | Browser app no longer depends on them | Do not delete until browser smoke; Electron still references legacy deps |
| Electron packaging | Deferred | `applications/electron/package.json` still has legacy deps | Post-v0.1 only; no release claim |
| JSON-RPC protocol | Implemented | `packages/arc-extension/src/common/arc-protocol.ts` | Monolithic; comments around audit command stale; trace type union narrow |
| Backend CLI bridge | Implemented | `packages/arc-extension/src/node/arc-backend-service.ts` | Sync `execFileSync`; PATH dependency; workspace-root handling needs proof |
| CLI command breadth | Implemented | `python/src/agent_runtime_cockpit/cli.py`; CLI tests | Chat-first `arc-studio` REPL is not current product |
| CLI discoverability | Implemented | `version`, `health`, `status`, `runtimes`, doctor tests | `adapter detect` target not implemented; aliases/fuzzy/history absent |
| CLI JSON envelopes | Partial | `_out(ok(...), --json)` pattern | `adapter list` lacks `--json`; some metadata/workspace inconsistency |
| Run lifecycle CLI | Implemented | `runs list/get/status/delete/export/import/replay/backfill/search/prune/diff` | No live `runs stream`, no cancel; replay is trace replay, not deterministic runtime replay |
| Run indexing | Partial | JSONL + SQLite stores exist | `arc run` appears to save JSONL path; verify/update new-run indexing before relying on search |
| Providers/keys/quotas | Implemented / partial | `providers list/catalog/status/diagnostics/proxy/key/accounts/quota/routing`; tests | `providers proxy` live wording vs dry-run behavior; keychain provider storage deferred |
| Profiles/workspace/config | Implemented / partial | `profiles`, `workspace`, `config` commands; tests | `--profile-id` vs docs `--profile`; paid profile/key gating needs proof |
| Audit CLI | Implemented / partial | `audit verify/export/key *`; HMAC modules | `audit verify/export` cwd/workspace mismatch risk; do not claim all runs signed |
| HITL CLI/storage | Implemented | `hitl pending/respond/approve/reject`; HITL store/tests | Decision tokens sensitive; document local trust boundary |
| Eval/storage/isolation CLI | Implemented | `eval`, `storage`, `isolation` groups; tests | Doctor network makes real calls; storage/eval dir naming needs verification |
| Python storage | Implemented | `JsonlTraceStore`, `SqliteStore`, `IndexedTraceStore` | Search/index split-brain risk until run path proof |
| Event broker/SSE/supervisor | Implemented / partial product proof | `orchestration/event_broker.py`, `supervisor.py`, web routes | Claim broker/SSE exists; avoid claiming browser live active-run UX until proven |
| Trust/security/redaction | Implemented / needs proof on all paths | `security/trust.py`, redaction, profiles, isolation tests | Confirm direct `arc run` trust enforcement before run record creation |
| Runtime router | Implemented | `orchestration/runtime_router.py` | Adoption routing intentionally limited |
| SwarmGraph standalone | Implemented | Adapter/router/tests | Mostly subprocess/CLI integration; not broad adoption layer |
| CrewAI + SwarmGraph | Implemented fake/offline | `crewai+swarmgraph` dry-run/fake path | No live provider/adoption product claim |
| LangGraph/AG2/OpenAI/LlamaIndex adoption runners | Partial / gated | Adoption runner files/tests | Not broadly router-runnable; mark scaffold/gated unless verified |
| AG2 standalone | Implemented / needs release wording | Adapter/tests/docs claim registered/gated | Real dependency/runtime path gated |
| OpenAI Agents | Partial / implemented export target | Adapter/export tests | Release docs may still under/overclaim; verify README wording |
| LlamaIndex | Partial | Adapter/detection/export support | Do not claim full runnable runtime unless tests prove |
| LM Arena | Deferred / stub-default | Arena code/tests; release scope excludes | Live path gated/experimental, out of v0.1 |
| HMAC audit | Implemented core, partial end-to-end | `audit/hmac_chain.py`, key manager, CLI | Do not imply every run emits signed audit material |
| Real-runtime smoke | Scaffolded | Gated tests/workflow | Need latest manual/nightly status before release |
| CI/release | Partial | Local tests/builds reported green | Main CI status must be checked; `.env` scrub unresolved |
| Docs truth | Partial | `RELEASE_CHECKLIST.md`, `AGENTS.md` more current | `REALITY_AUDIT.md`, `PLAN_COMPLETION_AUDIT.md`, `CLI_IDE_GAP_ANALYSIS.md`, `HANDOVER.md` stale |

## Current Source Of Truth

Use these as active docs after this analysis:
- `AGENTS.md`
- `docs/architecture/IMPLEMENTATION_STATUS_MATRIX.md`
- `docs/architecture/DEEP_ARCHITECTURE_ANALYSIS.md`
- `docs/roadmap/LOCKED_EXECUTION_PLAN.md`
- `docs/RELEASE_CHECKLIST.md`
- `docs/EXTENSION_MIGRATION.md` after reconciliation

Historical or stale unless refreshed:
- `docs/PLAN_COMPLETION_AUDIT.md`
- `docs/CLI_IDE_GAP_ANALYSIS.md`
- `docs/REALITY_AUDIT.md`
- `docs/handover/HANDOVER.md`
- Old status sections inside `docs/IMPLEMENTATION_PLAN.md`
