# ADR-013: SwarmGraph Runtime Architecture Lock

Status: Accepted
Date: 2026-05-19
Accepted: 2026-05-19
Deciders: ARC Studio core team
Parent ADR: ADR-011 (Full Parity Framing)
Related: ADR-014 (Security Architecture)
         ADR-015 (IDE Compliance Mode)

## Context

SwarmGraph is ARC Studio's owned default runtime (per ADR-011). Its queen/worker/consensus pattern is structurally well-positioned in the May 2026 multi-agent landscape, but the previous architectural lock left several runtime-specific commitments underspecified.

This ADR captures the SwarmGraph-specific architectural commitments required to ship the runtime in Phase 4 and complete its surface in Phases 4.5, 4.7, and 6.5.

## Decision

SwarmGraph commits to the orchestrator-worker pattern with explicit fan-out gating, strict worker context isolation, six selectable consensus strategies, hierarchical orchestration up to three levels, pluggable worker roles, per-step content-addressed checkpoints with auto-resume, detection-and-recovery for thirteen named failure modes, and MASS-based topology optimization in Phase 6.5.

### Pattern Lock

Pattern: orchestrator-worker. The queen is orchestrator; workers are isolated executors. Hierarchical SwarmGraph is supported up to 3 levels. Swarm/handoff is not supported because it lacks a central orchestrator for audit attribution.

### Fan-Out Gate

Before spawning workers, the queen computes a parallelizability score for the current plan and decides single-worker versus fan-out execution.

```text
parallelizable_score = heuristic in v1; learned in Phase 6.5
threshold = 0.6, configurable per workflow
score < threshold  -> single-worker execution
score >= threshold -> fan out, worker count = min(parallel_steps, max_workers)
```

The decision and score are logged to the audit trail.

### Worker Context Isolation

Workers receive assigned step, relevant memory facts, verbatim goal statement, and tools filtered to step requirements. Workers do not receive the full plan, other workers' outputs, the queen's full reasoning trace, or tools outside their declared requirements.

Workers return step result, reasoning summary for audit, token/cost accounting, and tool call list.

### Consensus Strategies

Six per-step selectable strategies are locked:

- judge-arbitrated: default queen synthesis.
- majority: workers vote, most common answer selected.
- weighted: workers vote with credibility weights.
- debate-N: workers revise across N rounds.
- proof-of-thought: judge evaluates reasoning quality, Phase 4.7.
- symbolic: deterministic verification against tests/schemas/types.

### Hierarchical Orchestration

Hierarchical SwarmGraph is bounded to 3 levels: top queen, sub-queens, sub-sub-queens. Level 3+ is rejected at plan synthesis.

### Worker Roles

Worker roles are prompt-file driven: generic, researcher, coder, reviewer, planner, verifier. New roles are registered in `prompts/_meta.yaml`; plan steps include `worker_role`.

### Checkpoint-Restore

SwarmGraph checkpoints after every step completion. Checkpoints include plan state, worker outputs, consensus result, memory deltas, cost accounting, and event log offset. Checkpoints are content-addressed with sha256 and stored under `.arc/runs/<run-id>/checkpoints/<step-id>.json`.

### Failure Mode Taxonomy

SwarmGraph detects thirteen named failure modes: coordination deadlock, infinite retry loops, goal drift, context loss, tool misuse, cascading errors, resource exhaustion, coordination amplification, specification ambiguity, consensus failure, tool poisoning detected, rug pull detected, and tool output injection.

Recovery actions are replan, retry, cancel, or escalate.

### MASS Topology Optimization

GEPA optimizes prompts and MASS optimizes topology in Phase 6.5. Both are eval-driven.

### Event Envelope SwarmGraph Attributes

The event envelope includes `swarmgraph.queen_id`, `swarmgraph.worker_id`, `swarmgraph.worker_role`, `swarmgraph.hierarchy_level`, `swarmgraph.fan_out_score`, `swarmgraph.fan_out_decision`, `swarmgraph.consensus_strategy`, `swarmgraph.consensus_rounds`, `swarmgraph.checkpoint_id`, `swarmgraph.failure_mode`, and `swarmgraph.recovery_action`.

### Slash Command Surface

`/swarmgraph`, `/swarmgraph fan-out`, `/swarmgraph consensus`, `/swarmgraph checkpoint`, `/swarmgraph checkpoint show <id>`, `/swarmgraph failure`, and `/swarmgraph roles` are locked Phase 4 commands. Earlier phases may stub them.

## Consequences

SwarmGraph gains a clear, testable multi-agent architecture. The cost is a larger test matrix across roles, consensus strategies, hierarchy depth, checkpointing, failure detection, and optimization.

## Banned Claims Specific to This ADR

- "SwarmGraph always fans out to workers" is unsafe; fan-out is gated.
- "Workers see the full plan" is unsafe; context isolation prevents this.
- "SwarmGraph achieves Byzantine consensus" is unsafe until proof-of-thought is tested.
- "SwarmGraph handles all multi-agent failures" is unsafe; honest claims name the 13 detected modes.
- "Consensus is automatic" is unsafe; consensus strategy is per-step selectable.
- "SwarmGraph optimization is automated" is unsafe until MASS + GEPA ship.
- "Hierarchical SwarmGraph is unbounded" is unsafe; it is bounded to 3 levels.
- "Workers are independent" is unsafe; state is queen-mediated.
- "Checkpoint resume is lossless" is unsafe; in-flight tool calls are exceptions.
- "SwarmGraph supports swarm/handoff" is unsafe; explicitly not supported.

## Acceptance Criteria (Phase 4 ship)

- Native SwarmGraphRunner implements all six consensus strategies in at least stub form, with judge-arbitrated and majority tested.
- Fan-out gate implemented with audit event emission.
- Worker context isolation tested.
- All 13 failure modes have detectors emitting events.
- Per-step checkpoint persistence verified.
- Resume from checkpoint tested against synthetic mid-step termination.
- Event envelope includes all locked `swarmgraph.*` attributes.
- `prompts/swarmgraph/{queen,worker,consensus}*.md` exist and are referenced.
- Banned-claims script passes against documentation.
