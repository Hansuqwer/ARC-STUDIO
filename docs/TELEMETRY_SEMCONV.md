# Telemetry Semantic Conventions

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
   - explicit user click on "Test export" in the preferences UI (PR8).

If/when upstream marks GenAI semconv stable, file a [VERIFY] PR to flip the
default and remove the experimental flag.
