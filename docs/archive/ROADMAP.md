# Roadmap

## P0

- Prove Theia build with `pnpm install && pnpm build`.
- Keep silent mock fallbacks out of normal product paths.
- Maintain CLI/TypeScript integration tests for command arguments.
- Exclude env/cache/dependency dirs from Python workspace scanning.

## P1

- Finish SwarmGraph live streaming, trace persistence, audit, and replay integration.
- Finish LangGraph streaming/event persistence beyond the explicit export/run path.
- Extend daemon integration tests beyond run listing and SSE replay.
- Expand replay viewer beyond JSONL event detail/export.
- Expand SSE coverage for reconnect/error paths.

## P2

- Expand CrewAI adapter graph extraction and runtime diagnostics.
- Add OpenAI Agents SDK project entrypoint/export support and streaming.
- Add AG2 adapter.
- Add signed Electron packaging.
- Define Open VSX/plugin bundling and license policy.
- Add auto-update pipeline.
