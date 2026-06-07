# ARC Studio Cleanup & Refactor Audit — 2026-06-07

> **Phase 1 (audit-only) + smallest safe Phase 2 slice.**  
> Methodology: multi-signal (static ref search + ruff + test refs + CLI entrypoint + package metadata + docs refs). No file deleted on grep-absence alone.  
> Baseline: `ruff check src tests` **clean**; HEAD `8e5012f`; pre-existing uncommitted arena work present (untouched).

---

## Audit corrections to prior synthesis (multi-signal disproof)

The earlier synthesis backlog (`unified-implementation-backlog-2026-06-07.md`) listed three "dead code" deletion targets. Real multi-signal analysis **disproves all three** — none are safe to delete:

| Suspected dead | Disproof signal | Verdict |
|---|---|---|
| `NotificationOutbox` (`notifications/outbox.py`) | `tests/notifications/test_outbox.py` imports it (5 refs) | **LIVE — keep** |
| `ArcRunTimelineWidget` | Wired via `arc-runs-contribution.ts` → `bindViewContribution` + `bind(FrontendApplicationContribution)`; command `arc:open-run-timeline`; contract tests in `ui-components.contract.test.ts` | **LIVE — keep** |
| `arena-frontend-module.ts` | Referenced in `docs/research/copilot-arena-complete-integration.md`; active **uncommitted** arena work in working tree | **DO NOT TOUCH** |

**Lesson:** ruff is in the release gate, so Python imports are already clean. The codebase has very little trivially-removable dead code. This is why this audit produced **zero deletions** in Phase 2.

---

## Table 1 — Dead-Code Candidates

| File | Symbol/code | Evidence (multi-signal) | Risk | Recommendation |
|---|---|---|---|---|
| `notifications/__init__.py` | empty module | Empty file; but `notifications/outbox.py::NotificationOutbox` has tests | Low | **Keep** — package needed for the tested `outbox.py` |
| `cli/mgmt.py` (~line 520) | first `eval run` registration | Two `@eval_app.command("run")` registrations; Typer last-wins → first is shadowed | Medium | **Possibly dead** — verify second registration is the intended one; remove first only with a test proving `eval run` behavior unchanged |
| `arc-protocol.ts` | deprecated `ArcErrorCode` enum values (4) | Marked `@deprecated`, "Removed in v0.3.0"; `canonicalErrorCode()` maps them | Low | **Legacy compatibility** — keep until v0.3 per additive protocol rule |
| `arc-protocol.ts` | `streamTrace`/`streamActiveTrace` (AsyncIterable) | Not JSON-RPC serializable; `readActiveTraceStream` is the used path | Medium | **Possibly dead** — confirm no caller uses the AsyncIterable variant before removing; keep for now |
| `protocol/mcp_decision_events.py` | `McpCallDecisionEvent` (schema v2) | Defined but never written; proxy writes `McpCallDecision` instead | Low | **Possibly dead** — protocol type; keep, wire it or document |
| `tui/widgets/slash_menu.py` | `_FALLBACK` phantom entries `theme`/`runtimes` | Not in registry; would fail if dispatched | Low | **Refactor** — remove phantom entries from fallback list |
| `cli_studio.py` entrypoint `arch-studio-cli` | typo'd console_script | Registered entrypoint; typo of `arc-studio-cli` | Low | **Additive fix** — add `arc-studio-cli`, keep `arch-studio-cli` for compat (EXECUTED this run) |

**Net safe deletions this run: 0.** All candidates are either tested, contribution-wired, legacy-compat, or require an equivalence test first.

---

## Table 2 — Refactor Candidates

| File | Problem | Proposed refactor | Risk | Tests |
|---|---|---|---|---|
| `cli/mgmt.py` (1794 LOC) | Largest CLI module; mixes eval + misc; duplicate `eval run` | Split into `cli/eval.py` + keep `mgmt.py` thin; dedupe `eval run` | Medium | Existing `test_cli_eval.py` + new equivalence test |
| `arc-protocol.ts` (1867 LOC) | 72-method god interface | Split into 9 sub-services (WorkflowService, TraceService, ConfigService, RunDetailsService, HitlAuditService, SessionService, EditPlanService, BattleService, TelemetryService) | High | Proxy + contract tests per service |
| `ConfigTab.tsx` (1253 LOC) | Largest IDE tab; provider+runtime+routing+diagnostics in one | Extract `ProviderSection`, `RuntimeSection`, `DiagnosticsSection`, `RoutingSection` components | Medium | Contract tests preserved |
| `cli/sandbox.py` (1183 LOC) / `cli/providers.py` (1178 LOC) | Large CLI modules | Extract shared sandbox/provider helper modules | Medium | Existing CLI tests |
| `providers/anthropic.py` + `openai_compatible.py` | Duplicated `_map_error` (no redaction) | Extract shared `providers/redaction.py::redact_provider_error()` | Low | New redaction tests |
| Async loading patterns across tabs | Each tab hand-rolls loading/error/data state | Extract `useAsyncState` hook | Medium | Per-tab contract tests |
| `RunsTab.tsx` | `.catch(() => null)` x3 hides errors | Explicit loading/error/missing/present states | Low | Contract test for error state |
| Card components (receipt/autopsy/contract) | Duplicate card chrome | Extract shared `<EvidenceCard>` base | Low | Render tests |
| `RunLifecycleService` + `ConfigService` | `execFileSync` blocking (startRun 120s, saveConfig 10s, getConfigStatus 20s) | Convert to `execFileAsync` | Low | Non-blocking test |
| `swarmgraph_ir/validation.py` | No cycle detection | Add DFS `_detect_cycles()` | Low | Cycle test cases |
| TUI status bar / IDE status bar | `setElement` every 10s no dirty-check | Compare-before-update | Low | Render test |

---

## Table 3 — Nested Command Inventory (depth 3+)

| Current command | Depth | Purpose | Proposed alias | Compatibility plan | Tests |
|---|---|---|---|---|---|
| `arc mcp workbench status` | 3 | ARC MCP server status | `arc mcp-status` | Keep nested; add flat alias | Equivalence JSON test |
| `arc mcp workbench inspect` | 3 | Inspect external MCP server | `arc mcp-inspect` | Keep nested; add flat alias | Equivalence test |
| `arc mcp workbench session-start/stop/list/show/cleanup` | 3 | MCP session lifecycle | `arc mcp-session <verb>` | Keep nested | Equivalence test |
| `arc sandbox audit verify/list/query/compact/show` | 3 | Sandbox audit ops | Already have flat `audit-verify` etc. | **Already aliased** — dedup the dual path | Existing |
| `arc studio sessions migrate/show/export/import/write/delete/update` | 3 | Session bridge ops | `arc sessions <verb>` | Keep nested; add `arc sessions` top-level | Equivalence test |
| `arc providers accounts list/add/disable/delete` | 3 | Provider account mgmt | `arc providers account-<verb>` | Keep nested | Equivalence test |
| `arc providers quota show/reset` | 3 | Local quota counters | `arc providers quota-<verb>` | Keep nested | Equivalence test |
| `arc providers routing get/set` | 3 | Routing policy | `arc providers routing-<verb>` | Keep nested | Equivalence test |

**Note:** Max depth is 3 (acceptable). The worst UX offenders are `mcp workbench *` and `studio sessions *`. Aliases should be added in a dedicated Phase 3 slice with JSON-equivalence tests, keeping all nested commands working. `sandbox audit *` already has a dual flat/nested path — that duplication should be consolidated (single impl, two registrations) not expanded.

---

## Table 4 — Performance Candidates

| Area | Suspected issue | Evidence | Proposed measurement | Proposed fix |
|---|---|---|---|---|
| Node backend `startRun()` | `execFileSync` 120s blocks event loop | run-lifecycle-service.ts | Time a second RPC during a run | `execFileAsync` |
| `ConfigService.getConfigStatus()` | 2× sequential `execFileSync` (20s) | config-service.ts | Time the call | `Promise.all([execFileAsync,...])` |
| ArcEventStreamWidget `liveEvents` | unbounded `[...arr, e]` O(n) per event | arc-event-stream-widget.tsx | Heap delta at 10k events | Cap at 2000 + eviction banner |
| `TraceParser.streamTrace()` | No per-line/byte cap | trace-parser.ts | Parse 100MB trace | Add size guard |
| `readActiveTraceStream()` | Buffers entire stream | run-lifecycle-service.ts | Memory on long run | Document/cap |
| CLI startup | Heavy imports at top of modules | mgmt.py 1794 LOC import surface | `python -X importtime` | Lazy-import in command bodies (already partially done) |
| `iter_workspace_files()` | rglob walks full tree before cap | workspace.py | Time on 10k-file repo | Cap on traversal, not just results |
| TUI status bar | `setElement` every 10s unconditional | status_bar widget | — | Dirty-check before update |
| `_is_nested_function` (symbols) | O(n²) `ast.walk` per function | workspace/symbols.py | Time on 500-func file | Precompute parent map once |

---

## Complete Implementation Slice Backlog (everything found)

> This supersedes the "top 25" list. Slices grouped by tier. P0 = safety/correctness, P1 = product coherence/parity/reliability, P2 = polish/coverage/perf, P3 = refactor/cleanup.

### P0 — Safety & broken-core (12 slices)
1. Sensitive file exclusion in `iter_workspace_files()` + `LocalRepoProvider` (`.env`/`*.key`/credentials)
2. TUI paid-call gate fail-closed default (`allow_paid` → False)
3. Provider `_map_error()` redaction (both clients) + shared `redact_provider_error`
4. MCP resources through `_tool_result()` risk gate + audit
5. MCP proxy `env=None` → always `_sanitise_env`
6. Run ID path-traversal sanitization in `storage/jsonl.py` + audit `--chain`
7. Theia `NotificationBackendService` env allowlist (`buildArcCliEnv`)
8. `arc mcp serve` stdout framing fix (Rich → stderr)
9. TUI streaming widget refresh (`MarkdownBlock.update` during stream)
10. McpWorkbenchTab risk badge color fix (critical≠high) + aria-label
11. TUI shell-escape stdout secret redaction (`redaction_applied`)
12. `arc policy rule-add/remove` + `arc sandbox audit-compact` confirmation gate

### P1 — Product coherence / parity / reliability (16 slices)
13. RunsTab honest receipt/autopsy/contract states (replace `.catch(()=>null)`)
14. `startRun`/`saveConfig`/`getConfigStatus`/`listRuntimeCapabilities` → async (non-blocking Node)
15. IDE persistent status rail (mode/trust/model/daemon, semantic colors)
16. Theia keybinding conflict fix (Ctrl+E/H/Shift+S + `when` guards; route to ArcStudioWidget)
17. MCP proxy timeout catch + 1MB structured error
18. Profile schema version guard + v1→v2 migration
19. SwarmGraph SDK→IDE event bridge (`translate_swarmgraph_event`)
20. TestBenchTab Run button (sandbox `local-safe`)
21. Workspace search result cap + pathlib timeout + realpath confinement
22. Per-tab React ErrorBoundary
23. `arc wallet` CLI command (fix README mismatch)
24. ContextPackEntry `line_number` field (IDE navigation)
25. CommandPalette empty-on-first-open fix (`_build_registry()` on mount)
26. TUI SettingsView persist theme + mode on Apply; add 4 missing themes
27. AGENTS.md content parsing + `AgentsMdProvider` injection
28. VercelGrepProvider env gate (`ARC_VERCEL_GREP_ENABLED`)

### P2 — Polish / coverage / performance (14 slices)
29. Real jest-axe accessibility coverage (replace no-op describe blocks)
30. liveEvents bounded buffer (2000) + eviction banner
31. IR cycle detection (`validate_graph` DFS)
32. ConfigService 3 methods add try/catch
33. `/memory` TUI slash command
34. TUI HelpScreen auto-generate from registry
35. TUI Ctrl+O implement or remove; Ctrl+R implement or remove
36. ContextMeter default limit 64k→200k
37. MESSAGE event schema mismatch fix (registry `text` vs typed model)
38. Denial events added to `KnownRunEvent` union
39. ConsensusEvidenceCard Phase 2 (risk/protocol/confidence)
40. McpWorkbenchTab tool descriptions + decisions audit path display
41. AssuranceTab HITL age fix (ISO timestamp); audit_path + signature_status display
42. Run-to-Assurance replay navigation + edit undo/redo IDE buttons

### P3 — Refactor / cleanup (15 slices)
43. **`arc-studio-cli` entrypoint alias (additive)** ← EXECUTED THIS RUN
44. Dedupe `eval run` double-registration in `cli/mgmt.py` (with equivalence test)
45. Split `cli/mgmt.py` (1794 LOC) → `cli/eval.py` + thin mgmt
46. Split `arc-protocol.ts` (1867 LOC) → 9 sub-service interfaces (additive)
47. Split `ConfigTab.tsx` (1253 LOC) → section components
48. Extract `useAsyncState` hook for IDE tabs
49. Extract shared `<EvidenceCard>` base component
50. Extract shared `redact_provider_error` (pairs with slice 3)
51. Remove `slash_menu.py` `_FALLBACK` phantom commands (theme/runtimes)
52. Consolidate `sandbox audit-verify` / `sandbox audit verify` dual path
53. CLI flat aliases for `mcp workbench *` and `studio sessions *` (Phase 3)
54. Remove `NotificationOutbox` ONLY if tests migrated to DurableNotificationOutbox (deferred)
55. Wire or document `McpCallDecisionEvent` schema v2 (currently unwritten)
56. License reconciliation (pyproject Apache-2.0 vs Proprietary LICENSE)
57. `pnpm build:prod` added to release gate + bootstrap `--frozen-lockfile` fix

### Deferred (require roadmap change / out of scope)
- Public SSE/WebSocket notification push route (R53 deferred)
- Remote MCP beyond loopback (roadmap deferred)
- Electron release packaging/signing (v0.2)
- PyPI/pipx/Homebrew distribution (blocked by swarmgraph-sdk workspace dep)
- Automatic memory injection (hardcoded blocked)
- Broad provider-backed SwarmGraph adoption (non-negotiable boundary)

**Total: 57 active slices + 6 deferred.**

---

## Executed This Run (smallest safe Phase 2 slice)

**SLICE 43 — `arc-studio-cli` entrypoint alias (additive)**

- **What:** Added `arc-studio-cli = "agent_runtime_cockpit.cli_studio:app"` to `[project.scripts]`, keeping the typo'd `arch-studio-cli` for backward compatibility.
- **Why safe:** Purely additive; no deletion; fixes a confirmed documented typo; backward-compatible.
- **Multi-signal:** `cli_studio.py` exists and `app` resolves; both old and new entrypoints register via `importlib.metadata`.
- **Verification:** `uv sync` re-registers; `arc-studio-cli --help` resolves.

---

## What was intentionally NOT changed

- **No deletions** — all suspected dead code is tested, contribution-wired, or legacy-compat.
- **Arena files** — active uncommitted work in the tree; left untouched.
- **Protocol fields** — no removals (additive-only rule).
- **Nested CLI commands** — kept working; aliases deferred to a Phase 3 slice with equivalence tests.
- **No mass formatting** — only `pyproject.toml` `[project.scripts]` touched.
- **CI-protected docs** — `roadmap.md`/`phases.md` updated in place under NEW INTAKE markers only.
