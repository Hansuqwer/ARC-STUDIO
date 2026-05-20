# Spike: SwarmGraph Library Import Path

**Date:** 2026-05-15
**Status:** Complete

## Result

The vendored SwarmGraph library at `runtimes/swarmgraph/packages/` can be imported as a Python library from the ARC Studio Python venv.

## Modules Tested (all OK)

| Module | Status | Notes |
|--------|--------|-------|
| `swarm_shared.audit` | ✅ OK | `AuditChainWriter`, `verify` available |
| `swarm_shared.hashing` | ✅ OK | SHA-256 hashing utilities |
| `swarm.models.state` | ✅ OK | `SwarmState` model |
| `swarm.nodes.queen` | ✅ OK | Queen orchestration node |
| `swarm.nodes.consensus` | ✅ OK | Consensus/voting mechanics |
| `swarm.nodes.worker` | ✅ OK | Worker execution node |
| `swarm.nodes.approval` | ✅ OK | HITL approval node |
| `swarm.nodes.judge` | ✅ OK | Judging/review node |
| `swarm.nodes.router` | ✅ OK | Task routing |
| `swarm.llm.dispatch` | ✅ OK | LLM dispatch |
| `swarm.graphs.factory` | ✅ OK | Graph factory |

## How Imported

```python
import sys
sys.path.insert(0, "runtimes/swarmgraph/packages/swarm-shared")
sys.path.insert(0, "runtimes/swarmgraph/packages/hive-swarm")
```

Alternatively, both packages could be installed as editable packages via pip.

## Recommendation

**Proceed with library-based adoption** instead of CLI subprocess fallback. The vendored SwarmGraph exposes:
- `swarm_shared.audit` — for HMAC audit chain verification
- `swarm.nodes.queen` — for queen/worker orchestration
- `swarm.nodes.consensus` — for voting/consensus
- `swarm.nodes.approval` — for HITL

This enables in-process SwarmGraph integration for all adoption modes.
