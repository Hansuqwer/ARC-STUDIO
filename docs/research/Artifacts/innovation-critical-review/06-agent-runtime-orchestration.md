# Agent Runtime Orchestration

> Research basis: uploaded `ARC_STUDIO_UX_SPEC.md` (2026-05-16), uploaded `CLI_IDE_REDESIGN_PLAN.md` (2026-05-15), public competitor/frontier research available on 2026-05-16, and architectural assumptions stated in the task. I could not read repository-only `docs/adr/`, `AGENTS.md`, or `feature-roadmap-review/*.md` because the GitHub search connector had no selected ARC repo; claims depending on those files are marked [needs internal verification].

## Core Critique

The current plan treats runtime switching as a selector plus gating. That is not enough. ARC can become the first developer tool where runtimes are negotiated by **capabilities, guarantees, evidence, cost, and handoff compatibility**.

## Runtime Manifest Negotiation

Add these manifest categories:

```yaml
capability_contract:
  inspect: [files, graph_state, tests, screenshots]
  change: [workspace_files, git_index, browser_state]
  evidence: [file_lines, test_output, graph_events, screenshots, audit_refs]
  safety: [dry_run_patch, rollback_commit, cancel_safe, redaction]
  cost: [estimate, ceiling, actual_usage, unknown]
  handoff:
    accepts: [swarmgraph.phase.v1, hotloop.frame.v1]
    emits: [arc.handoff.v1]
  recovery: [retry_node, resume_run, cancel_run, rollback_changes]
```

A runtime should not just be `enabled`; it should be **eligible for this run contract**.

## Handoff Contracts

The reserved `handoff` event should become a typed document:

```yaml
handoff_version: arc.handoff.v1
from_runtime: swarmgraph
next_runtime: hotloop
objective: string
state_refs: []
constraints: []
evidence_refs: []
risk_changes: []
cost_expectation: unknown | range
lost_capabilities: []
required_user_approval: true
```

The Handoff Workbench should validate before phase transition. If HotLoop cannot preserve an audit link or rollback guarantee, ARC should say so.

## Runtime Certification Tests

`/doctor runtime` should run probes:

| Probe | Purpose | v0.1 feasibility |
|---|---|---|
| Inspect probe | Can runtime read allowed context only? | Yes, local fixture. |
| Dry-run patch probe | Can runtime propose without applying? | Yes for SwarmGraph. |
| Event probe | Emits node/run events with stable IDs. | Yes. |
| Redaction probe | Secrets not exposed in summaries/events. | Yes. |
| Cost probe | Reports estimate/actual or declares unknown. | Reserve. |
| Cancel probe | Cancel leaves coherent run state. | Yes/partial. |
| Recovery probe | Retry/resume semantics. | v0.2+. |

## Multi-Runtime Sessions

ARC should avoid “runtime per chat” as a hard boundary. The session should support:

- One active run contract.
- Multiple runtime phases.
- Runtime-specific evidence obligations.
- Handoff documents between phases.
- Per-phase cost/risk summaries.
- Runtime fallbacks only when capability-compatible.

## SwarmGraph-Specific Opportunities

- Stable node IDs become the spine of evidence, receipts, autopsy, and graph commands.
- Queen/worker topology can expose deliberation as structured decisions, not hidden chain-of-thought.
- HITL nodes can become contract checkpoints.
- Edges can carry evidence/cost/risk deltas.
- Graph topology diff can explain workflow changes across versions.

## What To Avoid

- “Auto router” that silently switches runtime based on vague task classification.
- Runtime marketplace before conformance tests.
- Adapter support claims without evidence obligations.
- Handoff docs as plain prompt blobs.
- Treating HotLoop as just another graph runtime; it needs frame contracts.

## Roadmap

| Version | Runtime work |
|---|---|
| v0.1 | Manifest fields reserved; SwarmGraph manifest validated; run contract stores runtime capability snapshot. |
| v0.2 | Negotiation resolver, handoff validator, runtime certification harness, router suggestions. |
| v0.3 | Multi-runtime sessions, graph/phase diff debugger, cross-runtime evals. |
