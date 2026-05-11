# Roadmap

## P0

- Prove Theia build with `pnpm install && pnpm build`.
- Keep silent mock fallbacks out of normal product paths.
- Maintain CLI/TypeScript integration tests for command arguments.
- Exclude env/cache/dependency dirs from Python workspace scanning.

## P1

- Implement real SwarmGraph adapter execution, trace, audit, and replay support.
- Implement real LangGraph graph loading/export.
- Add daemon integration tests that start the HTTP server and call real endpoints.
- Implement replay viewer over JSONL trace storage.
- Wire SSE event stream to Theia run timeline.

## P2

- Add CrewAI adapter.
- Add OpenAI Agents SDK adapter.
- Add AG2 adapter.
- Add signed Electron packaging.
- Define Open VSX/plugin bundling and license policy.
- Add auto-update pipeline.
