# Phase 81 — SwarmGraph Consensus Differentiators Phase 1

**Roadmap:** R52  
**Status:** Implementation in progress  
**Created:** 2026-05-28

## Summary

Implement offline/eval-first consensus differentiators: selective debate, confidence-weighted quorum, critic/verifier lane, and HITL sign-off quorum. All fake/offline, no provider-backed execution.

## Assessment

| Priority | Item | Status | Notes |
|---|---|---|---|
| P0 | Selective debate protocol | Not Started | Multi-round: workers revise after seeing other outputs |
| P0 | Confidence-weighted quorum | Not Started | AgentVote.confidence field exists but unused |
| P0 | Critic/verifier lane | Not Started | Judge role exists in AgentRole enum but unused |
| P0 | HITL sign-off quorum | Not Started | Multiple-human quorum, not binary HITL |
| P0 | Offline eval harness + metrics CLI | Not Started | Quality/cost/latency/disagreement/escalation |
| P0 | Differentiation metrics | Not Started | Compare selective debate vs simple majority |
| P1 | Gossip protocol implementation | Not Started | Declared in enum, no implementation |
| P1 | CLI: `arc swarmgraph eval` | Not Started | Run consensus benchmarks |

## Existing Foundation

All requirements from Phase 17 (SwarmGraph native runtime), Phase 30 (consensus escrow), Phase 31 (adaptive consensus), and Phase 34 (battle mode) are already Baseline Complete. Key existing assets:

- `swarmgraph/consensus.py`: majority, quorum, raft, bft, bft_escrow
- `swarmgraph/risk_assessment.py`: adaptive risk-based protocol selection
- `swarmgraph/nodes/consensus.py`: per-task adaptive consensus
- `swarmgraph/events.py`: consensus event emission
- `battle/runner.py`: offline battle runner with deterministic voting
- `protocol/events.py` + `typed_events.py`: typed event types
- `evals/golden.py` + `evals/diff.py`: eval infrastructure

## Implementation Plan

### 1. New Consensus Protocols in `swarmgraph/consensus.py`

Add four new consensus functions alongside existing ones:

```
selective_debate_consensus(votes, candidates, config) -> ConsensusResult
confidence_weighted_consensus(votes, config) -> ConsensusResult
critic_verifier_consensus(votes, verifier_votes, config) -> ConsensusResult
hitl_signoff_quorum(prompts, operators_required) -> ConsensusResult
```

### 2. Extend Protocol Enum in `swarmgraph/config.py`

Add: `selective_debate`, `confidence_weighted`, `critic_verifier`, `hitl_signoff`, `gossip`

### 3. Eval Harness at `evals/consensus.py`

Create offline eval harness that:
- Generates synthetic worker outputs
- Runs each consensus protocol against same inputs
- Collects metrics: quality, cost, latency, disagreement, escalation rate
- Returns structured comparison

### 4. CLI: `arc swarmgraph eval`

Add CLI command to run consensus benchmarks:
```
arc swarmgraph eval --protocol selective_debate --workers 4 --rounds 3 --json
arc swarmgraph eval --compare --json
```

### 5. Event Types

Add `CONSENSUS_DIFFERENTIATOR` / `CONSENSUS_EVAL` event types.

### 6. Gossip Protocol

Implement gossip-style eventual consensus for completeness.

## Truth Constraints

- All fake/offline — no provider-backed execution
- No live LLM calls in tests
- No network calls
- Default CLI behavior unchanged
- Existing consensus tests remain green

## IDE Panels (Phase 78/79 Polish)

Promote CLI-only panels from CommandCentreTab sub-panels to standalone top-level tabs:

- **MCP Workbench Tab**: `arc mcp workbench status --json` data in dedicated tab
- **Test Bench Tab**: `arc testbench detect --json` results in dedicated tab  
- **CI Guardrails Tab**: `arc ci check --json` results in dedicated tab

All data types, CLI bridges, and service methods already exist in:
- `common/arc-protocol.ts` (types + ArcService interface)
- `node/services/local-telemetry-service.ts` (CLI bridge)
- `node/arc-backend-service.ts` (delegation)
- `browser/tabs/CommandCentreTab.tsx` (existing sub-panels)
