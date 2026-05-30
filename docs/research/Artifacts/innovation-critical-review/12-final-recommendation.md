# Final Recommendation

> Research basis: uploaded `ARC_STUDIO_UX_SPEC.md` (2026-05-16), uploaded `CLI_IDE_REDESIGN_PLAN.md` (2026-05-15), public competitor/frontier research available on 2026-05-16, and architectural assumptions stated in the task. I could not read repository-only `docs/adr/`, `AGENTS.md`, or `feature-roadmap-review/*.md` because the GitHub search connector had no selected ARC repo; claims depending on those files are marked [needs internal verification].

## Verdict

**Lock with changes.**

Do not lock the current plan as-is. It is too close to a late catch-up release. Lock only after adding minimal v0.1 reservations and small visible primitives for contracts, receipts, evidence, autopsy, runtime capabilities, and trust diffs.

## Current Plan Diagnosis

The current plan is **70% catch-up, 20% necessary foundation, 10% differentiated**.

- Catch-up: chat-first CLI, slash commands, config UI, sessions, Plan/Build/Auto, model/runtime selectors, diff review, status bar.
- Foundation: SwarmGraph default, local daemon, honest runtime gating, no default Trace UI, keyring, trust gate, graph surface.
- Differentiation: graph-first framing, runtime manifests, CLI/IDE shared sessions, HotLoop reservations.

The missing leap is to turn ARC into the first **Agent Runtime Cockpit**: not a chat app, not a trace viewer, not a workflow graph toy, but a runtime control plane for contracted, evidenced, policy-aware, multi-agent execution.

## Must Add Before Lock

1. `RunContract` schema with objective, runtime, mode, tool/write/cost policy, rollback plan, evidence expected.
2. `RunReceipt` artifact generated after every run.
3. `FailureAutopsy` object for failed runs, with evidence vs guesses.
4. `EvidenceRef` schema and UI reservation for Evidence Cards.
5. Stable `node_id`, `decision_id`, `approval_id`, `message_id`, `policy_decision_id` linkages.
6. Runtime manifest fields for evidence, cost model, recovery, handoff, and conformance.
7. `TrustDiff` data model for weakened trust/policy/provider changes.
8. CLI/IDE shared approval idempotency for Session Twin behavior.
9. `frame_receipt` reserved evidence type for HotLoop.
10. Explicit statement that graph commands are read-only until checkpoint/replay support exists.

## Innovation Bets

| Bet | v0.1 reservation | v0.2 implementation | Why it can win |
|---|---|---|---|
| Visual Run Contracts | `run_contract` in RunSummary; CLI/IDE minimal card. | Editable contracts, templates, fulfillment reports. | Makes agent execution bounded and accountable. |
| Agent Run Receipts | Save `run_receipt.md/json` per run. | PR export, support bundles, eval inputs. | Gives users a durable trust artifact. |
| Evidence Cards | `evidence_refs[]` on messages/run summaries. | Evidence browser, unsupported claim markers. | Turns plausible chat into verifiable claims. |
| Failure Autopsy | `failure_autopsy` with evidence/guess split. | Compare failed vs successful paths. | Replaces raw trace UI with honest diagnosis. |
| Runtime Capability Negotiation | Manifest fields and capability snapshots. | Negotiation resolver + conformance tests. | Turns runtime selection into guarantees. |
| Graph-Native Commanding | Stable IDs and read-only explain/select actions. | Rerun/pause/handoff after checkpoints. | Makes graph a cockpit, not decoration. |
| Trust Diff + Policy Simulator | Structured policy decisions and diffs. | Auto-mode simulation and scenario tests. | Makes autonomy safer and understandable. |
| Session Twin | Shared session state, client presence, idempotent approvals. | Mirrored selection, multi-surface collaboration. | CLI and IDE become one live control surface. |
| Handoff Workbench | Handoff schema refs in manifests/events. | Phase-boundary editor/validator. | Enables multi-runtime ARC story. |
| HotLoop Frame Receipts | `frame_receipt` type and visual contract fields. | Device/Frames with receipts and visual diffs. | Prevents HotLoop from becoming unsafe browser automation. |

## Do Not Build

| Idea | Why |
|---|---|
| Default raw Trace UI in v0.1 | Violates scope and hides the need for human summaries. |
| Full replay scrubber now | Needs storage/checkpoint semantics; v0.3. |
| Autonomous HotLoop in v0.1 | Too risky and distracts from cockpit foundation. |
| Runtime marketplace | Premature without conformance tests. |
| Secure delegation tokens as shipped security | Too complex unless actually enforced. Reserve IDs only. |
| Global unreceipted memory | Creepy, stale, and trust-damaging. |
| Fancy graph animations | Gimmick unless tied to decisions/commands/evidence. |
| Static command explosion | Recreates old nested CLI pain. |
| Copying Cursor inline diffs as the main moat | Useful later, but competitors own that mental model. |
| Auto-router without handoff validation | Unsafe and opaque. |

## New Positioning

ARC Studio is the first **Agent Runtime Cockpit**: a local-first CLI/IDE control plane where developers run multi-agent systems under explicit contracts, inspect graph-native execution, verify claims with evidence, simulate trust and cost risk, recover from failures with autopsies, and export receipts for every meaningful agent run.

## Final Go / No-Go On Current Plan Lock

**No-go as written. Go after the minimal cockpit reservations are added.**

The current plan is good enough to build a usable v0.1, but not good enough to justify the ARC Studio category claim. Add the cockpit primitives now; keep heavy implementations in v0.2/v0.3.
