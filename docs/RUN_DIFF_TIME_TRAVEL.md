# Run Diff / Time Travel

**ARC Studio — local-first, deterministic run comparison and timeline inspection.**

---

## What Is It?

Run Diff / Time Travel is a zero-network, read-only comparison and inspection layer for ARC Studio run artifacts. It compares two versions of a workflow's intermediate representation (IR), run records, policy reports, simulation results, capability cards, MCP manifests, and flight recorder segments — producing a `RunDiffReport` that identifies exactly what changed, where the first divergence occurred, and what semantic regressions were introduced.

The design is shaped by five hard constraints:

| Constraint | What it means |
|---|---|
| **Local-first** | No network calls, no external services, no model calls |
| **Read-only diffing** | Diff functions never mutate input artifacts |
| **Secrets redacted before display/export** | `redact_report()` always applied before output |
| **Corrupt/partial traces don't crash** | Graceful degradation with error/warning fields |
| **Unknown event types preserved as opaque** | Raw event types passthrough as `EventEntry` |

---

## Quick Start

```bash
# Compare two IR files
arc ir diff graph-a.ir.json graph-b.ir.json

# Output as JSON
arc ir diff graph-a.ir.json graph-b.ir.json --json

# Include timeline frames in output
arc ir diff graph-a.ir.json graph-b.ir.json --timeline --json

# Compare two run IDs from JSONL store
PYTHONPATH=$PWD/src python -c "
from agent_runtime_cockpit.run_diff import diff_ir_from_paths, to_json
report = diff_ir_from_paths('run-a.ir.json', 'run-b.ir.json', redact=True)
print(to_json(report))
"
```

---

## Architecture

```
run_diff/
  models.py       — Pydantic types: RunDiffReport, DiffSummary, GraphDiff, …
  loaders.py      — Load IR/policy/run/simulation/capability/JSONL from paths
  diff_ir.py      — IR graph diff: node/edge comparison, first divergence
  diff_policy.py  — Policy report diff: issue regression classification
  diff_events.py  — Run record diff: event alignment by sequence
  diff_simulation.py — Simulation report diff: HITL/paid-call delta
  diff_mcp.py     — MCP manifest diff: server drift detection
  diff_capabilities.py — Capability card diff: risk level, MCP drift
  diff_flight.py  — Flight recorder segment diff: hash chain validation
  timeline.py     — TimelineFrame generation + TimeTravelCursor
  redaction.py    — Secret redaction before display/export
  export.py       — JSON round-trip: to_json, from_json, write_json, load_report
  __init__.py     — Full public API exports
```

---

## Core Concepts

### `RunDiffReport`

The primary output type. Every diff operation returns a `RunDiffReport`:

```python
from agent_runtime_cockpit.run_diff import RunDiffReport

report: RunDiffReport
# Fields:
#   schema_version: int          # Always 1 for v1
#   generated_at: str            # ISO-8601 timestamp
#   left / right: DiffSubject    # Identity of each artifact
#   mode: DiffMode               # "ir_vs_ir" | "run_vs_run" | …
#   summary: DiffSummary         # Counts + regression flags
#   first_divergence: FirstDivergence | None
#   graph_diff: GraphDiff | None
#   event_diff: EventDiff | None
#   policy_diff: PolicyDiff | None
#   simulation_diff: SimulationDiff | None
#   capability_diff: CapabilityDiff | None
#   flight_diff: FlightDiff | None
#   mcp_diff: McpManifestDiff | None
#   cost_diff: CostDiff | None
#   risk_diff: RiskDiff | None
#   timeline: list[TimelineFrame]
#   warnings: list[str]
#   errors: list[str]
#   diff_hash: str               # SHA-256 of canonical report content
```

### `DiffMode`

The `mode` field describes what kind of artifacts were compared:

| Mode | Input types |
|---|---|
| `ir_vs_ir` | Two `.ir.json` files (SwarmGraph IR graphs) |
| `run_vs_run` | Two `RunRecord` objects from JSONL store |
| `policy_vs_policy` | Two `PolicyReport` objects |
| `simulation_vs_simulation` | Two `SimulationReport` objects |
| `simulation_vs_run` | One simulation + one run record |
| `capability_vs_capability` | Two `CapabilityCard` objects |
| `flight_vs_flight` | Two `FlightSegment` chains |
| `mcp_vs_mcp` | Two `McpServerManifest` lists |

### `ChangeType`

Enum with values: `added`, `removed`, `changed`, `unchanged`. Applied to nodes, edges, events, and timeline frames.

### `DiffSummary`

Aggregated counts and regression flags:

```python
summary.nodes_added          # int
summary.nodes_removed        # int
summary.nodes_changed        # int
summary.edges_added          # int
summary.edges_removed        # int
summary.events_added         # int
summary.events_removed       # int
summary.policy_blockers_introduced  # int
summary.risk_increased       # bool
summary.hitl_removed         # bool
summary.paid_call_delta      # int  (+1 = introduced)
summary.consensus_changed    # bool
summary.total_changes        # int  (auto-computed)
summary.has_changes          # bool
```

---

## Diff Operations

### IR Diff (`diff_ir_graphs`, `diff_ir_from_paths`)

Compares two `IRGraph` objects node-by-node and edge-by-edge.

**First divergence detection** finds the earliest structural change:
- Node added/removed/changed
- Edge added/removed
- Risk level escalation
- HITL gate removed
- Paid call introduced
- Consensus protocol weakened

**Semantic regression flags** are set on `NodeDiff.is_semantic_regression` when:
- HITL guard removed (risk increased without approval)
- Paid model call introduced in previously free path
- Consensus threshold decreased
- Trust boundary weakened

### Policy Diff (`diff_policy_reports`, `diff_policy_from_paths`)

Compares two `PolicyReport` objects for regression:

- **Error regression**: new `ERROR` severity issues introduced
- **Blocker regression**: `can_run` goes `True → False`
- **Severity escalation**: existing issue gets worse severity
- **Risk regression**: risk level increases

### Event Diff (`diff_run_records`, `diff_run_records_from_ids`)

Aligns events by `sequence` number between two `RunRecord` objects. Detects:
- Events added/removed
- Events changed (same sequence, different type or data)
- First event divergence index

### Simulation Diff (`diff_simulation_reports`)

Compares `SimulationReport` objects:
- `hitl_gate_delta`: gates added/removed
- `paid_call_delta`: paid calls introduced/removed
- `policy_regression`: `can_run` changed
- Reachable node count difference

### MCP Diff (`diff_mcp_manifests`)

Hash-comparison of MCP server manifests:
- Server added/removed
- Server hash changed (tool list drift)
- Approved/blocked tool delta

### Capability Diff (`diff_capability_cards`, `diff_capability_cards_from_paths`)

Compares `CapabilityCard` objects:
- MCP drift detection
- Risk level changes per card
- Trust regression flags

### Flight Diff (`diff_flight_segments`, `diff_flight_events`)

Validates hash chains between two flight segment sequences:
- Events added/removed
- Hash chain integrity check (`segment_hashes_match`)
- Chain continuity validation

---

## Load Functions

The `loaders.py` module provides file-type detection and loading for all artifact types:

```python
from agent_runtime_cockpit.run_diff import load_any, load_ir_from_path

# Auto-detect type from path suffix
result: LoadResult = load_any("path/to/something.ir.json")
if result.ok:
    data = result.data
else:
    print(result.error)  # LoadError with message

# Explicit loaders
ir_graph = load_ir_from_path("graph.ir.json").data
policy_report = load_policy_from_path("policy.yaml").data
simulation = load_simulation_from_path("sim.json").data
capability = load_capability_card_from_path("capability.json").data
```

---

## Timeline

### `build_timeline_from_report(report)`

Converts a `RunDiffReport` into an ordered list of `TimelineFrame` objects. Each frame represents a discrete change (node added/removed/changed, edge change, event change, policy issue). Frames are ordered by sequence index.

### `build_timeline_from_run_events(events, subject, run_id)`

Builds a timeline directly from run event objects.

### `TimeTravelCursor`

Step through a timeline frame-by-frame:

```python
from agent_runtime_cockpit.run_diff import TimeTravelCursor

cursor = TimeTravelCursor(report.timeline)
print(cursor.current)       # First frame

cursor.step_forward()       # Next frame
cursor.step_forward()       # Next frame
cursor.step_back()          # Back one

cursor.seek_to("abc123...")  # Jump to specific frame

# Get surrounding context
frames = cursor.context(before=2, after=2)

# Export cursor state
state = cursor.as_dict()
```

---

## Redaction

Every report goes through redaction before it is displayed or exported. The redaction pipeline applies:

1. **Pattern-based regex** (11 patterns from `security.redaction`):
   - API keys (Anthropic `sk-ant-...`, OpenAI `sk-...`)
   - AWS access keys (`AKIA...`)
   - GitHub tokens (`ghp_`, `ghs_`, `gho_`, `ghr_`)
   - Bearer tokens
   - URL-embedded passwords
   - Generic `api_key = ...` / `token = ...` assignments

2. **Key-name-based redaction**: any dict key containing `key`, `token`, `password`, `secret`, `credential`, `auth`, `private`, `bearer`, `signing`

```python
from agent_runtime_cockpit.run_diff import redact_report, redact_dict, is_safe

# Redact a report dict before JSON serialization
safe_report = redact_report(report.model_dump(mode="json"))

# Redact a nested dict
safe_data = redact_dict(event_data)

# Check if text is safe to display without redaction
if is_safe(text):
    print(text)
else:
    print(redact_text(text))
```

**Important**: `redact_report()` uses `redact_dict()` internally for nested dicts — it does not call itself recursively.

---

## Export

```python
from agent_runtime_cockpit.run_diff import to_json, from_json, write_json, load_report, summary_text

# Serialize to JSON string
json_str = to_json(report, indent=2)

# Deserialize from JSON
report2 = from_json(json_str)

# Write to file
write_json(report, "diff-report.json")

# Load from file
report3 = load_report("diff-report.json")

# Human-readable summary
summary = summary_text(report)
print(summary)
```

---

## CLI Integration

### `arc ir diff`

```bash
arc ir diff <left_path> <right_path> \
    [--timeline]          # Include timeline frames in JSON output
    [--redact | --no-redact]  # Force/enable redaction (default: on)
    [--json]              # JSON output
    [--output FILE]       # Write to file instead of stdout
```

Uses `ir_diff_cmd()` from `cli/ir.py`. Internally uses `diff_ir_from_paths()`.

### `arc runs timeline`

```bash
arc runs timeline <run_id> [--limit N]
```

Renders the event timeline for a single run as human-readable output.

---

## Safety Model

| Constraint | Enforcement |
|---|---|
| No network I/O | No `requests`, `httpx`, `aiohttp`, `socket`, `urlopen` in any module |
| No subprocess | No `subprocess`, `os.system`, `Popen` |
| No model calls | No LLM API calls — pure data comparison |
| No MCP server startup | Manifests referenced by ID and hash only |
| Read-only | Diff functions accept data, never mutate inputs |
| Fail closed | Corrupt inputs populate `errors` field, don't crash |
| Secrets redacted | `redact_report()` applied before every display/export |

**Safety scan:**
```bash
grep -RIn "subprocess\|socket\|aiohttp\|requests\|httpx\|os\.system\|Popen\|urlopen\|listen\|serve" \
  python/src/agent_runtime_cockpit/run_diff \
  python/tests/run_diff
# Expected: no matches in runtime code
```

---

## Relation to Existing `evals/diff.py`

The existing `arc runs diff` (from `evals/diff.py`) operates at the **run record level** — comparing two `RunRecord` objects for evaluation purposes.

The new `run_diff` package operates at the **artifact level** — comparing IR graphs, policy reports, simulation reports, capability cards, MCP manifests, and flight segments. It is orthogonal and composable with the existing evals diff.

| | `evals/diff.py` | `run_diff/` |
|---|---|---|
| Scope | `RunRecord` objects | IR, policy, simulation, capability, MCP, flight |
| Use case | Eval trending | Semantic regression detection |
| Output | `RunDiff` (evals) | `RunDiffReport` (run_diff) |
| Timeline | No | Yes — `TimelineFrame` list |

---

## Running Tests

```bash
cd python
uv run --extra dev python -m pytest tests/run_diff -q

# Specific test files
uv run --extra dev python -m pytest tests/run_diff/test_diff_ir.py -v
uv run --extra dev python -m pytest tests/run_diff/test_diff_policy.py -v
uv run --extra dev python -m pytest tests/run_diff/test_redaction_and_timeline.py -v
```

---

## File Format

`RunDiffReport` is serialized as JSON with the following top-level structure:

```json
{
  "schema_version": 1,
  "generated_at": "2026-06-03T12:00:00Z",
  "left": { "kind": "ir_graph", "id": "...", "path": "left.ir.json", "graph_hash": "..." },
  "right": { "kind": "ir_graph", "id": "...", "path": "right.ir.json", "graph_hash": "..." },
  "mode": "ir_vs_ir",
  "summary": {
    "nodes_added": 0, "nodes_removed": 0, "nodes_changed": 1,
    "edges_added": 0, "edges_removed": 0,
    "risk_increased": true, "hitl_removed": false, "paid_call_delta": 1,
    "total_changes": 1
  },
  "first_divergence": {
    "kind": "node", "node_id": "node-42",
    "reason": "Paid call introduced",
    "sequence": 5, "frame_index": 5
  },
  "graph_diff": { ... },
  "timeline": [ ... ],
  "warnings": [],
  "errors": [],
  "diff_hash": "sha256:..."
}
```

See `docs/schemas/run-diff.schema.json` for the complete JSON Schema.