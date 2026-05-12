# Phase 3 Roadmap (PR11–PR16)

| PR  | Slug                        | Acceptance commands                                            |
| --- | --------------------------- | -------------------------------------------------------------- |
| 11  | real-swarmgraph             | pytest python/tests/adapters/swarmgraph -q                     |
| 12  | real-langgraph-streaming    | pytest python/tests/adapters/langgraph -q                      |
| 13  | openai-agents-streaming     | pytest python/tests/adapters/openai_agents -q                  |
| 14  | crewai-adapter              | pytest python/tests/adapters/crewai -q                         |
| 15  | ag2-adapter                 | pytest python/tests/adapters/ag2 -q                            |
| 16  | integration-tests-hardening | pytest python/tests/integration -q && pytest --cov=src --cov-fail-under=70 |

## Verified upstream APIs pinned for this phase
- OpenAI Agents SDK: `Runner.run_streamed(...)` returns `RunResultStreaming`
  whose `stream_events()` yields `RawResponsesStreamEvent`,
  `RunItemStreamEvent`, and `AgentUpdatedStreamEvent`.
- LangGraph: `compiled_graph.astream_events(input, version="v2")` yields
  dicts with `event`, `name`, `run_id`, `data`. `langgraph.json` lists
  `"graphs": { "<id>": "module.path:variable" }` and is the canonical
  workspace entry point.
- CrewAI: `crewai.events.BaseEventListener.setup_listeners(bus)`; events
  include `CrewKickoffStartedEvent`, `CrewKickoffCompletedEvent`,
  `AgentExecutionStartedEvent`, `AgentExecutionCompletedEvent`,
  `TaskStartedEvent`, `TaskCompletedEvent`, `ToolUsageStartedEvent`,
  `ToolUsageFinishedEvent`, `LLMStreamChunkEvent`.
- AG2: `autogen.agentchat.a_run_group_chat(...)` returns an
  `AsyncRunResponse` whose `events` async iterator yields `RunEvent`
  objects with `type`, `content`, `sender`. Sync analog is `run_stream()`.
