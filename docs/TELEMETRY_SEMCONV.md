# Telemetry Semantic Conventions

## OpenTelemetry Version

**Package:** `@opentelemetry/semantic-conventions@^1.36`  
**GenAI Semconv:** v1.28.0 (Development status)  
**Spec:** https://opentelemetry.io/docs/specs/semconv/gen-ai/  
**Last Updated:** 2026-05-12

## Usage Policy

ARC pins `@opentelemetry/semantic-conventions@^1.36`. The GenAI semantic
conventions are still labeled "Development" upstream, so:

- The default span attribute set uses only the **stable** subset of GenAI
  attributes plus generic OpenTelemetry attributes.
- Experimental GenAI attributes (anything under `gen_ai.tool.*`,
  `gen_ai.agent.*`, the prompt/completion event bodies) are emitted only when
  `ARC_OTEL_GENAI_EXPERIMENTAL=1`.
- ARC never serializes raw prompts or tool arguments without first running
  them through the shared redaction module.
- The trace exporter is disabled by default. Enabling it requires both:
   - `arc.telemetry.otlpEndpoint` preference set, AND
   - explicit user action via "ARC: Export Trace to OTLP" command.

If/when upstream marks GenAI semconv stable, file a [VERIFY] PR to flip the
default and remove the experimental flag.

## Span Attributes

### Stable Attributes (Always Emitted)
- `service.name` - "arc-studio"
- `service.version` - ARC version
- `span.kind` - "INTERNAL"
- `trace.id` - Run ID
- `span.name` - Event type or step name

### GenAI Attributes (Development Status)
Emitted when `ARC_OTEL_GENAI_EXPERIMENTAL=1`:

**Agent Attributes:**
- `gen_ai.agent.name` - Agent/runtime name
- `gen_ai.agent.id` - Agent instance ID
- `gen_ai.system` - "swarmgraph" | "langgraph" | "openai-agents"

**Tool Attributes:**
- `gen_ai.tool.name` - Tool function name
- `gen_ai.tool.call.id` - Tool call ID

**Request/Response Attributes:**
- `gen_ai.request.model` - Model name (if applicable)
- `gen_ai.response.finish_reason` - Completion reason
- `gen_ai.usage.input_tokens` - Token counts (if available)
- `gen_ai.usage.output_tokens`

### Security

**Redacted Attributes:**
- API keys, tokens, passwords
- Environment variables
- Tool arguments containing secrets
- Prompt/completion content (unless explicitly enabled)

All attributes pass through `redactValue()` before export.

## Export Configuration

**Preference:** `arc.telemetry.otlpEndpoint`  
**Default:** `""` (disabled)  
**Example:** `http://localhost:4317`  
**Command:** "ARC: Export Trace to OTLP"

**Endpoint Validation:**
- Empty endpoint = export disabled
- Non-localhost endpoint = warning shown to user
- Invalid endpoint = error, no export

## Implementation

See `python/src/agent_runtime_cockpit/telemetry/otlp_exporter.py` for the exporter implementation.
