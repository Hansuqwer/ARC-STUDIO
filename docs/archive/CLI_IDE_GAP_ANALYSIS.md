# ARC Studio CLI & IDE Gap Analysis

Generated: 2026-05-14

Sources: `docs/REALITY_AUDIT.md`, `docs/IMPLEMENTATION_PLAN.md`, `README.md`, current code, external tool research (`docs/research/EXTERNAL_TOOLS_UI_RESEARCH.md`).

Canonical Theia extension: `packages/arc-extension`. Approved SwarmGraph adoption priority: LangGraph > CrewAI > AG2 > OpenAI Agents > LlamaIndex > Semantic Kernel > Haystack > DSPy/PydanticAI.

---

## 1. Executive Summary

ARC Studio currently has a real Python CLI with ~25 commands, an aiohttp daemon with 18 REST endpoints, and a canonical Theia extension with basic workflow execution, trace viewing, and workflow detection. The duplicate `theia-extensions/*` packages contain richer UI (event stream, run timeline, chat launcher, graph visualization, schema inspector, health monitor, context pack, arena) that should be ported into the canonical extension.

Compared to the market, ARC's CLI is more feature-rich than most agent runtime CLIs (only CrewAI and MLflow have more commands), but it is missing critical lifecycle commands: live streaming, background execution, cancel, resume, replay, diff, HITL, audit verification, and comprehensive diagnostics. The daemon API already exposes some of these (SSE replay, diff, OTLP export, arena) but the CLI does not.

The IDE is far behind LangGraph Studio, LangSmith, Langfuse, and Phoenix. The current canonical extension provides basic status cards and trace listing. The duplicate extensions have richer UI but are not wired into the canonical product. No audit viewer, HITL inbox, consensus dashboard, queen/worker topology, or live streaming exists in any IDE view.

The biggest gaps are:
1. **CLI**: no live stream, no cancel, no replay, no HITL, no audit verify, no `arc version`, no `arc doctor all`, no workspace init.
2. **IDE**: no runtime/adoption mode selection, no adapter setup wizard, no live event stream, no audit chain viewer, no HITL approval inbox, no consensus/voting dashboard, no queen/worker topology.
3. **Both**: no concept of SwarmGraph adoption mode anywhere in the user-facing surface.

---

## 2. Current ARC CLI Inventory

### Implemented Commands

| Command | What It Does | Status | Evidence |
|---------|-------------|--------|----------|
| `arc inspect` | Scans workspace, detects runtimes via all adapters, returns `WorkspaceInfo` | Implemented | `cli.py:121-160` |
| `arc runtimes` | Lists detected runtimes; `--capabilities` returns full `CapabilityReport` per adapter | Implemented | `cli.py:165-208` |
| `arc workflows` | Calls `adapter.export_workflow()` for detected adapters | Thin wrapper | `cli.py:213-237` |
| `arc schemas` | Calls `adapter.export_schemas()` for detected adapters | Thin wrapper | `cli.py:242-266` |
| `arc serve` | Starts aiohttp HTTP daemon on host:port | Implemented | `cli.py:271-283` |
| `arc run` | Resolves runtime, enforces gating, runs workflow, saves trace | Partial (blocking, no stream) | `cli.py:288-333` |
| `arc runs` | Lists stored run records from JSONL store | Implemented | `cli.py:460-476` |
| `arc runs get` | Loads single `RunRecord` by ID | Implemented | `cli.py:505-521` |
| `arc runs trace` | Returns trace file metadata + tail lines | Partial (raw lines, no structured parse) | `cli.py:524-548` |
| `arc runs prune` | Deletes oldest trace files beyond `--keep` | Implemented | `cli.py:479-502` |
| `arc context pack` | Generates context pack entries | Implemented | `cli.py:553-567` |
| `arc adapter test` | Runs 8-test conformance suite against adapter | Implemented | `cli.py:572-616` |
| `arc adapter list` | Lists registered adapters with capabilities | Implemented | `cli.py:619-632` |
| `arc providers list` | Lists built-in provider definitions | Implemented | `cli.py:348-353` |
| `arc providers status` | Returns dry-run provider status from env vars | Implemented (dry-run only) | `cli.py:366-372` |
| `arc providers accounts list/add/disable/delete` | Manages env-var-backed provider accounts | Implemented | `cli.py:379-430` |
| `arc providers routing get/set` | Manages provider routing policy | Implemented | `cli.py:437-457` |
| `arc eval run` | Evaluates run against golden trace | Partial (simple 3-check scoring) | `cli.py:637-683` |
| `arc eval list` | Lists saved golden traces | Implemented | `cli.py:686-705` |
| `arc doctor swarmgraph` | Checks SwarmGraph CLI availability | Implemented (single runtime only) | `cli.py:356-363` |

### Daemon API Endpoints With No CLI Equivalent

| API Route | CLI Equivalent | Gap |
|-----------|---------------|-----|
| `GET /health` | None | No `arc health` or `arc status` |
| `GET /api/runs/{run_id}/events` (SSE) | None | No `arc runs stream` or `arc runs tail --follow` |
| `POST /api/telemetry/export/{run_id}` | None | No `arc runs export --otlp` |
| `GET /api/runs/diff` | None | `evals/diff.py:34-79` exists but no CLI command |
| `POST /api/providers/proxy/chat` | None | No `arc providers proxy` |
| `POST /api/providers/diagnostics/redacted` | None | No `arc providers diagnostics` |
| `GET/POST /api/arena/*` | None | No `arc arena` commands |

### Missing CLI Commands (Full Product Gaps)

| Category | Missing Command | Notes |
|----------|----------------|-------|
| **Run lifecycle** | `arc run --stream` | No live event streaming; daemon SSE is replay-only |
| | `arc run --background` | No async/background execution |
| | `arc runs cancel <id>` | `RunStatus.CANCELLED` exists but no code path |
| | `arc runs status <id>` | No lightweight status-only command |
| | `arc runs tail --follow <id>` | No live follow mode |
| | `arc runs delete <id>` | No single-run delete |
| | `arc runs resume <id>` | `can_resume` flag exists, all `False` |
| | `arc runs fork <id>` | `can_fork` flag exists, all `False` |
| **Trace management** | `arc runs export <id> --format` | No export command |
| | `arc runs import <file>` | No import command |
| | `arc runs replay <id>` | `can_replay` flag exists, all `False` |
| | `arc runs diff <a> <b>` | `diff_runs()` exists in `evals/diff.py` but no CLI |
| | `arc runs search --query` | No search/index over traces |
| **Eval** | `arc eval save <id> --golden-id` | `save_golden()` exists but no CLI command |
| | `arc eval delete <id>` | No delete for goldens |
| | `arc eval run --batch` | No batch eval |
| **HITL** | `arc hitl approve/reject/pending/respond` | No HITL infrastructure exists anywhere |
| **Audit** | `arc audit log` | `AuditChainWriter` exists but no CLI to read/display |
| | `arc audit verify <id>` | `verify()` at `audit/chain.py:52-68` not exposed |
| | `arc audit export` | No audit export |
| **Provider/quota** | `arc providers quota` | `ProviderQuotaStore` exists but no CLI |
| | `arc providers quota reset` | |
| | `arc providers proxy --prompt` | `dry_run_proxy()` exists, daemon route exists, no CLI |
| | `arc providers diagnostics` | `redacted_diagnostics()` exists, daemon route exists, no CLI |
| | `arc providers accounts enable` | Only `disable` exists |
| | `arc providers accounts update` | No update/edit |
| **Profiles/workspace** | `arc profiles list/show/create` | Profiles hardcoded in `profiles.py:22-42`, no CLI |
| | `arc workspace init` | No workspace scaffolding |
| | `arc workspace config` | No `.arc/config.json` management |
| | `arc workspace info` | `arc inspect` is close but not dedicated |
| **Adapter management** | `arc adapter info <id>` | No detailed single-adapter info |
| | `arc adapter register/unregister` | Adapters hardcoded, no plugin system |
| | `arc adapter detect <id>` | Detection runs implicitly, no single-adapter command |
| **Secrets/env** | `arc env check` | No env var validation for detected runtimes |
| | `arc env redact <file>` | `Redactor` exists but no CLI |
| **Diagnostics** | `arc version` | No version command; version hardcoded in `web/routes.py:97` |
| | `arc doctor all` | Only `doctor swarmgraph` exists |
| | `arc doctor env` | No environment diagnostic |
| | `arc doctor network` | No provider endpoint connectivity check |
| | `arc doctor storage` | No trace dir/DB/disk diagnostic |
| | `arc bug-report` | No diagnostic bundle generation |
| **SwarmGraph adoption** | `arc run --mode adoption` | No adoption mode flag exists |
| | `arc adoption list` | No adoption registry |
| | `arc adoption status` | No adoption capability report |

### Infrastructure Gaps

| Component | Status | Notes |
|-----------|--------|-------|
| SQLite store | Stub | `storage/sqlite.py` defines schema but is never wired |
| Audit chain | Partial | `AuditChainWriter` + `verify()` exist; no CLI/daemon endpoint |
| Run cancellation | Missing | `RunStatus.CANCELLED` exists but no code path |
| Live event streaming | Stub | `stream_events()` defined but all adapters raise `NotImplementedError` |
| Run resume/fork/checkpoint | Missing | Capability flags exist, all `False` |
| Custom profiles | Missing | Hardcoded dict, no persistence |
| Workspace config | Missing | No `.arc/config.json` |
| Plugin system | Missing | Adapters hardcoded in `registry.py:build_default()` |
| Provider live health | Stub | Returns 501 "not implemented yet" |

---

## 3. Current ARC IDE Inventory

### Canonical Extension: `packages/arc-extension`

| Component | What It Displays | Backend Calls | Status | Evidence |
|-----------|-----------------|---------------|--------|----------|
| **ArcWidget** (main) | 3 collapsible sections: Workflow Execution, Trace Viewer, Workflow Detection | `executeWorkflow()`, `getTraces()`, `detectWorkflows()` | Implemented | `arc-widget.tsx:554` |
| **WorkflowExecutionSection** | Prompt input, execute button, progress bar, execution steps, result | Parent calls `executeWorkflow()` | Implemented | `components/WorkflowExecutionSection.tsx:142` |
| **TraceViewerSection** | Trace list with status/timestamp, filter input, load button | Parent calls `getTraces()` | Implemented (list only) | `components/TraceViewerSection.tsx:154` |
| **WorkflowDetectionSection** | Detected workflow list (type, name, path) | Parent calls `detectWorkflows()` | Implemented | `components/WorkflowDetectionSection.tsx:100` |
| **ErrorBanner** | Error message with retry button | None (props) | Implemented | `components/ErrorBanner.tsx:49` |
| **ExecutionSteps** | Step-by-step progress indicators | None (props) | Implemented | `components/ExecutionSteps.tsx:44` |
| **ProgressBar** | Percentage progress bar | None (props) | Implemented | `components/ProgressBar.tsx:23` |
| **ToastContainer** | Auto-dismissing toast notifications | None (props) | Implemented | `components/ToastContainer.tsx:49` |
| **ShortcutsModal** | Keyboard shortcuts help table | None (static) | Implemented | `components/ShortcutsModal.tsx:83` |
| **ArcBackendService** | Orchestration layer delegating to 4 specialized services | JSON-RPC at `/services/arc` | Implemented | `node/arc-backend-service.ts:276` |
| **WorkflowExecutor** | Spawns SwarmGraph CLI, manages processes | `executeWorkflow()`, `cancelWorkflow()` | Implemented | `node/services/workflow-executor.ts:475` |
| **TraceParser** | Parses JSONL traces, streams events | `parseTrace()`, `streamTrace()` | Implemented | `node/services/trace-parser.ts:325` |
| **WorkflowDetector** | Scans workspace for SwarmGraph CLI + LangGraph files | `detectWorkflows()` | Implemented | `node/services/workflow-detector.ts:293` |
| **FileManager** | Trace file listing, deletion, metadata | `getTraceFiles()`, `deleteTrace()` | Implemented | `node/services/file-manager.ts:134` |

### Duplicate Extensions: `theia-extensions/*` (Port Candidates)

| Extension | Key Components | Status | Port? | Evidence |
|-----------|---------------|--------|-------|----------|
| **arc-core** | Main widget, frontend service, commands, status bar, welcome widget, SSE client, cost warning, backend service impl | Implemented | YES (highest priority) | `arc-main-widget.tsx:518`, `arc-service-impl.ts:732` |
| **arc-adapters** | Runtime readiness widget with doctor actions, provider settings panel | Implemented | YES | `arc-adapters-widget.tsx:240` |
| **arc-event-stream** | Run list sidebar, virtualized event list, 33 AG-UI event type icons, SSE live streaming, event detail drawer, type filter | Partial (needs daemon SSE) | YES | `arc-event-stream-widget.tsx:973` |
| **arc-runs** | Run timeline, chat launcher, run diff widget | Partial | YES | `arc-run-timeline-widget.tsx:712`, `arc-chat-widget.tsx:327`, `arc-run-diff-widget.tsx:142` |
| **arc-workflows** | SVG-based graph rendering with BFS layout, color-coded nodes, arrow-marked edges | Partial | YES | `arc-workflow-graph-widget.tsx:238` |
| **arc-schemas** | Schema list sidebar, detail view with properties table, raw JSON display | Partial | YES | `arc-schema-inspector-widget.tsx:162` |
| **arc-health** | Daemon health polling, status display, restart command (stub) | Partial | YES | `arc-health-widget.tsx:150` |
| **arc-context** | Context pack generation UI with source icons, relevance scores | Partial | YES | `arc-context-pack-widget.tsx:114` |
| **arc-settings** | 15 preferences: daemon port/host, python paths, context7 key, GitHub token, swarmgraph provider, run profile, OTLP endpoint | Implemented | YES (merge prefs) | `arc-preference-schema.ts:81` |
| **arc-product** | Branded welcome page replacing Theia default | Implemented | MERGE into arc-core welcome | `arc-getting-started-widget.tsx:231` |
| **arc-arena** | Full arena UI: mode selector, model picker, chat history, candidate cards, battle view, vote buttons, adopt/reject | Partial (stub backend) | YES (separate domain) | `arc-arena-widget.tsx:520` |
| **arc-audit** | Empty stub with hardcoded empty array | STUB | NO (defer) | `arc-audit-widget.tsx:59` |

### Missing IDE Features

| Feature | Status | Notes |
|---------|--------|-------|
| Runtime/adoption mode selection | Partial | Runtime picker in arc-runs; no dedicated mode UI |
| Adapter setup wizard | Missing | arc-adapters shows readiness + doctor actions; no guided wizard |
| Workspace trust UI | Missing | `ARC_TRUST_WORKSPACE_LAUNCHER` env checked in code; no UI |
| Provider/account/cost setup UI | Partial | arc-adapters shows provider status; no account management or cost dashboard |
| Workflow graph visualization | Partial | arc-workflows has basic SVG; needs upgrade |
| Schema viewer | Partial | arc-schemas functional; depends on daemon schema export |
| Run launcher | Partial | arc-chat + arc-timeline both launch runs; no unified launcher |
| Live event stream | Partial | arc-event-stream has SSE client + UI; daemon endpoint needed |
| Trace timeline | Partial | arc-run-timeline has vertical timeline + replay; functional with stored traces |
| Replay stepper | Partial | arc-run-timeline:510 — 120ms per event replay; functional |
| Audit chain viewer | STUB | arc-audit is empty; no backend support |
| HITL approval inbox | Missing | No widget or backend support |
| Consensus/voting dashboard | Partial | arc-arena has vote buttons for battle; no aggregate dashboard |
| Queen/worker topology view | Missing | No widget |
| Tenant/profile selector | Partial | Profile dropdown in arc-chat + status bar; no multi-tenant UI |
| Eval/golden trace UI | Partial | arc-run-timeline has inline eval button; no golden trace management UI |
| Diff viewer | Partial | arc-run-diff has basic JSON diff; no visual diff |
| Logs/diagnostics | Partial | arc-health monitors daemon; no general log viewer |
| Extension/plugin marketplace | Missing | No marketplace infrastructure |
| Onboarding/demo projects | Partial | arc-welcome + arc-product welcome pages; no demo project creation |

---

## 4. Comparative CLI Matrix

| Capability | ARC (current) | LangGraph | CrewAI | AG2 | OpenAI Agents | LlamaIndex | SemKernel | Haystack | DSPy | PydanticAI | LangSmith | Langfuse | Phoenix | MLflow | Temporal | Prefect | Dagster |
|-----------|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **Has CLI** | ✅ | ✅ | ✅ | ⚠️ | ❌ | ⚠️ | ❌ | ❌ | ❌ | ⚠️ | ⚠️ | ❌ | ⚠️ | ✅✅ | ✅ | ✅ | ✅ |
| **Detect** | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **Inspect** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Run** | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ | ✅ | ✅ |
| **Stream** | ❌ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **Replay** | ❌ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ | ❌ | ✅ | ❌ | ✅ | ❌ | ❌ |
| **Audit** | ⚠️ | ✅ | ✅ | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Eval** | ⚠️ | ❌ | ⚠️ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |
| **Provider config** | ✅ | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ | ❌ | ✅ | ❌ | ❌ | ❌ |
| **Tenant/cost** | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| **HITL** | ❌ | ✅ | ✅ | ❌ | ✅ | ✅ | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ | ❌ |
| **Graph viz** | ❌ | ✅ | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| **Deploy** | ❌ | ✅ | ✅ | ❌ | ❌ | ⚠️ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ | ❌ | ✅ | ✅ |
| **Plugin mgmt** | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ |
| **CLI commands** | ~25 | ~6 | ~20+ | ~1 | 0 | ~5 | 0 | 0 | 0 | ~0 | ~3 | 0 | ~1 | 100+ | ~20 | ~10 | ~8 |

Key: ✅ = implemented, ⚠️ = partial/stub, ❌ = missing

### ARC's CLI Position

ARC has more CLI commands than most agent runtime tools. Only CrewAI (~20+) and MLflow (100+) have more. ARC's unique strengths:
- **Runtime detection** — no other tool auto-detects multiple runtimes
- **Provider management** — only ARC and CrewAI have CLI-based provider config
- **Multi-adapter conformance testing** — `arc adapter test` is unique
- **Context pack generation** — unique to ARC

ARC's biggest CLI gaps vs market leaders:
- **No streaming** — LangGraph, CrewAI, DSPy, PydanticAI all stream
- **No replay** — LangGraph, CrewAI, LangSmith, Phoenix, Temporal all replay
- **No HITL** — LangGraph, CrewAI, OpenAI Agents, PydanticAI, Temporal, Prefect all support HITL
- **No deploy** — LangGraph, CrewAI, MLflow, Prefect, Dagster all deploy
- **No graph viz** — LangGraph Studio, AG2 Studio, PydanticAI (Mermaid), Dagster all visualize

---

## 5. Comparative IDE Matrix

| Feature | ARC (current) | LangGraph Studio | LangSmith | Langfuse | Phoenix | MLflow | Temporal | Prefect | Dagster |
|---------|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **Graph visualization** | ⚠️ | ✅ | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ | ✅ |
| **Trace tree** | ⚠️ | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ |
| **Timeline/Gantt** | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ | ✅ | ✅ | ✅ |
| **Time travel/replay** | ⚠️ | ✅ | ❌ | ❌ | ✅ | ❌ | ✅ | ❌ | ❌ |
| **Real-time streaming** | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ | ❌ |
| **HITL intervention** | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ | ❌ |
| **Prompt management** | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |
| **Evaluation** | ⚠️ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |
| **Datasets** | ❌ | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| **Sessions/threads** | ❌ | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **Saved views/filters** | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ |
| **Workflow actions** | ⚠️ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ |
| **Cost tracking** | ❌ | ❌ | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| **Audit viewer** | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **Consensus/voting** | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **Queen/worker topology** | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **Multi-runtime support** | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **Self-hostable** | ✅ | ✅ | ⚠️ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |

Key: ✅ = implemented, ⚠️ = partial/stub, ❌ = missing

### ARC's IDE Position

ARC's IDE is significantly behind all comparators. The canonical extension provides basic status cards. The duplicate extensions have richer features but are not the canonical product.

ARC's unique advantages:
- **Multi-runtime** — only ARC supports multiple agent runtimes from one IDE
- **Self-hostable** — runs entirely locally, no cloud dependency
- **Theia-based** — full IDE platform with code editing, file management, terminal

ARC's biggest IDE gaps:
- **No live streaming** — LangGraph Studio and Prefect stream in real-time
- **No time travel** — LangGraph Studio and Temporal support checkpoint replay
- **No HITL** — Temporal and Prefect support human intervention
- **No cost tracking** — LangSmith, Langfuse, Phoenix all track costs per trace
- **No audit viewer** — unique to ARC's product vision, not implemented anywhere
- **No consensus/voting dashboard** — unique to SwarmGraph, not implemented
- **No queen/worker topology** — unique to SwarmGraph, not implemented

---

## 6. Recommended ARC CLI Command Tree

### Generic Commands (All Runtimes)

| Command | Description | Priority |
|---------|-------------|----------|
| `arc version` | Show ARC Studio version | P0 |
| `arc inspect [--workspace] [--runtime] [--json]` | Detect runtimes in workspace | P0 (exists) |
| `arc runtimes [--capabilities] [--json]` | List runtimes and capabilities | P0 (exists) |
| `arc workflows [--runtime] [--format text\|json\|mermaid] [--output]` | List/export workflows | P0 (exists, needs format) |
| `arc schemas [--runtime] [--validate] [--json]` | List/validate schemas | P0 (exists, needs validate) |
| `arc serve [--host] [--port] [--workspace] [--cors-origin]` | Start daemon | P0 (exists, needs cors) |
| `arc health` | Check daemon connectivity | P0 |
| `arc status` | Show daemon + workspace summary | P0 |

### Run Lifecycle (Generic)

| Command | Description | Priority |
|---------|-------------|----------|
| `arc run <workflow_id> [--runtime] [--mode standalone\|adoption] [--prompt] [--allow-paid-calls] [--profile-id] [--stream] [--background] [--timeout] [--input-file] [--env KEY=VAL]` | Execute workflow | P0 (exists, needs flags) |
| `arc runs [--limit] [--status] [--runtime] [--since] [--until] [--format]` | List runs | P0 (exists, needs filters) |
| `arc runs get <run_id> [--events-only] [--format]` | Get run record | P0 (exists, needs format) |
| `arc runs status <run_id>` | Lightweight status check | P1 |
| `arc runs cancel <run_id>` | Cancel running workflow | P1 |
| `arc runs delete <run_id>` | Delete single run | P1 |
| `arc runs stream <run_id> [--follow] [--tail N] [--filter type]` | Stream/tail run events | P1 |
| `arc runs tail <run_id> [--follow]` | Alias for `runs stream --follow` | P1 |
| `arc runs resume <run_id> [--input]` | Resume paused run | P2 |
| `arc runs fork <run_id> [--prompt] [--inputs]` | Fork run with modified inputs | P2 |

### Trace Management (Generic)

| Command | Description | Priority |
|---------|-------------|----------|
| `arc runs trace <run_id> [--head\|--tail\|--follow] [--events] [--filter]` | Inspect trace events | P0 (exists, needs flags) |
| `arc runs export <run_id> [--format jsonl\|json\|otlp] [--output]` | Export trace | P1 |
| `arc runs import <file> [--format jsonl\|json]` | Import trace | P2 |
| `arc runs replay <run_id> [--speed 1x\|2x\|0.5x]` | Replay trace events | P2 |
| `arc runs diff <run_a> <run_b> [--format json\|table]` | Compare two runs | P1 (diff logic exists) |
| `arc runs search --query [--runtime] [--status] [--since] [--until]` | Search traces | P3 |
| `arc runs prune [--keep] [--older-than] [--yes]` | Prune old traces | P0 (exists) |

### Eval / Golden Traces (Generic)

| Command | Description | Priority |
|---------|-------------|----------|
| `arc eval run <run_id> [--golden] [--expected-output] [--expected-status] [--expected-events]` | Evaluate run | P0 (exists) |
| `arc eval save <run_id> --golden-id [--output]` | Save run as golden trace | P1 |
| `arc eval list [--workspace]` | List golden traces | P0 (exists) |
| `arc eval delete <golden_id>` | Delete golden trace | P1 |
| `arc eval run --batch --golden-dir [--report]` | Batch eval | P2 |
| `arc eval report [--workspace]` | Aggregate eval report | P3 |

### HITL (SwarmGraph-specific)

| Command | Description | Priority |
|---------|-------------|----------|
| `arc hitl pending [--runtime]` | List pending HITL requests | P2 |
| `arc hitl approve <run_id> --token <token> [--reason]` | Approve HITL request | P2 |
| `arc hitl reject <run_id> --token <token> --reason` | Reject HITL request | P2 |
| `arc hitl respond <run_id> --token <token> --input <json>` | Respond to HITL with input | P2 |
| `arc hitl wait <run_id> [--timeout]` | Block until HITL request appears | P2 |

### Audit (SwarmGraph-specific)

| Command | Description | Priority |
|---------|-------------|----------|
| `arc audit log <run_id> [--tail N] [--format json\|table]` | Show audit chain for run | P2 |
| `arc audit verify <run_id>` | Verify audit chain integrity | P2 |
| `arc audit export <run_id> [--format jsonl] [--output]` | Export audit chain | P3 |
| `arc audit sign --key <key> [--rotate]` | Sign/rotate audit key | P3 |

### Provider / Account / Quota (Generic)

| Command | Description | Priority |
|---------|-------------|----------|
| `arc providers list` | List provider definitions | P0 (exists) |
| `arc providers status` | Show provider status from env | P0 (exists) |
| `arc providers accounts list/add/disable/enable/delete/update` | Manage provider accounts | P0 (exists, needs enable/update) |
| `arc providers routing get/set` | Manage routing policy | P0 (exists) |
| `arc providers proxy --provider --model --prompt [--dry-run]` | Test provider call | P1 |
| `arc providers diagnostics` | Redacted provider diagnostics | P1 |
| `arc providers quota [--provider]` | Show provider quota usage | P2 |
| `arc providers quota reset [--provider]` | Reset provider quota | P2 |

### Profiles / Workspace (Generic)

| Command | Description | Priority |
|---------|-------------|----------|
| `arc profiles list` | List security profiles | P1 |
| `arc profiles show <id>` | Show profile details | P1 |
| `arc profiles create <id> [--allow-paid-calls] [--allow-network]` | Create custom profile | P2 |
| `arc workspace init [--name]` | Initialize ARC workspace | P1 |
| `arc workspace info` | Show workspace config | P1 |
| `arc workspace config [key] [value]` | Get/set workspace config | P2 |

### Adapter Management (Generic)

| Command | Description | Priority |
|---------|-------------|----------|
| `arc adapter list` | List registered adapters | P0 (exists) |
| `arc adapter info <id>` | Show adapter details | P1 |
| `arc adapter test <id>` | Run conformance tests | P0 (exists) |
| `arc adapter detect <id> [--workspace]` | Run single-adapter detection | P1 |
| `arc adapter register <id> --module <path>` | Register plugin adapter | P3 |
| `arc adapter unregister <id>` | Unregister plugin adapter | P3 |

### Secrets / Env (Generic)

| Command | Description | Priority |
|---------|-------------|----------|
| `arc env check [--workspace]` | Validate required env vars | P1 |
| `arc env redact <file>` | Redact secrets from file | P2 |

### Diagnostics (Generic)

| Command | Description | Priority |
|---------|-------------|----------|
| `arc doctor [all\|swarmgraph\|langgraph\|crewai\|...]` | Run diagnostics | P0 (exists for swarmgraph, needs all) |
| `arc doctor env` | Environment diagnostic | P1 |
| `arc doctor network` | Provider connectivity check | P1 |
| `arc doctor storage` | Trace dir/DB/disk diagnostic | P1 |
| `arc bug-report [--output]` | Generate diagnostic bundle | P2 |

### LM Arena (Separate Domain)

| Command | Description | Priority |
|---------|-------------|----------|
| `arc arena models [--tags]` | List arena models | P2 |
| `arc arena tags` | List model tags | P2 |
| `arc arena chat --prompt [--mode] [--model] [--profile]` | Arena chat | P2 |
| `arc arena vote <run_id> --winner <candidate_id>` | Record vote | P2 |
| `arc arena adopt <run_id> --candidate <id>` | Adopt candidate code | P2 |

---

## 7. Recommended ARC IDE View Map

### Primary Views (Activity Bar / Sidebar)

| View | Location | Data Source | Backend Endpoints Needed | Priority |
|------|----------|-------------|-------------------------|----------|
| **ARC Dashboard** | Main area | Daemon health, runtime capabilities, recent runs | `/health`, `/api/runtimes/capabilities`, `/api/runs` | P0 |
| **Runtime Readiness** | Sidebar panel | Adapter capability reports, provider status, doctor actions | `/api/runtimes/capabilities`, `/api/providers/status` | P0 (port from arc-adapters) |
| **Workflows** | Sidebar panel | Detected workflows with graph preview | `/api/workflows`, `/api/schemas` | P0 (port from arc-workflows) |
| **Runs** | Sidebar panel | Run list with filters, status, timing | `/api/runs`, `/api/runs/{id}` | P0 (port from arc-runs timeline) |
| **Event Stream** | Main area or bottom panel | Live SSE events for active run | `/api/runs/{id}/events` (live SSE) | P1 (port from arc-event-stream) |
| **Trace Timeline** | Main area | Stored trace events with timeline | `/api/runs/{id}`, `/api/runs/{id}/events` | P0 (port from arc-runs timeline) |

### Secondary Views (Dockable Panels)

| View | Location | Data Source | Backend Endpoints Needed | Priority |
|------|----------|-------------|-------------------------|----------|
| **Run Launcher** | Modal or sidebar | Workflow list, runtime picker, profile selector, cost gate | `/api/runs/start` | P0 (port from arc-chat) |
| **Schema Inspector** | Sidebar panel | Schema list + detail | `/api/schemas` | P1 (port from arc-schemas) |
| **Graph Visualizer** | Main area | Workflow nodes/edges | `/api/workflows` | P1 (port from arc-workflows, upgrade to reactflow) |
| **Audit Chain Viewer** | Main area | Audit chain records with HMAC verification | New: `/api/runs/{id}/audit` | P2 |
| **HITL Inbox** | Sidebar panel or notification | Pending HITL requests | New: `/api/hitl/pending`, `/api/hitl/respond` | P2 |
| **Consensus Dashboard** | Main area | Vote results, agreement fractions, consensus rounds | New: `/api/runs/{id}/consensus` | P3 |
| **Queen/Worker Topology** | Main area | SwarmGraph agent topology visualization | New: `/api/runs/{id}/topology` | P3 |
| **Eval Manager** | Sidebar panel | Golden traces, eval results, scores | `/api/evals/run`, `/api/evals/list` | P2 |
| **Run Diff Viewer** | Main area | Side-by-side run comparison | `/api/runs/diff` | P1 (port from arc-runs diff) |
| **Provider Manager** | Sidebar panel | Provider accounts, routing, quota | `/api/providers/*` | P1 (port from arc-adapters provider panel) |
| **Context Pack** | Sidebar panel | Context entries with sources | `/api/context/pack` | P2 (port from arc-context) |
| **Health Monitor** | Status bar or small panel | Daemon status, active runs, poll interval | `/health` | P1 (port from arc-health) |
| **Arena** | Separate main area view | Arena models, chat, candidates, votes | `/api/arena/*` | P3 (port from arc-arena) |

### Status Bar Contributions

| Item | Data | Priority |
|------|------|----------|
| Daemon status indicator | Connected/disconnected | P0 |
| Active run count | Number of running workflows | P0 |
| Current profile | Active security profile | P1 |
| Cost gate status | Paid calls allowed/blocked | P1 |

### Command Palette Contributions

| Command | Keybinding | Priority |
|---------|-----------|----------|
| ARC: Open Dashboard | Cmd+Shift+A | P0 |
| ARC: Run Agent | Cmd+Shift+R | P0 |
| ARC: Compare Models | Cmd+Shift+M | P0 |
| ARC: Open Timeline | | P0 |
| ARC: Runtime Doctor | | P1 |
| ARC: Inspect Workspace | | P1 |
| ARC: Export Trace to OTLP | | P1 |
| ARC: Approve HITL | | P2 |
| ARC: Open Audit Viewer | | P2 |
| ARC: Open Consensus Dashboard | | P3 |

### Port Priority from `theia-extensions/*`

| Source Extension | What to Port | Priority |
|-----------------|-------------|----------|
| arc-core | Entire service layer, protocol, main widget, status bar, commands, welcome widget, SSE client, cost warning | P0 |
| arc-settings | Merge preference schemas | P0 |
| arc-adapters | Runtime readiness widget with doctor actions | P0 |
| arc-runs | Timeline + chat launcher + diff widgets | P0 |
| arc-event-stream | Live event stream widget with SSE client | P1 |
| arc-workflows | Graph visualization widget | P1 |
| arc-schemas | Schema inspector widget | P1 |
| arc-health | Health monitor widget | P1 |
| arc-context | Context pack widget | P2 |
| arc-arena | Full arena extension (separate domain) | P3 |
| arc-product | Merge welcome into arc-core's ArcWelcomeWidget | P0 |
| arc-audit | Delete stub; rebuild when backend exists | P2 |

---

## 8. Adapter-Specific Function Wish-List

### LangGraph

| Function | CLI | IDE | Notes |
|----------|-----|-----|-------|
| `arc langgraph export --target module:func` | ✅ | | Export compiled graph topology |
| `arc langgraph validate --target` | ✅ | | Validate export target resolves correctly |
| `arc langgraph serve --target` | ✅ | | Serve graph as local API |
| Graph visualization | | ✅ | Interactive DAG with node/edge detail |
| State inspector | | ✅ | View current state at any checkpoint |
| Time travel replay | | ✅ | Step through state at each node |
| Thread management | ✅ | ✅ | Manage conversation threads |
| Checkpoint browser | | ✅ | Browse saved checkpoints per thread |

### CrewAI

| Function | CLI | IDE | Notes |
|----------|-----|-----|-------|
| `arc crewai export --target module:attr` | ✅ | | Export crew topology |
| `arc crewai chat --target` | ✅ | | Interactive chat session with crew |
| `arc crewai train --target -n 10` | ✅ | | Training loop |
| `arc crewai test --target -n 5` | ✅ | | Evaluation test |
| `arc crewai replay --task-id` | ✅ | | Replay from specific task |
| `arc crewai reset-memories [--all]` | ✅ | | Memory management |
| Crew topology visualization | | ✅ | Show agents/tasks/relationships |
| Task output viewer | | ✅ | Browse task outputs per run |

### AG2

| Function | CLI | IDE | Notes |
|----------|-----|-----|-------|
| `arc ag2 export --target module:attr` | ✅ | | Export team/group chat topology |
| `arc ag2 chat --target` | ✅ | | Interactive group chat session |
| `arc ag2 serve --target` | ✅ | | Serve team as local API |
| Team visualization | | ✅ | Show agents/roles/relationships |
| Group chat transcript viewer | | ✅ | Browse conversation history |
| Agent role inspector | | ✅ | View agent capabilities/roles |

### OpenAI Agents SDK

| Function | CLI | IDE | Notes |
|----------|-----|-----|-------|
| `arc openai export --target module:attr` | ✅ | | Export agent topology |
| `arc openai serve --target` | ✅ | | Serve agent as local API |
| Agent topology visualization | | ✅ | Show agents/tools/handoffs |
| Trace viewer (OpenAI-compatible) | | ✅ | View traces in ARC format |
| Sandbox agent file browser | | ✅ | Browse agent filesystem |

### LlamaIndex

| Function | CLI | IDE | Notes |
|----------|-----|-----|-------|
| `arc llamaindex rag -f <files>` | ✅ | | Ingest files into local vector DB |
| `arc llamaindex rag -q "question"` | ✅ | | Q&A over ingested data |
| `arc llamaindex rag --chat` | ✅ | | Interactive chat REPL |
| `arc llamaindex workflow export` | ✅ | | Export workflow topology |
| RAG pipeline visualization | | ✅ | Show retrieval/generation pipeline |
| Index browser | | ✅ | Browse embedded documents |

### Semantic Kernel

| Function | CLI | IDE | Notes |
|----------|-----|-----|-------|
| `arc sk export --target` | ✅ | | Export plugin/kernel topology |
| `arc sk plugins list` | ✅ | | List registered plugins |
| Plugin browser | | ✅ | Browse available plugins |
| Kernel topology visualization | | ✅ | Show plugins/services/agents |

### Haystack

| Function | CLI | IDE | Notes |
|----------|-----|-----|-------|
| `arc haystack export --pipeline <file>` | ✅ | | Export pipeline topology |
| `arc haystack run --pipeline <file>` | ✅ | | Run pipeline |
| Pipeline visualization | | ✅ | Show pipeline DAG |
| Component inspector | | ✅ | View component configuration |

### DSPy / PydanticAI

| Function | CLI | IDE | Notes |
|----------|-----|-----|-------|
| `arc dspy eval --program <file> --dataset <file>` | ✅ | | Run DSPy evaluation |
| `arc dspy optimize --program <file>` | ✅ | | Run DSPy optimization |
| `arc pydanticai eval --agent <file> --dataset <file>` | ✅ | | Run PydanticAI evaluation |
| Module/signature browser | | ✅ | Browse DSPy modules |
| Graph viewer (PydanticAI) | | ✅ | View pydantic_graph Mermaid export |

---

## 9. SwarmGraph-Specific Function Wish-List

### Queen/Worker

| Function | CLI | IDE | Notes |
|----------|-----|-----|-------|
| `arc swarmgraph topology <run_id>` | ✅ | | Show queen/worker topology for run |
| Queen/worker topology view | | ✅ | Visualize queen fan-out, worker assignments |
| Worker result inspector | | ✅ | Browse individual worker results |
| Agent spec viewer | | ✅ | View agent roles/tasks/directives |
| Decomposition strategy selector | | ✅ | Choose hierarchical/mesh/ring/star/adaptive |

### Consensus

| Function | CLI | IDE | Notes |
|----------|-----|-----|-------|
| `arc swarmgraph consensus <run_id>` | ✅ | | Show consensus results for run |
| Consensus dashboard | | ✅ | Agreement fractions, protocol, vote counts |
| Vote detail viewer | | ✅ | Individual worker votes with reasoning |
| Protocol selector | | ✅ | Choose Raft/BFT/simple-majority |
| Consensus trend chart | | ✅ | Agreement over iterations |

### Voting

| Function | CLI | IDE | Notes |
|----------|-----|-----|-------|
| `arc swarmgraph votes <run_id>` | ✅ | | List all votes for run |
| Vote timeline | | ✅ | Visual timeline of voting rounds |
| Voter breakdown | | ✅ | Per-agent vote history |
| Dissenter analysis | | ✅ | Show dissenting votes with reasons |

### HITL

| Function | CLI | IDE | Notes |
|----------|-----|-----|-------|
| `arc hitl pending` | ✅ | | List pending HITL requests |
| `arc hitl approve/reject/respond` | ✅ | | Respond to HITL requests |
| HITL inbox | | ✅ | Pending approval queue with preview |
| HITL approval dialog | | ✅ | Single-use token, risk score, action preview |
| HITL history | | ✅ | Past approval decisions with audit trail |

### Replay

| Function | CLI | IDE | Notes |
|----------|-----|-----|-------|
| `arc runs replay <run_id>` | ✅ | | Replay trace events |
| `arc runs replay <run_id> --from-checkpoint <id>` | ✅ | | Replay from specific checkpoint |
| Replay stepper | | ✅ | Step through events with state inspection |
| Time travel debugger | | ✅ | Jump to any checkpoint, inspect state |
| State diff viewer | | ✅ | Compare state between checkpoints |

### Signed Audit

| Function | CLI | IDE | Notes |
|----------|-----|-----|-------|
| `arc audit log <run_id>` | ✅ | | Show audit chain |
| `arc audit verify <run_id>` | ✅ | | Verify chain integrity |
| `arc audit export <run_id>` | ✅ | | Export audit chain |
| Audit chain viewer | | ✅ | Visual chain with hash verification |
| Tamper detection indicator | | ✅ | Red/green indicator for chain integrity |
| Audit record detail | | ✅ | Show individual signed records |
| Key management | | ✅ | Audit key rotation, fingerprint display |

### Tenant Isolation

| Function | CLI | IDE | Notes |
|----------|-----|-----|-------|
| `arc tenants list` | ✅ | | List tenants |
| `arc tenants create <id>` | ✅ | | Create tenant |
| `arc tenants switch <id>` | ✅ | | Switch active tenant |
| Tenant selector | | ✅ | Dropdown in status bar or sidebar |
| Tenant usage dashboard | | ✅ | Per-tenant quota/cost/usage |
| Tenant isolation indicator | | ✅ | Show current tenant context |

### Provider Gateway / Quota

| Function | CLI | IDE | Notes |
|----------|-----|-----|-------|
| `arc providers quota [--provider] [--tenant]` | ✅ | | Show quota usage |
| `arc providers quota reset [--provider]` | ✅ | | Reset quota |
| `arc providers proxy --prompt` | ✅ | | Test provider call |
| Provider dashboard | | ✅ | All providers with status/quota/cost |
| Cost tracker | | ✅ | Per-run, per-trace, per-tenant cost breakdown |
| Budget alerts | | ✅ | Visual alerts when approaching budget limits |
| Provider routing UI | | ✅ | Configure routing policy from UI |

---

## 10. Gap-Ranked Roadmap

### P0: CLI/IDE Truth + Discoverability (1-2 weeks)

| Item | CLI | IDE | Outcome |
|------|-----|-----|---------|
| `arc version` | ✅ | | Basic version command |
| `arc health` / `arc status` | ✅ | Status bar | Daemon connectivity check |
| `arc doctor all` | ✅ | | Aggregate diagnostic for all runtimes |
| `arc env check` | ✅ | | Validate required env vars |
| `arc adapter info <id>` | ✅ | | Detailed single-adapter info |
| `arc providers accounts enable` | ✅ | | Enable provider accounts |
| `arc providers proxy` | ✅ | | Test provider calls from CLI |
| `arc providers diagnostics` | ✅ | | Redacted provider diagnostics |
| `arc runs diff` | ✅ | Diff viewer | Expose existing `diff_runs()` via CLI |
| Port arc-core service layer | | ✅ | Canonical extension gets full service layer |
| Port arc-adapters readiness | | ✅ | Runtime readiness widget in canonical extension |
| Port arc-runs timeline + chat | | ✅ | Run timeline and launcher in canonical extension |
| Merge arc-settings prefs | | ✅ | Unified preference schema |
| Merge arc-product welcome | | ✅ | Unified onboarding |

**Verification:** `arc version` returns version; `arc health` shows daemon status; `arc doctor all` checks all runtimes; canonical extension builds with ported components.

### P1: Run Lifecycle + Live Stream (2-3 weeks)

| Item | CLI | IDE | Outcome |
|------|-----|-----|---------|
| `arc run --stream` | ✅ | Event stream view | Live event streaming during run |
| `arc run --background` | ✅ | | Async start, return run_id |
| `arc runs cancel` | ✅ | Cancel button | Cancel running workflow |
| `arc runs stream --follow` | ✅ | | Live tail of run events |
| `arc runs status` | ✅ | Status indicator | Lightweight status check |
| `arc runs delete` | ✅ | | Single-run delete |
| `arc runs export` | ✅ | Export button | Export trace to JSONL/JSON/OTLP |
| `arc eval save` | ✅ | Save golden button | Save run as golden trace |
| `arc eval delete` | ✅ | | Delete golden trace |
| `arc profiles list/show` | ✅ | Profile selector | List/show security profiles |
| `arc workspace init/info` | ✅ | | Workspace scaffolding and info |
| Port arc-event-stream | | ✅ | Live event stream widget |
| Port arc-workflows graph | | ✅ | Graph visualization widget |
| Port arc-schemas inspector | | ✅ | Schema inspector widget |
| Port arc-health monitor | | ✅ | Health monitor widget |
| Runtime/adoption mode selector | | ✅ | UI to choose standalone vs adoption |

**Verification:** `arc run --stream` shows live events; `arc runs cancel` stops a run; event stream widget shows real-time updates; runtime mode selector works.

### P2: Audit / Replay / HITL (3-4 weeks)

| Item | CLI | IDE | Outcome |
|------|-----|-----|---------|
| `arc hitl pending/approve/reject/respond/wait` | ✅ | HITL inbox + dialog | Full HITL CLI workflow |
| `arc audit log/verify/export` | ✅ | Audit chain viewer | Full audit CLI workflow |
| `arc runs replay` | ✅ | Replay stepper | Trace replay with state inspection |
| `arc runs resume` | ✅ | | Resume paused run |
| `arc runs fork` | ✅ | | Fork run with modified inputs |
| `arc providers quota/reset` | ✅ | Provider dashboard | Quota management |
| `arc profiles create` | ✅ | | Custom security profiles |
| `arc workspace config` | ✅ | | Workspace config management |
| SwarmGraph adoption mode flag | ✅ | ✅ | `--mode adoption` in CLI, mode selector in IDE |
| Audit chain viewer | | ✅ | Visual chain with HMAC verification |
| HITL inbox + approval dialog | | ✅ | Pending approvals with single-use token |
| Consensus dashboard | | ✅ | Vote results, agreement fractions |
| Eval manager | | ✅ | Golden trace management UI |
| Provider manager | | ✅ | Accounts, routing, quota UI |

**Verification:** `arc hitl approve` approves a pending request; `arc audit verify` detects tampering; HITL inbox shows pending approvals; consensus dashboard displays vote results.

### P3: Adapter Config / Product UX (2-3 weeks)

| Item | CLI | IDE | Outcome |
|------|-----|-----|---------|
| `arc adapter register/unregister` | ✅ | | Plugin adapter system |
| `arc env redact` | ✅ | | Secret redaction utility |
| `arc bug-report` | ✅ | | Diagnostic bundle generation |
| Adapter-specific commands | ✅ | | LangGraph/CrewAI/AG2/etc. commands from Section 8 |
| Adapter setup wizard | | ✅ | Guided adapter configuration |
| Workspace trust UI | | ✅ | Trust gate before execution |
| Provider/account/cost setup | | ✅ | Full provider management UI |
| Queen/worker topology view | | ✅ | SwarmGraph agent topology visualization |
| Tenant selector + dashboard | | ✅ | Multi-tenant UI |
| Context pack widget | | ✅ | Context retrieval UI |
| Arena extension | | ✅ | Full arena UI (separate domain) |

**Verification:** Adapter setup wizard guides user through configuration; queen/worker topology shows agent assignments; tenant selector switches context.

### P4: Eval / Diff / Observability (2-3 weeks)

| Item | CLI | IDE | Outcome |
|------|-----|-----|---------|
| `arc eval run --batch` | ✅ | | Batch evaluation |
| `arc eval report` | ✅ | | Aggregate eval report |
| `arc runs search` | ✅ | | Trace search/index |
| `arc runs import` | ✅ | | Import traces |
| Time travel debugger | | ✅ | Checkpoint-based state inspection |
| State diff viewer | | ✅ | Compare state between checkpoints |
| Run comparison side-by-side | | ✅ | Visual run comparison |
| Cost tracker dashboard | | ✅ | Per-run/trace/tenant cost breakdown |
| Budget alerts | | ✅ | Visual budget limit warnings |
| Saved views/filters | | ✅ | Reusable filter queries |

**Verification:** Batch eval runs over multiple traces; time travel debugger steps through checkpoints; cost tracker shows accurate breakdowns.

### P5: Deploy / Packaging / Plugin Ecosystem (2-3 weeks)

| Item | CLI | IDE | Outcome |
|------|-----|-----|---------|
| `arc deploy` | ✅ | | Deploy workflows to target |
| `arc plugin list/install/uninstall` | ✅ | | Plugin management CLI |
| Electron packaging | | ✅ | Signed macOS installer |
| Extension/plugin marketplace | | ✅ | Browse and install plugins |
| Demo project creation | | ✅ | Scaffold sample projects |
| Full CI gate | | | Required checks for main branch |
| Real-runtime smoke suite | | | E2E tests with actual runtimes |

**Verification:** `arc deploy` deploys to target; Electron installer produces working app; marketplace lists available plugins.

---

## 11. "Do Not Build Yet" List

| Feature | Why Premature | When to Build |
|---------|--------------|---------------|
| **Plugin marketplace** | No plugin system exists; adapters are hardcoded | After P3 adapter register/unregister |
| **Multi-tenant UI** | No tenant infrastructure in ARC daemon | After SwarmGraph tenant isolation is wired into ARC |
| **Deployment CLI/UI** | No deployment target defined; ARC is local-only | After P5 deployment architecture is defined |
| **Extension/plugin ecosystem** | No plugin loading mechanism; all adapters are built-in | After P3 plugin registration system |
| **Arena live mode** | Arena is 100% stub; no live provider integration | After P2 provider gateway is wired into arena |
| **Prompt playground** | No prompt management infrastructure | After P3 when adapters expose prompt configuration |
| **Dataset management** | No dataset infrastructure; eval uses inline expectations | After P4 eval/diff infrastructure |
| **Annotation queues** | No human annotation workflow | After P2 HITL infrastructure |
| **Call stack query** | Requires runtime-level stack trace support | After P4 when runtimes expose debug interfaces |
| **Asset-centric navigation** | ARC is workflow-centric, not data-centric | Only if ARC pivots to data-product model |
| **Auto-instrumentation** | Requires OTLP auto-instrumentation of external runtimes | After P4 observability infrastructure |
| **No-code workflow builder** | ARC is a developer tool; visual builder is a different product | Only if ARC targets non-developer users |
| **Cloud deployment** | ARC is explicitly local-only | Only if ARC pivots to cloud product |
| **Multi-user daemon** | ARC is single-user by design | Only if ARC targets shared environments |
| **Browser-use agent support** | High side-effect risk; needs sandbox | After P4 workspace trust + sandbox infrastructure |

---

## 12. Open Questions

| Question | Why It Matters | Suggested Owner |
|----------|---------------|-----------------|
| Should `arc run --stream` use daemon SSE or direct adapter streaming? | Affects architecture: daemon as event broker vs adapter as event source | Runtime owner |
| Where should HITL state be persisted? | Determines resume semantics and crash recovery | Storage owner |
| What is the canonical syntax for adoption runtime IDs? | Affects CLI/API/UI contract: `langgraph+swarmgraph` vs `langgraph --mode adoption` | Protocol owner |
| Should ARC have its own graph visualization library or use reactflow/GLSP? | Affects IDE implementation complexity and visual quality | UI owner |
| Should the daemon support WebSocket for bidirectional communication? | Affects live streaming, HITL, and real-time UI updates | Backend owner |
| Should ARC support multiple concurrent daemon instances? | Affects multi-workspace and multi-tenant support | Architecture owner |
| Should SwarmGraph be imported as vendored library or invoked only via CLI? | Adoption layer needs tighter integration than subprocess JSON | Runtime owner |
| Where should HMAC audit keys live? | Determines security posture and UX | Security owner |
| Should ARC have a project scaffolding command like `crewai create`? | Affects onboarding and developer experience | Product owner |
| Should the IDE support custom editors for workflow definition files? | Affects IDE integration depth | UI owner |
| Should arena be part of the main IDE or a separate product? | Arena is a different domain (model comparison, not workflow execution) | Product owner |
| What is the deployment target for ARC workflows? | Affects P5 deploy commands | Architecture owner |
| Should ARC support remote daemon connections? | Currently loopback-only; remote access changes security model | Security owner |
