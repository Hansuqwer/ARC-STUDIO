# AG-UI Mapping Reference

This document is the single normative mapping from each supported runtime's
native event vocabulary to AG-UI events.

## SwarmGraph

| Native `kind`  | AG-UI events emitted                                                            |
| -------------- | ------------------------------------------------------------------------------- |
| `run.start`    | RUN_STARTED                                                                     |
| `run.finish`   | RUN_FINISHED                                                                    |
| `run.error`    | RUN_ERROR (code from `error.code`, message from `error.message`)                |
| `handoff`      | STEP_STARTED (stepName = `handoff:<agent>`)                                     |
| `agent.text`   | TEXT_MESSAGE_START, TEXT_MESSAGE_CONTENT, TEXT_MESSAGE_END                      |
| `tool.call`    | TOOL_CALL_START, TOOL_CALL_ARGS, TOOL_CALL_END, TOOL_CALL_RESULT                |
| `state`        | STATE_SNAPSHOT                                                                  |
| any other      | RAW with `source = "swarmgraph"`                                                |

## LangGraph (astream_events v2)

| Native `event`               | AG-UI events emitted                                       |
| ---------------------------- | ---------------------------------------------------------- |
| `on_chain_start` (name=langgraph) | RUN_STARTED                                           |
| `on_chain_start` (other)     | STEP_STARTED                                               |
| `on_chain_end` (name=langgraph)   | RUN_FINISHED                                          |
| `on_chain_end` (other)       | STEP_FINISHED                                              |
| `on_chat_model_stream`       | TEXT_MESSAGE_CHUNK                                         |
| `on_tool_start`              | TOOL_CALL_START + TOOL_CALL_ARGS                           |
| `on_tool_end`                | TOOL_CALL_END + TOOL_CALL_RESULT                           |
| `on_chain_state`             | STATE_SNAPSHOT                                             |
| `on_error`                   | RUN_ERROR (code = `LANGGRAPH_ERROR`)                       |
| anything else                | RAW with `source = "langgraph"`                            |

## Redaction invariants

All mapped events pass through `redactValue` and `capPayload` before leaving
the mapper. Tests in `redaction.test.js` enforce that:

- Tokens matching the patterns in `redaction.ts` are replaced with «REDACTED».
- Object keys named `api_key`, `token`, `authorization`, etc., have their
  values replaced wholesale.
- Events exceeding 64 KiB are replaced with a truncated preview record.

## Versioning

This mapping targets AG-UI core schema as captured in `docs/VERIFICATION.md`.
A change to the upstream `EventType` enum requires:

1. Update `packages/arc-ag-ui/src/event-types.ts`.
2. Regenerate golden fixtures in `packages/arc-ag-ui/test/fixtures/`.
3. Bump `@arc/ag-ui` minor version.
