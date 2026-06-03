# OpenInference / OpenTelemetry Export

ARC Studio can export runtime traces as local JSON files compatible with OpenInference and OpenTelemetry span conventions — without sending data to any external service.

## What it is

A local-first, opt-in export layer that converts ARC run artifacts into structured span JSON. You can:

- Inspect ARC runs as OTel-style spans offline
- Export to files readable by Phoenix, Langfuse, or any OTel-compatible tool
- Prove redaction before export (no secrets in output)
- Attach IR metadata, policy reports, and MCP manifest data as span events

## What it is NOT

- **Not a live exporter** — no OTLP HTTP/gRPC in MVP
- **Not a collector** — does not run a server or bind to a port
- **Not a backend** — does not store or index exported data
- **Not a cloud service** — nothing leaves your machine by default

## Local-only default

All exports write to local files only. The `--format` flag selects the schema; the `--out` flag selects the destination. No network calls are made.

## Redaction model

Redaction happens **before** hashing and **before** writing. The pipeline:

1. Load JSONL trace (tolerate corrupt lines)
2. Map events to spans
3. **Redact** API keys, tokens, secrets, key-named fields
4. Attach IR/policy metadata (also redacted)
5. Compute `export_hash` (over redacted content, excluding volatile fields)
6. Validate
7. Write to `--out`

The `arc obs redaction-check` command verifies the output file contains no detectable secrets.

## Supported formats

| Format | Description |
|---|---|
| `openinference-json` | OpenInference semantic conventions + ARC attributes |
| `arc-otel-json` | ARC-namespaced OTel-style spans, no OpenInference aliases |

## CLI examples

```bash
# Export a trace as OpenInference JSON
arc obs export --trace-file run.jsonl --format openinference-json --out run.oi.json --json

# Export with IR and policy metadata attached
arc obs export --trace-file run.jsonl --ir-file graph.ir.json --policy-file policy.json --out run.oi.json

# Export as arc-otel-json
arc obs export --trace-file run.jsonl --format arc-otel-json --out run.otel.json

# Inspect an export
arc obs inspect run.oi.json --json

# Validate an export
arc obs validate run.oi.json --json

# Check for secrets in export output
arc obs redaction-check run.oi.json --json
```

## ARC → OTel span mapping

| ARC concept | Span name | Representation |
|---|---|---|
| Run | `arc.run` | Root span |
| IR graph | `arc.ir.graph` | Span event on root |
| IR node | `arc.ir.node` | Child span |
| Model call | `arc.model.call` | Child span (CLIENT kind) |
| Tool call | `arc.tool.call` | Child span |
| MCP tool | `arc.mcp.tool` | Child span |
| HITL gate | `arc.hitl.gate` | Span event on root |
| Consensus | `arc.consensus.select` | Span event on root |
| Policy | `arc.policy.evaluate` | Span event on root |
| Eval recommendation | `arc.eval.recommend` | Span event |
| Unknown event | `arc.opaque.event` | Span event (preserved) |

## ARC span attributes

| Attribute | Description |
|---|---|
| `arc.run.id` | Run identifier |
| `arc.runtime.name` | Runtime name (swarmgraph, langgraph, etc.) |
| `arc.ir.graph_hash` | IR graph hash |
| `arc.policy.can_run` | Whether policy allows execution |
| `arc.policy.risk_level` | Risk level from policy linter |
| `arc.mcp.server_id` | MCP server identifier |
| `arc.mcp.manifest_hash` | Pinned manifest hash |
| `arc.mcp.drifted` | Whether manifest has drifted |
| `arc.consensus.protocol` | Selected consensus protocol |
| `arc.hitl.required` | Whether HITL approval was required |

## OpenInference attribute aliases (openinference-json only)

| ARC attribute | OpenInference alias |
|---|---|
| `arc.model.name` | `llm.model_name` |
| `arc.model.provider` | `llm.provider` |
| `arc.tool.name` | `tool.name` |
| Span kind | `openinference.span.kind` |

## Relation to SwarmGraph IR

When `--ir-file` is provided, the IR graph hash and node count are attached as a span event (`arc.ir.graph`) on the root span. This lets observability tools correlate the exported trace with its compiled IR.

## Relation to policy linter

When `--policy-file` is provided, policy findings (can_run, risk_level, issue_count) are attached as a `arc.policy.evaluate` span event.

## Relation to MCP registry

MCP tool calls in the trace produce `arc.mcp.tool` child spans with `server_id`, `manifest_hash`, and `drifted` attributes. No MCP servers are started.

## Relation to Flight Recorder

The Flight Recorder stores raw segment events; the observability exporter reads JSONL traces (storage format). They are complementary: FR for crash forensics, obs for structured portability.

## Future: Phoenix / Langfuse / collector

The `arc-otel-json` and `openinference-json` formats are designed to be ingested by:

- **Arize Phoenix** via OpenInference JSON file import
- **Langfuse** via OTLP JSON or direct file import
- **OTel Collector** via OTLP file exporter (future: add `--endpoint` to push)

No live OTLP HTTP/gRPC export is implemented in MVP. Configure `ObservabilityExportConfig(mode="local")` (the default) to stay local-only.
