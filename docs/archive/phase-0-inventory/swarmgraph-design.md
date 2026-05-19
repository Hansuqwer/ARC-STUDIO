# Phase 0 — SwarmGraph Architecture Design Reference

Status: REFERENCE (Phase 0 inventory output)
Scope: locked SwarmGraph architecture per ADR-013
Authoritative source: docs/adr/ADR-013-swarmgraph-architecture.md

This file is a Phase 0 reference that captures the locked SwarmGraph architecture for inventory cross-checking. It is not the authoritative source; ADR-013 is. This file exists so that Phase 0 inventory work on the existing codebase can be checked against the target architecture.

## Architecture Summary

Pattern: orchestrator-worker. Hierarchy is bounded to 3 levels. Fan-out is gated by a parallelizability score with default threshold 0.6. Workers see step + filtered memory + filtered tools. Worker roles are pluggable via `prompts/swarmgraph/roles/*.md`. Consensus has six selectable strategies with judge-arbitrated default. Checkpoints are per-step and content-addressed. Failure mode detection covers 13 named modes with bounded recovery paths. MASS topology optimization and GEPA prompt optimization land in Phase 6.5. Security maps queen to Privileged and workers to Quarantined per ADR-014.

## Trust Flow (ADR-013 + ADR-014 Composition)

```text
External content
  -> tagged with origin + trust level
  -> classified by injection detector
  -> enters worker context only
  -> worker produces structured output
  -> queen consumes output as untrusted_input
  -> queen authorizes privileged action
  -> audit event emitted
  -> AssuranceTab compliance mode renders events
  -> compliance bundle can export evidence
```

## Plan Artifact Schema (recap)

Stored at `.arc/runs/<run-id>/plan.md`. Format is Markdown with structured YAML frontmatter. Each step declares id, depends_on, worker_count, worker_role, runtime_mode, consensus strategy, budget_tokens, success_criteria, inputs, and outputs.

## Prompt File Layout (recap)

```text
python/src/agent_runtime_cockpit/prompts/swarmgraph/
  queen.system.md
  queen.plan.md
  queen.verify.md
  queen.reflect.md
  worker.system.md
  worker.execute.md
  consensus.system.md
  roles/
    generic.md
    researcher.md
    coder.md
    reviewer.md
    planner.md
    verifier.md
```

All prompts are versioned by sha256 and captured in run receipts per ADR-015.

## Phase 0 Inventory Cross-Check

Use this file to cross-check current implementation status:

| File | Cross-check |
|---|---|
| `python/src/agent_runtime_cockpit/swarmgraph/runner.py` | queen/worker separation, context isolation, consensus strategies, checkpoints, `swarmgraph.*` attributes |
| `python/src/agent_runtime_cockpit/swarmgraph/state.py` | hierarchy levels and plan artifact lifecycle |
| `python/src/agent_runtime_cockpit/swarmgraph/consensus.py` | six locked strategies |
| `python/src/agent_runtime_cockpit/adapters/swarmgraph.py` | external CLI delegation preserved without native provider-backed overclaim |

Results of this cross-check go in `runtime-matrix.md` under implementation status columns.

## Current Implementation Evidence

| Target item | Current evidence | Status |
|---|---|---|
| native fake/offline execution | `python/src/agent_runtime_cockpit/adapters/swarmgraph.py:305-374`; `swarmgraph/runner.py:40-110` | implemented |
| external CLI delegation | `adapters/swarmgraph.py:401-532` | implemented but external; not native proof |
| topology events | `swarmgraph/runner.py:57-59`; `adapters/swarmgraph.py:397-399` | implemented for native event mapping |
| consensus events | `swarmgraph/runner.py:90-94`; `adapters/swarmgraph.py:389-390` | implemented for native event mapping |
| budget events | `swarmgraph/runner.py:78-82`, `95-99`; `adapters/swarmgraph.py:391-392` | scaffolded/config-driven; native adapter disables budget by default |
| HITL events | `swarmgraph/runner.py:86-89`; `adapters/swarmgraph.py:393-394` | scaffolded/config-driven; native adapter disables HITL by default |
| provider-backed native mode | `adapters/swarmgraph.py:312-320` forces `ExecutionMode.fake_offline` | absent |
| env-filtered external subprocess | `adapters/swarmgraph.py:84-115`, `431-437` | implemented for external CLI path |
| workspace-root launcher rejection | `adapters/swarmgraph.py:534-557` | implemented for external CLI path |

## Cross-Check Result

Native SwarmGraph currently satisfies the fake/offline topology/worker/consensus event baseline. It does not satisfy ADR-013 provider-backed execution, bounded hierarchy, pluggable prompt role files, full six-strategy consensus, MASS/GEPA optimization, or ADR-014 security layers. External `ARC_SWARMGRAPH_CLI` delegation remains a legacy/delegated path and must not be used as evidence for native provider-backed completeness.

## References

- Anthropic, "How we built our multi-agent research system" (2025)
- Anthropic, "Effective context engineering for AI agents" (2025)
- Google Research, "Towards a science of scaling agent systems" (December 2025)
- Google Research, "MASS: Multi-Agent System Search" (arXiv 2502.02533)
- arXiv 2603.01213, "Can AI Agents Agree?" (early 2026)
- ResearchGate, "Byzantine-Robust Decentralized Coordination of LLM Agents" (2025)
- LangChain, "Benchmarking Multi-Agent Architectures" (2026)
- arXiv 2604.28138, "Crab: Semantics-Aware Checkpoint/Restore" (January 2026)
- arXiv 2601.17152, "Dynamic Role Assignment for Multi-Agent Debate" (January 2026)
- Augment Code, "Why Multi-Agent LLM Systems Fail" (2026)
- Latitude.so, "AI Agent Failure Detection Guide" (2026)
- Simon Willison, "CaMeL offers a promising new direction for mitigating prompt injection attacks" (April 2025)
- MIT CSAIL, "Defeating Prompt Injections by Design" (CaMeL paper, 2025/2026)
