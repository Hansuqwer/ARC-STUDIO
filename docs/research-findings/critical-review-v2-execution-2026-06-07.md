# ARC Studio — Critical Review v2 Execution Output (2026-06-07)

> Executed from `critical-review-elevation-prompt-v2.md`. **Review-only pass — no production files edited.**
> Reviews the prior "Final Synthesis" (`unified-implementation-backlog-2026-06-07.md`) + the 17 category audits + the cleanup-refactor audit, against real verification and external docs.

---

## 1. Executive verdict

**ACCEPTABLE WITH CORRECTIONS.**

The synthesis is broadly sound, well-evidenced, and disciplined about not overclaiming. It is **safe to use as a backlog**, but **not safe to run verbatim as implementation prompts** until the corrections below are applied. Specific reasons:

- **3 false dead-code deletions** in the synthesis would have broken live, tested, contribution-wired code (`NotificationOutbox`, `ArcRunTimelineWidget`, `arena-frontend-module.ts`). Already corrected in the cleanup audit; this review formally retires them as deletion targets.
- **No Baseline→Polished elevation track existed** — 90+ phases sit at `Baseline Complete` with no gate-by-gate path to `Polished Complete`. This review adds it (§8a).
- Several slices mix safety + UX + refactor in one pass (too broad to land safely).
- A handful of producer-truth gaps (UI proposed without a confirmed emitter).

No UNSAFE-TO-RUN blockers remain after the P0 corrections in §9.

---

## 2. External research log (honest)

| Tool | Status | What it gave |
|---|---|---|
| **Context7** `/eclipse-theia/theia` (427 snippets, High) | **Used** | Canonical `AbstractViewContribution`+`bindViewContribution`+`bind(FrontendApplicationContribution).toService`+`WidgetFactory` wiring; `KeybindingContribution.registerKeybinding({command, keybinding, when})` with `when` clauses for context scoping. |
| **Grep / searchGitHub** (`registerKeybinding({`) | **Used** | 8 real OSS contributions (Theia terminal/debug/search/scm/console/workspace; opensumi) — **all** use `when:` guards (`terminalFocus`, `!inDebugMode`, `hasSearchResult`). Confirms ARC's bare Ctrl+E/Shift+S/H without `when` is non-idiomatic and conflict-prone. |
| **web_fetch / web_search** | **Not used** | Context7 + Grep were sufficient for the surfaces under review; no additional current-fact lookups were needed. Stated rather than faked. |
| **Repo verification** | **Used** | `ruff` clean; `pytest --collect-only` = **5637 tests** (README's "5192+" undercounts — not an overclaim); `check-banned-claims.sh` clean on AGENTS/README/roadmap/phases; 12 IDE tabs; browser+electron apps present. |

**Docs that changed the review:** Theia keybinding docs upgraded the keybinding issue from "naming nit" to a concrete `when`-guard correction with cited idiom; Theia view-contribution docs confirmed the dead-code disproof.

---

## 3. Complete issue ledger (uncapped)

Severity: B=blocker, H=high, M=medium, L=low. Roadmap/phase use existing IDs where present, else `(new)`.

| ID | Title | Cat | Sev | Evidence | Affected files | Roadmap | Phase | Safe now | Slice |
|---|---|---|---|---|---|---|---|---|---|
| CR-001 | Sensitive files not excluded from workspace inventory/search | Security | B | `iter_workspace_files()` has no `.env`/`*.key` filter | `workspace.py`, `context/providers/local_repo.py` | R-AUDIT18 | new 159 | Y | A |
| CR-002 | TUI `allow_paid` defaults permissive | Security | B | `tui/screen.py` paid gate default | `tui/screen.py` | R23 | new 160 | Y | small |
| CR-003 | Provider `_map_error()` leaks unredacted body | Security | B | dup in both clients | `providers/anthropic.py`, `openai_compatible.py` | R23 | new 161 | Y | small |
| CR-004 | MCP resources bypass risk gate | Security | H | resources don't pass `_tool_result()` | `mcp/server.py` | R26 | 78 | Y | small |
| CR-005 | MCP proxy `env=None` leaks full env | Security | H | `mcp/proxy.py` | `mcp/proxy.py` | R26 | 78 | Y | small |
| CR-006 | Run-ID path traversal in JSONL store | Security | H | no sanitization of run_id path segment | `storage/jsonl.py` | R24 | new 162 | Y | small |
| CR-007 | Theia `NotificationBackendService` no env allowlist | Security | H | CLI bridge passes full env | `node/services/notification-service.ts` | R52 | 63 | Y | small |
| CR-008 | `arc mcp serve` Rich output corrupts stdio frame | Correctness | H | Rich writes stdout on stdio transport | `cli/mcp.py` | R26 | 78 | Y | small |
| CR-009 | TUI streaming transcript doesn't refresh mid-stream | UX | H | `MarkdownBlock.update` not called during stream | `tui/widgets/transcript.py`, `markdown_block.py` | R13 | 13 | Y | B |
| CR-010 | `policy rule-add` / `sandbox audit-compact` ungated | Security | H | mutating, no confirm | `cli/sandbox.py`, `cli/policy*` | R69 | 69 | Y | small |
| CR-011 | RunsTab hides errors with `.catch(()=>null)` ×3 | UX/Truth | H | RunsTab.tsx | `tabs/RunsTab.tsx` | R-AUDIT* | new 163 | Y | C |
| CR-012 | Node backend `execFileSync` blocks event loop | Perf/Reliab | H | startRun 120s, getConfigStatus 20s sync | `run-lifecycle-service.ts`, `config-service.ts` | R14 | new 164 | Y | medium |
| CR-013 | Theia keybindings lack `when` guards (Ctrl+E/Shift+S/H) | IDE | H | no `when:`; Theia idiom requires it (Context7+Grep) | `arc-*-contribution.ts` | R-AUDIT* | new 165 | Y | small |
| CR-014 | liveEvents buffer unbounded | Perf | M | `[...arr,e]` no cap | `arc-event-stream-widget.tsx` | R24 | 24 | Y | small |
| CR-015 | TraceParser no size cap on stream | Perf/Reliab | M | `trace-parser.ts` | `trace-parser.ts` | R24 | 24 | Y | small |
| CR-016 | SwarmGraph SDK events don't reach IDE | Truth | M | no `translate_swarmgraph_event` bridge | adapters + node bridge | R15 | 15 | N (needs producer) | medium |
| CR-017 | IR graph no cycle detection | Reliab | M | `swarmgraph_ir/validation.py` | `swarmgraph_ir/validation.py` | R17 | 17 | Y | small |
| CR-018 | MCP proxy no timeout/structured error cap | Reliab | M | `mcp/proxy.py` | `mcp/proxy.py` | R26 | 78 | Y | small |
| CR-019 | Profile schema version drift (1 vs 2) | Correctness | M | `security/profiles.py` | `security/profiles.py` | R50 | active P0 | Y | small |
| CR-020 | No per-tab React ErrorBoundary | Reliab | M | tabs throw to blank | `tabs/*`, `arc-studio-widget.tsx` | R-AUDIT* | new 166 | Y | medium |
| CR-021 | `arc wallet` CLI vs README mismatch | Docs/Parity | M | README shows `arc wallet`; verify command | `cli/*`, README | R-AUDIT17 | new 167 | Y | small |
| CR-022 | Workspace search no result cap / realpath confinement | Security/Perf | M | `workspace.py` search | `workspace.py` | R-AUDIT18 | 79 | Y | A-adj |
| CR-023 | CommandPalette empty on first open | UX | M | registry built lazily | `tabs/CommandCentreTab.tsx` | R-AUDIT* | new 168 | Y | small |
| CR-024 | TUI shell stdout not redacted | Security | M | shell-escape output | `tui/*` shell | R44 | 44 | Y | small |
| CR-025 | Duplicate `eval run` registration | Cleanup | M | two `@eval_app.command("run")` in mgmt.py | `cli/mgmt.py` | R-CLEAN1 | 158 | Y (w/ test) | small |
| CR-026 | `cli/mgmt.py` 1794 LOC god module | Refactor | M | wc -l | `cli/mgmt.py` | R-CLEAN1 | new 169 | N (large) | refactor |
| CR-027 | `arc-protocol.ts` 1867 LOC, 72-method interface | Refactor | M | wc -l | `common/arc-protocol.ts` | R22 | new 170 | N (large) | refactor |
| CR-028 | `ConfigTab.tsx` 1253 LOC | Refactor | L | wc -l | `tabs/ConfigTab.tsx` | R-AUDIT* | new 171 | N | refactor |
| CR-029 | Duplicate async load/error pattern across tabs | Refactor | L | every tab hand-rolls | `tabs/*` | R-AUDIT* | new 172 | N | refactor |
| CR-030 | `slash_menu.py` phantom fallback cmds (theme/runtimes) | Cleanup | L | not in registry | `tui/widgets/slash_menu.py` | R44 | 44 | Y | small |
| CR-031 | `sandbox audit-verify` / `audit verify` dual path | Cleanup | L | two registrations | `cli/sandbox.py` | R18 | 158 | Y | small |
| CR-032 | License drift: pyproject Apache-2.0 vs LICENSE Proprietary | Release | M | metadata mismatch | `python/pyproject.toml`, `LICENSE` | R7 | new 173 | Y | small |
| CR-033 | `arch-studio-cli` typo entrypoint | Cleanup | L | fixed additively | `python/pyproject.toml` | R-CLEAN1 | 158 | ✅ DONE | done |
| CR-034 | Eval metrics synthetic labelling completeness | Truth | L | partial (R-AUDIT19) | `evals/*` | R-AUDIT19 | 150 | Y | small |
| CR-035 | ContextMeter default limit 64k vs modern 200k | UX | L | TUI meter | `tui/*` | R-TS1 | new 174 | Y | small |
| CR-036 | MESSAGE event schema mismatch (registry `text` vs model) | Protocol | M | registry vs typed model | protocol + `tui` | R22 | new 175 | N (protocol) | additive |
| CR-037 | Denial events absent from `KnownRunEvent` union | Protocol | M | union incomplete | `arc-protocol.ts`, py protocol | R22 | new 175 | N (protocol) | additive |
| CR-038 | AGENTS.md "Active track" stale (P0 sprint Complete) | Docs | L | phases.md says complete | `AGENTS.md` | — | — | Y | small |
| CR-039 | `pnpm build:prod` not in release gate | Release | M | `scripts/release_check.sh` | scripts | R7 | new 173 | Y | small |
| CR-040 | bootstrap `--frozen-lockfile` inconsistency | Release | L | `scripts/bootstrap.sh` | scripts | R7 | new 173 | Y | small |
| CR-041 | AGENTS.md / README test count drift (5192 vs 5637) | Docs | L | collect-only=5637 | README, docs | R0 | — | Y | trivial |
| CR-042 | jest-axe a11y blocks are no-ops | Test/A11y | M | empty describe | `__tests__/*a11y*` | R-AUDIT21 | 152 | Y | medium |
| CR-043 | `McpCallDecisionEvent` schema v2 defined but never written | Protocol | L | unused producer | `protocol/mcp_decision_events.py` | R26 | new 175 | Y | small |
| CR-044 | TUI SettingsView doesn't persist theme/mode on Apply | UX | M | `/settings` apply | `tui/*` settings | R-AUDIT* | new 176 | Y | small |
| CR-045 | AGENTS.md md adopted DoD has no automated gate yet | Governance | L | new section, manual | `AGENTS.md`, scripts | — | new 177 | Y | small |

**Categories with no open blocker (verified adequate):** SQLite WAL busy-timeout (R-AUDIT20, confirmed), SDK version sweep (R-AUDIT24), handover-doc refs (R-AUDIT22).

---

## 4. Unsupported assumptions ledger

| ID | Assumption | Where | Missing evidence | How to verify | Map | Safer wording |
|---|---|---|---|---|---|---|
| AS-1 | "ArcRunTimelineWidget is dead code" | synthesis SLICE 15 | contribution exists | grep contribution + module bind | R-CLEAN1/158 | **Retract** — it is wired + tested |
| AS-2 | "NotificationOutbox has no consumer" | synthesis SLICE 15 | test file exists | `tests/notifications/test_outbox.py` | R-CLEAN1/158 | **Retract** — tested |
| AS-3 | "arena-frontend-module.ts is removable" | synthesis SLICE 15 | active uncommitted work | `git status` arena files | — | **Do not touch** |
| AS-4 | "SwarmGraph events visible in IDE" | swarmgraph audit | no bridge confirmed | trace IDE event path | R15/15 | "producer absent → degraded state required" |
| AS-5 | "arc wallet exists as shown in README" | README | command not confirmed | `arc wallet --help` | R-AUDIT17/167 | verify before citing in docs |
| AS-6 | "5192+ tests" | README/phases | actual 5637 | `pytest --collect-only` | R0 | update to "5600+" |

---

## 5. Overclaims ledger

| ID | Overclaim | Why unsupported | Forbidden wording | Allowed replacement | Map |
|---|---|---|---|---|---|
| OC-1 | implied "production-ready after slices" | banned + alpha posture | "Production ready" | "meets Definition of Done (Polished Complete) with cited evidence" | AGENTS DoD |
| OC-2 | "dead code removed" (none was dead) | all live | "removed dead code" | "audited; zero safe deletions; corrected 3 false positives" | R-CLEAN1 |
| OC-3 | "signed audit chain" elsewhere | HMAC only in vendored SDK | "signed audit chain" | "SHA-256 hash chain (ARC) / HMAC (vendored SwarmGraph)" | R21 |
| OC-4 | "live streaming" | SSE replay, not live push | "live streaming" | "SSE trace replay" | R8/R52 |
| OC-5 | broad provider-backed SwarmGraph | not proven | "provider-backed SwarmGraph adoption" | "narrow gated local-real path" | R6/R19 |

---

## 6. Producer-truth ledger

| ID | UI feature | Claimed data | Actual producer | Status | Required degraded state | Map |
|---|---|---|---|---|---|---|
| PT-1 | SwarmGraph Insight cost/topology | per-node cost+graph | SDK events (no IDE bridge) | absent (bridge) | "No SwarmGraph producer connected" | R15/15 |
| PT-2 | RunsTab receipt/autopsy/contract | evidence cards | CLI `runs links`/audit | conditional | explicit empty/missing/error states | new 163 |
| PT-3 | TestBenchTab results | run output | sandbox `local-safe` (no Run btn) | stub | "Run not wired — CLI only" | 79 |
| PT-4 | ContextDrawer AGENTS.md | parsed agents.md | provider stub | stub | "AGENTS.md parsing not wired" | R-AUDIT16/new |
| PT-5 | Assurance HITL age | ISO timestamp | audit store | conditional (age bug) | render `—` if no timestamp | R-AUDIT* |
| PT-6 | McpWorkbench decisions | per-call audit | `decisions.jsonl` | baseline | path display + empty state | 78 |

---

## 7. Corrected roadmap insertion plan (propose only — not edited)

| Proposed R-ID | Title | Status | Why it belongs |
|---|---|---|---|
| R-POLISH1 | DoD Elevation: Security P0 cluster (CR-001..010) | Not Started | safety items must land before any "complete" wording |
| R-POLISH2 | DoD Elevation: IDE UX-states + a11y + ErrorBoundary | Not Started | gates 1,2,7 for IDE tabs |
| R-POLISH3 | DoD Elevation: TUI streaming + settings persistence | Not Started | gates 1,3 for TUI |
| R-POLISH4 | DoD Elevation: Perf (async backend, bounded buffers) | Not Started | gate 5 |
| R-CLEAN2 | Refactor: split mgmt.py / arc-protocol.ts / ConfigTab | Not Started | gate-neutral maintainability |
| R-REL1 | Release gate: license reconcile + build:prod + lockfile | Not Started | gate 8 + release confidence |

---

## 8. Corrected phase insertion plan (propose only)

| Proposed phase | Roadmap | Status | Acceptance | Verification | Risks | Deps |
|---|---|---|---|---|---|---|
| 159 Sensitive-file exclusion | R-POLISH1 | Not Started | `.env`/`*.key`/creds never enumerated; tests | `pytest tests/cli/test_workspace_inventory.py tests/context -q` | over-broad filter hides real files | none |
| 160 TUI paid-gate fail-closed | R-POLISH1 | Not Started | default denies paid; audit on allow | `pytest tests/tui -q` | UX friction | none |
| 161 Provider error redaction | R-POLISH1 | Not Started | shared `redact_provider_error`; no body leak | `pytest tests/providers -q` | mask useful errors | none |
| 162 Run-ID path-traversal guard | R-POLISH1 | Not Started | `../` rejected; audit | `pytest tests/storage -q` | none | none |
| 163 RunsTab honest states | R-POLISH2 | Not Started | loading/empty/error/missing/present; no silent catch | `pnpm --filter arc-extension test` | snapshot churn | protocol stable |
| 164 Async Node backend | R-POLISH4 | Not Started | no `execFileSync` in hot paths; non-block test | `pnpm --filter arc-extension build` | timeout semantics | none |
| 165 Keybinding `when` guards | R-POLISH2 | Not Started | `when` scoped to ARC focus; no editor clobber | contract test | conflicts | Theia ctx keys |
| 166 Per-tab ErrorBoundary | R-POLISH2 | Not Started | tab error shows boundary not blank | `pnpm --filter arc-extension test` | none | none |
| 169 Split mgmt.py | R-CLEAN2 | Not Started | `cli/eval.py` extracted; behavior identical | CLI snapshot | import cycles | dedupe CR-025 first |
| 170 Split arc-protocol.ts (additive) | R-CLEAN2 | Not Started | 9 sub-interfaces; no field removed | `pnpm typecheck` | protocol break | additive-only |
| 173 Release gate hardening | R-REL1 | Not Started | license reconciled; build:prod in gate | `bash scripts/release_check.sh` | gate slow | none |
| 177 DoD automated checklist | R-POLISH* | Not Started | script asserts gate evidence cited | `bash scripts/check-pr.sh` | false rigidity | DoD §AGENTS |

---

## 8a. Baseline → Polished Complete elevation ledger (NEW — clustered by surface)

> 90+ phases sit at `Baseline Complete`. The 8 DoD gates apply at the **surface** level, so phases are clustered by subsystem and scored as a group; per-phase deviations are noted. **No cluster may move to `Polished Complete` until all failing gates close with cited evidence.** Status stays `Baseline Complete` today for every cluster.

Gate key: 1 UX-states · 2 a11y · 3 parity · 4 tests · 5 perf · 6 security · 7 reliability · 8 docs. ✅ pass(evidence) / ❌ fail(deficiency) / ◑ partial.

| Cluster (phases) | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | Elevation slices to reach Polished | Safe now |
|---|---|---|---|---|---|---|---|---|---|---|
| **IDE tabs** (2,3,4,10,12,13,45,56,57,63,78,91) | ❌ RunsTab silent catch | ❌ no-op axe | ◑ | ✅ contract tests | ❌ sync execFile | ◑ | ❌ no ErrorBoundary | ◑ | CR-011,013,020,012,042 → phases 163,165,166,164 | Y |
| **IDE protocol** (22,49) | ✅ | n/a | ◑ JSON documented | ✅ | ✅ | ✅ | ◑ | 1867-LOC split + denial events + MESSAGE schema | additive only |
| **TUI** (41,42,44,45,86) | ❌ stream no refresh | ◑ NO_COLOR ok, focus? | ◑ CLI/TUI drift | ◑ | ◑ | ❌ shell stdout unredacted | ◑ | CR-009,024,030,044,035 → phases 13,44,176 | Y |
| **CLI** (18,25,42,85,97) | ✅ JSON | n/a | ◑ depth-3 aliases | ✅ | ◑ startup imports | ◑ ungated mutators | ◑ | CR-010,025,026,031 → phases 158,169 | mostly Y |
| **Providers** (3,12,19,57) | ◑ | ◑ | ◑ | ✅ | ◑ | ❌ error leak | ◑ | CR-003,002 → phases 160,161 | Y |
| **Sandbox/isolation** (62,68,69,71,72,73,82,83,84,92–96) | ✅ | n/a | ✅ | ✅ fuzz suite | ✅ | ◑ ungated compact | ✅ | CR-010 confirm-gate; keep microVM truth labels | Y |
| **MCP** (26,27,39,78) | ◑ | ◑ | ◑ | ✅ | ◑ | ❌ resources bypass gate, env leak, stdout | ◑ | CR-004,005,008,018,043 → phase 78 | Y |
| **SwarmGraph** (5,15,17,51,59,60,61,64) | ◑ insight degraded | n/a | ◑ | ✅ | ◑ | ✅ deterministic | ◑ no cycle detect | CR-016,017 → phases 15,17 | partly (bridge=N) |
| **Audit/HITL** (4,21,29,32,48,69) | ◑ HITL age bug | ◑ | ◑ | ✅ | ✅ | ✅ SHA-256 (not "signed") | ◑ | PT-5 fix; wording OC-3 | Y |
| **Runs/events/streaming** (1,8,13,20,24,52,54,55,63,65) | ◑ | ◑ | ◑ | ✅ | ❌ unbounded buffer, no trace cap | ◑ | ◑ | CR-014,015,006 → phase 162,24 | Y |
| **Memory** (59,60,61,64) | ◑ research-proto | n/a | n/a | ✅ eval gate | ◑ | ✅ privacy guardrails | ◑ | keep "research prototype" label; no new claims | Y |
| **CI/eval** (53,58,80) | ◑ | n/a | ◑ | ✅ | ◑ | ✅ | ◑ | CR-034 synthetic labels | Y |
| **Config/profiles** (57,84) | ◑ | ◑ | ◑ | ✅ | ◑ | ❌ schema drift | ◑ | CR-019,044 → 176 | Y |
| **Release/packaging** (7,16) | n/a | n/a | n/a | ◑ | n/a | ◑ | ◑ | CR-032,039,040 → phase 173 | Y |

**Highest-leverage elevation order:** Security gate-6 failures first (MCP, providers, sandbox) → IDE UX/reliability gates 1+7 (RunsTab, ErrorBoundary, async) → TUI gate-1 streaming → a11y gate-2 (real axe) → docs gate-8 (release gate, license).

---

## 9. Corrected priority backlog

- **P0 (must fix before prompts are "safe"):** CR-001,002,003,004,005,006,007,008,010,024 (security/correctness). Map: R-POLISH1 / phases 159–162 + 78 + 63.
- **P1 (next slices):** CR-009,011,012,013,019,020 (UX-states, async, keybinding, ErrorBoundary, schema). Map: R-POLISH2/3/4 / phases 163–166.
- **P2 (important follow-up):** CR-014,015,016,017,018,022,023,034,036,037,042,043,044. Map: existing phases + 175,176.
- **P3 (polish/later):** CR-021,025,026,027,028,029,030,031,032,035,038,039,040,041,045. Map: R-CLEAN2/R-REL1 / phases 169–173,177.
- **Deferred:** SSE push route (R53), remote MCP, electron signing (v0.2), PyPI distribution, automatic memory injection, broad provider-backed SwarmGraph.

---

## 10. Corrected next implementation order

1. **Security P0 batch** (CR-001..003,006) — files: `workspace.py`, `providers/*`, `storage/jsonl.py` — non-goals: no UI — tests: `pytest tests/cli tests/providers tests/storage -q` — rollback: revert per-file.
2. **MCP safety batch** (CR-004,005,008,018) — `mcp/server.py`,`mcp/proxy.py`,`cli/mcp.py` — non-goals: no protocol change — tests: `pytest tests/mcp -q`.
3. **TUI streaming + redaction** (CR-009,024) — `tui/widgets/transcript.py`,`markdown_block.py` — tests: `pytest tests/tui -q`.
4. **IDE honest states + ErrorBoundary + keybinding when** (CR-011,013,020) — `tabs/RunsTab.tsx`, contributions — tests: `pnpm --filter arc-extension test`.
5. **Async Node backend** (CR-012) — `run-lifecycle-service.ts`,`config-service.ts` — tests: build + non-block test.
6. **Cleanup batch** (CR-025,030,031) — `cli/mgmt.py`,`slash_menu.py`,`cli/sandbox.py` — tests: CLI snapshots.
7. **Refactor (after green)** (CR-026,027,028) — large splits, additive.
8. **Release gate** (CR-032,039,040) — scripts — tests: `release_check.sh`.

Rollback note for all: changes are per-file and additive; no protocol/CLI removals; revert is `git checkout -- <file>`.

---

## 11. Top 3 next implementation prompts

### Prompt A — Security P0 batch (CR-001, CR-003, CR-006)
- **Scope:** sensitive-file exclusion in `iter_workspace_files()`+`LocalRepoProvider`; shared `redact_provider_error()`; run-ID path-traversal guard.
- **Roadmap/phase:** R-POLISH1 / phases 159,161,162. **Non-goals:** no UI, no protocol.
- **Steps:** add `_SENSITIVE_*` frozensets + `_is_sensitive_file()`; wire both producers; add `providers/redaction.py`; sanitize run_id segment.
- **Acceptance (DoD gates 1,4,6,8):** secrets never enumerated/echoed; deterministic; tests; docs/security/enforcement-surfaces.md updated.
- **Verify:** `cd python && uv run ruff check src tests && uv run pytest tests/cli/test_workspace_inventory.py tests/context tests/providers tests/storage -q`.

### Prompt B — IDE honest states + ErrorBoundary + keybinding `when` (CR-011, CR-013, CR-020)
- **Scope:** RunsTab explicit states; per-tab ErrorBoundary; add `when` clauses to ARC keybindings (Theia idiom, cited).
- **Roadmap/phase:** R-POLISH2 / phases 163,165,166. **Non-goals:** no protocol fields removed; no new tabs.
- **Acceptance (DoD gates 1,2,3,7):** loading/empty/error/missing/present states; boundary catches tab errors; keybindings scoped, no editor clobber.
- **Verify:** `pnpm --filter arc-extension build && pnpm --filter arc-extension test && pnpm typecheck`.

### Prompt C — TUI streaming refresh + shell redaction (CR-009, CR-024)
- **Scope:** call `MarkdownBlock.update` on stream deltas; redact shell stdout with `redaction_applied` flag.
- **Roadmap/phase:** R-POLISH3 / phases 13,44. **Non-goals:** no theme rework.
- **Acceptance (DoD gates 1,6):** transcript updates mid-stream; secrets masked; audit on allow.
- **Verify:** `cd python && uv run pytest tests/tui -q && uv run ruff check src tests`.

---

## 12. Rewritten Final Synthesis (short, safe, accurate)

ARC Studio's 17-area audit produced a credible backlog of **57 active slices** across security, IDE/TUI/CLI parity, evidence-truth, performance, and cleanup. Real verification confirms a healthy base: **ruff clean, 5637 tests collected, banned-claims clean**. The codebase has **almost no removable dead code** (3 prior "dead" targets were disproved as live/tested/wired).

The work is now organized as **DoD elevation**: every `Baseline Complete` surface is scored against 8 measurable gates (UX-states, a11y, parity, tests, perf, security, reliability, docs), and only earns `Polished Complete` when each gate cites evidence. **Security gate-6 failures (MCP resource/env/stdout, provider error leak, sensitive-file exclusion) are the P0 blockers** and must land first. No production-readiness, multi-user, signed-audit, live-streaming, or broad-provider-backed claims are made; ARC stays a single-user loopback alpha. Producers are named per UI feature, with degraded states required wherever an emitter is absent or gated.

---

## 13. Final recommendation

- **Is the prior synthesis safe to run verbatim?** No — fix the 3 false dead-code deletions (done) and apply the P0 security batch first.
- **What to fix first:** Prompt A (security P0), then Prompt B (IDE states), then Prompt C (TUI streaming).
- **Run first:** **Prompt A.** It is fully producer-backed, deterministic, testable offline, and unblocks every "secure/complete" gate claim.
- **Do not run yet:** the large refactors (mgmt.py / arc-protocol.ts splits), the SwarmGraph→IDE bridge (producer absent — needs the bridge slice first), and anything that would touch the active uncommitted arena work.
