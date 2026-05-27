# Swarm Memory Graph Research

**Status:** Phase 64 research prototype. Local-only extraction from stored traces and offline evidence-pack evaluation exist. No runtime prompt wiring, no cross-tenant memory, no remote sync, no provider/network evaluation calls.

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

Phase 64 adds offline evidence packs:

- `arc memory evidence create --samples <local-fixture.json> --output <pack.json>` creates a local pack.
- `arc memory evidence evaluate <pack.json>` evaluates baseline/candidate metrics from local fixtures only.
- `arc memory evidence show <pack.json>` prints the pack.
- `arc memory evaluate --evidence-pack <pack.json>` uses evidence-pack metrics instead of manual deltas.

Evidence packs require `memory_runtime_injection=false`, privacy review, redaction applied, and at least 10 valid samples. `proceed` means research gate only; it does not enable runtime memory injection or productized memory.

## Privacy Analysis

- Memory is workspace-local only.
- Source run IDs are retained for deletion/audit traceability.
- Phase 60 applies ARC redaction before extraction. This is a guardrail, not proof that all private data is removed.
- `arc memory forget-run <run_id>` removes source links and drops memories sourced only from that run.
- Cross-workspace or tenant memory is blocked until tenant isolation and deletion semantics are designed/tested.

## Decision

Current decision: continue research prototype only. Do not wire memory into runtime prompts until an offline evidence pack returns `proceed` on a fixed reviewed sample set, privacy controls are reviewed, and a separate implementation phase explicitly wires runtime behavior.
