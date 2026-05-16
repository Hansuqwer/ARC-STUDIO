# Plan / Tasks Review

## Current ARC Spec

The ARC Studio spec defines Plan/Tasks across several sections:

### Plan Mode (§7.13, §10.4)
- `/plan` is a **read-only mode** — disables writes and paid calls. It is a permission mode, not a planning agent.
- Mode chip in status line: `[Plan]`, `[Build]`, or `[Auto]`. `Tab` cycles `Plan → Build → Auto → Plan`.
- Plan copy: "Read-only. No writes or paid calls."
- `/build` switches back to apply-capable mode.
- Plan mode is defined as a **permission toggle**, not a multi-phase planner.

### Tasks Panel (§8.2)
- The Tasks panel replaces the previous planning sidebar.
- `/plan` remains the read-only mode command; `/tasks` opens the Tasks panel.
- Three views defined:

| View | v0.1 Status | Content |
|---|---|---|
| Step view | **Ships** | Runtime step list, blockers, current node, in-phase subtasks |
| Phase view | **Reserved v0.2** | Phase cards, runtime badges, cost ceilings, handoff document links |
| Loop trace view | **Reserved v0.2** | Observation loop ticks, target/device state, frame references |

- Runtime chooses default view. Phase and Loop trace views render reservation empty states in v0.1.
- User can toggle view when more than one view exists.

### CLI `/tasks` Phased Plan View (§7.15 — reserved v0.2)
- Shows multi-phase plan with runtime badges, cost ceilings, and handoff documents.
- Actions: `[Approve plan] [Edit phase] [Re-plan] [Cancel]`.
- Keys: arrows navigate phases, Enter expands, `e` edits phase, `a` approves plan, `r` replans.
- **Entirely reserved for v0.2** — no v0.1 implementation.

### PhaseCard Component (§9 — reserved v0.2)
- `PhaseCardProps`: phaseNumber, title, runtime, estimatedCostCeilingUsd, status, substeps, handoffDocumentRef.
- Represents one planner phase in Tasks Phase view.
- **Reserved v0.2** — not implemented in v0.1.

### Planner, Router, Handoff Copy (§10.7 — reserved v0.2)
- Planner approval: "Plan ready: {N} phases, estimated {min}-{max}. Approve to start with phase 1: {title}."
- Phase boundary: "Phase {n} done. Next: {title} on {runtime}. Carrying: {summary}. Continue?"
- Router suggestion: "This looks like UI work. HotLoop iterates faster here. Switch?"
- **All reserved v0.2 copy** — not exposed in v0.1.

### Reserved Protocol Elements (§0.5)
- `handoff` event kind reserved: carries `goal_for_next_phase`, `state`, `constraints`, `references`, `prior_audit_links`. No v0.1 runtime emits it.
- Tasks phase/loop views reserved in v0.1 protocol.
- `phase_advance` in auto policy is reserved for v0.2 planner integration (§7.13.1).

### Current Implementation Status
- **No Plan/Tasks panel exists** in the current codebase. The existing `arc-widget.tsx` has a "planning" execution step (line 252) but no dedicated Tasks panel or plan mode toggle.
- **No ModeToggle component** exists. Plan/Build/Auto mode switching is spec-only.
- **No `/plan` or `/tasks` slash commands** are implemented.
- The spec is clear that the planner (multi-phase planning agent) is v0.2. v0.1 ships only Step view within Tasks panel.

---

## Comparable Products / Research

| Feature | Claude Code | Cursor | Windsurf | OpenCode | Kiro | ARC Studio (spec) |
|---|---|---|---|---|---|---|
| **Plan mode (read-only)** | Yes — `/plan` or Shift+Tab cycle; reads only, no edits | Yes — numbered plan steps before execution | No explicit "plan mode"; Cascade has Write/Chat/Image modes | Yes — Plan/Build toggle via Tab key | Yes — spec-driven development with spec timelines | Spec: `/plan` read-only mode, Tab cycle |
| **Plan approval flow** | Yes — presents plan, offers: approve+auto, approve+acceptEdits, approve+manual, keep planning, Ultraplan | Yes — numbered steps, user approves before execution | No explicit plan approval; Cascade proposes and acts | No formal approval; plan mode is read-only only | Yes — spec approval before implementation | Spec: `[Approve plan] [Edit phase] [Re-plan] [Cancel]` (v0.2) |
| **Cloud planning** | Yes — `/ultraplan` drafts plan in cloud, browser review with inline comments, emoji reactions, execute web or teleport back | No | No — "Devin in Windsurf" delegates to cloud agent but not plan-specific | No | [needs verification] | No |
| **Task/step tracking** | Yes — `/tasks` slash command shows ultraplan entry with session link, agent activity, stop action. Todo lists via Agent SDK. | Yes — numbered plan steps shown in chat | Yes — Cascade tracks edited/viewed files, terminal commands, suggests "Continue my work" | No dedicated task panel | Yes — spec timelines with task breakdown | Spec: Step view (v0.1), Phase/Loop views (v0.2) |
| **Multi-phase plans** | No — single plan, not multi-phase with handoffs | No — single plan with numbered steps | No | No | Yes — specs with phases and timeline | Spec: Phase view reserved v0.2, handoff events reserved |
| **Phase boundaries / handoff** | No | No | No | No | [needs verification] | Spec: HandoffCard, phase transition flow (v0.2) |
| **Runtime routing suggestions** | No | No | No | No | No | Spec: Router suggestion card (v0.2) |
| **Plan editing** | Yes — `Ctrl+G` opens plan in editor; Ultraplan supports inline comments, emoji reactions, revision requests | No — plan is presented, not edited | No | No | [needs verification] | Spec: `[Edit phase]` action (v0.2) |
| **Acceptance criteria per task** | No | No | No | No | [needs verification] | Not specified |
| **Plan as persisted artifact** | Yes — Ultraplan persists in cloud session; local plans persist in transcript | No — plan is ephemeral per session | No | No | [needs verification] | Not specified |
| **Checklist support** | Yes — Agent SDK has Todo Lists feature | No | No — Cascade tracks implicit intent via file/terminal activity | No | [needs verification] | Not specified |

### Key Takeaways from Competitors

1. **Plan mode as read-only is universal.** Claude Code, Cursor, and OpenCode all implement plan mode as a permission mode that restricts writes. This is table stakes.

2. **Plan approval is the critical handoff.** Claude Code has the richest approval flow: approve+auto, approve+acceptEdits, approve+manual, keep planning, or Ultraplan. Cursor uses a simpler approve/decline. ARC's spec aligns with this pattern for v0.2.

3. **Nobody does multi-phase plans with handoffs.** Claude Code's plan is single-phase. Cursor's numbered steps are sequential within one plan. Kiro's spec-driven approach is the closest to ARC's multi-phase vision but details are [needs verification]. ARC's Phase view, handoff events, and phase boundary confirmation are genuinely novel.

4. **Cloud planning is Claude Code's differentiator.** `/ultraplan` drafts plans remotely with browser-based review (inline comments, emoji reactions). This is a research preview (v2.1.91+) and requires Claude Code on the web. ARC should not attempt this in v0.1 or v0.2.

5. **Task tracking is implicit in most products.** Windsurf tracks implicit intent (file edits, terminal commands, clipboard). Claude Code's `/tasks` shows ultraplan status. Cursor shows numbered steps in chat. Only Kiro appears to have structured task timelines [needs verification].

6. **No product has acceptance criteria per task.** This is a gap across all competitors. ARC could differentiate here if it fits the high-assurance positioning.

7. **Plans are ephemeral except Claude Code's Ultraplan.** Plans exist only within the session transcript. No product persists plans as standalone artifacts that survive session boundaries.

---

## Gaps

### G1: Plan mode toggle not implemented
The spec defines Plan/Build/Auto mode cycling, but no `ModeToggle` component, `/plan` slash command, or mode-switching logic exists in the codebase. The only reference is a "planning" execution step in `arc-widget.tsx:252`.

### G2: Tasks panel not implemented
No Tasks panel exists. The spec defines Step view for v0.1 (runtime step list, blockers, current node, in-phase subtasks), but no component or data model exists for it.

### G3: Step view data source undefined
The spec says Step view shows "runtime step list, blockers, current node, in-phase subtasks" but does not define:
- Where step data comes from (runtime events? LLM-generated plan? trace events?)
- What "blockers" means in the context of SwarmGraph execution
- How "in-phase subtasks" map to SwarmGraph queen/worker topology
- Whether steps are generated by the runtime or by a planning LLM call

### G4: No plan output persistence
Plans exist only in the chat transcript. If the user closes the session, the plan is gone. No product besides Claude Code's Ultraplan persists plans, but ARC's high-assurance positioning (audit trails, signed records) suggests plans should be auditable artifacts.

### G5: No acceptance criteria model
The spec does not define acceptance criteria per task. This is a missed opportunity for ARC's high-assurance positioning — SwarmGraph adoption runs could verify acceptance criteria before marking a phase complete.

### G6: Plan approval not wired to anything
The spec defines `[Approve plan]` action for v0.2, but does not specify:
- What happens when a plan is approved (does it switch mode? start a run? create a session?)
- Whether approval is recorded in the audit trail
- Whether approval can be revoked

### G7: Relationship between Plan mode and Tasks panel is unclear
The spec says `/plan` is read-only mode and `/tasks` opens the Tasks panel. But:
- Can you view Tasks in Build mode? (Presumably yes.)
- Does Plan mode automatically open Tasks? (Unclear.)
- Does Tasks panel require Plan mode? (Should not.)
- The relationship between mode (permission) and panel (visualization) is not defined.

### G8: No checklist/manual task support
The spec does not address whether users can manually add tasks or checklists in v0.1. Competitors (Claude Code Agent SDK Todo Lists) support this. For v0.1, manual checklists could be useful even without the planner.

### G9: Step view vs execution steps conflated
The current codebase has "execution steps" (planning, executing, completed) in `arc-widget.tsx`. The spec's Step view is different — it shows runtime steps within a phase. These concepts are conflated and need disambiguation.

### G10: No empty/loading/error states for Tasks panel
The spec's state table (§15) has a row for Plan/Tasks but the states are vague:
- Empty: "not-yet-planned"
- Loading: "planning"
- Populated: "executing-phase-N"
- Error: "failed-at-phase-N"

These assume the planner exists (v0.2). v0.1 Step view needs its own state definitions.

---

## Improvement Proposals

| Proposal | Why | v0.1/v0.2/v0.3 | Risk | Spec edits |
|---|---|---|---|---|
| **P1: Implement ModeToggle component for v0.1** | Plan/Build/Auto mode is table stakes. Every competitor has it. Without it, ARC cannot restrict writes or paid calls. | v0.1 | Low — simple UI component, backend enforcement already partially exists via workspace trust | §9 Toggle: add implementation note that ModeToggle is v0.1; §7.13: clarify that mode switching works without Tasks panel |
| **P2: Implement Step view as read-only execution observer for v0.1** | Step view should show live runtime steps during execution (node status, current worker, progress). This is useful without the planner. | v0.1 | Medium — needs runtime event mapping to step display | §8.2: redefine Step view content to "Live execution steps: current node, worker status, progress through runtime topology. No planner required." |
| **P3: Define step data source explicitly** | Without a defined data source, Step view cannot be implemented. Recommend: derive from existing `NODE_STARTED`, `NODE_UPDATE`, `NODE_COMPLETED` events that SwarmGraph already emits. | v0.1 | Low — uses existing event infrastructure | §8.2: add "Step view derives from runtime events: NODE_*, RUN_*. No planning LLM call required." |
| **P4: Add manual checklist support to Step view for v0.1** | Users need lightweight task tracking without the planner. A simple markdown-backed checklist (stored in session transcript) provides value with zero planner dependency. | v0.1 | Low — checklist is local state, no backend changes | §8.2: add "Step view supports optional user-created checklists. Checklists are stored in session transcript, not persisted across sessions." |
| **P5: Persist plan outputs as session artifacts starting v0.2** | Plans should be auditable. Store plan JSON in session directory alongside transcript. Enables replay, diff between planned vs actual, and audit chain linkage. | v0.2 | Medium — needs session storage schema addition | §7.15: add "Approved plans are stored as `{session_id}/plans/{plan_id}.json` in session directory. Plan JSON includes: phases, cost estimates, approval timestamp, approving user." |
| **P6: Add acceptance criteria field to Phase model for v0.2** | High-assurance positioning demands verifiable completion criteria. SwarmGraph adoption runs could check acceptance criteria before phase completion. | v0.2 | Medium — needs runtime support for criteria evaluation | §9 PhaseCard: add `acceptanceCriteria?: string[]` to PhaseCardProps; §7.15: add acceptance criteria display to phase cards |
| **P7: Wire plan approval to audit trail for v0.2** | Plan approval is a security-relevant decision. It should be recorded in the audit chain alongside HITL decisions. | v0.2 | Low — reuses existing HITL audit infrastructure | §7.15: add "Plan approval creates an audit record with: plan hash, approver, timestamp, approval mode." |
| **P8: Clarify Plan mode / Tasks panel independence** | Mode (permission) and panel (visualization) are orthogonal. Users should be able to view Tasks in any mode, and use Plan mode without Tasks. | v0.1 | None — spec clarification only | §8.2: add "Tasks panel is accessible in all modes. Plan mode does not auto-open Tasks. Tasks panel does not require Plan mode." |
| **P9: Disambiguate execution steps vs Step view steps** | Current codebase has "execution steps" (planning → executing → completed). Step view shows runtime topology steps. These need different names. | v0.1 | Low — rename only | §8.2: rename "Step view" to "Runtime Steps view"; §7.13: rename execution step to "run phase" or "lifecycle stage" |
| **P10: Define v0.1 Tasks panel empty state** | v0.1 has no planner, so Tasks panel cannot show "planned" phases. Need a useful empty state that doesn't imply planner functionality. | v0.1 | None — copy change only | §15: add v0.1-specific Tasks empty state: "No active run. Start a workflow to see runtime steps here." |
| **P11: Defer plan editing to v0.3** | Plan editing (`[Edit phase]`) requires a rich editor surface and plan persistence. Too complex for v0.2. Defer until plan artifacts are stable. | v0.3 | None — scope reduction | §7.15: change `[Edit phase]` to "Reserved v0.3"; §9 PhaseCard: remove edit action from v0.2 scope |
| **P12: Add plan diff view for v0.3** | When plans are re-planned or revised, users should see what changed. Leverages existing diff infrastructure. | v0.3 | Medium — needs plan versioning | New spec section: "Plan Diff View (v0.3): shows added/removed/modified phases between plan revisions." |

---

## Recommended Decisions

### D1: Plan mode ships in v0.1 as a permission toggle only
**Decision:** Implement `ModeToggle` component with Plan/Build/Auto cycling. Plan mode restricts writes and paid calls at the backend level. No Tasks panel dependency. No planner dependency.

**Rationale:** Plan mode is table stakes. Every competitor has it. It is a permission mode, not a planning feature. It should ship independently of Tasks, planner, or any v0.2 feature.

**Implementation:** 
- Create `ModeToggle.tsx` component per §9 Toggle spec
- Wire to existing workspace trust / paid-call gating infrastructure
- Store mode in session state
- CLI: `Tab` cycles; IDE: button toggle

### D2: Tasks panel ships in v0.1 with Step view only, driven by runtime events
**Decision:** Implement Tasks panel with Step view that shows live runtime execution steps derived from `NODE_*` and `RUN_*` events. No planner, no phases, no handoffs.

**Rationale:** Step view provides observability during execution without requiring the planner. It aligns with ARC's "See everything" tagline and is useful immediately.

**Implementation:**
- Create `TasksPanel.tsx` with Step view
- Map runtime events to step display
- Show current node, worker status, progress through topology
- Empty state: "No active run. Start a workflow to see runtime steps here."

### D3: Manual checklists are in-scope for v0.1 Step view
**Decision:** Allow users to add simple checklists in Step view. Checklists are stored in session transcript (not persisted across sessions). No planner dependency.

**Rationale:** Lightweight task tracking is useful even without the planner. Claude Code's Agent SDK has Todo Lists. A simple checklist provides value with minimal implementation cost.

**Implementation:**
- Add checklist UI to Step view
- Store checklist items in session transcript
- No backend changes required

### D4: Planner, Phase view, Loop trace view, and handoff are strictly v0.2
**Decision:** Do not implement any planner, phase, or handoff functionality in v0.1. Reserve protocol fields, event types, and UI slots as the spec already defines.

**Rationale:** The planner is a significant feature that requires:
- A planning LLM call (separate from execution)
- Multi-phase plan generation
- Cost estimation
- Handoff document generation
- Phase boundary management
- Plan approval with audit linkage

None of this should ship in v0.1. The spec already reserves these correctly.

### D5: Plan outputs become persisted artifacts starting v0.2
**Decision:** When the planner ships in v0.2, approved plans are stored as JSON files in the session directory. Plan JSON includes phases, cost estimates, acceptance criteria, approval timestamp, and plan hash for audit linkage.

**Rationale:** ARC's high-assurance positioning demands auditable plans. Persisted plans enable:
- Replay: "What was the plan for this run?"
- Diff: "How did the plan change between revisions?"
- Audit: "Who approved this plan and when?"
- Eval: "Did the execution match the plan?"

### D6: Acceptance criteria per task are v0.2 scope
**Decision:** Add `acceptanceCriteria` field to Phase model in v0.2. Do not implement in v0.1.

**Rationale:** Acceptance criteria are useful for high-assurance workflows but require runtime support for evaluation. This is too complex for v0.1.

### D7: Plan approval is recorded in audit trail starting v0.2
**Decision:** Plan approval creates an audit record with plan hash, approver, timestamp, and approval mode. Reuses existing HITL audit infrastructure.

**Rationale:** Plan approval is a security-relevant decision in high-assurance workflows. It should be auditable alongside HITL decisions.

### D8: Plan editing is deferred to v0.3
**Decision:** Remove `[Edit phase]` from v0.2 scope. Plan editing requires plan persistence, versioning, and diff infrastructure that v0.2 does not have.

**Rationale:** Plan editing is complex:
- Requires plan persistence (v0.2)
- Requires plan versioning (v0.2+)
- Requires plan diff view (v0.3)
- Requires re-approval workflow (v0.3)

Defer until the foundation is stable.

---

## Specific Spec Edits

### §0.5 v0.1 Scope — In, Out, Reserved
- **Add to "In Scope For v0.1" table:**
  - `Tasks | Step view (runtime execution steps), manual checklists. No planner, no phases.`
  - `Mode | Plan/Build/Auto toggle. Plan restricts writes and paid calls.`

- **Add to "Out Of Scope For v0.1" table:**
  - `Plan editing | Plan revision, re-approval, plan diff deferred to v0.3`

### §7.13 Plan / Build / Auto Chip
- **Add after paragraph 1:**
  > Plan mode is a permission toggle. It does not open the Tasks panel, invoke a planner, or generate a plan. Plan mode works independently of the Tasks panel. The Tasks panel is accessible in all modes.

### §7.15 `/tasks` Phased Plan View (reserved v0.2)
- **Add before the code block:**
  > v0.1 implements `/tasks` as a Step view showing live runtime execution steps. The phased plan view described here is reserved for v0.2 when the planner exists.

- **Change `[Edit phase]` to:**
  > `[Edit phase]` — Reserved v0.3. Plan editing requires plan persistence and versioning.

### §8.2 Tasks Panel Views
- **Replace the current table with:**

| View | v0.1 status | Default when | Content |
|---|---|---|---|
| Step view | **Ships v0.1** | Any active run | Runtime execution steps derived from `NODE_*` and `RUN_*` events: current node, worker status, progress through topology. Optional user-created checklists stored in session transcript. No planner required. |
| Phase view | Reserved v0.2 | Planner emits multi-phase plan | Phase cards, runtime badges, cost ceilings, acceptance criteria, handoff document links. Requires planner. |
| Loop trace view | Reserved v0.2 | HotLoop active phase | Observation loop ticks, target/device state, frame references. Requires HotLoop. |

- **Add after the table:**
  > Tasks panel is accessible in all modes (Plan, Build, Auto). Plan mode does not auto-open Tasks. Tasks panel does not require Plan mode. Step view derives from runtime events, not from a planning LLM call.

- **Add empty state for v0.1:**
  > v0.1 Step view empty state: "No active run. Start a workflow to see runtime steps here." Loading state: "Waiting for runtime events..." Error state: "Runtime steps unavailable. Check run status."

### §9 PhaseCard (reserved v0.2)
- **Add to PhaseCardProps interface:**
  ```ts
  acceptanceCriteria?: string[];
  ```

- **Add after PhaseCardProps:**
  > Acceptance criteria are verifiable conditions that must be met for a phase to be considered complete. SwarmGraph adoption runs may evaluate acceptance criteria before marking a phase done. Acceptance criteria are optional in v0.2.

### §9 Toggle
- **Add implementation note:**
  > ModeToggle is a v0.1 component. It does not depend on Tasks panel, planner, or any v0.2 feature. Mode switching works by updating session state and enforcing permission checks at the backend level.

### §10.4 Help Text
- **Update `/tasks` entry:**
  ```
  /tasks      open the Tasks panel (Step view in v0.1; phases reserved v0.2)
  ```

### §15 States And Edge Cases
- **Update Plan/Tasks row:**

| Surface | Empty | Loading | Populated | Error | Offline | Awaiting approval | Applied/Rolled back | v0.2 HotLoop |
|---|---|---|---|---|---|---|---|---|
| Plan/Tasks (v0.1 Step view) | "No active run" | "Waiting for runtime events" | Runtime steps + checklists | "Steps unavailable" | Cached steps if available | N/A (v0.2) | N/A (v0.2) | Phase/Loop views reserved |
| Plan/Tasks (v0.2 Phase view) | not-yet-planned | planning | executing-phase-N | failed-at-phase-N | blocked | awaiting-approval | completed | Reserved |

### New section after §8.2: Step View Data Model
- **Add:**
  > Step view derives from runtime events. No planning LLM call is required.
  >
  > **Event mapping:**
  > - `RUN_STARTED` → Step view shows "Run starting"
  > - `NODE_STARTED` → Step view adds step for node, marks as running
  > - `NODE_UPDATE` → Step view updates node status
  > - `NODE_COMPLETED` → Step view marks step done
  > - `NODE_FAILED` → Step view marks step failed with error
  > - `RUN_COMPLETED` → Step view shows "Run complete"
  >
  > **Checklist storage:**
  > Checklist items are stored in session transcript as `checklist_item` entries. They are not persisted across sessions. Checklist items support: add, toggle complete, delete. No backend changes required.

---

## Acceptance Criteria

### v0.1 Plan Mode
- [ ] `ModeToggle` component renders Plan/Build/Auto segments
- [ ] `Tab` key cycles modes in CLI
- [ ] Button click cycles modes in IDE
- [ ] Plan mode prevents file writes (verified by test)
- [ ] Plan mode prevents paid provider calls (verified by test)
- [ ] Mode persists within session (survives message send/receive)
- [ ] Mode does not persist across sessions (default to Build on new session)
- [ ] Live region announces mode change per §14 accessibility
- [ ] Status bar shows current mode chip

### v0.1 Tasks Panel — Step View
- [ ] Tasks panel renders in IDE sidebar
- [ ] Step view is the default (only) view in v0.1
- [ ] Step view shows runtime execution steps during active run
- [ ] Steps update in real-time from `NODE_*` events
- [ ] Step view shows current node, worker status, progress
- [ ] Empty state: "No active run. Start a workflow to see runtime steps here."
- [ ] Loading state: "Waiting for runtime events..."
- [ ] Error state: "Runtime steps unavailable. Check run status."
- [ ] Tasks panel is accessible in Plan, Build, and Auto modes
- [ ] Tasks panel does not auto-open when entering Plan mode
- [ ] Plan mode works without Tasks panel open

### v0.1 Tasks Panel — Manual Checklists
- [ ] User can add checklist items in Step view
- [ ] User can toggle checklist items complete/incomplete
- [ ] User can delete checklist items
- [ ] Checklist items are stored in session transcript
- [ ] Checklist items are lost when session ends (by design)
- [ ] Checklist UI does not imply planner functionality

### v0.1 Protocol Reservations
- [ ] `handoff` event kind is reserved but not emitted
- [ ] Phase view tab/slot is reserved with empty state
- [ ] Loop trace view tab/slot is reserved with empty state
- [ ] `phase_advance` in auto policy is reserved
- [ ] No v0.1 code references planner, phases, or handoffs

### v0.2 Reservations (not implemented in v0.1)
- [ ] PhaseCard component stub exists with `acceptanceCriteria` field
- [ ] HandoffCard component stub exists
- [ ] RuntimeSuggestionCard component stub exists
- [ ] Plan approval audit record schema is defined
- [ ] Plan JSON storage schema is defined
- [ ] Plan editing is documented as v0.3

---

## Reject / Do Not Build

### R1: Do not build a planner in v0.1
**Rejected:** Multi-phase plan generation, cost estimation, and handoff document creation.

**Reason:** The planner requires a dedicated planning LLM call, multi-phase reasoning, cost estimation logic, and handoff document generation. This is a significant feature that deserves its own design and implementation cycle. Shipping it in v0.1 would delay release and introduce untested complexity.

### R2: Do not build plan editing in v0.2
**Rejected:** `[Edit phase]` action, plan revision UI, plan re-approval workflow.

**Reason:** Plan editing requires plan persistence (v0.2), plan versioning (v0.2+), plan diff view (v0.3), and re-approval workflow (v0.3). Editing a plan that cannot be diffed or versioned is worse than no editing. Defer to v0.3.

### R3: Do not build cloud planning (Ultraplan equivalent)
**Rejected:** Remote plan drafting, browser-based plan review, inline comments on plans, emoji reactions, cloud execution.

**Reason:** Claude Code's Ultraplan requires cloud infrastructure, web sessions, Remote Control, and a dedicated review surface. ARC is local-first in v0.1. Cloud planning is a fundamentally different product direction that should not be attempted without explicit infrastructure and design work.

### R4: Do not build acceptance criteria evaluation in v0.1
**Rejected:** Runtime evaluation of acceptance criteria, automated pass/fail for phase completion.

**Reason:** Acceptance criteria evaluation requires: criteria parsing, runtime evaluation logic, integration with SwarmGraph adoption runs, and failure handling. This is v0.2 scope at minimum. v0.1 should not imply automated verification exists.

### R5: Do not build plan-as-artifact persistence in v0.1
**Rejected:** Plan JSON storage, plan versioning, plan replay, plan diff.

**Reason:** Plan persistence requires the planner to exist first. Storing plans that no planner generates is dead code. Add in v0.2 when the planner ships.

### R6: Do not build Kiro-style spec timelines in v0.1
**Rejected:** Spec-driven development with timeline visualization, spec approval gates, spec-to-task mapping.

**Reason:** Kiro's spec-driven approach is a product philosophy, not a feature. ARC's equivalent is the multi-phase planner with handoffs (v0.2). Attempting to build spec timelines without the planner produces a visualization with no backend. Defer to v0.2+.

### R7: Do not auto-open Tasks panel when entering Plan mode
**Rejected:** Automatic panel opening on mode switch.

**Reason:** Mode (permission) and panel (visualization) are orthogonal. Users enter Plan mode for various reasons (code exploration, cost inspection, safe workspace navigation). Forcing Tasks panel open is focus theft and implies a planning workflow that does not exist in v0.1.

### R8: Do not persist checklists across sessions in v0.1
**Rejected:** Checklist persistence in session directory or workspace file.

**Reason:** Cross-session persistence requires a storage schema decision. Checklists in v0.1 are lightweight scratchpad. If users need persistent task tracking, they should use their existing tools (GitHub issues, Jira, markdown TODO files). Add persistence in v0.2 if user demand exists.
