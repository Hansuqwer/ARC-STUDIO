# ADR-0005: SwarmGraph Runtime Architecture — Runner Canonical Path

**Status:** Accepted  
**Date:** 2026-05-14  
**Deciders:** Lead Orchestrator, Security Reviewer

## Context

Two parallel SwarmGraph execution implementations existed:

1. **Monolithic** (`swarmgraph.py:run_workflow`): Subprocess CLI, 3-event synthesis, `ARC_SWARMGRAPH_CLI` env var.
2. **Modular** (`swarmgraph/runner.py`): STUB/LOCAL/GATEWAY backends, real-time AG-UI event streaming, audit chain integrity.

Both disagreed on:
- Cost gating semantics (monolithic had its own `ARC_SWARMGRAPH_ALLOW_COSTS` check)
- Event streaming (none vs real-time with `MappingContext`)
- Execution model (CLI subprocess vs async generator produce/consume)

Additionally, the monolithic path had a **P0 security vulnerability**: it searched `workspace / "swarmgraph"` as a fallback when `ARC_SWARMGRAPH_CLI` was not set, allowing arbitrary code execution from untrusted workspaces ([#10](https://github.com/Hansuqwer/arc-theia-studio/issues/10)).

## Decision

**The modular `SwarmGraphRunner` is the canonical runtime path.**

1. The monolithic CLI subprocess path (`swarmgraph.py:run_workflow`) is **deprecated** and will be removed in a future release.
2. All cost gating **must** go through the shared `require_dual_gate("SWARMGRAPH")` function. No adapter-level `ALLOW_COSTS` checks.
3. `ARC_SWARMGRAPH_CLI` is the only supported launcher variable. Workspace-local `swarmgraph` files are **never** executed.
4. New backends (LOCAL, GATEWAY) are added to `SwarmGraphRunner._produce()`, not as branches in the monolithic adapter.

## Consequences

- ✅ Security: No executable code can be run from untrusted workspaces.
- ✅ Gating: Single source of truth for cost approval—no bypass possible.
- ✅ Streaming: Real-time AG-UI events with audit chain integrity for all backends.
- ✅ Extensibility: New backends (e.g., REMOTE, DOCKER) are added to the runner's `_produce()` dispatch, not as new branches.
- ⚠️ Breaking change: Users relying on the old CLI-subprocess path (without `ARC_SWARMGRAPH_CLI`) must configure the env var. This is documented in this ADR and release notes.
- ⚠️ The monolithic `run_workflow` remains for backward compatibility but is untested for new features.

## Migration Path

1. Set `ARC_SWARMGRAPH_CLI` to a trusted launcher **outside** any workspace.
2. Use `ARC_SWARMGRAPH_RUN_BACKEND` to select stub, local, or gateway modes.
3. Cost gating is automatic via `ARC_SWARMGRAPH_ALLOW_COSTS=true` for non-stub backends.
4. The deprecated monolithic path remains available for compatibility but does not emit runtime warnings because CLI and daemon tests run with warnings as errors.

## Related

- [#10](https://github.com/Hansuqwer/arc-theia-studio/issues/10): Workspace-rooted launcher vulnerability (CLOSED)
- [#13](https://github.com/Hansuqwer/arc-theia-studio/issues/13): Unified cost gating (CLOSED)
- [#15](https://github.com/Hansuqwer/arc-theia-studio/issues/15): Architecture decision tracking (CLOSED)
- `python/src/agent_runtime_cockpit/gating.py`: `require_dual_gate()`
- `python/src/agent_runtime_cockpit/adapters/swarmgraph/runner.py`: Canonical runner
- `python/src/agent_runtime_cockpit/adapters/swarmgraph.py`: Deprecated monolithic path
