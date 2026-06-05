# External Agent Runtime / Workflow Tools — UI/Studio Research

> Compiled 2026-05-14. Sources cited per tool.

---

## 1. LangGraph Studio (LangSmith)

**Source:** https://docs.langchain.com/langsmith/studio | https://docs.langchain.com/langsmith/quick-start-studio

### What exists
LangGraph Studio is a specialized agent IDE hosted within LangSmith. It connects to Agent Server instances (local via `langgraph dev` or deployed to LangSmith Cloud). Access URL: `https://smith.langchain.com/studio/?baseUrl=http://127.0.0.1:2024`

### Views/Panels/Features
- **Graph Visualizer** — renders the full LangGraph node/edge architecture as an interactive graph
- **Graph Mode** — full-featured view showing node traversals, intermediate states, LangSmith integrations (add to datasets, playground)
- **Chat Mode** — simplified chat UI for testing chat agents (requires `MessagesState`)
- **Run & Interact** — send inputs to agents, stream responses, manage conversations
- **Assistant Management** — configure and switch between different assistants/graphs
- **Thread Management** — manage conversation threads across runs
- **Time Travel Debugging** — step through agent state at any checkpoint, replay from any point
- **Prompt Iteration** — edit prompts inline and re-run
- **Experiments** — run graph over datasets and compare results
- **Memory Management** — inspect and manage long-term memory
- **Tracing Integration** — click through to LangSmith traces for any run
- **Evaluation Integration** — score outputs, add to datasets

### Key UX Patterns for ARC Studio
- **Dual-mode UI** (Graph vs Chat) — simple mode for business users, detailed mode for developers
- **Time travel** — checkpoint-based replay is the killer feature for agent debugging
- **Graph visualization as first-class citizen** — the graph IS the primary navigation
- **Inline prompt editing** — change prompts and re-run without leaving the UI
- **Thread-based conversation model** — threads as the unit of stateful interaction

### Limitations/Gaps
- Only works with LangGraph graphs implementing Agent Server API
- Cloud-hosted Studio requires LangSmith account (local Studio connects to `langgraph dev`)
- No built-in code editor — graph definition is in code, not visual
- No multi-agent swarm visualization (single graph at a time)
- No side-by-side comparison of runs

---

## 2. LangSmith

**Source:** https://docs.smith.langchain.com/ | https://docs.langchain.com/langsmith/observability-quickstart

### What exists
LangSmith is a full-platform web UI for LLM application development. Cloud-hosted at `smith.langchain.com` with self-hosted options.

### Views/Panels/Features
- **Traces** — hierarchical trace tree showing all LLM calls, tool calls, retrievals with timing
- **Trace Detail** — expandable tree view with inputs, outputs, metadata, tokens, latency per span
- **Sessions** — grouped traces by conversation/session
- **Datasets** — manage test datasets with examples, create from traces
- **Evaluations** — run evals on traces/datasets, view scores, compare results
- **Experiments** — compare runs across prompt/model/config changes on same datasets
- **Prompt Hub** — version-controlled prompt management with inline editing
- **Playground** — test prompts with different models, compare outputs side-by-side
- **Monitoring Dashboard** — quality, cost, latency metrics over time
- **Fleet** — visual no-code agent builder
- **Deployments** — deploy agents as Agent Servers
- **Feedback** — collect user feedback (thumbs up/down) on traces
- **Saved Views/Filters** — filter traces by status, type, time range, custom attributes

### Key UX Patterns for ARC Studio
- **Trace tree with expandable spans** — the standard pattern for LLM observability
- **Dataset → Experiment → Evaluation pipeline** — systematic iteration workflow
- **Playground with side-by-side model comparison** — essential for prompt engineering
- **Feedback collection on traces** — human-in-the-loop annotation
- **Cost tracking per trace** — token usage and cost breakdown per span

### Limitations/Gaps
- SaaS-first (self-hosting is complex)
- No graph visualization (that's LangGraph Studio's role)
- No real-time streaming in trace view (traces appear after completion)
- No HITL intervention during execution

---

## 3. Langfuse

**Source:** https://langfuse.com/docs | https://langfuse.com/docs/demo

### What exists
Open-source LLM engineering platform with a self-hostable web UI. Live demo at the example project on langfuse.com.

### Views/Panels/Features (from left navigation)
- **Traces** — list of all traces with timing, cost, scores; click to see execution steps
- **Sessions** — multi-turn conversation tracking
- **Timeline** — Gantt-style latency visualization for debugging performance
- **Users** — per-user cost/usage tracking with deep links
- **Agent Graphs** — visualize agentic workflows as graphs
- **Dashboard** — quality, cost, latency metrics overview
- **Prompts** — prompt management with version control, deployment labels, change tracking
- **LLM Playground** — test prompts interactively
- **Scores/Evaluations** — LLM-as-a-judge, user feedback, manual labeling, custom evals
- **Datasets** — systematic testing datasets
- **Experiments** — test prompts/models on datasets without code
- **Annotation Queues** — human annotation workflow
- **Models** — model usage tracking

### Key UX Patterns for ARC Studio
- **Timeline/Gantt view** — unique latency debugging pattern not seen in other tools
- **Agent graph visualization** — shows agent flow as a graph (similar to LangGraph Studio)
- **Prompt versioning with deployment labels** — promote prompts to production via labels
- **Change tracking on prompts** — diff view showing how prompts evolved
- **Annotation queues** — structured human review workflow
- **Sessions as first-class concept** — multi-turn conversation grouping

### Limitations/Gaps
- Agent graphs are auto-inferred from traces, not designed visually
- No time-travel/checkpoint replay
- No real-time streaming during execution
- Playground is prompt-only, not full workflow testing

---

## 4. Arize Phoenix

**Source:** https://docs.arize.com/phoenix

### What exists
Open-source AI observability tool with a local web UI. Runs as a local server with browser-based interface.

### Views/Panels/Features
- **Tracing** — distributed traces with model calls, retrieval, tool use, custom logic
- **Trace Detail** — step-by-step execution view with inputs/outputs
- **Evaluations** — LLM-based evals, code-based checks, human labels on traces/spans
- **Prompt Playground** — experiment with prompts and models side-by-side, version prompts
- **Span Replay** — replay individual LLM calls with different inputs/models
- **Datasets** — create from traces, upload CSV, or from code
- **Experiments** — compare application versions on same datasets with attached evaluators
- **Human Annotations** — attach ground truth labels in the UI
- **Dashboard** — quality, cost, latency metrics

### Key UX Patterns for ARC Studio
- **Span Replay** — unique feature: replay a single LLM call with modified inputs, great for debugging
- **Dataset evaluators auto-run** — evaluators attached to datasets run automatically during experiments
- **Prompts-in-code sync** — bidirectional sync between code and UI prompt definitions
- **OpenTelemetry-native** — traces via OTLP, reduces vendor lock-in

### Limitations/Gaps
- No graph/workflow visualization
- No real-time streaming
- No HITL intervention
- Less mature than LangSmith/Langfuse in prompt management

---

## 5. MLflow UI

**Source:** https://mlflow.org/docs/latest/genai/ | https://demo.mlflow.org/

### What exists
MLflow is the largest open-source AI engineering platform. Web UI accessible via `mlflow ui` or demo at `demo.mlflow.org`.

### Views/Panels/Features
- **Experiments** — list of experiments with runs, parameters, metrics, artifacts
- **Runs** — individual run detail with params, metrics, tags, artifacts, traces
- **Traces (GenAI)** — LLM/agent traces with expandable span tree, inputs/outputs, token usage
- **Trace Detail** — hierarchical view of LLM calls, retrievals, tool calls
- **Models** — registered models with version history, stages, deployment status
- **Prompt Registry** — version-controlled prompts with lineage tracking
- **Evaluation** — LLM-as-a-judge evaluation with pre-built and custom judges
- **AI Gateway** — manage model access, cost control, routing
- **Agent Serving** — deploy agents as servers
- **Version Tracking** — git-like version control for prompts and configurations
- **Dashboard** — experiment comparison, metric charts

### Key UX Patterns for ARC Studio
- **Experiment/Run hierarchy** — the classic MLflow pattern, well-suited for systematic comparison
- **Prompt lineage** — trace which prompt versions were used in which runs
- **Automated prompt optimization** — algorithmic prompt improvement
- **AI Gateway integration** — cost control and model access management in the same UI
- **OpenTelemetry-compatible tracing** — vendor-neutral trace format

### Limitations/Gaps
- UI feels more "ML" than "agent-native" — designed for experiments, not real-time workflows
- No graph visualization
- No real-time streaming during execution
- No HITL intervention
- Trace UI is less polished than LangSmith/Langfuse

---

## 6. Temporal Web UI

**Source:** https://docs.temporal.io/web-ui

### What exists
Temporal ships with a built-in web UI for workflow orchestration. Available with Temporal CLI (`temporal server start-dev`) and Temporal Cloud.

### Views/Panels/Features
- **Namespaces** — left sidebar namespace switcher
- **Workflows** — main table of all workflow executions with filtering by status, ID, type, time, search attributes
- **Saved Views** — reusable filter queries (up to 20 per user), shareable via URL
- **Workflow Detail** — per-workflow page with:
  - **History** — event timeline (chronological/reverse), compact view, JSON view
  - **Relationships** — parent/child workflow tree
  - **Workers** — currently polling workers on task queue
  - **Pending Activities** — active/pending activity executions
  - **Call Stack** — live stack trace query showing where code is waiting
  - **Queries** — query history sent to workflow
  - **Metadata** — user metadata, human-readable log
- **Workflow Actions** — cancel, signal, update, reset, terminate, "start like this one"
- **Task Failures View** — pre-filtered view of workflows with consecutive task failures
- **Schedules** — cron-based schedule management with frequency, runs, upcoming runs
- **Archive** — archived workflow data
- **Settings** — user management, observability, audit logging

### Key UX Patterns for ARC Studio
- **Saved Views** — powerful pattern for reusable queries, shareable via URL
- **Event History with multiple views** — Timeline, Compact, All, JSON — gives users flexibility
- **Call Stack query** — live stack trace of running workflow (unique and powerful)
- **Relationships tree** — parent/child hierarchy visualization
- **Workflow Actions** — direct intervention from UI (cancel, signal, reset, terminate)
- **"Start like this one"** — pre-fill new run from existing run parameters
- **Task Failures auto-flagging** — automatic detection of stuck workflows (5 consecutive failures)

### Limitations/Gaps
- No graph/DAG visualization of workflow structure
- No LLM-specific features (traces, tokens, prompts)
- No real-time streaming (polling-based)
- UI is functional but not modern/polished

---

## 7. Prefect UI

**Source:** https://docs.prefect.io/v3/

### What exists
Prefect provides a modern web UI (Prefect Cloud or self-hosted server) for workflow orchestration.

### Views/Panels/Features
- **Dashboard** — overview of flow runs, task runs, deployments with charts
- **Flows** — list of flow definitions
- **Flow Runs** — table of runs with status, timing, logs
- **Flow Run Detail** — per-run page with:
  - **Timeline/Gantt** — visual timeline of task execution
  - **Logs** — real-time log streaming
  - **Task Runs** — individual task status and details
  - **Artifacts** — outputs and artifacts from the run
  - **Parameters** — input parameters
- **Deployments** — deployed flow configurations
- **Work Pools** — worker/infrastructure management
- **Automations** — event-driven triggers and actions
- **Blocks** — reusable configuration blocks
- **Variables** — shared variables across flows
- **Concurrency Limits** — manage execution concurrency

### Key UX Patterns for ARC Studio
- **Real-time flow run monitoring** — live updates during execution
- **Timeline/Gantt for tasks** — visual execution timeline
- **Automations** — event-driven workflow triggers (reactive patterns)
- **Interactive workflows** — pause flows for human intervention/approval
- **Dynamic runtime** — tasks created at runtime (not pre-defined DAG)

### Limitations/Gaps
- No graph/DAG visualization (embraces dynamic runtime over static DAGs)
- No LLM-specific features
- No trace-level detail (task-level only)
- Self-hosted UI is more limited than Cloud

---

## 8. Dagster UI

**Source:** https://docs.dagster.io/getting-started/quickstart | https://docs.dagster.io/guides/operate/webserver

### What exists
Dagster provides a web UI (Dagster webserver at `localhost:3000`) for data pipeline orchestration. Dagster+ adds cloud features.

### Views/Panels/Features
- **Assets** — primary view showing data assets with dependency graph
- **Asset Lineage** — interactive DAG visualization showing upstream/downstream dependencies
- **Asset Detail** — per-asset view with materialization history, checks, freshness policies
- **Runs** — list of pipeline runs with status, timing
- **Run Detail** — per-run page with:
  - **Gantt chart** — execution timeline with multiple view options
  - **Logs** — structured log viewer
  - **Steps** — individual step status
- **Jobs** — executable job definitions
- **Schedules** — cron-based schedule management
- **Sensors** — event-based triggers
- **Partitions** — partitioned data management
- **Backfills** — historical data reprocessing
- **Overview** — dashboard with asset health, recent runs
- **Asset Checks** — data quality checks with pass/fail status
- **Catalog (Dagster+)** — searchable asset catalog
- **Alerts (Dagster+)** — alert configuration
- **Insights (Dagster+)** — cost, performance, reliability analytics

### Key UX Patterns for ARC Studio
- **Asset-centric navigation** — assets (data products) are the primary concept, not runs
- **Asset Lineage DAG** — interactive dependency graph is the core visualization
- **Materialize button** — direct execution from the asset view
- **Multiple run view options** — Gantt, list, and other display modes
- **Asset checks** — inline data quality validation with pass/fail
- **Partitions and backfills** — systematic historical processing

### Limitations/Gaps
- Data-pipeline focused, not agent/LLM focused
- No real-time streaming
- No HITL intervention
- Dagster+ features (catalog, alerts, insights) are paid-only

---

## 9. VS Code Extension Patterns

**Source:** https://code.visualstudio.com/api/extension-guides/webview | https://code.visualstudio.com/api/ux-guidelines/

### What exists
VS Code provides a rich extension API for building custom UI within the IDE.

### Key UI Patterns
- **Activity Bar** — left-most bar with icons for major sections (Explorer, Search, SCM, Extensions, custom)
- **Sidebar Panels** — expandable panels in the sidebar (file explorer, search results, custom tree views)
- **Tree Views** — hierarchical data display with expand/collapse, icons, inline actions, context menus
- **Webview Panels** — full HTML/JS panels in the editor area (like Markdown preview)
- **Webview Views** — webviews embedded in sidebar or panel areas (more constrained than panels)
- **Custom Editors** — replace the default editor for specific file types
- **Status Bar** — bottom bar for status indicators
- **Quick Picks** — command palette-style dropdown for selection
- **Notifications** — toast-style notifications (info, warning, error)
- **Context Menus** — right-click menus with `when` clause conditions
- **Walkthroughs** — guided onboarding experiences

### Webview Capabilities
- Full HTML/CSS/JS rendering (like an iframe)
- Message passing between extension and webview (bidirectional `postMessage`)
- Theme-aware (light/dark/high-contrast via CSS classes and CSS variables)
- Local resource loading via `asWebviewUri`
- State persistence via `getState`/`setState`
- Serialization for restore across restarts
- Context menus with `data-vscode-context`
- Content Security Policy support

### Key UX Patterns for ARC Studio
- **Activity bar icon** — single click to open the main panel (ARC Studio should have one)
- **Tree view for hierarchical data** — perfect for trace spans, workflow nodes, run lists
- **Webview for complex visualizations** — graph visualization, timeline, custom React UIs
- **Status bar indicators** — running state, connection status, active run count
- **Quick picks for actions** — select workflow, select run, filter options
- **Notifications for events** — run complete, error detected, HITL request

### Limitations/Gaps
- Webviews are resource-heavy (separate context)
- No native access to VS Code APIs from webview (must use message passing)
- Limited layout control (constrained by VS Code's workbench layout)
- State management across hide/show cycles requires explicit persistence

---

## 10. Theia Extension Patterns

**Source:** https://theia-ide.org/docs/authoring_extensions/ | https://theia-ide.org/docs/widgets/ | https://theia-ide.org/docs/architecture/

### What exists
Eclipse Theia is an open-source platform for building cloud & desktop IDEs. ARC Studio is built on Theia.

### Key Extension Mechanisms
- **Theia Extensions** — native extensions using DI modules (`theiaExtensions` in package.json)
- **VS Code Extensions** — Theia can run VS Code extensions natively
- **Contribution Interfaces** — `CommandContribution`, `MenuContribution`, `WidgetContribution`, etc.

### Widget System
- **ReactWidget** — base class for React-based widgets (recommended for custom UI)
- **TreeWidget** — for tree-based views (file explorer, trace trees)
- **BaseWidget** — for non-React widgets
- **WidgetFactory** — registers widget creation with `WidgetManager`
- **AbstractViewContribution** — wires widgets into view menu, commands, and workbench

### Widget Lifecycle
- `@postConstruct` init — set ID, label, icon, closable
- `render()` — React component rendering
- `onUpdateRequest` — triggered when widget needs re-render
- `onResize` — handle size changes
- Managed by `WidgetManager` (supports `getOrCreate` for singleton behavior)

### Architecture
- **Frontend/Backend split** — frontend runs in browser, backend in Node.js
- **JSON-RPC communication** — services communicate over JSON-RPC
- **Inversify DI** — dependency injection for both frontend and backend
- **Phosphor.js** — underlying window management (dragging, docking, tab management)

### Layout Areas
- **Left area** — sidebar panels (like VS Code sidebar)
- **Right area** — secondary sidebar
- **Main area** — editor tabs
- **Bottom area** — panels (terminal, problems, output)
- **Status bar** — bottom status indicators

### Key UX Patterns for ARC Studio
- **Custom widget in main area** — ARC Studio widget as a dockable tab (current approach)
- **Tree widget in sidebar** — trace list, workflow list, run history in sidebar
- **ReactWidget for complex UI** — all custom UI should use ReactWidget base class
- **Command + menu contribution** — open ARC Studio via command palette and View menu
- **JSON-RPC service** — backend services exposed to frontend via JSON-RPC (current pattern)
- **Widget contribution with default area** — auto-place widget in left/main area on first open

### What's Possible
- Full React UIs within Theia workbench
- Custom editors for specific file types (e.g., `.swarmgraph` files)
- Tree views with icons, inline actions, context menus
- Status bar contributions for run status
- Bottom panel contributions for logs/output
- Toolbar contributions for quick actions
- Theia AI integration — built-in AI framework for chat interfaces and AI agents
- Dynamic toolbar — context-aware toolbar actions
- Breadcrumbs — navigation breadcrumbs for hierarchical views
- Property view — context-sensitive property panels

---

## Structured Comparison Matrix

| Feature | LangGraph Studio | LangSmith | Langfuse | Phoenix | MLflow | Temporal | Prefect | Dagster |
|---------|-----------------|-----------|----------|---------|--------|----------|---------|---------|
| **Graph Visualization** | ✅ Interactive | ❌ | ✅ Auto-inferred | ❌ | ❌ | ❌ | ❌ | ✅ Asset DAG |
| **Trace Tree** | ❌ (via LangSmith) | ✅ Expandable | ✅ Expandable | ✅ Expandable | ✅ Expandable | ✅ Event History | ❌ | ❌ |
| **Timeline/Gantt** | ❌ | ❌ | ✅ Latency | ❌ | ❌ | ✅ Event timeline | ✅ Task timeline | ✅ Run Gantt |
| **Time Travel/Replay** | ✅ Checkpoints | ❌ | ❌ | ✅ Span replay | ❌ | ✅ Reset/replay | ❌ | ❌ |
| **Real-time Streaming** | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ (polling) | ✅ | ❌ |
| **HITL Intervention** | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ Signal/Cancel | ✅ Pause | ❌ |
| **Prompt Management** | ✅ Inline edit | ✅ Hub | ✅ Versioned | ✅ Playground | ✅ Registry | ❌ | ❌ | ❌ |
| **Evaluation** | ✅ Via LangSmith | ✅ Full | ✅ Full | ✅ Full | ✅ LLM judges | ❌ | ❌ | ❌ |
| **Datasets** | ✅ Via LangSmith | ✅ Full | ✅ Full | ✅ Full | ❌ | ❌ | ❌ | ❌ |
| **Sessions/Threads** | ✅ Threads | ✅ Sessions | ✅ Sessions | ❌ | ❌ | ❌ | ❌ | ❌ |
| **Saved Views/Filters** | ❌ | ✅ | ❌ | ❌ | ❌ | ✅ Saved Views | ❌ | ❌ |
| **Workflow Actions** | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ Cancel/Signal/Reset | ❌ | ❌ |
| **Cost Tracking** | ❌ | ✅ Per trace | ✅ Per trace | ✅ | ❌ | ❌ | ❌ | ❌ |
| **Self-hostable** | ✅ (langgraph dev) | ⚠️ Complex | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Open Source** | ⚠️ Partial | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |

---

## Top UX Patterns to Adopt for ARC Studio

### Must-Have (from research)
1. **Graph Visualization** — Interactive SwarmGraph/LangGraph DAG as the primary view (LangGraph Studio, Dagster)
2. **Trace Tree with Expandable Spans** — Hierarchical execution detail (LangSmith, Langfuse, MLflow)
3. **Timeline View** — Gantt-style execution timeline for latency debugging (Langfuse, Temporal, Prefect, Dagster)
4. **Time Travel / Replay** — Checkpoint-based state inspection and replay (LangGraph Studio, Temporal)
5. **Real-time Streaming** — Live updates during workflow execution (LangGraph Studio, Prefect)
6. **Run List with Filters** — Table of runs with status, timing, filtering (all tools)
7. **Workflow Actions** — Cancel, retry, re-run from UI (Temporal)

### Should-Have
8. **Saved Views** — Reusable filter queries shareable via URL (Temporal)
9. **Sessions/Threads** — Group related runs by conversation or workflow session (LangGraph Studio, LangSmith, Langfuse)
10. **Prompt Playground** — Test and iterate on prompts inline (LangSmith, Langfuse, Phoenix)
11. **Evaluation Integration** — Score outputs, run evals on datasets (LangSmith, Langfuse, Phoenix, MLflow)
12. **Cost/Token Tracking** — Per-trace and per-run cost breakdown (LangSmith, Langfuse, Phoenix)
13. **"Start Like This One"** — Pre-fill new run from existing parameters (Temporal)

### Nice-to-Have
14. **HITL Intervention** — Pause for human input during execution (Temporal signals, Prefect pause)
15. **Annotation Queues** — Structured human review workflow (Langfuse)
16. **Call Stack Query** — Live stack trace of running workflow (Temporal)
17. **Relationships Tree** — Parent/child workflow hierarchy (Temporal)
18. **Asset-centric View** — Data products as primary navigation (Dagster)

### Theia-Specific Implementation Notes
- Use **ReactWidget** as base class for the main ARC Studio widget (current approach is correct)
- Consider adding a **TreeWidget** in the sidebar for run history / trace list
- Use **AbstractViewContribution** to wire ARC Studio into the View menu
- Add **Activity Bar** icon (Theia supports sidebar contributions)
- Use **Status Bar** contribution for active run status
- Leverage **JSON-RPC** for frontend-backend communication (already in place)
- Consider **Custom Editor** for `.swarmgraph` or workflow definition files
- Use **Theia AI** framework if adding chat/assistant features
- **WidgetFactory** with singleton pattern for single ARC Studio instance
