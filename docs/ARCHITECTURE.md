# ARC Studio — Architecture

## 1. System Boundaries

```
ARC Studio = Theia IDE shell + 9 native Theia extensions
ARC Core   = Python daemon/CLI + 2 adapters + context engine + storage + security
```

The Theia frontend **never imports Python code**. All communication crosses a JSON boundary.

## 2. Communication Model

```
┌─────────────────────────────────────────────────────┐
│                 Theia Frontend (Browser)             │
│  ReactWidget → ArcFrontendService → WebSocket proxy │
└──────────────────────────┬──────────────────────────┘
                           │ JSON-RPC (WebSocket)
┌──────────────────────────▼──────────────────────────┐
│              Theia Backend (Node.js)                 │
│  ArcServiceImpl → HTTP GET localhost:7777            │
│              OR  spawn "uv run arc <cmd> --json"     │
└──────────────────────────┬──────────────────────────┘
                           │ ARC Protocol Envelope JSON
┌──────────────────────────▼──────────────────────────┐
│              Python ARC Daemon / CLI                 │
│  cli.py → adapters → context → storage → web        │
└─────────────────────────────────────────────────────┘
```

## 3. ARC Protocol Envelope

Every response from the Python backend uses this envelope:

```json
{
  "version": "1.0",
  "ok": true,
  "data": { ... },
  "error": null,
  "meta": {
    "duration_ms": 42,
    "adapter": "swarmgraph",
    "workspace": "/path/to/project",
    "timestamp": "2025-01-01T00:00:00Z"
  }
}
```

TypeScript validates every response before rendering. Invalid responses show an error state.

## 4. Runtime Adapter Protocol

Every adapter must implement `adapters/base.py::RuntimeAdapter`:

```python
class RuntimeAdapter(abc.ABC):
    def detect(workspace: Path) -> (bool, confidence_0_to_1, [evidence])
    def capabilities() -> RuntimeCapabilities
    def export_workflow(workspace: Path) -> [WorkflowInfo]
    def export_schemas(workspace: Path) -> [SchemaInfo]
    async def run_workflow(workflow_id, inputs) -> RunRecord
    async def stream_events(run_id) -> AsyncIterator[RunEvent]
```

Rules:
- `capabilities()` must never lie
- `detect()` must check real files; no false positives
- Unsupported methods raise `NotImplementedError`

## 5. Theia Extension Layering

```
arc-product     ← branding, welcome page, about
arc-core        ← IPC, commands, widget contributions, service proxy
arc-workflows   ← workflow graph widget
arc-schemas     ← schema inspector widget
arc-runs        ← run timeline, trace viewer
arc-audit       ← audit chain viewer
arc-context     ← context pack viewer
arc-adapters    ← adapter status widget
arc-settings    ← preferences schema
```

## 6. AG-UI Event Mapping

ARC run events are mapped to AG-UI-compatible types:

| ARC Type | AG-UI Type |
|----------|------------|
| RUN_STARTED | RunStarted |
| RUN_COMPLETED | RunFinished |
| NODE_STARTED | StepStarted |
| NODE_COMPLETED | StepFinished |
| MESSAGE | TextMessageStart |
| TOOL_CALL | ToolCallStart |

SSE endpoint: `GET /api/runs/:id/events`

## 7. Context Retrieval Pipeline

```
Task string
    ↓
LocalRepoProvider  (no API key required)
Context7Provider   (requires ARC_CONTEXT7_API_KEY)
VercelGrepProvider (best-effort scraping)
GitHubCodeSearch   (requires GITHUB_TOKEN)
WebSearchProvider  (requires ARC_SEARCH_API_KEY)
    ↓
Deduplication + Ranking
    ↓
ContextPackEntry[] → saved to docs/context-packs/
```

## 8. Security Boundary

- Daemon only listens on `localhost` (never `0.0.0.0`)
- All paths validated against traversal (`..` blocked)
- All responses redacted for secrets before leaving Python
- Trust boundary: TypeScript validates every Python response
- No user-supplied input reaches the filesystem unvalidated

## 9. Mock Policy

See [DECISIONS/ADR-0004-mock-policy.md](DECISIONS/ADR-0004-mock-policy.md).

Every mock is:
- Behind the real interface
- Clearly marked with `MOCK_REASON`, `LOCAL_FIX_STEPS`
- Covered by tests
- Replaced by real implementation when external services available
