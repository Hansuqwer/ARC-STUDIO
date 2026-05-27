# Swarm Memory Graph Research

**Status:** Phase 59 research prototype. Local-only extraction from stored traces exists. No cross-tenant memory, no remote sync, no claimed quality/cost lift yet.

## Schema

- Nodes: `concept`, `decision`, `pattern`, `risk`, `outcome`.
- Edges: `derived_from`, `supports`, `contradicts`, `co_occurs`.
- Metadata: `confidence`, `frequency`, `source_run_ids`, timestamps.
- Persistence: `.arc/memory/graph.json` per workspace.
- Privacy mode: `local_workspace_only`.
- Tenant isolation: `not_claimed`.

## Extraction Prototype

`arc memory extract` scans up to 10 local JSONL traces by default and extracts deterministic keyword/phrase memories. It does not call providers or execute trace content. Phase 60 applies existing ARC redaction before extraction and records `redaction_applied=true` in the snapshot.

## Evaluation Plan

Required before productizing memory-assisted runs:

1. Build 10 fixed sample run bundles.
2. Extract memory graph from baseline runs.
3. Re-run comparable offline/fake tasks with and without memory context.
4. Measure quality delta, cost delta, latency delta.
5. Proceed only if quality improves by 10%+ or cost drops by 20%+ without privacy regressions.

`arc memory evaluate` records this gate. Without measured `--quality-delta >= 0.10` or `--cost-delta <= -0.20` across at least 10 source runs, the decision is `insufficient_evidence` or `no_go`.

## Privacy Analysis

- Memory is workspace-local only.
- Source run IDs are retained for deletion/audit traceability.
- Phase 60 applies ARC redaction before extraction. This is a guardrail, not proof that all private data is removed.
- `arc memory forget-run <run_id>` removes source links and drops memories sourced only from that run.
- Cross-workspace or tenant memory is blocked until tenant isolation and deletion semantics are designed/tested.

## Decision

Current decision: continue research prototype only. Do not wire memory into runtime prompts until `arc memory evaluate` returns `proceed` on a fixed sample set and privacy controls are reviewed.
