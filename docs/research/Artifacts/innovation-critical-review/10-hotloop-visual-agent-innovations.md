# HotLoop Visual Agent Innovations

> Research basis: uploaded `ARC_STUDIO_UX_SPEC.md` (2026-05-16), uploaded `CLI_IDE_REDESIGN_PLAN.md` (2026-05-15), public competitor/frontier research available on 2026-05-16, and architectural assumptions stated in the task. I could not read repository-only `docs/adr/`, `AGENTS.md`, or `feature-roadmap-review/*.md` because the GitHub search connector had no selected ARC repo; claims depending on those files are marked [needs internal verification].

## Core Critique

HotLoop should not ship early as “AI clicks around screenshots.” That market is crowded and risky. ARC should ship HotLoop only when it can make visual loops accountable: every frame, action, diff, and approval should be receipted.

## HotLoop Frontier

| Concept | What it means | When |
|---|---|---|
| Frame Receipts | Each visual observation/action records frame hash, target, action, evidence, and result. | Reserve v0.1, v0.2 implementation. |
| Visual Run Contract | Objective, devices, allowed UI actions, max loops, max cost, rollback/checkpoint plan. | v0.2. |
| Visual Diff Contracts | Before/after screenshots tied to user intent and acceptance criteria. | v0.2. |
| Visual Failure Autopsy | Identify last successful frame, failed action, suspected selector/layout issue. | v0.2/v0.3. |
| HotLoop Handoff | SwarmGraph backend phase hands UI objective/state to HotLoop with constraints/evidence. | v0.2. |
| Multimodal Evidence Cards | Screenshot regions as evidence, not just images in chat. | v0.2/v0.3. |

## Visual Loop UX

HotLoop should default to Device + Frames panels, not Graph. However, it should still produce a logical run graph:

- Plan node.
- Observe frame node.
- Action node.
- Evaluate frame node.
- HITL approval node.
- Rollback/checkpoint node.

This lets ARC preserve cockpit semantics across non-graph visual runtimes.

## Multimodal Risks

| Risk | Mitigation |
|---|---|
| Agent clicks destructive UI. | Visual run contract, action allowlist, HITL for destructive labels. |
| Screenshots leak secrets. | Redaction and frame storage scope. |
| Visual hallucination. | Evidence cards require frame region and OCR/DOM proof when available. |
| Infinite visual loops. | Max loop count, cost ceiling, progress invariant. |
| Non-reproducible UI state. | Frame receipts, checkpoints, environment metadata. |
| Accessibility bypass. | Prefer semantic accessibility tree/DOM when possible, screenshots as evidence not sole control. |

## Why Not Ship Too Early

HotLoop without receipts becomes a flashy unsafe browser/device agent. It would dilute the v0.1 cockpit thesis and create support burden. Reserve the schema now:

```ts
interface FrameReceipt {
  frameId: string;
  frameHash: string;
  timestamp: string;
  target: string;
  action?: string;
  evidenceRefs: EvidenceRef[];
  redactionReport?: string;
  checkpointRef?: string;
}
```

## v0.1 Reservations

- Device panel slot.
- Frames panel slot.
- `frame_receipt` evidence type.
- `visual_contract` optional contract section.
- Handoff fields for `visual_target`, `acceptance_criteria`, `checkpoint_policy`.

## Rejected Gimmicks

| Idea | Why |
|---|---|
| Autonomous browser use by default | Unsafe and not core to v0.1. |
| Screenshot-only reasoning | Weak evidence and poor accessibility. |
| Animated frame timeline without decisions | Eye candy, not cockpit. |
| Visual agent marketplace | Premature. |
