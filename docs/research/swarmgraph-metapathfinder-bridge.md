# SwarmGraph MetaPathFinder Bridge

**Phase reference:** Introduced alongside the swarmgraph-sdk extraction (Phases 80-100 range).  
**Status:** Active — installed unconditionally when `agent_runtime_cockpit.swarmgraph` is imported.  
**Source:** `python/src/agent_runtime_cockpit/swarmgraph/__init__.py`

---

## What it is

A Python import hook (`importlib.abc.MetaPathFinder` + `Loader`) that aliases
`agent_runtime_cockpit.swarmgraph.<name>` imports to the corresponding
`swarmgraph.<name>` module in the standalone `swarmgraph-sdk` distribution.

The hook is implemented as `_SwarmGraphBridgeFinder` and installed once into
`sys.meta_path` at import time.

---

## Why it exists

The SwarmGraph SDK logic was extracted into a standalone distribution
(`packages/swarmgraph-sdk/swarmgraph`). Code that previously imported
`from agent_runtime_cockpit.swarmgraph.config import SwarmGraphConfig` would
break if a simple `__path__` extension was used — that approach re-executes
the source under a second module name, producing distinct (incompatible)
Pydantic class objects.

The `MetaPathFinder` solves this by redirecting the import to the
*already-imported* `swarmgraph.<name>` module object, preserving Pydantic
class identity across both import paths.

---

## When it activates

Any `import agent_runtime_cockpit.swarmgraph` statement installs the finder.
It is installed unconditionally (not gated by an env var). The finder is
idempotent — it checks `sys.meta_path` before inserting.

---

## What it imports / intercepts

All sub-imports matching the prefix `agent_runtime_cockpit.swarmgraph.*` are
intercepted and redirected to `swarmgraph.*`. The top-level
`agent_runtime_cockpit.swarmgraph` package also re-exports the full public API
via `from swarmgraph import *`.

---

## Current status

- **Active/default**: The bridge installs whenever `agent_runtime_cockpit.swarmgraph` is imported.
- **Not gated**: There is no `ARC_ENABLE_*` flag; the bridge is required for SDK compatibility.
- **Not production-grade isolation**: The bridge does not sandbox or restrict the SDK. It is a compatibility shim only.

---

## Honest limits

- The bridge assumes `swarmgraph` (the standalone SDK) is installed. If it is
  not, the import fails with `ModuleNotFoundError`. There is no fallback.
- The bridge does not apply any enforcement gate on the SwarmGraph calls it
  enables. Enforcement is applied upstream in `SwarmGraphRunner.run()` via
  `require_dual_gate("SWARMGRAPH")`.
- This is not a security sandbox. A caller can still reach the SwarmGraph SDK
  directly via `import swarmgraph` without going through the bridge.

---

## Security implication

The bridge is a compatibility shim. The security-relevant gate is
`require_dual_gate("SWARMGRAPH")` in
`python/src/agent_runtime_cockpit/adapters/swarmgraph/runner.py`, not the
import hook itself. See `docs/security/enforcement-surfaces.md` S-100.1 and
the `SwarmGraphRunner` gating documentation.
