# ARC Studio API & Protocol Verification (PR1)

Status: RESOLVED for Tier-1 start.

## Theia 1.71 — confirmed import paths
| Symbol                       | Package                          | Source                              |
| ---------------------------- | -------------------------------- | ----------------------------------- |
| `Agent`                      | `@theia/ai-core`                 | packages/ai-core/src/common         |
| `AIVariableContribution`     | `@theia/ai-core`                 | packages/ai-core/src/common/variable-service.ts |
| `AIVariableService`          | `@theia/ai-core`                 | same                                |
| `PromptService`              | `@theia/ai-core`                 | packages/ai-core/src/common         |
| `ChatAgent`                  | `@theia/ai-chat/lib/common`      | packages/ai-chat/src/common/chat-agents.ts |
| `AbstractChatAgent`          | `@theia/ai-chat/lib/common`      | same                                |
| `ChatAgentLocation`          | `@theia/ai-chat/lib/common`      | same                                |
| `AbstractViewContribution`   | `@theia/core/lib/browser`        | stable                              |
| `ReactWidget`                | `@theia/core/lib/browser`        | stable                              |
| `StatusBar`, `StatusBarEntry`| `@theia/core/lib/browser/status-bar` | optional usage only; PR2 of any feature |

The Status Bar contribution is **optional** for all Tier-1 features per
roadmap §3.

## AG-UI — schema pin
- TypeScript: `@ag-ui/core` (events, schemas, types).
- Python: `ag-ui-protocol`.
- Canonical `EventType` enum (33 variants) is captured in
  `packages/arc-ag-ui/src/event-types.ts`. Any drift must regenerate fixtures.

## OpenTelemetry GenAI semantic conventions
- npm: `@opentelemetry/semantic-conventions@^1.36`.
- Default emission set: stable subset only.
- Experimental GenAI attributes (`gen_ai.tool.name`, agent spans, etc.) are
  emitted **only** when `ARC_OTEL_GENAI_EXPERIMENTAL=1`.
- The upstream docs page still labels GenAI semconv "Development" at the time
  of pinning; treat all experimental attrs as subject to change. Snapshot
  attributes from fixtures, not from a live backend.

## OpenAI Agents SDK
- Package: `openai-agents` (Python). Tracing via the SDK's built-in tracer.
- Adapter must consume SDK tracing/events; no direct OpenAI client.

## LangGraph
- Stream API: `astream_events(version="v2")`.
- Mapping fixtures live in `tests/fixtures/langgraph/*.jsonl`.

## A2A and MCP
- Schemas not yet pinned. **Tier-2** items. No coding before a fixture pin PR.

## Repo layout (after path audit)
- `packages/arc-ag-ui/` — AG-UI schema, mappers, redaction (new).
- `packages/arc-protocol/` — runtime-native event types (rename if existing
  package found during PR2 path audit).
- `packages/arc-test-fixtures/` — fixture loader & golden JSONL.
- `theia-extensions/arc-event-stream/` — Event Stream widget (PR5).
- `theia-extensions/arc-config-chat-agent/` — Chat Agent (PR18).
- `python/arc_daemon/adapters/openai_agents.py` — adapter (PR4).
- `.arc/traces/*.jsonl` — runtime trace source of truth.
