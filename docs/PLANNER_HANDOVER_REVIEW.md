# ARC Studio — Planner Handover Document Review

**Review Date:** 2026-05-18  
**Reviewer:** OpenCode (kr-claude-sonnet-4.5)  
**Status:** Review artifact only; not a roadmap or execution source of truth  
**Review Scope:** Technical accuracy, alignment with codebase reality, feasibility assessment. Execution decisions must be folded into `docs/LOCKED_REMAINING_ROADMAP.md` and `docs/LOCKED_PHASE_IMPLEMENTATION_PLAN.md`.

---

## Executive Summary

The handover document presents a coherent v0.2 vision focused on **IDE productization** around existing CLI/daemon capabilities. The strategic frame is sound: position ARC as the local-first, audit-first operator's IDE for multi-runtime agent work, anchored by SwarmGraph's differentiation.

**Overall Assessment:** ✅ **Approved with modifications**

The document correctly identifies the highest-leverage work and sequences it well. However, it contains **factual inaccuracies** about current implementation state, **underestimates scope** for several priorities, and **overestimates** what can ship in a single cycle without adapter work.

---

## Section-by-Section Review

### 1. Strategic Frame ✅ SOUND

**Strengths:**
- Clear positioning: local-first audit-first operator's IDE, not competing with Cursor/LangSmith/Ruflo
- Honest about the wedge: SwarmGraph's HITL + audit + consensus differentiation
- The "single rule" (no adapter ships without IDE view) is correct and enforceable

**Concerns:**
- The frame assumes more SwarmGraph product integration than ARC currently exposes. Vendored SwarmGraph is sophisticated, but ARC's productized paths remain narrow and gated.
- The positioning relies on features that are only partially present: live transport/proxy baseline exists, effect-boundary replay does not, and BudgetVector accounting/enforcement does not.

**Recommendation:** Accept the frame but acknowledge it describes v0.2 **target state**, not current reality.

---

### 2. What We Are Not Doing ✅ CORRECT

All exclusions are appropriate:
- ✅ No new adapters beyond the existing seven
- ✅ No Agent Bundle / portable format work
- ✅ No capability handles / policy engine
- ✅ No live LM Arena (correctly identified as stub-only)
- ✅ No Electron packaging (browser app is the target)
- ✅ No LangGraph Studio feature parity chase

**Factual correction needed:**
> "Remove the ARC_ALLOW_LIVE_ARENA fiction from code and docs."

**Reality:** `ARC_ALLOW_LIVE_ARENA` is already documented as gating nothing real. The arena service returns 100% stub responses. This is already honest in `docs/REALITY_AUDIT.md` Fiction List.

**Recommendation:** Change to "Keep LM Arena stub-only and out of v0.2 product scope."

---

### 3. Highest-Leverage Work — Priority Assessment

#### Priority 1: Wire Live Active-Run SSE ⚠️ PARTIALLY COMPLETE

**Document claim:**
> "The daemon already exposes GET /api/runs/{run_id}/events as SSE. The arc-event-stream widget exists in archived theia-extensions/* with 33 AG-UI event type icons, virtualized event list, SSE client, event detail drawer, and type filter. SwarmGraph already produces the events. The wiring between them is missing."

**Reality check:**
- ✅ `EventBroker` exists in `python/src/agent_runtime_cockpit/orchestration/event_broker.py` with `stream_live()` and `sse_handler()`
- ✅ `/api/runs/{id}/events` SSE endpoint exists in `web/routes.py`
- ✅ Phase 1 (R1) is marked **Complete** in `LOCKED_PHASE_IMPLEMENTATION_PLAN.md`
- ✅ `streamActiveTrace()` exists in Theia backend service contract
- ✅ Event Stream and Run Timeline widgets distinguish live/replay/disconnected states
- ✅ `/api/sse-proof` deterministic stub endpoint exists with e2e coverage

**Gap:** The document says "the wiring between them is missing" but Phase 1 status says the transport/proxy/UI-state baseline is complete. The remaining work is **productization**: connecting Theia live mode to a configured Python web base URL for real in-flight runtime streams beyond the deterministic stub path.

**Scope correction:** This is not 2-3 weeks of greenfield work. It's 1-2 weeks of **productization polish** on top of the existing Phase 1 baseline.

**Recommendation:** Reframe as "Complete Phase 1 productization: wire Theia live mode to Python daemon base URL for real runtime streams."

---

#### Priority 2: Effect-Boundary Replay ❌ SIGNIFICANTLY UNDERSCOPED

**Document claim:**
> "Stored-trace replay (transcript playback) works. Effect-boundary replay — re-executing orchestration logic against journaled adapter responses, the Temporal-style model — does not."

**Reality check:**
- ✅ `can_replay`, `can_fork`, `can_resume` capability flags exist uniformly in the data model
- ✅ All are uniformly `False` in adapter implementations
- ✅ `arc runs replay` CLI command exists and does **stored-trace replay** (JSONL event playback)
- ❌ No journal record/replay layer exists
- ❌ No effect-boundary capture exists in any adapter
- ❌ No content-addressed hashing of effect inputs/outputs exists
- ❌ No orchestration-replay logic exists

**Scope reality:** Full adapter-wide replay is **not** 3-4 weeks. It is **8-12 weeks minimum** and requires:
1. Design and implement journal schema (content-addressed or hash-chained)
2. Instrument adapters to capture effect boundaries (model calls, tool calls, HITL decisions)
3. Build orchestration-replay engine that can re-execute against journaled responses
4. Implement fork-at-step with patch application
5. Wire to IDE with "Fork from here" UI
6. Test across multiple adapters

**Architectural concern:** Effect-boundary replay requires **deep adapter integration**. The document says "no new adapter work" but this priority **is** adapter work. A SwarmGraph-only v0.2 replay slice would be a deliberate one-adapter exception, still likely 6-8 weeks.

**Recommendation:** Either:
- **Defer to v0.3** and focus v0.2 on IDE productization of existing capabilities, OR
- **Scope down** to "deterministic replay for one adapter (SwarmGraph) only" and accept 6-8 weeks

---

#### Priority 3: Budget Vector ⚠️ FEASIBLE BUT UNDERSPECIFIED

**Document claim:**
> "SwarmGraph already tracks per-call USD cost and rolls it up across workers. Provider quota stores exist. Paid-call gating exists. What is missing is a uniform multi-dimensional BudgetVector (USD, prompt tokens, completion tokens, latency, tool calls, risk points) enforced by the runtime router across all adapters."

**Reality check:**
- ✅ SwarmGraph has cost tracking
- ✅ `ProviderQuotaStore` exists in `python/src/agent_runtime_cockpit/providers.py`
- ✅ Paid-call gating exists via `enforce_profile()` in `security/profiles.py`
- ⚠️ No `BudgetVector` primitive exists
- ⚠️ No multi-dimensional budget enforcement exists in `runtime_router.py`
- ⚠️ No pressure threshold events exist
- ⚠️ No graceful exhaustion interrupts exist

**Scope assessment:** 2-3 weeks is realistic only if v0.2 is scoped to post-hoc accounting/reporting:
1. Define `BudgetVector` Pydantic model
2. Add `default_budget` to workflow config
3. Calculate final budget usage from stored trace/metadata where data exists
4. Surface IDE gauges with present/missing/degraded states
5. Ship `arc runs budget <id>` CLI command

Real-time pressure/exhaustion events require adapter/effect-boundary instrumentation and should remain v0.3 unless limited to a proven path.

**Open question from document:**
> "The BudgetVector risk-points dimension needs a calibration policy. Either ship a reference taxonomy or make risk a per-workspace policy file."

**Recommendation:** Per-workspace policy file is correct. Ship with a **reference example** in `docs/examples/budget-policy.yaml` but do not hardcode risk scores. This avoids the "what risk is a CRM lookup really?" debate.

---

#### Priority 4: HITL Inbox + Audit Chain Viewer ⚠️ PARTIALLY COMPLETE

**Document claim:**
> "SwarmGraph's strongest features are interactive HITL with single-use tokens and HMAC-SHA256 audit chains with offline verification. The CLI exposes them. The IDE has stub or absent widgets for both."

**Reality check:**
- ✅ HITL CLI exists: `arc hitl pending/approve/reject/respond`
- ✅ Audit CLI exists: `arc audit verify/export/key`
- ✅ Phase 4 (R4) is marked **Complete baseline** in `LOCKED_PHASE_IMPLEMENTATION_PLAN.md`
- ✅ Dedicated **Assurance tab** exists in `packages/arc-extension/src/browser/tabs/AssuranceTab.tsx`
- ✅ HITL inbox view exists with approve/reject/respond, token expiry, replay-attack-safe messaging
- ✅ Audit chain viewer exists for runs with audit material
- ✅ Replay stepper exists with HITL/audit annotations

**Gap:** The document says "stub or absent widgets" but the code shows **implemented baseline widgets**. The remaining work is **polish**: live refresh, filtering, export affordances.

**Scope correction:** This is not 2-3 weeks of greenfield work. It's **1 week of polish** on top of the existing Phase 4 baseline.

**Recommendation:** Reframe as "Polish HITL/Audit UX: add live refresh, filtering, and export affordances to existing Assurance tab."

---

### 4. Discipline Items ✅ CORRECT

All discipline items are appropriate and necessary:
- ✅ Truth alignment against Fiction List
- ✅ Archive cleanup after ports complete
- ✅ Daemon-CLI parity audit
- ✅ SQLite/search verification and docs alignment
- ✅ `arc doctor all` parity/coverage audit
- ✅ Test discipline (offline default, opt-in real-runtime smoke)

**Factual correction:**
> "SQLite store wiring. storage/sqlite.py defines the schema and is documented as a stub never wired. Either wire it (preferred) or delete it."

**Reality:** SQLite store **is wired** as of Phase P1a. `IndexedTraceStore` in `storage/indexed_store.py` wraps JSONL + SQLite with dual-write. `backfill_index()` exists for idempotent rebuild. 20 storage tests exist. `arc doctor all` also exists; remaining work is coverage/parity audit, not first implementation.

**Recommendation:** Change to "SQLite store is wired; verify `arc runs search` uses the index."

---

### 5. Sequencing ✅ SOUND

The sequencing within each priority is logical and follows dependency order. No concerns.

---

### 6. Risk to Watch ✅ CORRECT

> "Runtime sprawl outpacing IDE coherence. ARC supports seven runtimes; two have real execution paths; the IDE has not yet caught up to even those two."

**Reality check:** Directionally accurate. Current locked-doc status: SwarmGraph standalone and LangGraph standalone have real paths; `langgraph+swarmgraph` has a narrow dual-gated local-real path; `crewai+swarmgraph` and `langgraph+swarmgraph` fake/offline routes exist; provider-backed adoption remains unclaimed; OpenAI Agents, AG2, LlamaIndex are gated/fake-tested; LM Arena is stub-default.

The mitigation rule is correct and enforceable.

---

### 7. Success Criteria ⚠️ OVERSTATED

**Document claim:**
> "A user opens ARC Studio in the browser, picks a SwarmGraph workflow from a workspace, sets a $0.40 / 12-second budget, launches a run, and watches it execute live in the Run Timeline view — events streaming, budget gauges filling, queen-worker decomposition visible, consensus rounds rendered."

**Reality check against current implementation:**
- ✅ Open browser app: works
- ✅ Pick SwarmGraph workflow: detection works
- ❌ Set budget: `BudgetVector` does not exist (Priority 3 work)
- ⚠️ Launch run: works via CLI bridge
- ⚠️ Watch live: Phase 1 baseline exists but productization incomplete
- ❌ Budget gauges: do not exist (Priority 3 work)
- ⚠️ Queen-worker/topology visible only where event-backed topology producer data exists; `langgraph+swarmgraph` can emit first topology/consensus events, while standalone SwarmGraph CLI internals are not broadly captured
- ⚠️ Consensus rounds rendered only for runs with explicit consensus/vote events

**The next day:**
- ❌ Replay bit-identically from journal: effect-boundary replay does not exist (Priority 2 work)
- ❌ Fork at step seven: fork does not exist (Priority 2 work)
- ❌ Compare side by side: run diff UI exists but not integrated into main flow

**Scope reality:** This success scenario requires **all four priorities plus significant SwarmGraph integration work**. If the document's scope estimates are accurate (2+3+2+2 = 9 weeks), this is a **2.5-month cycle**, not a single sprint.

**Recommendation:** Either:
- **Scope down** the success criteria to what can ship in 6-8 weeks (Priorities 1 polish + 3 + 4 polish), OR
- **Acknowledge** this is a 10-12 week cycle and defer Priority 2 to v0.3

---

### 8. Open Questions ✅ GOOD

All three open questions are legitimate and correctly scoped:
1. Journal schema: JSONL with hash chaining is the right v0.2 choice
2. Risk-points calibration: per-workspace policy file is correct
3. Widget port scope: four-only approach is correct

**Recommendation:** Accept all three recommendations as stated.

---

## Factual Corrections Required

### Current Implementation State Misstatements

| Document Claim | Reality | Source |
|---|---|---|
| "The wiring between daemon SSE and IDE is missing" | Phase 1 baseline complete; productization remains | `LOCKED_PHASE_IMPLEMENTATION_PLAN.md` Phase 1 status |
| "Effect-boundary replay does not exist" | Correct, but scope is 8-12 weeks, not 3-4 | No journal layer exists in codebase |
| "The IDE has stub or absent HITL/Audit widgets" | Assurance tab exists with HITL inbox + audit viewer baseline | `packages/arc-extension/src/browser/tabs/AssuranceTab.tsx` |
| "SQLite store is a stub never wired" | SQLite store is wired via `IndexedTraceStore` | `python/src/agent_runtime_cockpit/storage/indexed_store.py` |
| "No audit viewer exists in any IDE view" | Audit chain viewer exists in Assurance tab | `AssuranceTab.tsx` |
| "No HITL inbox exists" | HITL inbox exists in Assurance tab | `AssuranceTab.tsx` |

### Scope Estimate Corrections

| Priority | Document Estimate | Realistic Estimate | Reason |
|---|---|---|---|
| Priority 1 (Live SSE) | 2-3 weeks | 1-2 weeks | Phase 1 baseline complete; only productization remains |
| Priority 2 (Effect Replay) | 3-4 weeks | 8-12 weeks | Requires journal layer + adapter instrumentation + orchestration-replay engine |
| Priority 3 (Budget Vector) | 2 weeks | 2-3 weeks | Estimate is reasonable |
| Priority 4 (HITL/Audit UI) | 2-3 weeks | 1 week | Baseline widgets exist; only polish remains |

**Total cycle time:**
- **Document estimate:** 9-12 weeks
- **Realistic estimate (all four):** 12-18 weeks
- **Realistic estimate (defer Priority 2):** 4-6 weeks

---

## Architectural Concerns

### 1. Priority 2 Conflicts with "No Adapter Work" Rule

Effect-boundary replay **requires** deep adapter integration. Every adapter must be instrumented to journal effect boundaries. This is **adapter work**, not IDE work.

**Options:**
- **Defer Priority 2 to v0.3** when adapter work is back on the table
- **Scope to SwarmGraph only** and accept it as the one adapter exception
- **Redefine** as "deterministic replay for adapters that already journal" (currently: none)

**Recommendation:** Defer to v0.3. Focus v0.2 on IDE productization of existing capabilities.

---

### 2. Success Criteria Depends on Real SwarmGraph Runs

The success scenario shows "queen-worker decomposition visible, consensus rounds rendered." This requires:
1. Real SwarmGraph runs (not CLI subprocess, but in-process or adoption-layer integration)
2. SwarmGraph or adoption paths emitting topology/consensus events into ARC traces
3. IDE consuming those events

**Current reality:**
- Standalone SwarmGraph runs as CLI subprocess (`swarmgraph swarm --json`)
- ARC does not broadly capture standalone SwarmGraph's internal topology/consensus events
- SwarmGraph Insight tab renders only explicit event-backed data; `langgraph+swarmgraph` has first topology/consensus producers, but cost producer remains absent

**Options:**
- **Scope down** success criteria to "budget gauges + live streaming" only
- **Keep** SwarmGraph-specific visualizations event-backed only, with degraded states where producers are absent
- **Defer** standalone SwarmGraph internal event capture and measured cost producers to later work unless scoped explicitly

**Recommendation:** Scope down success criteria. Render topology/consensus only where event producers exist; defer standalone SwarmGraph internal event capture and measured cost producers.

---

### 3. Budget Vector Enforcement Requires Adapter Cooperation

The document says budget enforcement happens "at every effect boundary" in `runtime_router.py`. But the runtime router doesn't see effect boundaries — adapters do. Enforcement requires either:
1. **Adapter instrumentation** (every adapter reports costs/tokens/latency back to router)
2. **Post-hoc accounting** (router reads costs from trace after run completes)

**Current reality:** SwarmGraph tracks costs internally. Other adapters do not.

**Recommendation:** Scope Priority 3 to "post-hoc budget accounting + IDE visualization" for v0.2. Real-time enforcement requires adapter work (v0.3).

---

## Recommendations

### Immediate Actions

1. **Correct factual misstatements** about Phase 1 and Phase 4 completion status
2. **Revise scope estimates** for Priorities 1, 2, and 4
3. **Defer Priority 2** (effect-boundary replay) to v0.3 or scope to SwarmGraph-only
4. **Scope down success criteria** to remove SwarmGraph topology/consensus visualization
5. **Clarify** that Budget Vector enforcement is post-hoc accounting, not real-time interrupts

### Revised v0.2 Scope (6-8 weeks)

**Priority 1:** Complete Phase 1 productization (1-2 weeks)
- Wire Theia live mode to Python daemon base URL
- End-to-end demo with configured daemon/local runtime stream; keep provider-backed/runtime breadth claims out unless separately proven

**Priority 3:** Budget Vector with post-hoc accounting (2-3 weeks)
- Define `BudgetVector` Pydantic model
- Add `default_budget` to workflow config
- Post-hoc budget calculation from trace
- IDE budget gauges showing final consumption
- `arc runs budget <id>` CLI command

**Priority 4:** Polish HITL/Audit UX (1 week)
- Add live refresh to HITL inbox
- Add filtering to audit chain viewer
- Add export affordances

**Discipline items:** (ongoing)
- Truth alignment
- Daemon-CLI parity audit
- `arc doctor all` parity/coverage audit

**Success criteria (revised):**
> A user opens ARC Studio in the browser, picks a local workflow, launches a run, and watches events stream live in the Run Timeline view through the configured daemon/local runtime path. After the run completes, they open the budget panel and see final consumption where trace/metadata is present, with honest missing/degraded states elsewhere. They open the HITL inbox, approve a pending request, and verify the approval in the audit chain viewer where audit material exists.

---

## Alternative: Aggressive v0.2 (10-12 weeks)

If the team wants the full vision, accept the longer cycle:

**Priority 1:** Live SSE productization (1-2 weeks)  
**Priority 2:** Effect-boundary replay for SwarmGraph only (6-8 weeks)  
**Priority 3:** Budget Vector post-hoc accounting (2-3 weeks)  
**Priority 4:** HITL/Audit polish (1 week)  

**Total:** 10-14 weeks

**Success criteria:** As stated in document, minus queen-worker topology visualization

---

## Conclusion

The handover document presents a **sound strategic vision** and correctly identifies the highest-leverage work. However, it **underestimates scope** for Priority 2 (effect-boundary replay) and **overstates** current implementation gaps for Priorities 1 and 4.

**Recommended path forward:**
1. **Accept** the strategic frame and discipline items as written
2. **Defer** Priority 2 (effect-boundary replay) to v0.3
3. **Focus** v0.2 on IDE productization: live streaming polish + budget vector + HITL/Audit polish
4. **Scope down** success criteria to remove features that require adapter work or SwarmGraph event integration
5. **Revise** cycle estimate to 6-8 weeks for the scoped v0.2

This delivers a **coherent, shippable v0.2** that makes ARC Studio feel like an IDE instead of "a CLI with a tabbed widget" — which is the document's core goal — without overcommitting to features that require 3+ months of adapter instrumentation work.

---

## Appendix: Current Phase Status (from LOCKED_PHASE_IMPLEMENTATION_PLAN.md)

| Phase | Status | Notes |
|---|---|---|
| Phase 1 (Live Streaming) | ✅ Complete baseline | Python SSE, Theia proxy, UI states, stub e2e |
| Phase 2 (Runtime Setup) | ✅ Complete polished UI | ConfigTab with safe fields, wizard, export helpers |
| Phase 3 (Provider/Quota) | ⚠️ Active narrow baseline | Gated 9router action path; no broad provider claim |
| Phase 4 (HITL/Audit) | ✅ Complete baseline | Assurance tab with inbox + audit viewer |
| Phase 5 (SwarmGraph Insight) | ✅ Complete baseline | Topology/consensus/cost panels; no fabricated data |
| Phase 6 (Real Adoption) | ✅ Complete local-real hardening | `langgraph+swarmgraph` local-real path; no provider calls |
| Phase 7 (Release Ops) | ⚠️ Partial | Evidence refreshed; green-window active; `.env` scrub blocked |

**Key takeaway:** Phases 1, 2, 4, 5, 6 are substantially complete. The handover document treats them as greenfield work.
