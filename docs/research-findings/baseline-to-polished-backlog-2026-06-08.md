# ARC Studio — Baseline → Polished Backlog + DoD Scorecard (2026-06-08)

**Purpose:** A durable, comprehensive plan for elevating every in-flight surface from `Baseline Complete`
to `Polished Complete`, with deep per-item research on the path to the **engineering quality bar** — so
the canonical roadmap doesn't need daily churn. Read-only research artifact (not a competing roadmap, per
`AGENTS.md`). Promote selected rows into `docs/roadmap.md` deliberately.

> **Honesty / posture boundary (non-negotiable).** ARC Studio is a **single-user, loopback-only alpha
> workstation tool** by deliberate design. "Polished Complete" means the **8 DoD gates** (the *engineering*
> quality bar in `AGENTS.md`) all have cited evidence. It does **not** unlock product claims. True product
> "production/enterprise readiness" depends on **posture-gated** capabilities — authentication, multi-party
> isolation, real native device access, broad provider-backed execution, microVM-on-Linux — each of which is
> **human-gated and out of current scope**. For every item below we therefore record two separate things:
> (a) the concrete work to reach the **Polished engineering bar**, and (b) whether the item is additionally
> **posture-gated** (cannot become a product-readiness claim without an explicit human decision).
> Release-facing wording stays governed by `scripts/check-banned-claims.sh` (authoritative): do not introduce
> the forbidden product-readiness / multi-party / isolation / keyed-audit / broad-adoption phrases it bans.

---

## Part 1 — The reusable prompt

> **Role:** You are elevating ARC Studio from Baseline Complete to Polished Complete. Code is the only proof.
>
> **The 8 DoD gates (from `AGENTS.md`) — the definition of "Polished Complete":**
> 1. **UX states** — every surface has loading/empty/error/degraded/success; no silent `.catch(()=>null)`; no invented data (producer-truth).
> 2. **Accessibility** — keyboard-reachable, visible focus, ARIA roles/labels, color contrast, `NO_COLOR`/high-contrast TUI parity; run axe/contract checks.
> 3. **Parity** — CLI ↔ TUI ↔ IDE behave consistently; JSON output stable + documented.
> 4. **Tests** — unit + integration; contract/e2e if a UI surface changed; CLI snapshot if a command changed; protocol test if the protocol changed; deterministic + offline.
> 5. **Performance** — bounded buffers, virtualized lists, no sync FS I/O in hot paths, async bridges, debounced inputs; measure before/after.
> 6. **Security** — paid calls gated; secrets redacted; destructive/mutating actions confirmation-gated; deterministic security decisions; audit appended on allow.
> 7. **Reliability** — timeouts, cancellation, structured error envelopes on every long-running/bridged action.
> 8. **Docs** — README, `--help`, `roadmap.md`, `phases.md` updated in place; all claims pass `check-banned-claims.sh`.
>
> **Scope:** Read-only on `docs/roadmap.md` + `docs/phases.md`. Read any source/test/CI to verify. Do not edit code.
>
> **Method (per item):**
> 1. **Locate** the item (roadmap/phase line anchor + the code file:line it lives in). Verify it against code — treat doc claims as ~50% reliable.
> 2. **Current state:** what works today (Baseline), with evidence.
> 3. **Work to the quality bar:** the concrete, smallest-safe changes to close the open DoD gate(s). Name files/modules.
> 4. **Tests:** the exact unit/contract/e2e/snapshot/protocol tests required.
> 5. **DoD gate(s) closed:** which of the 8.
> 6. **Dependencies / order.**
> 7. **Effort:** S (≤½ day) / M (1–2 days) / L (>2 days).
> 8. **Risk:** blast radius + reversibility.
> 9. **Posture-gating:** `none` (pure engineering — reachable now) OR `posture-gated` (additionally needs a human decision: auth, isolation, real-device, provider-backed, microVM-on-Linux) — and say which.
>
> **Output:** (#1) an actionable backlog table (ID, item, source anchor, work, files, tests, DoD gate(s),
> effort, risk, posture-gate) with status `Not Started`; (#2) a DoD scorecard — major surfaces × the 8 gates
> (✅ has evidence / ⚠️ partial / ❌ open), with the cited evidence anchor for each ✅.
>
> **Rules:** Strengthen, don't weaken, existing tests. Additive-only. Never introduce a banned claim. For any
> posture-gated item, the "path to production/enterprise" must explicitly say *what human decision unblocks it*,
> never imply ticking engineering boxes alone gets there.

---

## Part 2 — (#1) Actionable Baseline → Polished backlog

All rows are `Not Started`. **Effort:** S ≤½d · M 1–2d · L >2d. **Posture-gate:** `none` = pure engineering,
reachable now; `GATED` = additionally needs an explicit human decision (auth / isolation / real-device /
paid-live provider / Linux-KVM host) before it can support any product-readiness claim.
DoD gates: 1 UX-states · 2 a11y · 3 parity · 4 tests · 5 perf · 6 security · 7 reliability · 8 docs.

### Domain A — TUI / IDE / UX

| ID | Item | Source | Concrete work + files | DoD | Effort | Posture |
|---|---|---|---|---|---|---|
| R-AUDIT26 | IDE risk-badge color + aria | roadmap L171; `McpWorkbenchTab.tsx:14` | `RISK_VARIANT` give `critical` a distinct `danger`/red variant (today `high`+`critical`→`'info'`); add `aria-label` to the risk badge span | 2 | S | none |
| R-AUDIT27 | IDE status rail | roadmap L172 | New persistent top-rail widget (mode/trust/model/daemon) reading existing services; loading/degraded states; `arc-extension/src/browser/` + frontend module | 1,2,3 | M | none |
| R-AUDIT28 | Remove orphaned IDE dead code | roadmap L173 | Delete `browser/arena/arena-frontend-module.ts` + `browser/arc-run-timeline-widget.tsx` (confirm no contribution refs); contract test asserts no import | 8 | S | none |
| R-AUDIT29 | TestBenchTab Run button | roadmap L174 | Add sandbox-policy-gated Run action → `execArcCliAsync('testbench run --policy local-safe …')`; loading/error/output states; confirm gate | 1,3,6,7 | M | none |
| B2P-01 | TUI `/statusline` slot reordering | roadmap L1242 (R-UX4) | Config key for slot order + render from config; TUI snapshot test | 1,3 | S | none |
| B2P-02 | arc-extension `TraceEvent` → typed events migration | roadmap L538 | Migrate IDE consumers off legacy `TraceEvent` to the `KnownRunEvent` typed union; parity/contract tests | 3,4 | M | none |
| B2P-03 | Real-component jest-axe a11y | roadmap L1755 (R-POLISH13 follow-up) | Run axe against real rendered tabs (not mocks); browser-level contrast check | 2,4 | M | none |

### Domain B — Security / MCP

| ID | Item | Source | Concrete work + files | DoD | Effort | Posture |
|---|---|---|---|---|---|---|
| B2P-04 | MCP live invocation from IDE | roadmap L634 | Today `McpWorkbenchTab` is status/inspection only (no `callTool`). Add a loopback MCP client to drive stdio tools through the risk gate; render decisions/results with full UX states | 1,3,6,7 | L | none |
| B2P-05 | SwarmGraph MCP tool wrappers | roadmap L621 | Expose SwarmGraph ops as MCP tools (deferred at scaffold time); tests + risk-gate coverage | 3,4,6 | M | none |
| B2P-06 | MCP HTTP transport | roadmap L634 | **Define auth/trust policy first**, then add HTTP transport behind it; stdio stays default | 6 | L | **GATED** (auth design + human decision; stdio-only by safety today) |
| B2P-07 | MCP task notifications + real exec | roadmap L650/L659/L1311 | SSE for task state changes (today polling); wire task exec to real run/trace/audit (today placeholder ops); daemon API integration | 1,4,7 | M | none |
| B2P-08 | Runtime-wide high/critical confirmation | roadmap L746/L755 | Today high/critical surfaces `hitl_required=true` but confirmation isn't enforced at every runtime entrypoint; make it mandatory + audited everywhere | 6 | M | none |
| B2P-09 | Real-time budget enforcement at effect boundaries | roadmap L456 | `BudgetEnforcer` exists (`budget/schema.py:166`) but isn't called at every adapter effect boundary (post-hoc only); wire pressure/exhaustion checks into each adapter | 5,6,7 | L | none |
| B2P-10 | Type the intentionally-untyped events | roadmap L523 | Type the remaining events in the cross-language registry or document each as intentional; parity test | 4 | S | none |

### Domain C — Mobile (simulator-preview; most are posture-gated)

| ID | Item | Source | Concrete work + files | DoD | Effort | Posture |
|---|---|---|---|---|---|---|
| R79.3 | Device posture / MDM hooks | roadmap L167 | Deterministic posture/MDM hook interface (simulator-preview, fixtures); real enforcement is later | 4,6 | M | none (scaffold); real enforcement GATED |
| R79.4 | Mobile package supply-chain provenance | roadmap L168 | SBOM attestation + signed provenance (SLSA/sigstore) for the mobile packages in CI | 6,8 | M | none |
| R79.5 | Mobile-package dependency vuln scanning | roadmap L169 | `npm audit` / Dart `pub` audit gates for the mobile JS/Dart trees in `release_check`/CI | 6,8 | S | none |
| R79.1 | Real native framework package builds | roadmap L165 | Shippable Expo/RN/Flutter builds from distribution artifacts + real native example-app CI | 4,8 | L | **GATED** (native toolchains + Phase 11 entry gates) |
| R79.2 | Native device-capability execution | roadmap L166 | Flip capability gate from fixtures to real device access (camera/mic/contacts/location) | 6 | L | **GATED** (human decision; the hard safety boundary) |

### Domain D — CLI / Providers / SwarmGraph / Memory

| ID | Item | Source | Concrete work + files | DoD | Effort | Posture |
|---|---|---|---|---|---|---|
| B2P-11 | Eval artifact schema + Inspect export + report compare | roadmap L696/L698/L704 | `--batch` flag already exists (`mgmt_eval.py:124`). Add a repeatable eval **artifact schema** (stable paths), Inspect-AI-compatible export, and two-run comparison report | 3,4,8 | M | none |
| B2P-12 | Memory runtime wiring | roadmap L1187 | Confirmed **not** wired into the run path (`runtime_router`/adapters don't import memory). Invoke extract/query during runs with redaction-before-extraction (store/query already exist CLI-only) | 3,4 | M | none |
| B2P-13 | Phase 42 IDE write bridge | roadmap L1202 | IDE write operations, deferred pending advisory-lock integration; build the lock then the bridge | 6,7 | M | none (depends on advisory lock) |
| B2P-14 | ADK adapter T3 execution | roadmap L1016/L1033 | Live `LlmAgent`/`Runner` execution | 4 | M | **GATED** (google-adk 1.0 + live Gemini/paid calls) |
| B2P-15 | MCP adapter (Phase 35) T3 execution | roadmap L1041 | Live MCP transport + client-session lifecycle | 4,6 | M | **GATED** (live transport + trust posture) |
| B2P-16 | Broad provider-backed SwarmGraph adoption | roadmap L1156/L831 | Beyond the one opt-in CrofAI/DeepSeek E2E proof | 4 | L | **GATED** (paid/live providers + human decision; forbidden claim until proven) |

### Domain E — CI / Release / Audit

| ID | Item | Source | Concrete work + files | DoD | Effort | Posture |
|---|---|---|---|---|---|---|
| B2P-17 | Full Electron app packaging | roadmap L389 | Today a PyInstaller daemon spike only (ADR-008). Full Electron packaging + signing + lifecycle; browser stays canonical target | 4,8 | L | none |
| B2P-18 | Doctor/daemon parity remainder | roadmap L466 | Resolve the fate-labeled orphan routes (`ui-deferred` → add UI, or finalize `daemon-only-deprecated`) | 3,8 | M | none |
| B2P-19 | Keyed audit material across every run path | roadmap "Non-Negotiable Scope Boundaries" | Ensure every adapter run path writes + verifies keyed audit material (not guaranteed adapter-wide today) | 4,6 | M | none |
| B2P-20 | Reviewed Memory Evidence pack | phases Ph67/Ph70 | Produce the human-reviewed memory evidence fixture pack that unblocks the gate | 4,8 | M | needs human review |
| B2P-21 | Firecracker Linux host proof | phases Ph66 | Run the gated microVM proof on a real Linux/KVM host | 4 | M | **GATED** (Linux/KVM host) |
| B2P-22 | Live Battle Arena | phases Ph34.6 | Provider-backed battle execution | 4,6 | L | **GATED** (paid/live provider calls) |

---

## Part 3 — (#2) DoD scorecard (major surfaces × 8 gates)

`✅` evidence exists · `⚠️` partial · `❌` open. Gates: 1 UX-states · 2 a11y · 3 parity · 4 tests ·
5 perf · 6 security · 7 reliability · 8 docs. This is an evidence-anchored **assessment** — each `✅` must be
re-confirmed with a cited anchor in `docs/phases.md` at the moment a surface is actually flipped to
`Polished Complete` (labels follow evidence).

| Surface | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | Top open gaps → backlog |
|---|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|---|
| **CLI** | ✅ | ⚠️ | ⚠️ | ✅ | ✅ | ✅ | ✅ | ✅ | G2 NO_COLOR audit; G3 a few non-compliant JSON envelopes (a2a/flight/events) |
| **TUI** | ✅ | ✅ | ⚠️ | ✅ | ⚠️ | ✅ | ⚠️ | ✅ | G3 B2P-01 statusline; G5/G7 streaming-widget perf + cancellation |
| **Theia IDE** | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ | ✅ | ⚠️ | G1/G3 R-AUDIT27 status rail, R-AUDIT29 TestBench Run, B2P-04 MCP client; G2 R-AUDIT26 + B2P-03; cleanup R-AUDIT28 |
| **Security / Sandbox** | ✅ | n/a | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | G6 B2P-19 keyed audit adapter-wide; B2P-08 runtime-wide confirmation |
| **MCP** | ⚠️ | n/a | ❌ | ✅ | ✅ | ✅ | ✅ | ⚠️ | G3 B2P-04 IDE client + B2P-05 SwarmGraph wrappers; B2P-07 task notify; B2P-06 HTTP (GATED) |
| **Providers / Budget** | ✅ | n/a | ✅ | ✅ | ⚠️ | ✅ | ✅ | ✅ | G5 B2P-09 real-time enforcement at effect boundaries |
| **SwarmGraph** | ✅ | n/a | ⚠️ | ✅ | ✅ | ✅ | ✅ | ✅ | G3 B2P-16 broad provider-backed adoption (GATED) |
| **Audit / Evidence** | ⚠️ | n/a | ✅ | ✅ | ✅ | ✅ | ✅ | ⚠️ | G1 receipt/autopsy states; G6 B2P-19 keyed audit everywhere |
| **Mobile (sim-preview)** | ✅ | ⚠️ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | G2 a11y of any mobile UI; native R79.1/R79.2 (GATED) |
| **Runs / Events** | ✅ | n/a | ⚠️ | ✅ | ✅ | ✅ | ✅ | ✅ | G3 active-run parity across surfaces |
| **Config / Profiles** | ✅ | n/a | ⚠️ | ✅ | ✅ | ✅ | ✅ | ✅ | G3 CLI↔TUI↔IDE settings parity polish |
| **Release / CI** | ✅ | n/a | ✅ | ✅ | ✅ | ✅ | ✅ | ⚠️ | G6/G8 R79.4 provenance, R79.5 vuln-scan, B2P-17 Electron |

**Evidence basis for the `✅`s** (representative anchors): security P0 batch + R-POLISH1–18 (Phases 159–177),
R-UX1–4 (TUI), R-POLISH7/14 (async Node backend), R-POLISH9/11 (bounded buffers), R-POLISH4 (MCP hardening),
R-POLISH13 (jest-axe), R-POLISH15 (SwarmGraph cost), mobile Phases 187–195, banned-claims CI gate (Phase 193).

---

## Part 4 — How to use this (so the roadmap doesn't churn daily)

1. **This doc is the durable plan.** Each backlog row is fully specified (work + files + tests + DoD gate +
   effort + posture). Pick a row, implement it, cite evidence — no re-planning per day.
2. **Promote, don't duplicate.** When a row is scheduled, add it to `docs/roadmap.md` (Not Started) and record
   the phase in `docs/phases.md` on completion. The roadmap stays the index; this stays the spec.
3. **Two finish lines, kept separate.** A surface reaches **Polished Complete** when its 8 gates have cited
   evidence — that is the achievable engineering target. Items marked **GATED** additionally need an explicit
   **human posture decision** (auth, isolation, real-device, paid-live provider, Linux-KVM host) before they
   can support any product-readiness wording; ticking engineering gates alone never gets there.
3. **Suggested order:** close `none`-posture, low-effort, high-DoD-impact first — R-AUDIT26 (S, a11y defect),
   R-AUDIT28 (S, cleanup), B2P-10/B2P-01 (S), then the M items (R-AUDIT27/29, B2P-07/08/11/12), then the L
   engineering items (B2P-04/09, R-AUDIT-IDE), and leave all `GATED` rows parked until a posture decision.

**Honesty footer:** Completing every `none`-posture row elevates ARC Studio to a coherent, accessible, tested,
documented **Polished** engineering state. It remains a **single-user, loopback-only alpha** until the GATED
posture items are deliberately unlocked by a human owner. Nothing here authorizes a product-readiness claim;
`scripts/check-banned-claims.sh` remains authoritative.
