# SwarmGraph IR + Compiler — Deep Architecture Analysis

**Repo:** `Hansuqwer/arc-theia-studio` · **Date:** 2026-06-02
**Author role:** Principal AI-agent runtime architect / compiler engineer / SDK designer / security reviewer
**Status:** Design proposal (patch-ready). No runtime behaviour changed by this document.

> **Mission:** design the missing *middle layer* that normalizes workflows from many agent
> frameworks into a typed, inspectable, policy-aware **SwarmGraph Intermediate Representation
> (IR)** — a *normalization & analysis* layer, **not** a new runtime engine.

---

## 0. Repo-verified ground truth (read before trusting any assumption)

Everything below was confirmed by cloning and executing against the repo, not inferred.

| Claim in brief | Verified? | Evidence in repo |
|---|---|---|
| `security/policy_linter.py` with 8 rules, `PolicyReport(can_run, issues, risk_level, suggested_consensus)` | ✅ | `python/src/agent_runtime_cockpit/security/policy_linter.py`; rules R1–R8 present; calls `assess_prompt_risk()` + `select_consensus_protocol()` |
| Linter calls SwarmGraph SDK | ✅ but **note the import path** | It uses `from swarmgraph import assess_prompt_risk, select_consensus_protocol` (the **top-level SDK**, not `agent_runtime_cockpit.swarmgraph`) |
| `mcp/manifests.py` — `ManifestStore`, SHA-256 hash, `pin/check_drift/load`, `McpToolRisk` 4 flags | ✅ | `mcp/manifests.py`; hash is `sha256(...)[:16]`; pins stored at `<workspace>/.arc/mcp/pins/<server_id>.json` (**not** `~/.arc` — that's the registry) |
| `mcp/registry.py` — `McpRegistryStore`, `~/.arc/mcp/servers.json`, `approve_tool/block_tool` | ✅ | `mcp/registry.py`; `_SHARED_DIR = Path.home()/".arc"/"mcp"` |
| `evals/policy_recommend.py` — `recommend_policy`, `PolicyRecommendation`, 4 categories, `save_recommendations` → `.arc/evals/recommendations/` | ✅ | `evals/policy_recommend.py`; categories `consensus/hitl/tool_gate/paid_call`; never auto-applies |
| SwarmGraph lives at `runtimes/swarmgraph/` (vendored) and the **SDK** at `python/packages/swarmgraph-sdk/swarmgraph/` | ✅ | `pyproject.toml`: `swarmgraph-sdk = { workspace = true }`, `[tool.uv.workspace] members = ["packages/*"]` |
| **Import trap is real** for `agent_runtime_cockpit.swarmgraph.*` | ✅ **empirically reproduced** | See §0.1 below |

### 0.1 The MetaPathFinder import trap — *reproduced, not theorized*

`python/src/agent_runtime_cockpit/swarmgraph/__init__.py` installs a `MetaPathFinder`
(`_SwarmGraphBridgeFinder`) at `sys.meta_path[0]` that rewrites **any**
`agent_runtime_cockpit.swarmgraph.<name>` import to `swarmgraph.<name>` and also sets
`__path__` to the SDK's directory. I executed:

```python
import agent_runtime_cockpit.swarmgraph          # installs the finder
import agent_runtime_cockpit.swarmgraph.ir       # hypothetical new submodule
# -> ModuleNotFoundError: No module named 'swarmgraph.ir'
```

**Result:** a file physically placed at
`python/src/agent_runtime_cockpit/swarmgraph/ir.py` would be **unreachable** — the finder
intercepts the name first and tries `swarmgraph.ir` in the SDK, which does not exist, so the
import *fails closed*. Pydantic class identity would also fragment.

➡️ **Hard constraint, now proven:** do **not** put IR code under
`agent_runtime_cockpit/swarmgraph/`. Use a neutral package.

### 0.2 Other load-bearing facts discovered

- **Adapters already produce the perfect IR ingestion input.** `adapters/base.py` defines
  `RuntimeAdapter.export_workflow(workspace) -> list[WorkflowInfo]`. Adapters exist for
  `langgraph, crewai, openai_agents, ag2, llamaindex, swarmgraph` (+ dspy, haystack, langchain,
  semantic_kernel, smolagents, pydantic_ai, google_adk, mcp_sdk). **We ingest `WorkflowInfo`,
  we do not re-parse frameworks.**
- **`WorkflowInfo` schema** (`protocol/schemas.py`): `WorkflowInfo{id,name,runtime,source_file,
  nodes,edges,entry_points,metadata}`, `WorkflowNode{id,label,type:NodeType,source_location,
  metadata}`, `WorkflowEdge{id,from_node,to_node,label,conditional,metadata}`.
  `NodeType ∈ {agent,tool,resource,prompt,router,start,end,unknown}`. **The linter already
  reads node/edge `metadata` keys** (`is_mcp`, `mcp_manifest_hash`, `requires_paid_call`,
  `paid_call_gate`, `write_path`, `privileged`, `trust_annotation`, `consensus_protocol`,
  `num_workers`). → IR ⇄ `WorkflowInfo` is a **metadata-projection** problem, not a rewrite.
- **CLI is Typer.** Sub-apps are declared in `cli/_subapps.py` and wired in `cli/_app.py`.
  There is **no `ir` sub-app yet** — the `arc ir` namespace is free.
- **TS protocol mirror** lives in `packages/arc-protocol-ts/src/arc-protocol-types.ts` and
  already mirrors `WorkflowInfo/WorkflowNode/WorkflowEdge`. ADR-018 makes the protocol package
  the canonical schema home.
- **Visual graph UI already has a home:** `packages/arc-extension/src/browser/
  arc-workflow-graph-widget.tsx` (Wave 5) already renders nodes/edges with evidence refs and a
  graph↔chat selection contract. The IR can feed it directly.
- **Reusable primitives:** `protocol/stable_ids.py` (ULID-like IDs, node-id format
  `<workflow>.<node>`, edge-id `<from>→<to>`), `security/redaction.py::redact_secrets()`.
- **SDK risk API:** `swarmgraph.assess_prompt_risk(str) -> RiskAssessment{risk:RiskLevel,...}`,
  `select_consensus_protocol(assessment) -> ProtocolSelection`, plus constant
  `CONSENSUS_PROTOCOL_BY_RISK`.

---

## 1. Current repo capability map

| Area | Existing files | Current capability | IR implication | Missing piece | Patch opportunity |
|---|---|---|---|---|---|
| **Adapters** | `adapters/base.py`, `adapters/{langgraph,crewai,openai_agents,ag2_adapter,llamaindex,swarmgraph}.py`, `adapters/registry.py` | Every adapter implements `export_workflow() -> list[WorkflowInfo]`; honest capability reporting; AST + real-graph export | `WorkflowInfo` is the **canonical ingestion artifact**; no need to touch framework code | No typed enrichment (tool refs, budgets, side-effects, provenance) above `metadata: dict` | Adapter-local `ir_hints()` is **not** required for MVP; compiler reads existing `WorkflowInfo.metadata` |
| **SwarmGraph runtime/SDK** | `runtimes/swarmgraph/` (vendored), `python/packages/swarmgraph-sdk/swarmgraph/*`, bridge `agent_runtime_cockpit/swarmgraph/__init__.py` | Risk assessment, consensus protocols, decomposition, checkpoints, events | IR borrows `RiskLevel`, `CONSENSUS_PROTOCOL_BY_RISK`, `assess_prompt_risk` for hints | A neutral seam that imports the SDK **without** triggering the finder | Import SDK as top-level `swarmgraph` (works) from a **neutral** package |
| **Policy linter** | `security/policy_linter.py` | 8 deterministic rules → `PolicyReport`; consumes `WorkflowInfo` + metadata keys | IR must **emit a faithful `WorkflowInfo`** so the linter runs unchanged | Nothing in linter; IR just needs a bridge | `swarmgraph_ir.exporters.to_workflow_info()` → feed `lint_workflow()` |
| **MCP manifests/registry** | `mcp/manifests.py`, `mcp/registry.py` | Manifest pin + drift + `McpToolRisk` (4 flags); per-tool approve/block; `~/.arc/mcp/servers.json` | IR MCP nodes carry pin hash + risk; enrichment is a **local read** | IR-side join between MCP tool nodes and `ManifestStore`/`McpRegistryStore` | `swarmgraph_ir.enrich.attach_mcp_risk(graph, workspace)` |
| **Eval recommendations** | `evals/policy_recommend.py`, `evals/golden.py` | `recommend_policy(results)` → `PolicyRecommendation` (consensus/hitl/tool_gate/paid_call), persisted, never auto-applied | IR can carry an `eval_metadata` block linking recs → nodes (advisory only) | No mapping from rec `action` → IR node/edge | `swarmgraph_ir.eval_link.attach_recommendations()` (read-only) |
| **Trace / replay** | `tracing/jsonl_writer.py`, `cli/replay.py`, `protocol/typed_events.py` | JSONL trace writer; replay analysis; stable IDs | IR `IRReplayMarker` pins node↔event correlation keys | No declared replay anchors at compile time | Emit `replay_markers` from node IDs (deterministic, no exec) |
| **Audit** | `audit/*`, ADR-005, ADR-021 | HMAC audit chain; trust diff | IR `IRAuditBoundary` marks where audit attribution must occur | No compile-time audit-boundary annotation | Derive boundaries from privileged/paid/HITL nodes |
| **Protocol TS types** | `packages/arc-protocol-ts/src/arc-protocol-types.ts` (ADR-018) | Mirrors `WorkflowInfo` family; discriminated unions shipped | IR needs a **read-only TS mirror** for UI/diff | No `swarmgraph-ir.ts` | Add `packages/arc-protocol-ts/src/swarmgraph-ir.ts` |
| **CLI** | `cli/_app.py`, `cli/_subapps.py`, Typer-based | 30+ sub-apps; consistent `ok/err` envelope helpers (`cli/swarmgraph.py`) | `arc ir …` is a new sub-app following the same pattern | No `ir_app` | Add `ir_app` + `cli/ir.py` |
| **Theia UI** | `arc-extension/src/browser/arc-workflow-graph-widget.tsx`, `arc-workflow-contribution.ts` | Renders nodes/edges + evidence refs + selection contract (Wave 5) | IR JSON is a **superset**; widget can consume IR directly later | No IR data source wired to widget | Differentiator: IR → widget feed + diff overlay |
| **TUI** | `tui/views/*`, `tui/widgets/*` | Textual TUI dashboards | `arc ir inspect --json` can back a TUI panel later | No IR panel | Optional later; CLI JSON is enough |
| **Storage** | `storage/{atomic,jsonl,sqlite,indexed_store}.py`, `storage/advisory_lock.py` | Atomic writes, advisory locks, JSONL/sqlite stores | IR JSON written via `storage.atomic` for determinism | None | Use `atomic.write_text` for `graph.ir.json` |
| **Security / trust** | `security/{redaction,trust,context,enforcement}.py`, ADR-006/014/019 | 4-tier trust model; secret redaction; workspace isolation; enforcement context | IR carries `IRRisk`, `IRCapabilityRequirement`, trust annotations; redaction applied on emit | No IR-level trust normalization | Compiler runs `redact_secrets()` on string fields; preserves trust tags |
| **Paid-call gates** | `budget/*`, enforcement `--allow-paid`, linter R3 | Paid-call denial + gate metadata (`requires_paid_call`, `paid_call_gate`) | IR `IRBudget` + `IRSideEffect(paid_call=True)` | No typed budget on nodes | Project metadata → `IRBudget`; **never executes a paid call** |

---

## 2. Architecture options (compared on 7 axes)

### A. `swarmgraph_ir/` — neutral Python package *(recommended)*

- **Benefits:** Clear domain name; avoids the finder entirely (it only hooks
  `agent_runtime_cockpit.swarmgraph.*`); co-located with adapters/security/mcp/evals it must
  call; one cohesive seam for models + compiler + adapters + exporters.
- **Drawbacks:** Slight name overlap with the bridge package (mitigated: different leaf name).
- **Import risks:** **None** — `swarmgraph_ir` is not matched by `_BRIDGE_PREFIX`
  (`agent_runtime_cockpit.swarmgraph.`). Verified by reading the finder's `find_spec`.
- **Testability:** High — pure data + pure functions; no I/O in core; CI-safe.
- **Future UI compatibility:** High — emits IR JSON consumed by the existing graph widget.
- **Policy-linter compatibility:** High — exports `WorkflowInfo`; linter untouched.
- **MCP compatibility:** High — imports `mcp.manifests`/`mcp.registry` (local reads).
- **Recommendation:** ✅ **Adopt.** Best balance of clarity, safety, and cohesion.

### B. `compiler/` — runtime-agnostic compiler package

- **Benefits:** Emphasizes the compiler framing; generic-sounding.
- **Drawbacks:** Loses the SwarmGraph-IR semantic anchor; "compiler" collides conceptually with
  the SDK's decomposition/`plan_dag`; reviewers may expect a general compiler (scope creep).
- **Import risks:** None.
- **Testability/UI/linter/MCP:** Same as A.
- **Recommendation:** ❌ Reject as the *package*; keep `compiler.py` as a **module inside**
  `swarmgraph_ir/`.

### C. Adapter-local exporters only (each `adapters/<fw>/ir.py` emits IR)

- **Benefits:** No new top-level package; provenance is trivially local.
- **Drawbacks:** Duplicates models per adapter; no central validation/hash/diff; drift across
  14 adapters; violates DRY; "do not bypass existing adapters" becomes "scatter IR across
  adapters." No single home for `to_workflow_info()` bridge.
- **Import risks:** None, but inconsistent.
- **Testability:** Low — N copies to test.
- **UI/linter/MCP:** Fragmented.
- **Recommendation:** ❌ Reject as primary. Re-use adapters' **existing** `export_workflow()`
  output instead; optional thin `ir_hints()` hook can be added later (1-week+).

### D. Vendored runtime extension under `runtimes/swarmgraph/`

- **Benefits:** Lives "next to" SwarmGraph.
- **Drawbacks:** `runtimes/swarmgraph/` is a **vendored upstream** (own `.github`, `CHANGELOG`,
  ADRs) — putting ARC IR there pollutes the vendor boundary and complicates upstream syncs;
  not importable as `agent_runtime_cockpit.*`; couples IR to runtime internals (explicitly
  forbidden: "do not duplicate SwarmGraph runtime internals").
- **Import risks:** High packaging risk; not on the ARC import path.
- **Testability/UI/linter/MCP:** Poor integration.
- **Recommendation:** ❌ Reject.

**Decision:** **Option A**, package `agent_runtime_cockpit.swarmgraph_ir`, with `compiler.py`
as an internal module (folding in the best of B).

---

## 3. Recommended architecture

- **Package name:** `agent_runtime_cockpit.swarmgraph_ir` (neutral; finder-safe; verified).
- **Module layout:** see §4.
- **Public Python API** (`swarmgraph_ir/__init__.py`):
  ```python
  from .models import (IRGraph, IRNode, IREdge, IRToolRef, IRMcpToolRef, IRModelCall,
      IRHumanGate, IRConsensusHint, IRRisk, IRCapabilityRequirement, IRSideEffect,
      IRBudget, IRAuditBoundary, IRReplayMarker, IRAdapterProvenance, IRValidationReport,
      IR_SCHEMA_VERSION)
  from .compiler import compile_workflow, compile_from_json, CompileResult
  from .validation import validate_graph
  from .exporters import to_workflow_info, to_json, from_json
  from .hashing import graph_hash
  # enrichment (optional, local-only):
  from .enrich import attach_mcp_risk
  from .eval_link import attach_recommendations
  ```
- **CLI surface:** new `ir_app` (`arc ir …`) — see §7. MVP = `compile`, `inspect`.
- **TypeScript protocol types:** `packages/arc-protocol-ts/src/swarmgraph-ir.ts`, exported from
  `index.ts` (ADR-018), structurally mirroring the Python models (read-only).
- **Storage format:** single-file `*.ir.json` (canonical, sorted keys, `\n` newline) written via
  `storage.atomic`. Optional sidecar `*.ir.hash` for the deterministic digest.
- **JSON schema:** generated from the Pydantic models (`IRGraph.model_json_schema()`) into
  `docs/schemas/swarmgraph-ir.schema.json` — mirrors the repo's "JSON Schema generated from
  Python models" convention.
- **Future UI integration:** IR JSON is a superset of the `WorkflowInfo` the
  `arc-workflow-graph-widget.tsx` already renders; the widget gains an IR source + a diff
  overlay (differentiator phase).
- **Connection to `security/policy_linter.py`:** `exporters.to_workflow_info(graph)` produces a
  `WorkflowInfo` whose node/edge `metadata` carries exactly the keys the linter reads
  (`is_mcp`, `mcp_manifest_hash`, `requires_paid_call`, `paid_call_gate`, `write_path`,
  `privileged`, `trust_annotation`, `consensus_protocol`, `num_workers`). `arc ir policy` calls
  `lint_workflow(to_workflow_info(graph))`. **Linter code is untouched.**
- **Connection to `mcp/manifests.py` + `mcp/registry.py`:** `enrich.attach_mcp_risk(graph,
  workspace)` loads `ManifestStore(workspace)` + `McpRegistryStore()`, and for each
  `IRMcpToolRef` fills `manifest_hash`, `risk` (from `McpToolRisk`), and `approved/blocked`.
  Pure local reads; no MCP server is launched.
- **Connection to `evals/policy_recommend.py`:** `eval_link.attach_recommendations(graph,
  report)` maps each `PolicyRecommendation.category` to advisory annotations on matching IR
  nodes (`eval_metadata`), never mutating execution semantics. Read-only.
- **Avoiding the finder trap:** the package is `swarmgraph_ir` (not a submodule of
  `agent_runtime_cockpit.swarmgraph`). When it needs the SDK it imports **`import swarmgraph`**
  (top-level distribution), exactly as `policy_linter.py` already does — that path is *not*
  rewritten and is proven to work.

---

## 4. Proposed module layout (adjusted to repo reality)

```
python/src/agent_runtime_cockpit/swarmgraph_ir/
├── __init__.py            # public API surface (§3)
├── models.py              # all IR* Pydantic models + IR_SCHEMA_VERSION
├── hashing.py             # canonical JSON + graph_hash() (split out for testability)
├── compiler.py            # compile_workflow(), compile_from_json(), CompileResult
├── provenance.py          # IRAdapterProvenance builders (adapter id, version, source_file)
├── validation.py          # validate_graph() -> IRValidationReport (fail-closed)
├── exporters.py           # to_workflow_info(), to_json(), from_json()
├── enrich.py              # attach_mcp_risk()  (local reads of mcp/manifests+registry)
├── eval_link.py           # attach_recommendations() (read-only eval→IR annotation)
└── adapters/
    ├── __init__.py        # ADAPTER_IMPORTERS registry: name -> importer
    ├── native.py          # WorkflowInfo/IR-JSON passthrough importer (MVP)
    ├── langgraph.py       # WorkflowInfo(runtime="langgraph") -> IRGraph metadata mapping
    ├── crewai.py
    ├── openai_agents.py
    ├── ag2.py
    └── llamaindex.py

packages/arc-protocol-ts/src/swarmgraph-ir.ts     # read-only TS mirror (ADR-018)
docs/schemas/swarmgraph-ir.schema.json            # generated JSON Schema
python/src/agent_runtime_cockpit/cli/ir.py        # arc ir sub-app commands
tests/python/swarmgraph_ir/                        # fixtures + regression tests
└── fixtures/{native_minimal,langgraph_branch,mcp_graph}.ir.json
```

**Deviations from the brief's suggested layout (and why):**
- Added `hashing.py` (kept hashing out of `models.py`/`compiler.py` so the deterministic digest
  is independently unit-testable).
- Added `enrich.py` + `eval_link.py` (the brief lists MCP/eval *integration* requirements;
  these are their concrete homes).
- `adapters/*.py` are **importers of existing `WorkflowInfo`**, not new framework parsers —
  honoring "do not bypass existing adapters."

---

## 5. IR model design

Conventions for **all** models:
- **Versioning:** module constant `IR_SCHEMA_VERSION = 1`; every `IRGraph` stamps `ir_version`.
  Additive evolution only within a major; breaking change bumps major + migration in
  `from_json`.
- **JSON serialization:** Pydantic v2 (`model_dump(mode="json")` / `model_validate`). Canonical
  form = `json.dumps(obj, sort_keys=True, separators=(",", ":"))`.
- **Stable IDs:** reuse `protocol/stable_ids.py`. Node IDs use `<graph>.<node>`; edge IDs use
  `<from>→<to>`. IDs are **derived from input**, never random, so output is reproducible.
- **Deterministic hashing:** `graph_hash()` = `sha256` over canonical JSON of a *normalized*
  view (nodes & edges sorted by id; volatile fields — timestamps, absolute paths, `compiled_at`
  — excluded). Mirrors `mcp/manifests.py::_hash_tools` style (`sha256(...)`); we keep full 64
  hex chars for the graph digest.
- **Backwards compatibility:** unknown fields ignored on load (`model_config =
  ConfigDict(extra="ignore")`) so newer files load in older readers; `ir_version` gate triggers
  a migration shim.

```python
# models.py  (abridged — types & required/optional intent)
from __future__ import annotations
from enum import Enum
from typing import Any, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field

IR_SCHEMA_VERSION = 1

class IRNodeKind(str, Enum):
    AGENT="agent"; TOOL="tool"; MCP_TOOL="mcp_tool"; MODEL_CALL="model_call"
    HUMAN_GATE="human_gate"; CONSENSUS="consensus"; ROUTER="router"
    FAN_OUT="fan_out"; FAN_IN="fan_in"; START="start"; END="end"; UNKNOWN="unknown"

class SideEffectKind(str, Enum):
    NONE="none"; READ="read"; WRITE="write"; NETWORK="network"
    PAID_CALL="paid_call"; EXEC="exec"; SECRET_READ="secret_read"

class _Base(BaseModel):
    model_config = ConfigDict(extra="ignore", frozen=False)

class IRRisk(_Base):
    level: Literal["low","medium","high","critical"] = "low"   # required (defaulted)
    score: float = 0.0                                          # 0..1
    signals: list[str] = Field(default_factory=list)
    rationale: Optional[str] = None
    source: Literal["sdk","heuristic","manual"] = "heuristic"

class IRCapabilityRequirement(_Base):
    capability: str                          # required, e.g. "fs.write","net.http"
    reason: Optional[str] = None
    optional: bool = False

class IRSideEffect(_Base):
    kind: SideEffectKind                     # required
    target: Optional[str] = None             # redacted path/host
    paid: bool = False
    confidence: float = 1.0

class IRBudget(_Base):
    tokens: Optional[int] = None
    cost_usd: Optional[float] = None
    latency_ms: Optional[int] = None
    requires_paid_call: bool = False
    paid_call_gate: bool = False

class IRToolRef(_Base):
    name: str                                # required
    namespace: Optional[str] = None
    pinned: bool = False
    capabilities: list[IRCapabilityRequirement] = Field(default_factory=list)

class IRMcpToolRef(_Base):
    server_id: str                           # required
    tool_name: str                           # required
    manifest_hash: Optional[str] = None      # filled by enrich.attach_mcp_risk
    can_write: bool = False; can_network: bool = False
    can_read_secrets: bool = False; accesses_outside_workspace: bool = False
    risk_level: Literal["low","medium","high"] = "low"
    approved: bool = False; blocked: bool = False

class IRModelCall(_Base):
    provider: Optional[str] = None
    model: Optional[str] = None
    paid: bool = False
    budget: Optional[IRBudget] = None

class IRHumanGate(_Base):
    gate_id: str                             # required
    blocking: bool = True
    prompt: Optional[str] = None
    trust_required: Optional[int] = None     # ADR-014 tier

class IRConsensusHint(_Base):
    protocol: Optional[str] = None           # from select_consensus_protocol / CONSENSUS_PROTOCOL_BY_RISK
    suggested_protocol: Optional[str] = None
    min_workers: Optional[int] = None
    source: Literal["sdk","metadata","default"] = "default"

class IRAuditBoundary(_Base):
    boundary_id: str                         # required
    reason: str                              # e.g. "privileged","paid_call","hitl"
    audit_level: Literal["none","arc_sha256","swarmgraph_hmac"] = "arc_sha256"

class IRReplayMarker(_Base):
    marker_id: str                           # required, deterministic from node id
    node_id: str
    correlation_key: str                     # stable join key for trace events

class IRAdapterProvenance(_Base):
    adapter_id: str                          # required, e.g. "langgraph"
    adapter_version: Optional[str] = None
    runtime: str                             # required
    source_file: Optional[str] = None        # redacted/relative
    exported_via: str = "export_workflow"
    imported_at: Optional[str] = None        # excluded from hash

class IRNode(_Base):
    id: str                                  # required, stable
    label: str = ""
    kind: IRNodeKind = IRNodeKind.UNKNOWN
    tool: Optional[IRToolRef] = None
    mcp_tool: Optional[IRMcpToolRef] = None
    model_call: Optional[IRModelCall] = None
    human_gate: Optional[IRHumanGate] = None
    consensus: Optional[IRConsensusHint] = None
    risk: IRRisk = Field(default_factory=IRRisk)
    capabilities: list[IRCapabilityRequirement] = Field(default_factory=list)
    side_effects: list[IRSideEffect] = Field(default_factory=list)
    budget: Optional[IRBudget] = None
    audit_boundary: Optional[IRAuditBoundary] = None
    replay_marker: Optional[IRReplayMarker] = None
    trust_annotation: Optional[str] = None   # ADR-014 origin/trust tag
    privileged: bool = False
    write_path: Optional[str] = None         # redacted; relative when in-workspace
    eval_metadata: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)

class IREdge(_Base):
    id: str                                  # required, "<from>→<to>"
    from_node: str; to_node: str             # required
    conditional: bool = False
    condition: Optional[str] = None
    label: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)

class IRValidationReport(_Base):
    ok: bool = True
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    node_count: int = 0
    edge_count: int = 0

class IRGraph(_Base):
    ir_version: int = IR_SCHEMA_VERSION       # required
    id: str                                   # required, stable
    name: str
    runtime: str                              # required, e.g. "langgraph"
    provenance: IRAdapterProvenance           # required
    nodes: list[IRNode] = Field(default_factory=list)
    edges: list[IREdge] = Field(default_factory=list)
    entry_points: list[str] = Field(default_factory=list)
    risk: IRRisk = Field(default_factory=IRRisk)
    consensus: IRConsensusHint = Field(default_factory=IRConsensusHint)
    graph_hash: Optional[str] = None          # filled at emit; excluded from its own input
    compiled_at: Optional[str] = None         # excluded from hash
    metadata: dict[str, Any] = Field(default_factory=dict)
```

---

## 6. Compiler design

`compile_workflow(workflow_info, *, workspace=None, enrich_mcp=False, use_sdk_risk=True) ->
CompileResult` (pure orchestration of pure stages; **no execution**):

1. **Load adapter export metadata** — accept a `WorkflowInfo` (from a real adapter's
   `export_workflow()`) or raw IR/`WorkflowInfo` JSON via `compile_from_json`.
2. **Normalize nodes** — map `NodeType` + `metadata` flags → `IRNode.kind` + typed sub-objects
   (`IRToolRef`, `IRMcpToolRef`, `IRHumanGate`, `IRConsensusHint`, …). Label heuristics reuse
   the linter's keyword sets (`hitl/approval/...`, `consensus/vote/...`) to stay consistent.
3. **Normalize edges** — copy `conditional`/`condition`/`label`; assign `<from>→<to>` IDs;
   drop dangling edges into validation warnings.
4. **Attach provenance** — `provenance.build(workflow_info, adapter_id, adapter_version)`;
   `source_file` made relative; absolute paths redacted.
5. **Attach MCP manifest/risk metadata** — *iff* `enrich_mcp`: `enrich.attach_mcp_risk(graph,
   workspace)` reads `ManifestStore`/`McpRegistryStore` (local only).
6. **Attach tool capability metadata** — derive `IRCapabilityRequirement` from tool/MCP flags
   (`fs.write`, `net.http`, `secret.read`, `fs.outside_workspace`).
7. **Infer side effects** — `SideEffectKind` from capabilities + `write_path` +
   `requires_paid_call` → `IRSideEffect` (with redacted targets). Inference only.
8. **Infer consensus hints** — if `use_sdk_risk`: `assess_prompt_risk()` →
   `select_consensus_protocol()` (graceful fallback to `CONSENSUS_PROTOCOL_BY_RISK` /
   metadata). Populates graph + node `IRConsensusHint`.
9. **Infer policy-linter input** — set node `metadata` keys the linter expects so the round-trip
   is loss-free.
10. **Validate graph** — `validation.validate_graph()` → `IRValidationReport` (fail-closed: any
    error ⇒ `CompileResult.ok=False`).
11. **Emit IR JSON** — canonicalize, compute `graph_hash`, set it, return canonical bytes.
12. **Emit `WorkflowInfo` for the existing linter** — `exporters.to_workflow_info(graph)`.
13. **(Later) emit SwarmGraph-native execution plan** — explicitly **out of scope for MVP**; a
    `to_execution_plan()` stub may be added once a non-executing planner contract is defined.

`CompileResult{ok: bool, graph: IRGraph, validation: IRValidationReport, workflow_info:
WorkflowInfo}`. **MVP compiles to IR + policy input only; it does not run the workflow.**

---

## 7. CLI design (`arc ir`)

| Command | Purpose | MVP? |
|---|---|---|
| `arc ir compile <wf-or-export> --runtime <name> --out graph.ir.json` | Adapter `WorkflowInfo`/JSON → IR JSON | ✅ MVP |
| `arc ir inspect graph.ir.json [--json]` | Human/JSON summary: nodes, kinds, risk, side-effects | ✅ MVP |
| `arc ir validate graph.ir.json` | Run `validate_graph`; exit non-zero on error | 1-week |
| `arc ir policy graph.ir.json [--json]` | `lint_workflow(to_workflow_info(graph))` → `PolicyReport` | 1-week |
| `arc ir diff a.ir.json b.ir.json` | Structural + hash diff | Differentiator |
| `arc ir explain graph.ir.json` | Narrate risk/consensus/side-effect rationale | Differentiator |

All commands use the repo's `ok()/err()` envelope helpers and never execute the workflow.
**MVP subset = `compile` + `inspect`.**

---

## 8. MVP scope

### 48-hour MVP (foundation, fully CI-safe)
- `swarmgraph_ir/models.py` (all IR models) + `hashing.py` (`graph_hash`).
- JSON serialization round-trip (`exporters.to_json/from_json`).
- `adapters/native.py` — importer for `WorkflowInfo` **and** raw IR JSON.
- `validation.py` — `validate_graph` (duplicate IDs, dangling edges, missing entry points,
  unknown node refs) → `IRValidationReport`, fail-closed.
- `exporters.to_workflow_info()` — IR → `WorkflowInfo` with linter-compatible metadata.
- CLI `arc ir compile` + `arc ir inspect`.
- `tests/python/swarmgraph_ir/` with `native_minimal.ir.json` fixture + round-trip/hash tests.

### 1-week MVP
- `adapters/{langgraph,crewai,openai_agents}.py` metadata importers over existing
  `WorkflowInfo`.
- `enrich.attach_mcp_risk()` (MCP manifest/registry enrichment, local reads).
- `arc ir policy` wired to `security/policy_linter.lint_workflow`.
- Stable `graph_hash` locked by golden test; `docs/schemas/swarmgraph-ir.schema.json` generated.
- `packages/arc-protocol-ts/src/swarmgraph-ir.ts` mirror + parity test (Py↔TS), matching the
  repo's existing parity-test pattern.

### 2–4 week differentiator
- Visual IR graph in Theia (feed `arc-workflow-graph-widget.tsx` from IR; risk/side-effect
  badges).
- `arc ir diff` + diff overlay in the widget (time-travel friendly via ADR-021 audit chain).
- Action-simulator integration (dry annotate side-effects; no execution).
- `eval_link.attach_recommendations()` surfaced in `inspect`/UI (advisory).
- Compiler importer plugins for **all** existing adapters (ag2, llamaindex, + dspy/haystack/
  semantic_kernel/etc.).

---

## 9. Patch plan (patch-ready commits)

> Sequence chosen so each commit is independently reversible and CI-green. Tests assume the
> repo's existing `pytest`/`uv`/`pnpm` toolchain.

### Commit 1 — `ir: add SwarmGraph IR models and stable graph hashing`
- **Message:** Introduce neutral `swarmgraph_ir` package with typed IR models and a
  deterministic `graph_hash`. No runtime behaviour; pure data. Package name avoids the
  `agent_runtime_cockpit.swarmgraph.*` MetaPathFinder (verified: that path is rewritten to the
  SDK and a submodule there is unreachable).
- **Files:** `swarmgraph_ir/__init__.py`, `swarmgraph_ir/models.py`, `swarmgraph_ir/hashing.py`.
- **Code:** models from §5; `hashing.py`:
  ```python
  import hashlib, json
  _VOLATILE = {"compiled_at", "graph_hash", "imported_at"}
  def _strip(obj):
      if isinstance(obj, dict): return {k:_strip(v) for k,v in sorted(obj.items()) if k not in _VOLATILE}
      if isinstance(obj, list): return [_strip(x) for x in obj]
      return obj
  def canonical_json(graph_dict: dict) -> str:
      return json.dumps(_strip(graph_dict), sort_keys=True, separators=(",", ":"))
  def graph_hash(graph) -> str:
      d = graph.model_dump(mode="json")
      return hashlib.sha256(canonical_json(d).encode()).hexdigest()
  ```
- **Tests:** `pytest tests/python/swarmgraph_ir/test_models.py` — construct `IRGraph`, dump/load
  round-trip, hash stability across two builds, hash insensitivity to `compiled_at`.
- **Expected output:** identical hash for identical logical graphs; differing hash when a node
  id changes.
- **Rollback:** delete the `swarmgraph_ir/` package (no other module imports it yet).

### Commit 2 — `ir: add JSON importer and validation report`
- **Files:** `swarmgraph_ir/exporters.py` (`to_json/from_json`),
  `swarmgraph_ir/validation.py`, `swarmgraph_ir/adapters/{__init__,native}.py`.
- **Tests:** `test_validation.py` (duplicate ids, dangling edge, empty entry points → errors/
  warnings; `ok` flips correctly), `test_native_importer.py` (WorkflowInfo→IR and IR-JSON→IR).
- **Expected output:** invalid metadata ⇒ `IRValidationReport.ok=False` (**fail closed**).
- **Rollback:** revert the three files; Commit 1 stands alone.

### Commit 3 — `ir: add WorkflowInfo bridge for policy linter`
- **Files:** `swarmgraph_ir/exporters.py` (`to_workflow_info`), `swarmgraph_ir/compiler.py`
  (`compile_workflow`, `compile_from_json`, `CompileResult`), `swarmgraph_ir/provenance.py`.
- **Tests:** `test_policy_bridge.py` — compile a graph with MCP/paid/privileged nodes →
  `to_workflow_info` → `lint_workflow` returns expected rules (R3/R4/R6) **without modifying the
  linter**.
- **Expected output:** linter `PolicyReport.issues` matches fixtures; `can_run` correct.
- **Rollback:** revert; linter untouched throughout.

### Commit 4 — `cli: add arc ir compile and arc ir inspect`
- **Files:** `cli/ir.py`, edits to `cli/_subapps.py` (`ir_app = typer.Typer(name="ir", ...)`)
  and `cli/_app.py` (`app.add_typer(ir_app)`).
- **Tests:** `test_cli_ir.py` (Typer `CliRunner`): `arc ir compile fixture.json --runtime native
  --out /tmp/x.ir.json` then `arc ir inspect /tmp/x.ir.json --json`.
- **Expected output:** exit 0; `--json` emits envelope with node/kind/risk summary; `--out` file
  is byte-identical on re-run (determinism).
- **Rollback:** remove `ir.py`, drop the two registration lines.

### Commit 5 — `tests: add IR fixtures and compiler regression tests`
- **Files:** `tests/python/swarmgraph_ir/fixtures/{native_minimal,langgraph_branch,mcp_graph}.ir.json`,
  `test_compiler_regression.py`, golden `expected_hashes.json`.
- **Tests:** `pytest tests/python/swarmgraph_ir -q`.
- **Expected output:** golden hashes match (locks determinism); regression guard for future
  changes.
- **Rollback:** delete fixtures/tests.

### Commit 6 — `protocol: add TypeScript SwarmGraph IR mirror`
- **Files:** `packages/arc-protocol-ts/src/swarmgraph-ir.ts`, export from `index.ts`,
  `swarmgraph-ir.test.ts` parity test.
- **Tests:** `pnpm --filter @arc/protocol-ts test` (or repo's TS test cmd).
- **Expected output:** TS interfaces structurally mirror Python; parity test green.
- **Rollback:** remove the `.ts` file + index export.

### Commit 7 — `ir: enrich MCP tool nodes from manifest registry`
- **Files:** `swarmgraph_ir/enrich.py`, compiler `enrich_mcp=True` path, `cli/ir.py`
  `--enrich-mcp` flag, `test_mcp_enrich.py`.
- **Tests:** seed a temp `ManifestStore`/`McpRegistryStore`, compile an MCP graph with
  `enrich_mcp=True`, assert `IRMcpToolRef.manifest_hash/risk_level/approved` populated; assert
  **no MCP server process is spawned** (monkeypatch session launcher to raise).
- **Expected output:** enriched IR; zero network/process side-effects.
- **Rollback:** revert `enrich.py` + flag; compiler default `enrich_mcp=False` keeps prior
  behaviour.

---

## 10. Safety checklist (with how each is proven)

| Property | How it's guaranteed | How it's proven in CI |
|---|---|---|
| **No workflow execution in compiler** | Compiler only maps data; never calls `run_workflow`/`stream_events` | grep test: assert `swarmgraph_ir/` source contains no `run_workflow`/`await`/`subprocess`/`asyncio.run` |
| **No new network exposure** | No sockets/HTTP clients imported in the package | import-graph test forbids `aiohttp`/`requests`/`http` in `swarmgraph_ir` |
| **No paid calls** | Paid intent is *recorded* (`IRBudget.requires_paid_call`), never *invoked* | unit test: compiling a paid node performs zero provider calls (provider monkeypatched to raise) |
| **No tool invocation** | Tools are referenced (`IRToolRef`), never called | grep/monkeypatch test |
| **No MCP server execution** | Enrichment only reads `ManifestStore`/`McpRegistryStore` files | test monkeypatches MCP session launcher to raise; enrich still succeeds |
| **Manifest reads are local only** | `ManifestStore` = `<ws>/.arc/mcp/pins`, registry = `~/.arc/mcp/servers.json` (both file reads) | covered by enrich test on a temp dir |
| **Workspace trust preserved** | `trust_annotation` carried through; writes outside workspace surfaced via `IRSideEffect`/linter R5 | round-trip test preserves trust tags; linter R5 fires on out-of-ws `write_path` |
| **Generated IR is deterministic** | Canonical sorted JSON; derived IDs; volatile fields excluded from hash | golden-hash regression test (Commit 5) |
| **Secrets redacted** | Compiler runs `security.redaction.redact_secrets()` over string fields on emit | test feeds a fake `sk-...`/token; asserts redaction in output IR |
| **Invalid adapter metadata fails closed** | `validate_graph` → `ok=False`; `compile_*` propagates; CLI exits non-zero | validation tests + CLI exit-code test |
| **Compiler runs in CI** | Pure-Python, no network/process, no external deps beyond pydantic | the entire `tests/python/swarmgraph_ir` suite runs offline |

---

## 11. Final recommendation

1. **Recommended package name:** `agent_runtime_cockpit.swarmgraph_ir`
   (neutral, finder-safe — the trap was empirically reproduced; imports the SDK as top-level
   `import swarmgraph`, exactly like `policy_linter.py`).
2. **Selected architecture option:** **Option A** (neutral `swarmgraph_ir/` package) with
   `compiler.py` as an internal module (absorbing the best of Option B). Reject C and D.
3. **First 5 commits:**
   1. `ir: add SwarmGraph IR models and stable graph hashing`
   2. `ir: add JSON importer and validation report`
   3. `ir: add WorkflowInfo bridge for policy linter`
   4. `cli: add arc ir compile and arc ir inspect`
   5. `tests: add IR fixtures and compiler regression tests`
4. **Exact next command to run:**
   ```bash
   mkdir -p python/src/agent_runtime_cockpit/swarmgraph_ir/adapters \
            tests/python/swarmgraph_ir/fixtures && \
   python - <<'PY'
   import sys; sys.path.insert(0,'python/src'); sys.path.insert(0,'python/packages/swarmgraph-sdk')
   import agent_runtime_cockpit.swarmgraph  # install bridge finder
   import importlib
   try:
       importlib.import_module('agent_runtime_cockpit.swarmgraph.ir')
       print('UNEXPECTED: submodule resolved — re-check before proceeding')
   except ModuleNotFoundError as e:
       print('CONFIRMED finder trap ->', e, '| proceed with package name swarmgraph_ir')
   PY
   ```
   (Run this guard first; it re-confirms the import trap on the target machine, then start
   Commit 1 by creating `python/src/agent_runtime_cockpit/swarmgraph_ir/models.py`.)
