# Roadmap Impact

> Research basis: uploaded `ARC_STUDIO_UX_SPEC.md` (2026-05-16), uploaded `CLI_IDE_REDESIGN_PLAN.md` (2026-05-15), public competitor/frontier research available on 2026-05-16, and architectural assumptions stated in the task. I could not read repository-only `docs/adr/`, `AGENTS.md`, or `feature-roadmap-review/*.md` because the GitHub search connector had no selected ARC repo; claims depending on those files are marked [needs internal verification].

## Existing Plan Sections That Should Change

| Existing area | Change |
|---|---|
| v0.1 Scope | Add minimal Run Contract, Run Receipt, Failure Autopsy, EvidenceRefs, stable event linkage. |
| Reserved Protocol | Add `run_contract`, `evidence_refs`, `decision_id`, `policy_decision`, `trust_diff`, `frame_receipt`, `capability_snapshot`. |
| CLI Layouts | Add `/preview`, `/contract`, `/receipt`, `/autopsy`, `/evidence` as default or near-default commands. |
| IDE Layouts | Add ContractCard, EvidenceCard, AutopsyCard, TrustDiffModal, node cross-highlighting. |
| Runtime Manifest Appendix | Extend from capabilities/events/panel slots to negotiated guarantees/evidence/cost/recovery/handoff. |
| Runs Panel | Runs summary should include contract fulfillment, receipt, evidence, autopsy; not trace timeline. |
| Graph Visualizer | Add node action metadata and cross-surface linkage. |
| Config/Trust | Trust weakening must show diff before save. |
| `/doctor` | Add runtime manifest/conformance probe reservations. |
| HotLoop Reservation | Add frame receipts and visual contract hooks. |

## v0.1 Lock Criteria To Add

1. Every run has a `RunContract` object, even if minimal.
2. Every completed/failed run has a `RunReceipt` artifact.
3. Every failed run has a `FailureAutopsy` object with evidence-vs-guess split.
4. Assistant claims can carry optional `EvidenceRef[]`; unsupported claims can be visibly marked later.
5. Graph events include stable `node_id` and cross-links to messages/tool calls when available.
6. Runtime manifests include reserved fields for evidence, cost model, recovery, handoff, and conformance.
7. Policy/trust/provider changes can produce a structured Trust Diff.
8. CLI/IDE actions are idempotent with shared approval IDs.
9. `/doctor` validates manifest shape.
10. No default raw Trace UI is reintroduced.

## Move Up / Move Down

| Item | Current likely timing | Recommendation | Reason |
|---|---:|---:|---|
| Run Receipts | Not explicit | v0.1 | Low cost, high trust. |
| Failure Autopsy | Partial FailureCard | v0.1 | Needed because Trace UI is hidden. |
| Evidence refs | Not explicit | v0.1 reservation | Avoid repainting storage. |
| Graph/chat cross-links | Not explicit | v0.1 reservation/partial | Cheap differentiator. |
| Trust Diff | Not explicit | v0.1/v0.2 | Security differentiation. |
| Runtime negotiation | v0.2 implied | v0.1 reservation, v0.2 implementation | Manifest design must anticipate it. |
| Handoff Workbench | v0.2 | Keep v0.2 | Needs planner/router. |
| HotLoop | v0.2 | Keep v0.2, add frame receipts now | Avoid premature risky visual agent. |
| Full replay/audit explorer | v0.3 | Keep v0.3 | Respect no Trace UI v0.1. |
| Secure delegation tokens | Not planned | Research | Too complex for near-term. |
| Local memory with receipts | Not planned | v0.2+ research | Useful but riskier. |

## Dependency Graph

```text
Stable Event IDs
  -> Graph/Chat Cross-Highlighting
  -> Evidence Cards
  -> Failure Autopsy
  -> Intent Ledger
  -> Run Receipts

Runtime Manifest Extensions
  -> Capability Negotiation
  -> Cost-Risk Preview
  -> Handoff Workbench
  -> Runtime Black Box Tests

Policy Decision Events
  -> Trust Diff
  -> Policy Simulator
  -> Visual Run Contracts
  -> Secure Delegation Tokens (future)

Frame Receipt Reservation
  -> HotLoop Device/Frames
  -> Visual Diff Contracts
  -> Multimodal Evidence Cards
```

## Risk Table

| Risk | Impact | Mitigation |
|---|---|---|
| v0.1 scope creep | Missed release. | Ship receipts/autopsy as summaries, reserve heavier UI. |
| Schema churn | v0.2 repaint. | Reserve stable IDs and optional fields now. |
| Evidence noise | Users ignore cards. | Collapse by default; show unsupported claims only where valuable. |
| Trust fatigue | Users click through. | Diff only when weakening permissions. |
| Runtime manifest overclaim | Unsafe routing. | Black-box probes before enabling guarantees. |
| Missing internal docs | Review may miss ADR constraints. | Re-run after repo docs are connected/selected. |

## Revised Milestones

| Milestone | Scope |
|---|---|
| v0.1 Lock | Chat-first plus minimal cockpit primitives: contract, receipt, autopsy, evidence refs, stable IDs. |
| v0.1 Alpha | CLI/IDE show receipts/autopsies; graph cross-links minimal; trust diff for weakened policy. |
| v0.2 | Runtime negotiation, handoff workbench, HotLoop frame receipts, policy simulator, richer evidence UI. |
| v0.3 | Audit explorer, replay, differential debugger, parallel phases, secure delegation token prototype. |
