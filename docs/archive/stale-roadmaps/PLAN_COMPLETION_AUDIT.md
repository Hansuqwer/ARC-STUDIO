# ARC Studio Plan Completion Audit

Generated: 2026-05-14
Source: Full codebase audit against `docs/IMPLEMENTATION_PLAN.md`, `docs/adr/`, `docs/REALITY_AUDIT.md`

## 1. Executive Summary

ARC Studio has a solid Python CLI/daemon foundation, real standalone adapters for 4 runtimes, a vendored SwarmGraph runtime with production-grade queen/worker/consensus/HITL/HMAC audit, and a canonical Theia extension with 239 tests. The architecture is coherent at the code level but fragmented at the product level: the browser app depends on 12 duplicate `theia-extensions/*` but NOT the canonical `arc-extension`, the adoption layer is entirely unimplemented, and security infrastructure (workspace trust, HMAC audit, daemon auth) is deferred too late.

**Biggest blockers:**
1. Canonical extension not wired into browser/electron apps (documented but not connected)
2. No adoption layer exists (zero code in `adoption/` directory)
3. Security items misplaced in P4 that should be P1-P2 (workspace trust, HMAC audit, daemon auth, env allowlist)
4. P1 is too broad (11 items spanning protocol, infrastructure, IDE, security, features)
5. HITL contract defined before persistence infrastructure exists

**What is already solid:**
- Python CLI/daemon with 40+ REST endpoints
- 4 standalone adapters with runners, mappers, dual gating (SwarmGraph, LangGraph, CrewAI, AG2)
- Vendored SwarmGraph runtime (production-grade, not stub)
- SHA-256 audit chain (unauthenticated but functional)
- AG-UI event mapping for all major runtimes
- 239 Jest tests in canonical extension
- CI gate (`arc-roadmap-gate.yml`) passing
- Foundation ADRs (000-008) as planning baseline

**What is misleading or over-scoped:**
- `REALITY_AUDIT.md` claims LM Arena is "100% stub" — live mode EXISTS behind dual gates (audit docs contain a fiction about Arena)
- `arc-extension` is documented as canonical but browser app depends on zero `arc-extension` and twelve `theia-extensions/*`
- P4 contains security items that should block P1-P2 implementation (workspace trust, HMAC audit)
- Firecracker in P4 is unrealistic (zero code, Linux-only, high ops burden, depends on entire isolation stack)
- P1 groups 11 items that should be split into infrastructure-first and adoption-second phases

**Is the implementation plan complete enough to execute?**
Yes, with edits. The plan correctly identifies all gaps and phases. The ADR review gate provides guardrails. But phase boundaries need adjustment (security items moved earlier, P1 split, Firecracker deferred, P2 adoption priority reordered based on code evidence).

**What must change before implementation starts:**
1. Split P1 into P1a (infrastructure) and P1b (adoption + IDE)
2. Move workspace trust, HMAC audit wiring, daemon auth, and env allowlist from P4 to P1-P2
3. Defer Firecracker to P5/Future
4. Reorder P2 adoption: AG2 before CrewAI (group chat maps more naturally to workers)
5. Fix Arena documentation (live mode exists, not 100% stub)
6. Wire `arc-extension` into browser app before any UI porting
7. Resolve protocol conflicts between `arc-extension` and `theia-extensions/*` (RunEvent vs TraceEvent, ExecutionResult vs RunRecord)

**Verdict: Ready with edits**

---

## 2. Phase Readiness Table

| Phase | Plan Goal | Current Evidence | Missing Work | Risk | Recommendation |
|---|---|---|---|---|---|
| P0 | Truth, coherence, runnability | CLI exists, adapters exist, docs mostly honest, ADRs drafted | 7 CLI commands missing, AG2 unregistered, OpenAI hardcoded TestAgent, canonical extension not wired, Arena docs wrong | Medium | **Edit** — reframe Arena item, split canonical wiring into sub-PRs |
| P1 | SwarmGraph adoption foundation | Runtime router exists, capability schema exists, AG-UI mapping exists | Adoption protocol (0 code), live stream (0 code), isolation interface (0 code), prompt optimizer (0 code), HITL premature | High | **Edit** — split into P1a (infrastructure) + P1b (adoption), reorder items, defer HITL contract |
| P2 | Runtime + SwarmGraph integrations | 4 standalone adapters complete, SwarmGraph vendored runtime production-grade | Zero adoption wiring, 3 runtimes need standalone fixes first, HMAC audit not wired | High | **Edit** — reorder adoption priority (AG2↑, CrewAI↓), defer SK/Haystack/DSPy, split audit/HITL |
| P3 | Theia UX productization | 12 theia-extensions with rich UI, canonical extension with basic UI | 6 widgets to port, 2 protocol conflicts, no live stream backend | Medium | **Proceed** — port order defined, salvage matrix complete |
| P4 | Audit, replay, HITL, security | SHA-256 chain exists, eval CLI exists, SwarmGraph HMAC exists in vendored runtime | 4 security items should move earlier, Firecracker unrealistic, replay split needed | High | **Edit** — move 4 items to P1-P2, defer Firecracker, split replay/eval |
| P5 | Release readiness | CI gate passing, release checklist archived, Electron scaffolding exists | Docs truth script missing, checklist stale, Electron not realistic for v0.1 | Low | **Edit** — promote checklist, define v0.1 surface (browser + CLI, not Electron) |

---

## 3. P0 Audit: Truth, Coherence, Runnability

### P0-1: Confirm Canonical Extension Wiring

1. **Current implementation evidence:** `packages/arc-extension/` has 239 tests, valid Theia extension, backend service (276 lines), widget (~450 lines), 8 components. README declares it canonical.
2. **Missing implementation:** `applications/browser/package.json` does NOT depend on `arc-extension` — depends on all 12 `theia-extensions/*` instead. Same for `applications/electron/package.json`.
3. **Docs/readme mismatch:** README claims canonical but browser app contradicts — zero dependency on `arc-extension`.
4. **Tests present:** 239 Jest tests in `arc-extension/`.
5. **Tests missing:** Integration test proving `arc-extension` works when wired into browser app.
6. **Risk:** **High** — canonical extension is documented fiction until wired.
7. **Required plan edit:** Understates gap. Browser app must be re-wired.
8. **Recommended implementation PR:** Add `arc-extension` to browser app dependencies, verify build, confirm widget appears.
9. **Acceptance criteria:** Browser app depends on `arc-extension`, builds, loads widget.
10. **Remain P0?** **Yes** — blocker for all IDE work.

### P0-2: Inventory Secondary Theia Extensions

1. **Current implementation evidence:** 12 extensions exist. Migration policy table in plan. Inventory in `CLI_IDE_GAP_ANALYSIS.md`.
2. **Missing implementation:** No port/archive/delete actions taken. No deprecation markers.
3. **Docs/readme mismatch:** README says secondary but browser app depends on ALL of them.
4. **Tests present:** Individual extension tests.
5. **Tests missing:** Ported component equivalence tests.
6. **Risk:** **Medium** — inventory done, no action.
7. **Required plan edit:** Add explicit port ordering.
8. **Recommended implementation PR:** Docs-only PR adding deprecation markers, then incremental port PRs.
9. **Acceptance criteria:** Every extension has explicit status (port/archive/delete).
10. **Remain P0?** **Yes** — architecture confusion blocks P3.

### P0-3: Register or Explicitly Hide AG2

1. **Current implementation evidence:** AG2 runner (63 lines), mapping (37 lines), detection (23 lines), tests (3 tests). Dual gating implemented.
2. **Missing implementation:** NOT registered in `registry.py:build_default()`. Invisible to `arc runtimes`.
3. **Docs/readme mismatch:** README correctly says "not registered" — accurate.
4. **Tests present:** `python/tests/adapters/ag2/test_adapter.py` (3 tests).
5. **Tests missing:** CLI integration test via `arc runtimes --capabilities --json`.
6. **Risk:** **Low** — one-line registration change.
7. **Required plan edit:** None.
8. **Recommended implementation PR:** Add import + register in `registry.py`, add CLI test.
9. **Acceptance criteria:** `arc runtimes` shows AG2 with honest capability report.
10. **Remain P0?** **Yes** — quick fix, high clarity value.

### P0-4: Fix OpenAI Agents Export Target

1. **Current implementation evidence:** Adapter (333 lines), streaming (88 lines), mapping (46 lines), RunHooks capture. Dual gating.
2. **Missing implementation:** Hardcoded `TestAgent` in `run_workflow()` (line 272-275). No `ARC_OPENAI_AGENTS_EXPORT` env var.
3. **Docs/readme mismatch:** README correctly identifies hardcoded agent — accurate.
4. **Tests present:** `python/tests/adapters/openai_agents/test_streaming.py`.
5. **Tests missing:** Fake SDK workspace test with export target.
6. **Risk:** **Medium** — SDK API volatile.
7. **Required plan edit:** None.
8. **Recommended implementation PR:** Add env var parsing, use `resolve_python_entrypoint()`, remove hardcoded agent from product path.
9. **Acceptance criteria:** `ARC_OPENAI_AGENTS_EXPORT=my_agents:main_agent` resolves and runs user's agent.
10. **Remain P0?** **Yes** — hardcoded test agent in product path is fiction.

### P0-5: Mark LM Arena Stub-Only — REFRAMED

1. **Current implementation evidence:** Stub functions exist (`_stub_battle`, etc.) BUT `_live_response()` at `arena/service.py:298-396` DOES implement real provider calls (OpenAI, Anthropic, Mistral, DeepSeek, OpenRouter). Gated behind `ARC_ALLOW_LIVE_ARENA=true` + `ARC_LMARENA_ALLOW_COSTS=true`.
2. **Missing implementation:** Live mode has no tests.
3. **Docs/readme mismatch:** **`REALITY_AUDIT.md` contains a FALSE claim** — says Arena is "100% stub" and "`ARC_ALLOW_LIVE_ARENA=true` is a fiction". Live mode code EXISTS and is functional.
4. **Tests present:** `python/tests/arena/test_arena_service.py`, `test_arena_models.py`, `test_lmarena_adapter.py`.
5. **Tests missing:** Live-mode integration test (expected — opt-in).
6. **Risk:** **Low** — live mode properly gated. Issue is documentation inaccuracy.
7. **Required plan edit:** **Reframe**: "Document Arena honestly: stub-default with gated live mode" not "mark stub-only".
8. **Recommended implementation PR:** Docs-only PR correcting `REALITY_AUDIT.md` and `CLI_IDE_GAP_ANALYSIS.md`.
9. **Acceptance criteria:** Docs accurately describe stub-default + gated-live.
10. **Remain P0?** **Yes, but reframed** — the audit docs themselves contain a fiction about Arena.

### P0-6: Normalize Capability Reports

1. **Current implementation evidence:** `RuntimeCapabilities` (16 boolean fields), `CapabilityReport` (10 fields), `RuntimeAvailability` (6 values). Each adapter implements `capability_report()`.
2. **Missing implementation:** No `support_level`, `execution_modes`, `adoption_modes`, or schema versioning.
3. **Docs/readme mismatch:** Plan calls for fields that don't exist.
4. **Tests present:** Adapter-level capability tests.
5. **Tests missing:** Contract test for consistent capability report shape across all adapters.
6. **Risk:** **Medium** — schema change affects CLI, daemon API, Theia UI.
7. **Required plan edit:** Add schema versioning strategy before adding fields.
8. **Recommended implementation PR:** Add `support_level`, `execution_modes`, `schema_version` to capability models.
9. **Acceptance criteria:** `arc runtimes --capabilities --json` includes new fields, all adapters report honest values.
10. **Remain P0?** **Yes** — core to product narrative (standalone vs adoption distinction).

### P0-7: Update Docs Index

1. **Current implementation evidence:** `docs/INDEX.md` exists. `docs/adr/` has 9 ADRs. `docs/archive/` has 60+ archived docs. Active docs are coherent.
2. **Missing implementation:** `docs/SECURITY_AUDIT_REPORT.md` referenced in README but does NOT exist. `docs/ARCHITECTURE.md` missing. Standalone vs adoption not consistently applied.
3. **Docs/readme mismatch:** README:L9 and L204 reference non-existent `SECURITY_AUDIT_REPORT.md`.
4. **Tests present:** None.
5. **Tests missing:** Grep test for banned claims. Link checker for broken doc references.
6. **Risk:** **Low** — docs cleanup.
7. **Required plan edit:** Add explicit file list.
8. **Recommended implementation PR:** Fix broken links, create missing docs, add standalone/adoption distinction.
9. **Acceptance criteria:** All README doc links resolve. No banned claims. Standalone vs adoption clear.
10. **Remain P0?** **Yes** — broken links undermine trust.

### P0-8: Add CLI Truth/Discoverability Commands

1. **Current implementation evidence:** `arc inspect`, `arc runtimes`, `arc workflows`, `arc schemas`, `arc serve`, `arc run`, `arc adapter list/test`, `arc doctor swarmgraph` all exist.
2. **Missing implementation:** `arc version` (NOT implemented), `arc health` (NOT implemented), `arc status` (NOT implemented), `arc doctor all` (NOT implemented), `arc env check` (NOT implemented), `arc adapter info` (NOT implemented), `arc adapter detect` (NOT implemented).
3. **Docs/readme mismatch:** README does not overclaim — accurate.
4. **Tests present:** CLI smoke, error paths, runs, eval, gating, doctor tests.
5. **Tests missing:** Tests for 7 missing commands.
6. **Risk:** **Low** — straightforward CLI additions.
7. **Required plan edit:** None.
8. **Recommended implementation PR:** Single PR adding 7 CLI commands.
9. **Acceptance criteria:** All 7 commands return JSON envelopes with correct data.
10. **Remain P0?** **Yes** — core discoverability gap.

### P0-9: Add CLI Daemon-Parity Commands

1. **Current implementation evidence:** Daemon endpoints exist for runs diff, providers proxy, providers diagnostics, OTLP export. No CLI wrappers.
2. **Missing implementation:** `arc runs diff`, `arc providers diagnostics`, `arc providers proxy`, `arc providers accounts enable`.
3. **Docs/readme mismatch:** None — plan correctly identifies gaps.
4. **Tests present:** `test_diff.py`, `test_providers.py`.
5. **Tests missing:** CLI tests for new commands.
6. **Risk:** **Low** — thin wrappers over existing logic.
7. **Required plan edit:** None.
8. **Recommended implementation PR:** Single PR adding 4 CLI commands.
9. **Acceptance criteria:** CLI commands expose existing daemon functionality.
10. **Remain P0?** **Yes** — quick parity wins.

### P0-10: Port Canonical Shell Basics

1. **Current implementation evidence:** `arc-extension` has 3 sections + 8 components. `theia-extensions/arc-core` has richer UI (518-line widget, 732-line service impl, status bar, commands, welcome).
2. **Missing implementation:** No porting started. All richer UI in `theia-extensions/*`.
3. **Docs/readme mismatch:** Plan accurately describes gap.
4. **Tests present:** 239 tests in `arc-extension`.
5. **Tests missing:** Integration tests for ported components.
6. **Risk:** **High** — largest P0 item, requires protocol alignment.
7. **Required plan edit:** **Split into sub-items**: P0-10a (service layer), P0-10b (readiness + runs), P0-10c (workflows + health).
8. **Recommended implementation PR:** 6 incremental PRs, each building independently.
9. **Acceptance criteria:** `arc-extension` contains dashboard, readiness, runs panel, launcher, status bar, commands.
10. **Remain P0?** **Yes, but split** — too large for single item.

### P0-11: Document Current Isolation Honestly

1. **Current implementation evidence:** README honest about loopback/single-user. ADR-006 comprehensive. Plan has isolation table.
2. **Missing implementation:** No dedicated security docs page. Broken `SECURITY_AUDIT_REPORT.md` link.
3. **Docs/readme mismatch:** README references non-existent file.
4. **Tests present:** Profile enforcement, security, adapter security tests.
5. **Tests missing:** Docs test verifying isolation claims match implementation.
6. **Risk:** **Low** — docs-only.
7. **Required plan edit:** Add explicit deliverable.
8. **Recommended implementation PR:** Create security docs, fix broken link, add "What Is NOT Implemented" section.
9. **Acceptance criteria:** Docs explicitly state subprocess/trusted-local posture. No Docker/Firecracker implications.
10. **Remain P0?** **Yes** — quick fix.

### P0 Summary Matrix

| Item | Status | Risk | Remain P0? | Action |
|------|--------|------|------------|--------|
| 1. Canonical extension wiring | Declared but NOT wired | High | Yes | Wire into browser app |
| 2. Inventory secondary extensions | Inventory done, no action | Medium | Yes | Add deprecation markers |
| 3. Register AG2 | Code exists, not registered | Low | Yes | One-line registration |
| 4. Fix OpenAI export target | Hardcoded TestAgent | Medium | Yes | Add env var, remove hardcoded |
| 5. Mark LM Arena stub | **REFRAME**: Live mode EXISTS | Low | Yes (reframed) | Fix audit docs |
| 6. Normalize capability reports | Basic schema exists | Medium | Yes | Add adoption fields |
| 7. Update docs index | Broken links | Low | Yes | Fix links, create missing docs |
| 8. CLI truth commands | 7 commands missing | Low | Yes | Add commands |
| 9. CLI daemon-parity commands | 4 commands missing | Low | Yes | Add commands |
| 10. Port canonical shell | No porting started | High | Yes (split) | Split into 3 sub-items |
| 11. Document isolation honestly | Mostly honest, broken link | Low | Yes | Create security docs |

---

## 4. P1 Audit: SwarmGraph Adoption Foundation

### P1-1: Define Adoption Protocol

1. **Current implementation evidence:** NONE. `adoption/` directory does not exist.
2. **Missing implementation:** Entire package. All Pydantic models (`AdoptionSpec`, `WorkerTask`, `Vote`, `ConsensusResult`, `HitlRequest`, `AuditRef`).
3. **Required schemas/contracts:** All 6 models + registry interface.
4. **Required daemon endpoints:** None at protocol stage.
5. **Required CLI commands:** None at protocol stage.
6. **Required IDE changes:** None at protocol stage.
7. **Required tests:** Protocol unit tests.
8. **Risks:** Interface coupling with SwarmGraph (too tight or too loose). Adoption runtime ID syntax unresolved.
9. **Minimal path:** `adoption/__init__.py` + `adoption/protocol.py` with Pydantic models. ~100 lines.
10. **Plan edits:** None — greenfield, plan accurate.

### P1-2: Add Adoption Capability Fields

1. **Current implementation evidence:** `RuntimeCapabilities` (16 booleans), `CapabilityReport` (10 fields). No adoption fields.
2. **Missing implementation:** `can_adopt`, `adoption_modes`, `audit_level`, `hitl_level`.
3. **Required schemas/contracts:** 4 new fields + TypeScript mirror.
4. **Required daemon endpoints:** None — already exposed via `/api/runtimes/capabilities`.
5. **Required CLI commands:** None — `arc runtimes --capabilities` auto-includes.
6. **Required IDE changes:** Runtime selection UI (P3).
7. **Required tests:** Python unit + TS contract.
8. **Risks:** Backward compatibility. Schema versioning needed.
9. **Minimal path:** Add 4 fields, default to `False`/empty. One test file.
10. **Plan edits:** Refine field names to match existing `can_*` pattern.

### P1-3: Add Adoption Runner Skeleton

1. **Current implementation evidence:** Router exists (`runtime_router.py`, 175 lines). No adoption registry or mode resolution.
2. **Missing implementation:** Adoption mode parsing (`langgraph+swarmgraph`), adoption registry, `AdoptionRunner` skeleton.
3. **Required schemas/contracts:** Adoption mode ID syntax.
4. **Required daemon endpoints:** None at skeleton stage.
5. **Required CLI commands:** None at skeleton stage.
6. **Required IDE changes:** None at skeleton stage.
7. **Required tests:** Router tests for adoption mode parsing → "not runnable" with doctor action.
8. **Risks:** Mode syntax bikeshed (`+` vs `:` vs `/`).
9. **Minimal path:** `resolve_adoption()` in router, empty registry, returns not-runnable. ~40 lines.
10. **Plan edits:** None.

### P1-4: Map ARC Traces to SwarmGraph Audit Refs

1. **Current implementation evidence:** SHA-256 chain (`audit/chain.py`, 69 lines). `RunRecord` has `metadata: dict`. Vendored SwarmGraph has HMAC audit (474 lines).
2. **Missing implementation:** `audit_path` field in `RunRecord`. No wiring to SwarmGraph HMAC.
3. **Required schemas/contracts:** `audit_path` top-level field (not buried in metadata). `AuditRef` model.
4. **Required daemon endpoints:** None at mapping stage.
5. **Required CLI commands:** None at mapping stage.
6. **Required IDE changes:** None at mapping stage.
7. **Required tests:** Unit test: run → audit chain entry → `audit_path` ref.
8. **Risks:** HMAC key management (P2-P4). SHA-256 vs HMAC coexistence.
9. **Minimal path:** Add `audit_path` to `RunRecord`. Write chain entry on completion.
10. **Plan edits:** Promote `audit_path` to top-level field per ADR-002.

### P1-5: Replace Combo Semantics

1. **Current implementation evidence:** `ComboRuntimeAdapter` exists (`runtime_router.py:42-102`). Sequential execution.
2. **Missing implementation:** No explicit distinction from adoption in docs/API.
3. **Required schemas/contracts:** `mode: Literal["explicit", "auto", "sequence"]` field.
4. **Required daemon endpoints:** None.
5. **Required CLI commands:** None.
6. **Required IDE changes:** None.
7. **Required tests:** Router tests verifying combo ≠ adoption.
8. **Risks:** Breaking change for comma-separated runtime syntax.
9. **Minimal path:** Add `mode` field + docstring. ~5 lines.
10. **Plan edits:** Keep as `sequence` with clear docs, don't remove.

### P1-6: Define HITL Event Contract — PREMATURE

1. **Current implementation evidence:** Vendored SwarmGraph has extensive HITL (`approval.py`, `stream_hitl_*` state fields, `StreamingHITLInterrupt`). AG-UI protocol has NO HITL events. ARC protocol has NO HITL.
2. **Missing implementation:** Everything — event types, payloads, daemon endpoints, persistence, TypeScript types.
3. **Required schemas/contracts:** 4 HITL event types + Pydantic payloads.
4. **Required daemon endpoints:** `POST /api/runs/{id}/hitl/respond`, `GET /api/runs/{id}/hitl/pending`.
5. **Required CLI commands:** None at contract stage.
6. **Required IDE changes:** None at contract stage.
7. **Required tests:** Contract serialization tests.
8. **Risks:** **HITL events are premature before persistence exists.** Single-use tokens need secure generation. Resume semantics unclear without `JobSupervisor`.
9. **Minimal path:** Add 4 event types to AG-UI protocol. Define payloads. No wiring.
10. **Plan edits:** **Move to P2.** HITL requires `JobSupervisor` (P1-8) + persistence infrastructure. Define event types in ADR-004 now (additive), defer implementation.

### P1-7: Add Run Lifecycle CLI

1. **Current implementation evidence:** `runs_app` exists with `runs` (list), `runs prune`, `runs get`, `runs trace`. SSE endpoint exists (replay only).
2. **Missing implementation:** `arc runs status`, `arc runs cancel`, `arc runs delete`, `arc runs stream`, `arc runs tail --follow`, `arc runs export`. Daemon endpoints: `POST /api/runs/{id}/cancel`, `DELETE /api/runs/{id}`.
3. **Required schemas/contracts:** None new.
4. **Required daemon endpoints:** Cancel, delete, status, live SSE broker.
5. **Required CLI commands:** 6 new commands.
6. **Required IDE changes:** None directly.
7. **Required tests:** CLI integration tests. Cancel test with fake running process.
8. **Risks:** Cancellation unreliable without `JobSupervisor`. `stream`/`tail` need live event broker.
9. **Minimal path:** **Split**: `status/delete/export` first (no live infra). `cancel/stream/tail` after `JobSupervisor` + `EventBroker`.
10. **Plan edits:** Split into two sub-items with different dependencies.

### P1-8: Add Live Stream Architecture — CRITICAL INFRASTRUCTURE

1. **Current implementation evidence:** SSE replay exists (`routes.py:352-381`). `append_event()` exists. `JsonlTraceWriter` exists. No `EventBroker`, no `JobSupervisor`, no live subscription.
2. **Missing implementation:** `EventBroker` class, `JobSupervisor` class, active SSE endpoint, subscription/reconnection, `RUNNING` status persistence.
3. **Required schemas/contracts:** `EventBroker` + `JobSupervisor` per ADR-002. `RunRecord` supervisor fields.
4. **Required daemon endpoints:** Background `POST /api/runs/start`, live `GET /api/runs/{id}/events`, `POST /api/runs/{id}/cancel`.
5. **Required CLI commands:** `arc runs stream`, `arc runs tail --follow` (depends on this).
6. **Required IDE changes:** Event stream component handles live vs replay.
7. **Required tests:** Streaming fake-run, reconnect, orphan recovery, cancel.
8. **Risks:** Race conditions, reconnection semantics, memory leaks from unbounded queues.
9. **Minimal path:** EventBroker (~40 lines) → JobSupervisor (~80 lines) → modify start_run route → modify SSE route → add cancel endpoint → integration test.
10. **Plan edits:** **Move earlier in P1.** This is foundational infrastructure that enables items 6 (HITL), 7 (cancel/stream), 9 (IDE live stream), 10 (isolation). Should be item #4 in P1 ordering.

### P1-9: Port Run Visualization IDE

1. **Current implementation evidence:** `arc-extension` has 3 sections + 8 components. `theia-extensions/` has workflows graph (238 lines), event stream (973 lines), run timeline (712 lines), run diff (142 lines), schema inspector (162 lines), health monitor (150 lines).
2. **Missing implementation:** Nothing ported to canonical extension.
3. **Required schemas/contracts:** None new.
4. **Required daemon endpoints:** Live SSE (P1-8).
5. **Required CLI commands:** None.
6. **Required IDE changes:** Port 6 widgets into `arc-extension/src/browser/components/`.
7. **Required tests:** UI contract tests, browser smoke.
8. **Risks:** Protocol mismatch, merge conflicts, duplicate cleanup.
9. **Minimal path:** Port in priority order: workflows graph → event stream → run timeline. Each as new component.
10. **Plan edits:** **Split into sub-items** with priority ordering. Too large for single item.

### P1-10: Add Isolation Provider Interface

1. **Current implementation evidence:** `isolation/` does NOT exist. Subprocess env allowlist exists in `workflow-executor.ts`. Security profiles exist. No `IsolationProvider` interface.
2. **Missing implementation:** Entire package. Provider interface. `none`/`subprocess` implementations. CLI commands.
3. **Required schemas/contracts:** `IsolationProvider` protocol, `IsolationProfile`, `IsolationStatus`.
4. **Required daemon endpoints:** `GET /api/isolation/status`, `GET /api/isolation/providers`, `PUT /api/isolation/set`.
5. **Required CLI commands:** `arc isolation status/doctor/list/set`.
6. **Required IDE changes:** Isolation settings in `arc-extension`.
7. **Required tests:** Provider interface unit tests, CLI tests.
8. **Risks:** Must not imply Docker/Firecracker implemented.
9. **Minimal path:** Create `isolation/` package, implement `NoneProvider` + `SubprocessProvider`, add CLI, wire routes.
10. **Plan edits:** None — accurately scoped to `none`/`subprocess`.

### P1-11: Add Local Prompt Optimizer Foundation

1. **Current implementation evidence:** `prompt_optimizer/` does NOT exist. `--prompt` flag exists. No optimizer anywhere.
2. **Missing implementation:** Entire package. Local template optimizer. CLI commands. Protocol types.
3. **Required schemas/contracts:** `PromptOptimizerMode`, `PromptOptimizationResult`, `PromptDiff`.
4. **Required daemon endpoints:** `POST /api/prompt/optimize`, `POST /api/prompt/diff`.
5. **Required CLI commands:** `arc prompt optimize`, `arc prompt optimize --file`, `arc prompt diff`.
6. **Required IDE changes:** Toggle near run input (P3).
7. **Required tests:** Unit tests with vague prompts. No network tests.
8. **Risks:** Intent preservation hard to test. Template approach may be rigid.
9. **Minimal path:** Rule-based template cleanup. CLI command. 5-10 test cases.
10. **Plan edits:** None — accurately scoped to local mode. Deprioritize to last in P1.

### P1 Strategic Assessment

**Is P1 too broad?** Yes. 11 items spanning protocol design, routing infrastructure, audit/tracing, run lifecycle, IDE porting, security, and features. **Split into P1a and P1b:**

**P1a (Infrastructure Foundation):**
1. Capability fields (P1-2) — quick win
2. Combo semantics cleanup (P1-5) — 5-line change
3. Audit refs (P1-4) — lightweight
4. Live stream architecture (P1-8) — **critical infrastructure**
5. Run lifecycle CLI (P1-7) — depends on P1-8
6. Isolation provider interface (P1-10) — depends on P1-8

**P1b (Adoption Layer + IDE):**
7. Adoption protocol (P1-1) — now has infrastructure
8. Adoption runner skeleton (P1-3) — depends on P1-1, P1-8
9. IDE porting (P1-9) — depends on P1-8 for live stream
10. Prompt optimizer (P1-11) — independent, last
11. HITL contract (P1-6) — **move to P2** (premature)

**Should run lifecycle/live stream happen before adoption protocol?** Yes, absolutely. Adoption protocol is a design exercise without infrastructure to execute it.

**Does ADR-004 cover all needed P1 events?** No. Missing HITL events (add to ADR-004 registry, additive change). Other events can be added when their items are implemented.

**Are HITL events premature before persistence?** Yes. Move HITL contract to P2.

**Is local prompt optimizer properly scoped?** Yes, mostly. Deprioritize to last in P1.

---

## 5. P2 Audit: Runtime + SwarmGraph Integrations

### Cross-Cutting Finding

**No `adoption/` directory exists.** The entire SwarmGraph adoption layer is unimplemented. This is the core gap for every P2 item.

### P2-1: LangGraph + SwarmGraph — KEEP as #1

1. **Existing standalone adapter:** 541-line adapter with AST scanning, real streaming (`astream_events v2`), runner (43 lines), mapping (38 lines), loader (27 lines). Registered. `can_run=False` by default, `True` when `ARC_LANGGRAPH_EXPORT` set.
2. **Existing SwarmGraph adoption evidence:** None.
3. **Runtime API assumptions:** `langgraph.json` config, compiled graph with `astream_events(v2)`, `ARC_LANGGRAPH_EXPORT=module:function`.
4. **Required adapter changes:** `LangGraphAdoptionRunner` accepting `WorkerTask`, converting graph invocation to worker callable.
5. **Required SwarmGraph worker mapping:** LangGraph node → worker role. LangGraph state → SwarmGraph `AgentState`. Conditional edges → queen decomposition.
6. **Required event mapping:** Already mapped to AG-UI; need AG-UI → SwarmGraph bridge.
7. **Required audit/HITL/replay:** LangGraph checkpoints → audit refs. Interrupt/resume → HITL.
8. **Test strategy (fake):** Mock `astream_events`, verify adoption runner flow.
9. **Test strategy (real):** Minimal `langgraph.json` ReAct graph, STUB backend.
10. **Priority:** **KEEP as #1** — most complete adapter, closest to SwarmGraph model.

### P2-2: CrewAI + SwarmGraph — MOVE to #3

1. **Existing standalone adapter:** 289-line adapter, runner (52 lines), listener (72 lines), mapping (60 lines). Registered. `requires_paid_calls=True`.
2. **Existing SwarmGraph adoption evidence:** None.
3. **Runtime API assumptions:** `ARC_CREWAI_EXPORT=module:attribute`, `crewai_event_bus`, `kickoff_async()`.
4. **Required adapter changes:** `CrewAIAdoptionRunner`, crew output → worker proposal.
5. **Required SwarmGraph worker mapping:** Crew → worker. Agent → sub-worker. Task → queen decomposition.
6. **Required event mapping:** Already has AG-UI mapping.
7. **Required audit/HITL/replay:** Crew output → signed worker result. HITL between tasks.
8. **Test strategy (fake):** Mock `crewai_event_bus`, fake crew object.
9. **Test strategy (real):** Minimal crew with 2 agents, 1 task.
10. **Priority:** **MOVE to #3** — side-effect/cancellation risks, less clean than AG2 for adoption mapping.

### P2-3: AG2 + SwarmGraph — MOVE to #2, CREATE adapter first

1. **Existing standalone adapter:** Runner (63 lines), mapping (37 lines), detection (23 lines). **NOT registered in `registry.py`**. No `AG2Adapter` class.
2. **Existing SwarmGraph adoption evidence:** None.
3. **Runtime API assumptions:** `a_run_group_chat(messages=[...])`, `run_stream(task=message)`.
4. **Required adapter changes:** **Create `AG2Adapter` class first** (P0 item). Register in registry. Then `AG2AdoptionRunner`.
5. **Required SwarmGraph worker mapping:** Group chat → worker. Each speaker → sub-worker. `speaker.changed` → queen routing.
6. **Required event mapping:** Already has AG-UI mapping.
7. **Required audit/HITL/replay:** Group chat messages → audit records. Speaker transitions → HITL points.
8. **Test strategy (fake):** Mock `a_run_group_chat`, fake team with canned transitions.
9. **Test strategy (real):** Minimal AG2 group chat with 2 agents.
10. **Priority:** **MOVE to #2** — group chat maps most naturally to SwarmGraph consensus. But P0 registration must happen first.

### P2-4: OpenAI Agents + SwarmGraph — KEEP as #4, fix standalone first

1. **Existing standalone adapter:** 333-line adapter, streaming (88 lines), mapping (46 lines). Registered. **CRITICAL BUG:** hardcoded `TestAgent` (P0 item).
2. **Existing SwarmGraph adoption evidence:** None.
3. **Runtime API assumptions:** OpenAI Agents SDK: `Agent`, `Runner`, `RunHooks`.
4. **Required adapter changes:** Fix standalone first (P0). Then `OpenAIAgentsAdoptionRunner`.
5. **Required SwarmGraph worker mapping:** Agent → worker. Handoff → queen-directed routing.
6. **Required event mapping:** Streaming bridge already exists.
7. **Required audit/HITL/replay:** SDK hooks provide good audit surface.
8. **Test strategy (fake):** Mock `Runner.run()` and `RunHooks`.
9. **Test strategy (real):** Requires `OPENAI_API_KEY`.
10. **Priority:** **KEEP as #4** — but standalone must be fixed first. SDK volatile.

### P2-5: LlamaIndex + SwarmGraph — KEEP as #5, standalone must be built first

1. **Existing standalone adapter:** 38-line **minimal stub**. Detection only. No runner, no mapping, no `run_workflow`.
2. **Existing SwarmGraph adoption evidence:** None.
3. **Runtime API assumptions:** Not implemented.
4. **Required adapter changes:** Implement standalone run first. Then adoption wrapper.
5. **Required SwarmGraph worker mapping:** Workflows → workers. Query engines → evidence workers.
6. **Required event mapping:** No existing mapping. Need to identify LlamaIndex callback system.
7. **Required audit/HITL/replay:** Workflow checkpoints → audit records.
8. **Test strategy (fake):** Mock workflow execution.
9. **Test strategy (real):** Minimal RAG workflow. Significant API knowledge needed.
10. **Priority:** **KEEP as #5** — but entire standalone adapter needs building first.

### P2-6: Semantic Kernel + SwarmGraph — DEFER to P3+

1. **Existing standalone adapter:** **NONE.** Zero files, zero references.
2. **Existing SwarmGraph adoption evidence:** None.
3. **Priority:** **DEFER to P3+** — zero code, enterprise focus, SDK drift risk.

### P2-7: Haystack + SwarmGraph — DEFER to P3+

1. **Existing standalone adapter:** **NONE.** Zero files, zero references.
2. **Existing SwarmGraph adoption evidence:** None.
3. **Priority:** **DEFER to P3+** — zero code, pipeline-only, overlaps with LlamaIndex.

### P2-8: DSPy/PydanticAI Typed Workers — DEFER to P4+

1. **Existing standalone adapter:** **NONE.** Zero files, zero references.
2. **Existing SwarmGraph adoption evidence:** None.
3. **Priority:** **DEFER to P4+** — zero code, selective typed-worker pattern, lower product priority.

### P2-9: SwarmGraph Native Adoption Runner — CRITICAL P1 PREREQUISITE

1. **Existing standalone adapter:** Deprecated adapter (570 lines, CLI subprocess), runner (98 lines, STUB/LOCAL/GATEWAY), local executor (43 lines), gateway client (48 lines), mapping (54 lines). Vendored runtime has full queen/worker/consensus/HITL.
2. **Existing SwarmGraph adoption evidence:** Partial — runner exists but runs SwarmGraph as standalone, not as adoption layer.
3. **Required adapter changes:** **Import SwarmGraph as library** instead of only CLI subprocess. Expose queen/worker/consensus APIs. Keep CLI fallback.
4. **Priority:** **KEEP as critical P1 prerequisite** — foundation for ALL adoption integrations.

### P2-10: Add Audit/Replay/HITL CLI

1. **Existing evidence:** SHA-256 chain exists. SwarmGraph HMAC exists (vendored). ADR-005 written. No CLI commands. No daemon endpoints.
2. **Required:** CLI commands, daemon endpoints, HITL persistence, HMAC key management, replay API.
3. **Priority:** **KEEP as P2** — depends on P1 audit refs. ADR-005 ready for implementation.

### P2-11: Add High-Assurance IDE Views

1. **Existing evidence:** Audit widget is stub (empty array). No HITL UI. No replay UI.
2. **Required:** Audit chain viewer, HITL inbox, replay stepper. All backed by real endpoints.
3. **Priority:** **KEEP as P2-P3** — must not build before backend exists.

### P2 Adoption Priority (Evidence-Based)

| Plan Order | Evidence-Based Order | Change | Rationale |
|---|---|---|---|
| 1. LangGraph | 1. LangGraph | Same | Most complete adapter, closest to SG |
| 2. CrewAI | 2. AG2 | **Swap** | Group chat maps more naturally to workers |
| 3. AG2 | 3. CrewAI | **Swap** | Side-effect/cancellation risks |
| 4. OpenAI Agents | 4. OpenAI Agents | Same | But standalone must be fixed first |
| 5. LlamaIndex | 5. LlamaIndex | Same | But standalone must be built first |
| 6. Semantic Kernel | 6. Semantic Kernel | Defer P3+ | Zero code |
| 7. Haystack | 7. Haystack | Defer P3+ | Zero code |
| 8. DSPy/PydanticAI | 8. DSPy/PydanticAI | Defer P4+ | Zero code |

### Standalone Fixes Required Before Adoption

| Runtime | Standalone Issue | P0/P1 Fix |
|---|---|---|
| OpenAI Agents | Hardcoded TestAgent | P0: implement `ARC_OPENAI_AGENTS_EXPORT` |
| AG2 | No adapter class, not registered | P0: create `AG2Adapter`, register |
| LlamaIndex | No `run_workflow`, no runner | P1: implement standalone run path |
| SwarmGraph | CLI subprocess only, not library | P1: import vendored SG as library |
| LangGraph | Standalone complete | None |
| CrewAI | Standalone complete | None |

---

## 6. P3 Audit: Theia UX Productization

### P3-1: Runtime Selection UI — PORT

1. **Canonical:** NONE.
2. **Duplicate:** `arc-runs/arc-run-timeline-widget.tsx:281-334` (full picker + combo + readiness), `arc-adapters/arc-adapters-widget.tsx:72-138` (readiness cards).
3. **Action:** Port → `RuntimeSelectionSection.tsx`.
4. **Backend dependency:** `listRuntimeCapabilities()`.
5. **Protocol dependency:** `RuntimeCapabilityReport` — NOT in arc-extension protocol.
6. **UI risks:** Combo selection duplicated across 3 widgets.
7. **Tests:** Runtime picker, combo mode, disabled states.
8. **Minimal path:** Single dropdown + readiness indicator.
9. **Plan edits:** Add types to arc-protocol, create component.

### P3-2: Adapter Config UI — PORT

1. **Canonical:** NONE.
2. **Duplicate:** `arc-adapters/arc-adapters-widget.tsx` (240 lines) — readiness cards, provider settings, doctor actions.
3. **Action:** Port → `AdapterConfigSection.tsx`.
4. **Backend dependency:** `listRuntimeCapabilities()`, `getProviderStatus()`.
5. **Protocol dependency:** `ProviderStatus`, `DoctorAction`.
6. **UI risks:** Custom inline dialog instead of Theia `ConfirmDialog`.
7. **Tests:** Adapter cards, provider status, doctor flow.
8. **Minimal path:** Collapsible section + Theia ConfirmDialog.
9. **Plan edits:** Replace inline dialog with Theia dialog.

### P3-3: Run Launch UX — REWRITE

1. **Canonical:** `arc-widget.tsx:239-338` — basic execution, no runtime selection.
2. **Duplicate:** `arc-runs/arc-run-timeline-widget.tsx:281-479` — full controls with runtime picker, combo, prompt, paid calls.
3. **Action:** Rewrite — unify into single run launch UX.
4. **Backend dependency:** Two incompatible execution paths (`executeWorkflow` vs `startRun`).
5. **Protocol dependency:** `ExecutionOptions` vs `StartRunRequest` — **incompatible**.
6. **UI risks:** Two execution paths, hardcoded workflow ID, scattered state.
7. **Tests:** Simple execution, runtime selection, combo mode, paid calls.
8. **Minimal path:** Single prompt + optional runtime dropdown.
9. **Plan edits:** Extend `ExecutionOptions` with `runtime`, unify methods.

### P3-4: Live Event Stream — PORT

1. **Canonical:** NONE. `TraceViewerSection` shows historical traces only.
2. **Duplicate:** `arc-event-stream/arc-event-stream-widget.tsx` (973 lines) — production-quality AG-UI renderer with react-window, SSE reconnection, 33 event types, auto-scroll, filter.
3. **Action:** Port — most complete UI in codebase.
4. **Backend dependency:** Python daemon SSE endpoint — NOT exposed through Theia RPC.
5. **Protocol dependency:** `RunEvent` vs `TraceEvent` — **incompatible field names**.
6. **UI risks:** `react-window` not in arc-extension deps. 33 AG-UI icons need mapping.
7. **Tests:** SSE connection, event rendering, auto-scroll, filter.
8. **Minimal path:** Live streaming toggle + `ResilientSSEClient` + event mapping.
9. **Plan edits:** Unify event types, add react-window dependency.

### P3-5: Audit Viewer — ARCHIVE (stub)

1. **Canonical:** NONE.
2. **Duplicate:** `arc-audit/arc-audit-widget.tsx` (59 lines) — **100% stub**, empty array, "Not implemented" badge.
3. **Action:** Delete. No backend exists.

### P3-6: HITL Approval Dialog — ARCHIVE (doesn't exist)

1. **Canonical:** NONE.
2. **Duplicate:** NONE.
3. **Action:** No action. Future roadmap.

### P3-7: Provider/Cost Controls — PORT

1. **Canonical:** `costAllowed` field only, no UI.
2. **Duplicate:** `cost-warning-service.ts` (43 lines), paid calls checkbox in arc-runs, provider settings in arc-adapters.
3. **Action:** Port → `ProviderCostSection.tsx`.
4. **Backend dependency:** `getProviderStatus()`, `listProviders()`.
5. **Protocol dependency:** `ProviderStatus`, `ProviderDefinition`, `ProviderRoutingPolicy`.
6. **UI risks:** Cost warning not wired to actual run flow.
7. **Tests:** Cost warning dialog, provider status, paid calls checkbox.
8. **Minimal path:** Single checkbox + provider status tooltip.
9. **Plan edits:** Port cost warning service, add provider types.

### P3-8: Product Config CLI — ARCHIVE (backend feature)

Not a Theia UX item. Belongs in Python CLI layer.

### P3-9: Product Setup IDE — PORT (merge welcome widgets)

1. **Canonical:** NONE.
2. **Duplicate:** `arc-product/arc-getting-started-widget.tsx` (231 lines, branded welcome), `arc-core/arc-welcome-widget.tsx` (176 lines, onboarding).
3. **Action:** Port — consolidate into single welcome experience.
4. **UI risks:** Two duplicate welcome widgets.
5. **Tests:** Welcome page rendering, action buttons.
6. **Minimal path:** Keep simpler `arc-welcome-widget.tsx`, port to arc-extension.

### P3-10: Docker-compatible Isolation — ARCHIVE (infrastructure)

Not a Theia UX item. Backend infrastructure feature.

### P3-11: Prompt Optimizer IDE Toggle — ARCHIVE (doesn't exist)

Feature doesn't exist yet. Future roadmap.

### Theia Extension Salvage Matrix

| Extension | Current Contents | Real Value | Stub/Duplicate Risk | Action | Target Phase |
|---|---|---|---|---|---|
| `arc-core` | Service layer (732 lines), protocol (276 lines), SSE client, cost warning, commands, status bar, welcome widget | Foundation everything depends on | Main widget duplicates arc-widget. Protocol conflicts with arc-extension. | **Port** — merge protocol, service, utilities, commands | P3 |
| `arc-runs` | Timeline (712 lines), chat (327 lines), diff (142 lines) | Most feature-complete UI | Run diff bypasses Theia RPC. Chat duplicates execution section. | **Port** — timeline as advanced trace viewer | P3 |
| `arc-event-stream` | Event stream widget (973 lines), react-window, SSE reconnection, 33 event types | Production-quality event viewer | Uses `@arc/ag-ui` external dependency. Simpler SSE in arc-runs. | **Port** — extract event rendering + SSE logic | P3 |
| `arc-workflows` | SVG graph (238 lines), DAG layout, node coloring | Functional topology visualization | No duplicate in arc-extension. | **Port** — advanced visualization | P3 (low priority) |
| `arc-schemas` | Schema inspector (162 lines) | Complete property table | Niche feature, daemon-dependent. | **Archive** | N/A |
| `arc-adapters` | Readiness cards (240 lines), provider settings, doctor actions | Production-quality adapter status | Readiness duplicated in arc-core main widget. | **Port** — merge into settings section | P3 |
| `arc-health` | Health monitor (150 lines), 5s polling | Simple daemon monitoring | Covered by status bar contribution. | **Archive** | N/A |
| `arc-context` | Context pack widget (114 lines) | Working context pack UI | Daemon-dependent, niche. | **Archive** | N/A |
| `arc-settings` | Preference schema (81 lines), 14 preferences | Comprehensive schema | 4 overlapping UI prefs with arc-core. | **Port** — merge preferences | P3 |
| `arc-audit` | Stub widget (59 lines), empty array | None | 100% stub. | **Delete** | N/A |
| `arc-arena` | Arena UI (520 lines), service (139 lines), protocol (78 lines) | Feature-complete LM Arena | Self-contained, stub fallback. | **Archive** (keep separate) | Post-P3 |
| `arc-product` | Branded welcome (231 lines) | Professional branding | Duplicates arc-core welcome widget. | **Archive** | N/A |

### Protocol Conflicts to Resolve

| Conflict | arc-extension | theia-extensions/arc-core | Resolution |
|---|---|---|---|
| Event type | `TraceEvent` (line 172-203) | `RunEvent` (line 167-173) | Unify to single type, prefer `RunEvent` naming |
| Execution result | `ExecutionResult` | `RunRecord` | Unify or create adapter layer |
| Field naming | `runId` (camelCase) | `run_id` (snake_case) | Standardize on one convention |
| Service path | `ArcService.executeWorkflow()` | `ArcFrontendService.startRun()` | Unify into single method |

---

## 7. P4 Audit: Audit, Replay, HITL, Security Hardening

### P4-1: SwarmGraph HMAC Audit Integration — MOVE to P2

1. **Current ARC:** SHA-256 hash chain (`audit/chain.py`, 69 lines). Unauthenticated — anyone can forge chain. All adapters report `can_audit=False`. IDE widget is stub.
2. **Current SwarmGraph (vendored):** Full HMAC-SHA256 audit (`swarm_shared/audit.py`, 474 lines). Production-grade with file locking, fsync, S3 backend. CLI verify command exists.
3. **Wiring gap:** ARC never imports `swarm_shared.audit`. HMAC secret never set. No `AuditService`. No `/api/audit/*` endpoints.
4. **Security risk:** **HIGH.** Unauthenticated SHA-256 chain is tamper-evident but forgeable.
5. **Required storage:** Parallel `.arc/audit/{run_id}.hmac.jsonl` or migrate to HMAC. Keychain key storage.
6. **Required work:** Daemon endpoints, CLI commands, IDE wiring, adapter env injection.
7. **Tests:** Tamper detection, integration, key management, UI contract.
8. **Phase recommendation:** **Move to P2.** HMAC is production-ready in vendored runtime. Wiring is thin adapter layer.
9. **Plan edit:** Split: P2 (HMAC wiring, verify endpoint, CLI) + P3 (key management, IDE viewer).

### P4-2: Replay API — SPLIT

1. **Current ARC:** SSE replay only. `can_replay=False` for all adapters. No replay CLI.
2. **Current SwarmGraph:** No explicit replay command.
3. **Wiring gap:** No replay spec, no deterministic replay, no `arc runs replay`.
4. **Security risk:** Low-Medium. Replay needs re-gating for paid runs.
5. **Phase recommendation:** Split: P2 (trace replay: re-stream stored events) + P3-P4 (deterministic runtime replay).
6. **Plan edit:** Split into two items.

### P4-3: HITL Persistence — KEEP as P2-P3

1. **Current ARC:** None.
2. **Current SwarmGraph:** Interactive HITL in CLI (single-use tokens, streaming HITL).
3. **Wiring gap:** ARC doesn't pass `--interactive` flag. No HITL surfacing to IDE. No persistence.
4. **Security risk:** Medium. HITL is a security control.
5. **Phase recommendation:** Correctly placed. P2 (protocol + CLI), P3 (IDE inbox), P4 (hardening).
6. **Plan edit:** None.

### P4-4: Safer Daemon Auth Default — MOVE to P2

1. **Current ARC:** Optional bearer token, auth OFF by default. Loopback only. Constant-time comparison correct.
2. **Wiring gap:** No auto-generated token. No Theia auto-injection.
3. **Security risk:** **Medium.** Any local process can call daemon without auth.
4. **Phase recommendation:** **Move to P2.** Straightforward change with high security value.
5. **Plan edit:** Rename to "Auto-generated daemon auth token". Generate on first start, Theia auto-reads.

### P4-5: Subprocess Isolation Hardening — MOVE partial to P2

1. **Current ARC:** Env allowlist exists for SwarmGraph adapter only. `RunProfile.env_allowlist` defined but never enforced. No resource limits. No network isolation.
2. **Wiring gap:** No unified subprocess wrapper. Other adapters may not filter env.
3. **Security risk:** **HIGH.** Env leakage to subprocesses can expose API keys.
4. **Phase recommendation:** Split: P2 (unified env allowlist for all adapters) + P3 (resource limits, network proxy) + P4 (advanced hardening).
5. **Plan edit:** Split into three sub-items.

### P4-6: Workspace Trust Model — MOVE to P1-P2

1. **Current ARC:** Path validation only. Zero trust code. No `TrustLevel`, no `.arc/trusted`, no trust CLI.
2. **Wiring gap:** ADR-006 fully designed but zero code implemented.
3. **Security risk:** **HIGH.** Any workspace executes with full user privileges. Fundamental gap.
4. **Phase recommendation:** **Move to P1-P2.** Foundational security. Trust resolution should be part of isolation provider interface.
5. **Plan edit:** P1 (trust resolver + enum + marker) + P2 (trust CLI + enforcement) + P3 (trust UI).

### P4-7: Firecracker microVM Provider — DEFER to P5/Future

1. **Current ARC:** None. Zero firecracker references in Python source.
2. **Current SwarmGraph:** None.
3. **Wiring gap:** Entire stack missing. Linux/KVM only. High ops burden.
4. **Phase recommendation:** **Defer to P5 or mark Future/Experimental.** Realistically 6+ months out.
5. **Plan edit:** Move to P5/Future. P4 DOD should not require Firecracker.

### P4-8: Eval/Observability CLI — SPLIT

1. **Current ARC:** Basic eval exists (`arc eval run`, `arc eval list`, golden traces, diff). SQLite store defined but NOT wired.
2. **Wiring gap:** No `save`/`delete`/`batch`/`report` commands. No `runs search`. No `doctor env/network/storage`. No `bug-report`.
3. **Phase recommendation:** Split: P2 (eval CLI completion) + P3 (SQLite wiring, `runs search`) + P4 (observability CLI).
4. **Plan edit:** Split into three sub-items.

### P4-9: SwarmGraph Insight IDE — KEEP as P4

1. **Current ARC:** None.
2. **Current SwarmGraph:** Consensus data + TUI dashboard in CLI.
3. **Wiring gap:** ARC doesn't capture consensus/voting events. No endpoints. No UI.
4. **Phase recommendation:** Correctly placed. Depends on P1-P2 adoption runs producing real data.
5. **Plan edit:** Add explicit dependency note.

### P4-10: Gated Prompt Optimizer Providers — KEEP split (P1 local + P4 provider)

1. **Current ARC:** None. Zero prompt optimizer code.
2. **Wiring gap:** Entire stack missing.
3. **Security risk:** **HIGH for provider modes.** Can leak sensitive prompts.
4. **Phase recommendation:** Correctly split. P1 (local optimizer) + P4 (provider modes with gates).
5. **Plan edit:** Add explicit gate checklist for provider modes.

### P4 Summary

| Item | Security Risk | Phase Rec | Move? |
|------|--------------|-----------|-------|
| 1. HMAC Audit | **HIGH** (unauthenticated chain) | P2 | **↑ Move up** |
| 2. Replay API | Low-Med | P2-P3 | Split |
| 3. HITL Persistence | Med | P2-P3 | Keep |
| 4. Daemon Auth | **Med** | P2 | **↑ Move up** |
| 5. Subprocess Isolation | **HIGH** (env leakage) | P2 | **↑ Move up** (partial) |
| 6. Workspace Trust | **HIGH** (no trust model) | P1-P2 | **↑ Move up** |
| 7. Firecracker | Low | P5/Future | **↓ Defer** |
| 8. Eval/Observability | Low | P2-P4 | Split |
| 9. SwarmGraph Insight | Low | P4 | Keep |
| 10. Prompt Optimizer | **HIGH** (provider modes) | P1+P4 | Keep (already split) |

---

## 8. P5 Audit: Release Readiness

### P5-1: Full CI Gate — MOSTLY DONE

1. **Current evidence:** 5 CI workflows. `arc-roadmap-gate.yml` most comprehensive (lint, typecheck, Python tests ≥60% coverage, pip-audit, PR hygiene).
2. **Missing:** No real-runtime smoke job. No nightly/offline split.
3. **v0.1 status:** **Blocker** (mostly done). `arc-roadmap-gate.yml` passing is sufficient.
4. **Plan edit:** Mark as mostly done. Real-runtime smoke is separate sub-item.

### P5-2: Real-Runtime Smoke Suite — POST-v0.1

1. **Current evidence:** Integration tests exist. E2E tests use stub backend. No real-provider CI job.
2. **Missing:** No opt-in marker for live tests. No minimal real smoke.
3. **v0.1 status:** **Post-v0.1.** Vendored SwarmGraph smoke nice-to-have.
4. **Plan edit:** Split into "vendored smoke" (v0.1) and "provider-backed smoke" (post-v0.1).

### P5-3: Electron Packaging — POST-v0.1

1. **Current evidence:** Electron scaffolding exists. Prebuilds, webpack, signing preflight.
2. **Missing:** **Critical**: `arc-extension` not wired into Electron app. Daemon bundling not implemented. ADR-008 still "Proposed".
3. **v0.1 status:** **Post-v0.1.** Not realistic for v0.1.
4. **Plan edit:** Move to P5-post-v0.1 or P6. v0.1 = browser app + CLI only.

### P5-4: Docs Freeze — v0.1 BLOCKER

1. **Current evidence:** `docs/archive/` clean. Active docs coherent. ADRs drafted.
2. **Missing:** No top-level `RELEASE_CHECKLIST.md`. No `scripts/check-docs-truth.sh`.
3. **v0.1 status:** **Blocker.** README must not overclaim.
4. **Plan edit:** Add explicit deliverable: `scripts/check-docs-truth.sh`.

### P5-5: Release Checklist — v0.1 BLOCKER

1. **Current evidence:** `docs/archive/RELEASE_CHECKLIST.md` well-structured. Version stale (0.6.0-alpha).
2. **Missing:** Not at top level. Version stale.
3. **v0.1 status:** **Blocker.** Promote and update.
4. **Plan edit:** Add as explicit P0 sub-task.

### P5-6: Arena CLI After Real Backend — POST-v0.1

Correctly deferred. Plan accurate.

### P5-7: Define Deploy/Plugin Architecture — POST-v0.1

Correctly deferred. Note: `scripts/deploy.sh` is stale (references non-existent `packages/arc-browser-app`). Delete it.

### P5-8: Signed/Reproducible Sandbox Images — POST-v0.1

Correctly deferred. Depends on P2-P4 isolation work.

### P5 v0.1 Blockers vs Post-Release

| Item | v0.1 Status | Rationale |
|------|-------------|-----------|
| Full CI gate | **Blocker** (mostly done) | `arc-roadmap-gate.yml` sufficient |
| Real-runtime smoke | Post-v0.1 | Stub CI acceptable for alpha |
| Electron packaging | Post-v0.1 | Not realistic for v0.1 |
| Docs freeze | **Blocker** | README must not overclaim |
| Release checklist | **Blocker** | Promote from archive, update version |
| Arena CLI | Post-v0.1 | Correctly deferred |
| Deploy/plugin | Post-v0.1 | Correctly deferred |
| Signed images | Post-v0.1 | Depends on P2-P4 |

**v0.1 release surface: Browser app + Python CLI/wheel. Electron is out of scope.**

---

## 9. Do Not Build Yet Review

All 13 items are **correctly deferred**. No changes needed.

| Feature | Prerequisite | Status |
|---------|-------------|--------|
| Plugin marketplace | P5 plugin architecture | Correctly deferred |
| Multi-tenant UI | Tenant model | Correctly deferred |
| Deployment CLI/UI | Deploy target defined | Correctly deferred |
| No-code workflow builder | Runtime/adoption stable | Correctly deferred |
| Cloud deployment | Beyond local mode | Correctly deferred |
| Multi-user daemon | Auth redesign | Correctly deferred |
| Browser-use agents | Workspace trust + browser sandbox | Correctly deferred |
| Firecracker as default | Docker mature + workspace trust | Correctly deferred |
| Prompt playground | Prompt versioning infra | Correctly deferred |
| Provider-backed prompt opt. by default | Local optimizer + gates | Correctly deferred |
| SwarmGraph consensus prompt opt. | Basic optimizer + adoption stable | Correctly deferred |
| Dataset management | Eval/golden trace infra | Correctly deferred |
| Annotation queues | HITL + eval workflows | Correctly deferred |

**New observation:** `scripts/deploy.sh` references non-existent `packages/arc-browser-app` and should be deleted.

---

## 10. First 10 PRs Review → Revised First 15 PRs

### Original PR Audit

| PR | Title | Order | Mergeable | Split? | Move? |
|----|-------|-------|-----------|--------|-------|
| 1 | Docs truth cleanup | Correct | Yes | No | Keep first |
| 2 | Canonical extension declaration | Correct | Yes | Split wiring | Keep second |
| 3 | Theia extension salvage inventory | Correct | Yes | No | Keep third |
| 4 | CLI discoverability commands | Correct | Yes | Split into 2 | Keep fourth |
| 5 | CLI daemon parity commands | Correct | Yes | Split into 2 | Keep fifth |
| 6 | Adapter capability schema cleanup | Correct | Yes | No | Keep sixth |
| 7 | Register AG2 | Correct | Yes | No | Could move earlier |
| 8 | OpenAI Agents export target | Correct | Yes | No | Keep eighth |
| 9 | Live stream architecture | **Too early** | Partial | **Yes (3 parts)** | **Move to PR 15** |
| 10 | Adoption protocol skeleton | Correct | Yes | No | Keep tenth |

### Revised First 15 PRs

| # | Title | Scope | Files | Tests | Depends On | Why Now |
|---|-------|-------|-------|-------|------------|---------|
| 1 | Docs truth cleanup | Remove fiction claims, fix Arena docs, add banned-claims script | `README.md`, `docs/RUNTIMES.md`, `docs/REALITY_AUDIT.md`, `scripts/check-docs-truth.sh` | Script exits 0 | None | Foundation for honest product |
| 2 | Promote release checklist | Move archived checklist to top level, update to v0.1.0-alpha | `docs/RELEASE_CHECKLIST.md` (new) | None | PR 1 | Defines "shippable" before building |
| 3 | Canonical extension + browser wiring | Document + wire `arc-extension` into browser app | `README.md`, `applications/browser/package.json`, `applications/electron/package.json` | `pnpm build` | None | Resolves dual-extension confusion |
| 4 | Theia extension salvage inventory | Port/archive/delete table per extension | `docs/EXTENSION_MIGRATION.md` (new) | None | PR 3 | Guides all UI porting |
| 5 | CLI: `arc version` + `arc health` | Minimal discoverability | `cli.py` | CLI JSON envelope tests | None | Users can inspect ARC |
| 6 | CLI: `arc status` + `arc doctor all` | Full diagnostics | `cli.py`, new doctor subcommands | CLI + daemon-offline tests | PR 5 | Completes discoverability |
| 7 | Register AG2 or explicitly hide | Add to registry or mark stub | `adapters/registry.py`, `README.md` | `arc runtimes` expected output | None | Resolves ambiguity |
| 8 | Adapter capability schema cleanup | Add `support_level`, `execution_modes`, `schema_version` | `protocol/capabilities.py`, each adapter | Python unit + TS contract | PR 7 | Required before adoption |
| 9 | OpenAI Agents export target | Replace hardcoded TestAgent | `adapters/openai_agents.py` | Fake SDK workspace test | PR 8 | Fixes partial implementation |
| 10 | CLI daemon parity: `arc runs diff` | Expose existing diff | `cli.py`, `evals/diff.py` | Temp trace diff test | None | Low-hanging fruit |
| 11 | CLI daemon parity: `arc providers diagnostics` + `proxy` | Expose existing helpers | `cli.py`, `providers.py` | Dry-run proxy test | PR 10 | Completes parity |
| 12 | Adoption protocol skeleton | Pydantic models for adoption | New `adoption/` package | Protocol unit tests | PR 8 | Foundation for P1 adoption |
| 13 | Adoption runner skeleton + router | Router resolves `langgraph+swarmgraph` (not-runnable) | `orchestration/runtime_router.py`, adoption registry | Router not-runnable tests | PR 12 | Makes adoption modes visible |
| 14 | Delete stale `scripts/deploy.sh` | Remove broken script | `scripts/deploy.sh` (delete) | None | None | Cleanup |
| 15 | Live stream: daemon event broker | Active event broker + SSE replay fallback | `web/routes.py`, `orchestration/events.py` | Streaming fake-run + reconnect | PR 12, ADR-002, ADR-004 | P1 foundation for live runs |

**Key changes from original:**
- Added PR 2 (release checklist promotion)
- Split PR 4 into PRs 5 + 6
- Split PR 5 into PRs 10 + 11
- Moved PR 9 (live stream) to PR 15, scoped to daemon broker only
- Added PR 14 (delete stale deploy.sh)

---

## 11. Open Questions Resolution

### Q1: Which widgets from `theia-extensions/*` to port first?

1. **Evidence:** E2E tests reference `run-timeline`, `event-stream`, `health-monitor` from `theia-extensions/*`. Browser app depends on all 12 extensions but not `arc-extension`.
2. **Recommended answer:** Port order: (1) arc-adapters (readiness), (2) arc-runs (timeline, tested in E2E), (3) arc-workflows (graph), (4) arc-event-stream (SSE), (5) arc-health (small). Archive: arc-audit, arc-arena, arc-product, arc-core.
3. **Confidence:** High.
4. **Owner approval:** Yes — product owner.
5. **Plan edit:** Add explicit port order numbers to migration table.

### Q2: SwarmGraph as vendored library or CLI only?

1. **Evidence:** Vendored in `runtimes/swarmgraph/packages/` (3 packages). ARC invokes via CLI subprocess only. Adoption layer needs in-process calls.
2. **Recommended answer:** **Hybrid**: CLI subprocess for standalone runs. In-process library import for adoption adapters. Resolve import path spike.
3. **Confidence:** Medium — needs packaging spike.
4. **Owner approval:** Yes — runtime owner.
5. **Plan edit:** Add P1 sub-task: "SwarmGraph import path spike."

### Q3: Where should HMAC audit keys live?

1. **Evidence:** ADR-005 proposes keychain + env fallback. Currently env var only. `keyring` not in dependencies.
2. **Recommended answer:** Follow ADR-005. Add `keyring` as optional dependency. Validate platform behavior before implementation.
3. **Confidence:** Medium — `keyring` platform behavior needs validation spike.
4. **Owner approval:** Yes — security owner.
5. **Plan edit:** Add P2 sub-task: "keyring platform validation spike."

### Q4: Canonical syntax for adoption runtime IDs?

1. **Evidence:** Current IDs: `swarmgraph`, `langgraph`, `crewai`, `lmarena`. No adoption IDs.
2. **Recommended answer:** `<runtime>+swarmgraph` syntax. `+` separator is unambiguous, URL-safe, readable.
3. **Confidence:** High.
4. **Owner approval:** Yes — protocol owner.
5. **Plan edit:** Add to P1 adoption protocol PR.

### Q5: Is LM Arena in scope for v0.1?

1. **Evidence:** Arena has stub-default + gated-live mode. All modes functional. No real provider calls tested.
2. **Recommended answer:** **No.** Exclude from v0.1. Mark as `stub-only` in capability report. Archive `arc-arena` extension.
3. **Confidence:** High.
4. **Owner approval:** Yes — product owner.
5. **Plan edit:** Add to P0 DoD: "Arena excluded from v0.1."

### Q6: Is multi-user daemon support a goal?

1. **Evidence:** Loopback-only, auth-off-by-default, single-user, workspace-local JSONL.
2. **Recommended answer:** **Not for v0.1.** Document as out of scope for P0-P5.
3. **Confidence:** High.
4. **Owner approval:** Yes — product/security owner.
5. **Plan edit:** Add explicit statement to IMPLEMENTATION_PLAN.md.

### New Questions Discovered

### Q7: Should `arc-extension` replace all `theia-extensions/*` in app dependencies?

1. **Evidence:** Browser/Electron apps depend on 12 `theia-extensions/*` but NOT `arc-extension`. E2E tests work with current setup.
2. **Recommended answer:** Wire `arc-extension` first (PR 3). Incrementally replace `theia-extensions/*` as ported. Both can coexist during transition.
3. **Confidence:** Medium.
4. **Owner approval:** Yes — maintainer.

### Q8: Is `scripts/deploy.sh` intentionally stale?

1. **Evidence:** References non-existent `packages/arc-browser-app`. Not used in CI. 27 lines.
2. **Recommended answer:** Delete it.
3. **Confidence:** High.
4. **Owner approval:** Low risk — cleanup PR.

### Q9: Should release checklist reference `docs/ADR.md` or `docs/adr/`?

1. **Evidence:** Archived checklist references `docs/ADR.md` which doesn't exist. ADRs are in `docs/adr/` (9 files).
2. **Recommended answer:** Update to reference `docs/adr/` directory.
3. **Confidence:** High.
4. **Owner approval:** Low risk — fix during checklist promotion.

---

## 12. Plan Edit Patch List

| Section | Current Problem | Exact Edit Needed | Priority |
|---------|----------------|-------------------|----------|
| P0-5 | Claims Arena is "100% stub" — live mode EXISTS | Reframe: "Document Arena honestly: stub-default with gated live mode". Fix `REALITY_AUDIT.md` fiction. | P0 |
| P0-10 | Too large for single item | Split into P0-10a (service layer), P0-10b (readiness + runs), P0-10c (workflows + health) | P0 |
| P1 overall | 11 items too broad | Split into P1a (infrastructure: items 2,4,5,7,8,10) and P1b (adoption+IDE: items 1,3,9,11) | P1 |
| P1-6 | HITL contract premature before persistence | Move HITL contract to P2. Add HITL event types to ADR-004 registry now (additive). | P1 |
| P1-7 | Groups commands with different dependencies | Split: `status/delete/export` (no live infra) vs `cancel/stream/tail` (needs JobSupervisor+EventBroker) | P1 |
| P1-8 | Live stream positioned too late | Move to item #4 in P1 ordering. Critical infrastructure for HITL, cancel, IDE live stream. | P1 |
| P1-9 | 6 UI components in single item | Split into sub-items with port priority ordering | P1 |
| P2 adoption order | CrewAI before AG2 | Swap: AG2 (#2) before CrewAI (#3). Group chat maps more naturally to workers. | P2 |
| P2-6,7,8 | SK/Haystack/DSPy in P2 with zero code | Defer all three to P3+ (SK, Haystack) and P4+ (DSPy/PydanticAI) | P2 |
| P4-1 | HMAC audit in P4 but vendored SG has production HMAC | Move to P2 (wiring) + P3 (key management, IDE). Unauthenticated SHA-256 chain is security gap. | P4→P2 |
| P4-2 | Replay API single item | Split: P2 (trace replay) + P3-P4 (deterministic runtime replay) | P4 |
| P4-4 | Daemon auth in P4 | Move to P2. Auto-generated token, Theia auto-injects. | P4→P2 |
| P4-5 | Subprocess isolation in P4 | Split: P2 (unified env allowlist) + P3 (resource limits) + P4 (advanced) | P4→P2 |
| P4-6 | Workspace trust in P4 | Move to P1 (trust resolver) + P2 (trust CLI + enforcement) + P3 (trust UI) | P4→P1 |
| P4-7 | Firecracker in P4 | Defer to P5/Future. Zero code, Linux-only, high ops, depends on entire isolation stack. | P4→P5 |
| P4-8 | Eval/observability single item | Split: P2 (eval CLI completion) + P3 (SQLite wiring) + P4 (observability CLI) | P4 |
| P5-3 | Electron packaging as v0.1 item | Move to P5-post-v0.1 or P6. v0.1 = browser app + CLI only. | P5 |
| P5-5 | Release checklist in archive | Promote to `docs/RELEASE_CHECKLIST.md`, update version to v0.1.0-alpha | P0 |
| Overall | No v0.1 scope definition | Add: "v0.1 release surface: Browser app + Python CLI/wheel. Electron out of scope." | P0 |
| Overall | No multi-user scope statement | Add: "ARC Studio v0.1 is single-user, loopback-only. Multi-user daemon out of scope for P0-P5." | P0 |
| Overall | `scripts/deploy.sh` stale | Delete `scripts/deploy.sh` (references non-existent path) | P0 |

---

## 13. Final Verdict

### 1. Is the current plan executable as-is?

**No, but close.** The plan correctly identifies all gaps, phases, and dependencies. The ADR review gate provides guardrails. But phase boundaries need adjustment before implementation:
- P1 is too broad (11 items) and misordered (live stream infrastructure should come before adoption protocol)
- P4 contains 4 security items that should be in P1-P2 (workspace trust, HMAC audit, daemon auth, env allowlist)
- P2 adoption priority should be reordered based on code evidence (AG2 before CrewAI)
- Firecracker should be deferred to P5/Future

### 2. Which items must be edited before implementation?

1. **Split P1** into P1a (infrastructure) and P1b (adoption + IDE)
2. **Move 4 security items from P4 to P1-P2** (workspace trust, HMAC audit, daemon auth, env allowlist)
3. **Defer Firecracker to P5/Future**
4. **Reorder P2 adoption** (AG2 ↑, CrewAI ↓, defer SK/Haystack/DSPy)
5. **Fix Arena documentation** (live mode exists, audit docs contain fiction)
6. **Split P0-10** (canonical shell porting) into 3 sub-items
7. **Split P1-7** (run lifecycle CLI) into 2 sub-items
8. **Move P1-8** (live stream) earlier in P1 ordering
9. **Move P1-6** (HITL contract) to P2
10. **Promote release checklist** from archive to top level
11. **Define v0.1 scope** (browser app + CLI, not Electron)
12. **Delete stale `scripts/deploy.sh`**

### 3. Which items are approved as-is?

- P0 items 1-4, 6-9, 11 (with P0-5 reframed, P0-10 split)
- P1 items 1-5, 10-11 (with ordering changes and splits)
- P2 items 1, 5, 9-11 (with priority reordering)
- P3 items (with salvage matrix guidance)
- P4 items 3, 9-10 (with splits)
- P5 items 1, 4, 6-8 (with Electron deferred)
- All "Do Not Build Yet" items (correctly deferred)

### 4. Which items should be deferred?

- **Firecracker** (P4 → P5/Future) — zero code, Linux-only, high ops burden
- **Semantic Kernel** (P2 → P3+) — zero code, enterprise focus
- **Haystack** (P2 → P3+) — zero code, pipeline-only
- **DSPy/PydanticAI** (P2 → P4+) — zero code, selective typed-worker pattern
- **Electron packaging** (P5 → P5-post-v0.1) — not realistic for v0.1

### 5. What are the next 5 actions?

1. **Apply plan edits** — update `docs/IMPLEMENTATION_PLAN.md` with all changes from section 12
2. **Fix Arena documentation** — correct `REALITY_AUDIT.md` fiction about Arena being "100% stub"
3. **Promote release checklist** — move `docs/archive/RELEASE_CHECKLIST.md` to `docs/RELEASE_CHECKLIST.md`, update version
4. **Wire canonical extension** — add `arc-extension` to `applications/browser/package.json` dependencies
5. **Begin PR 1** — docs truth cleanup + `scripts/check-docs-truth.sh`
