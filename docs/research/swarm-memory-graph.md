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

`arc memory extract` scans up to 10 local JSONL traces by default and extracts deterministic keyword/phrase memories. It does not call providers or execute trace content.

## Evaluation Plan

Required before productizing memory-assisted runs:

1. Build 10 fixed sample run bundles.
2. Extract memory graph from baseline runs.
3. Re-run comparable offline/fake tasks with and without memory context.
4. Measure quality delta, cost delta, latency delta.
5. Proceed only if quality improves by 10%+ or cost drops by 20%+ without privacy regressions.

## Privacy Analysis

- Memory is workspace-local only.
- Source run IDs are retained for deletion/audit traceability.
- Raw secret scanning is not yet integrated; do not ingest arbitrary private traces into shared memory.
- Cross-workspace or tenant memory is blocked until tenant isolation and deletion semantics are designed/tested.

## Decision

Continue research prototype only. Do not wire memory into runtime prompts until evaluation passes and privacy controls exist.
