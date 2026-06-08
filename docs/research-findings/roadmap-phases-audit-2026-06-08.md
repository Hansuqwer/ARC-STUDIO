# Roadmap ↔ Phases Reconciliation Audit (2026-06-08)

**Purpose:** Reconcile `docs/roadmap.md` and `docs/phases.md` against code reality so we know exactly
what is **not complete** and what was **forgotten / left stale**. Read-only on the two canonical docs
(this is a research-findings artifact, not a competing roadmap — per `AGENTS.md`).

---

## Part 1 — The reusable audit prompt

> **Task:** Audit `docs/roadmap.md` and `docs/phases.md` to produce an actionable list of incomplete and
> forgotten work. Treat **code as the only proof** — a doc status is a claim, not evidence.
>
> **Scope:** Read-only on the two canonical docs. You may read any source/test/CI file to verify.
>
> **Method:**
> 1. **Extract non-complete items.** From both docs, list every item whose status is not `Baseline Complete`
>    or `Polished Complete`: `Not Started`, `In Progress`, `Blocked`, `Deferred`, `Partial`. Capture line anchors.
> 2. **Find buried follow-ons.** Grep both docs for `follow-up|follow-on|not yet|deferred to|TODO|FIXME|stub|
>    remaining:|still (missing|needed|pending)`. These are sub-tasks hidden inside "Baseline Complete" phases —
>    the real Baseline→Polished gap.
> 3. **Cross-reference.** Map roadmap `R-IDs` ↔ `phases.md` phases. Flag (a) the same item with **different
>    statuses** in the two docs, (b) roadmap items with no phase, (c) recorded phases with no roadmap row.
> 4. **Reality spot-check the suspicious.** For each "stale-complete" or "forgotten" candidate, verify against
>    code/tests. Classify each as **doc-lag** (work done, doc says incomplete → update the doc) or
>    **genuinely-incomplete** (doc is right → it's real remaining work).
> 5. **Classify Blocked/Deferred.** For each, record *what unblocks it* (external host, paid-call policy,
>    human-gated safety boundary, separate plan) so parked items are distinguishable from actionable ones.
>
> **Output:** Five buckets — (A) Genuinely incomplete (Blocked/Not Started/Deferred/Partial, with unblock
> condition); (B) Doc-lag inconsistencies (work done, label stale, with code evidence); (C) Completeness gaps
> (phases/roadmap not reflected in the other); (D) Baseline→Polished gap (deferred sub-items in done phases);
> (E) Recommended doc edits. Cite a file:line or commit/test anchor for every claim. Do not relabel anything
> `Polished Complete` without citing every DoD gate (`AGENTS.md`).

---

## Part 2 — Executed findings (2026-06-08)

Inventory size: **187 unique roadmap R-IDs**, **195 phases** (highest `Phase 195`). roadmap.md status
distribution: 407 `Baseline Complete`, 13 `Deferred`, 6 `Not Started`, 5 `Blocked`, 1 `In Progress`,
**0 `Polished Complete`** (legend only). phases.md: 382 `Baseline Complete`, **0 `Polished Complete`**.

### A. Genuinely incomplete (real remaining work)

| Item | Status | Where | Unblock condition |
|---|---|---|---|
| Ph34.6 / R34.6 — Provider-Backed Battle Arena | Blocked | roadmap L170, phases L158 | Requires default paid/live provider calls (policy-gated). |
| Ph66 — Firecracker Opt-In Host Proof Evidence | Blocked | phases L160 | Needs a Linux/KVM host (cannot run on macOS). |
| Ph67 — Reviewed Memory Evidence Fixture Pack | Blocked | phases L161 | Needs a human-reviewed memory evidence pack. |
| Ph70 — Reviewed Memory Evidence Pack Gate | Blocked | phases L162 | Depends on Ph67. |
| Ph32 — Event Notifications | Not Started | phases L2608 | P2 / enterprise-compliance; no slice begun. |
| R79.3 — Device posture / MDM hooks | Not Started | roadmap L167 | Buildable in simulator-preview posture; no slice begun. |
| R79.4 — Mobile package supply-chain provenance (SLSA/sigstore) | Not Started | roadmap L168 | Not implemented. |
| R79.5 — Mobile-package dependency vuln scanning (npm/pub audit) | Not Started | roadmap L169 | Python deps scanned via `pip-audit`; mobile trees not. |
| R79.1 — Real native framework package builds | Deferred | roadmap L165 | Gated behind native toolchains + Phase 11. |
| R79.2 — Native device-capability execution (Phase 11) | Deferred | roadmap L166 | Human-gated safety boundary; out of scope. |
| LM Arena live productization | Deferred | roadmap L447/L478 | Requires a separate plan/gates/tests/docs. |
| Ph104/105 — microVM Linux/Firecracker host proof | Deferred (v0.8+) | phases L177/L200 | Linux/KVM host access. |
| R6 — `langgraph+swarmgraph` provider-backed real runtime | Partial (intentional) | phases L461/L466 | Local-real baseline done; provider-backed deliberately not claimed. |

### B. Doc-lag inconsistencies (work done — labels are stale; fix the docs)

1. **[HIGH] R79 / Phase 111 status conflict — 110.6 is actually DONE.**
   - roadmap **L164**: `R79 | Baseline Complete` (evidence cites "Theia Mobile Runtime IDE tab").
   - roadmap **L1695**: `R79 | Partial — Slices 110.1–110.5 shipped; 110.6 follow-up`.
   - phases **L165**: `Phase 111 | Partial — slices 110.1–110.5 done; 110.6 Theia/TUI surfacing follow-up`.
   - **Code reality:** `packages/arc-extension/src/browser/arc-mobile-widget.tsx` + `arc-mobile-contribution.ts`
     + `__tests__/arc-mobile-widget.test.tsx` **exist** → the Theia/TUI mobile surfacing (110.6) shipped.
   - **Verdict:** roadmap L1695 + phases L165 are **stale**. Update both to `Baseline Complete` (matching L164).

2. **[LOW] R6 wording mismatch.** roadmap L51 `Complete (local-real baseline)` vs phases L461/L466 `Partial`.
   Both are honest in context (local-real done; provider-backed not claimed) but the labels read inconsistently —
   align on `Baseline Complete (local-real baseline; provider-backed deferred)`.

### C. Completeness gaps (recorded in one place, thin in the other)

- **Phases 187–192 (mobile roadmap impl, Batch 5)** are fully recorded in phases.md (L6011–L6086) but the
  roadmap surfaces mobile only via the **R79** umbrella + R79.x (remaining) + R-MOBILE-CLI/HARDEN (Batch 6 C/D).
  The completed Batch 5 phases (Expo buildable, secure storage/egress/queue, RN/Flutter scaffolds, SIEM/RBAC,
  entry-gate, MCP bridge) have **no dedicated roadmap rows**. Likely intentional (folded under R79), but the
  roadmap under-reflects what shipped. *Recommendation:* add a short "R79 delivered slices" note or per-phase rows.
- Positive: this session's **Phases 187–195 are all present** in phases.md — nothing forgotten there.

### D. Baseline → Polished gap (deferred sub-items inside "Baseline Complete" phases)

These are the concrete tasks standing between Baseline and Polished. Each lives inside a phase already marked
`Baseline Complete`, so they are easy to forget:

| Sub-item | Anchor |
|---|---|
| R-UX2: ApprovalCard event-driven mount / data-stream subscription not wired | roadmap L1240 |
| R-UX3: per-command frontmatter `.md`, DiffViewer side-by-side toggle, ToolCard rerun | phases L197 |
| R-UX4: `/statusline` slot reordering not configurable; `ux/mockups/` not preserved | roadmap L1242, phases L198 |
| R-AUDIT16: IDE Context Drawer renders **stub data** — CLI proxy wiring is a follow-on | roadmap L1732 |
| Phase 4.1: tokenizer estimator runtime/REPL integration deferred | phases L903/L906 |
| Phase 26: SwarmGraph MCP wrappers deferred (Ph28+); MCP control plane **not wired to IDE** | phases L1250/L1251 |
| Phase 31: `--consensus-escrow` flag deferred | phases L1433/L1457 |
| Phase 34.x: battle real-time updates + cancellation are follow-ups; `arc runs replay` determinism for battle runs **not verified** | phases L1779/L1801 |
| Phase (task tool): task execution uses **placeholder operations** (TODO: integrate run/trace/audit) | phases L1311 |
| Enforcement gating of critical surfaces (SwarmGraph/isolation/gateway/provider actions) deferred — TODO markers | phases L1088/L1091 |
| `_legacy_cli.py` duplicate command definitions — cleanup follow-up | phases L1210 |
| SwarmGraph compile/optimize lifecycle not surfaced in events (future T3) | phases L1492 |

### E. Recommended actions (no doc edits made yet)

1. **Fix the stale R79/Phase 111 label** → set phases.md L165 + roadmap L1695 to `Baseline Complete` (code proof
   above). *(1-line edits, both canonical docs, banned-claims-safe.)*
2. **Align R6 wording** between roadmap L51 and phases L461/L466.
3. **Decide on Phases 187–192 roadmap representation** (umbrella note under R79 vs per-phase rows).
4. **Triage the Blocked items:** Ph66 (Linux host) and Ph34.6 (paid calls) are externally parked; Ph67+Ph70
   (Reviewed Memory Evidence) need a decision on producing the evidence pack — confirm owner/plan or mark Deferred.
5. **Track the Baseline→Polished sub-items (bucket D)** explicitly if v0.2 polish is in scope; otherwise they stay
   correctly deferred but should be visible (they currently hide inside Baseline-Complete phases).

**Honest note:** Most "incomplete" items are *intentionally* Blocked/Deferred/gated (safety or external
dependency), not neglected. The one clear **defect** is the stale R79/Phase 111 `Partial` label (110.6 shipped).
