# ARC Studio User Guide

**Complete documentation for using ARC Studio — Agent Runtime Cockpit IDE.**

---

## Table of Contents

1. [Getting Started](#getting-started)
2. [Interface Overview](#interface-overview)
3. [Executing Workflows](#executing-workflows)
4. [Viewing Traces](#viewing-traces)
5. [Scanning Workspaces](#scanning-workspaces)
6. [Configuration](#configuration)
7. [Keyboard Shortcuts](#keyboard-shortcuts)
8. [Troubleshooting](#troubleshooting)
9. [FAQ](#faq)

---

## Getting Started

### What is ARC Studio?

ARC Studio is an IDE for agent workflow development built on Eclipse Theia. It provides a complete environment for building, executing, and debugging agent workflows using SwarmGraph and LangGraph.

**Key capabilities:**
- Execute SwarmGraph workflows with natural language prompts
- Visualize execution traces in real time
- Detect workflows in your workspace automatically
- Browse and inspect historical execution traces

### Prerequisites

| Tool | Minimum Version | Check Command |
|------|----------------|---------------|
| Node.js | 18.0.0 | `node --version` |
| pnpm | 8.0.0 | `pnpm --version` |
| Python | 3.11 | `python --version` |
| Git | Any | `git --version` |
| SwarmGraph CLI | Latest | `which swarmgraph` |

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/Hansuqwer/arc-theia-studio.git
cd arc-theia-studio
git checkout build/no-mockups-handoff

# 2. Check environment
bash scripts/check-env.sh

# 3. Bootstrap development environment
bash scripts/bootstrap-dev.sh

# 4. Start the application
pnpm start:browser
```

Visit **http://localhost:3000** to access ARC Studio.

### First Steps

1. **Open the ARC Studio panel** — Click the ARC Studio icon in the left activity bar
2. **Execute a workflow** — Enter a prompt and click "Execute Workflow"
3. **View traces** — Click "Load Traces" to see execution history
4. **Scan workspace** — Click "Scan Workspace" to detect workflows

For a detailed walkthrough, see the [Quick Start Guide](QUICKSTART.md).

---

## Interface Overview

### Layout

ARC Studio appears as a side panel in the Eclipse Theia IDE:

```
┌─────────────────────────────────────────────────────────────┐
│  Theia Menu Bar                                             │
├──────────┬──────────────────────────────────────────────────┤
│ Activity │                                                  │
│ Bar      │              Main Editor Area                    │
│          │                                                  │
│ [ARC] ◄──┤                                                  │
│ [Files]  │                                                  │
│ [Search] │                                                  │
│ [Git]    ├──────────────────────────────────────────────────┤
│          │              Status Bar                          │
└──────────┴──────────────────────────────────────────────────┘
```

### ARC Studio Panel Components

The ARC Studio panel contains three main sections:

#### 1. Header

- **Title:** "ARC Studio"
- **Subtitle:** "Agent Runtime Cockpit"
- **Help button (?)** — Opens keyboard shortcuts reference

#### 2. Workflow Execution Section

- **Prompt input** — Text field for entering workflow prompts
- **Execute button** — Triggers workflow execution
- **Progress bar** — Shows execution progress (0-100%)
- **Execution steps** — Five-step progress visualization:
  1. Parsing prompt
  2. Planning execution
  3. Executing workflow
  4. Recording trace
  5. Finalizing results
- **Status indicator** — Shows running/completed/failed state
- **Result display** — Shows run ID, trace path, and status on completion

#### 3. Trace Viewer Section

- **Filter input** — Filter traces by run ID (debounced, 300ms)
- **Load Traces button** — Scans `.arc/traces/` for trace files
- **Progress bar** — Shows loading progress
- **Trace list** — Table with columns:
  - Status (✓ completed, ✗ failed)
  - Run ID (e.g., `run-sg-abc123`)
  - Timestamp (local date/time)

#### 4. Workflow Detection Section

- **Scan Workspace button** — Initiates workspace scan
- **Progress bar** — Shows scanning progress
- **Workflow list** — Table with columns:
  - Type (`swarmgraph` or `langgraph`)
  - Name (human-readable)
  - Path (absolute path)

#### 5. Footer

- Keyboard shortcuts quick reference
- Shows: `Ctrl+H` shortcuts | `Ctrl+E` execute | `Ctrl+L` traces | `Ctrl+S` scan | `Esc` close

### Notifications

ARC Studio uses three notification channels:

1. **Toast notifications** — Appear in top-right corner, auto-dismiss after 5 seconds
   - Green (✓) for success
   - Red (✗) for errors
   - Yellow (⚠) for warnings
   - Blue (ℹ) for info

2. **Theia message service** — Appears in Theia's notification area
   - `info` for completions
   - `error` for failures
   - `warn` for validation issues

3. **Error banner** — Persistent error display within the widget
   - Shows error title and details
   - "Try Again" button for recovery
   - Dismiss button (×)

---

## Executing Workflows

### Basic Execution

1. Open the ARC Studio panel
2. Enter a prompt in the **Workflow Execution** section
3. Click **Execute Workflow** or press `Ctrl+Enter`
4. Monitor progress via the progress bar and execution steps
5. View results in the execution result display

### Prompt Guidelines

- **Minimum:** At least 1 character
- **Maximum:** 10,000 characters
- **Content:** Natural language description of the task
- **Examples:**
  - `What is 2+2?`
  - `Summarize the latest news about artificial intelligence`
  - `Write a Python function that sorts a list`

### Execution Backends

| Backend | Description | Use Case | API Cost |
|---------|-------------|----------|----------|
| `gateway` | SwarmGraph gateway with real LLM providers | Production | Yes |
| `stub` | Stub backend for testing | Development/testing | No |

### Execution Flow

```
User enters prompt
    │
    ▼
Validate input (non-empty, < 10,000 chars)
    │
    ▼
Spawn SwarmGraph CLI subprocess
    │
    ▼
Execute workflow (swarmgraph swarm --json "prompt")
    │
    ▼
Write trace to .arc/traces/run-sg-{hash}.jsonl
    │
    ▼
Return result with run ID and trace path
    │
    ▼
Display results in UI
```

### Execution Results

On success, you'll see:

- **Run ID:** Unique identifier (format: `run-sg-{hash}`)
- **Trace Path:** Location of the trace file (`.arc/traces/{runId}.jsonl`)
- **Status:** "Completed" with green badge
- **Execution Time:** Duration in seconds

On failure:

- **Error Banner:** Shows error title and details
- **Toast Notification:** Red error toast
- **Status:** "Execution failed" with red indicator
- **Recovery:** Click "Try Again" to reset and retry

### Cancelling Execution

Currently, execution cancellation is handled via the `cancelWorkflow` API method, which sends SIGTERM to the subprocess. The UI does not yet expose a cancel button.

---

## Viewing Traces

### Trace Format

Traces use **JSONL format** (JSON Lines) — one JSON object per line:

```jsonl
{"type":"RUN_STARTED","timestamp":"2026-05-12T20:30:00Z","runId":"run-sg-abc123","sequence":0,"data":{}}
{"type":"NODE_COMPLETED","timestamp":"2026-05-12T20:30:10Z","runId":"run-sg-abc123","sequence":1,"data":{"nodeId":"agent-1"}}
{"type":"RUN_COMPLETED","timestamp":"2026-05-12T20:30:15Z","runId":"run-sg-abc123","sequence":2,"data":{}}
```

### Event Types

| Event | Description | Key Data Fields |
|-------|-------------|----------------|
| `RUN_STARTED` | Execution began | `workflowId`, `runtime` |
| `NODE_COMPLETED` | Graph node finished | `nodeId`, `nodeName`, `output`, `duration` |
| `MESSAGE` | Message sent/received | `role`, `content`, `nodeId` |
| `RUN_COMPLETED` | Execution succeeded | `result`, `duration` |
| `RUN_FAILED` | Execution failed | `error`, `stackTrace` |
| `ERROR` | Error occurred | Varies by error type |

### Loading Traces

1. Navigate to the **Trace Viewer** section
2. Click **Load Traces**
3. Wait for the progress bar to complete
4. Browse the trace list (sorted newest first)

### Filtering Traces

1. Type in the **Filter traces** input field
2. Filtering matches against run IDs (case-insensitive)
3. Results update after 300ms debounce delay
4. Click × to clear the filter

### Selecting Traces

1. Click a trace row to select it
2. Selected trace is highlighted
3. Use keyboard: `Tab` to focus, `Enter`/`Space` to select
4. Selection is announced to screen readers

### Viewing Trace Files Manually

```bash
# List all traces
ls -la .arc/traces/

# View a specific trace
cat .arc/traces/run-sg-abc123.jsonl

# Pretty-print with jq
cat .arc/traces/run-sg-abc123.jsonl | jq

# Count events
wc -l .arc/traces/run-sg-abc123.jsonl

# Filter by event type
grep "RUN_COMPLETED" .arc/traces/run-sg-abc123.jsonl | jq
```

### Trace Storage

- **Location:** `.arc/traces/` directory in workspace root
- **Format:** JSONL (one JSON event per line)
- **Naming:** `run-sg-{hash}.jsonl`
- **Retention:** Manual cleanup required (no auto-deletion)

---

## Scanning Workspaces

### What Gets Detected

**SwarmGraph:**
- CLI binary in system PATH
- Local installations in `node_modules/.bin/`
- Virtual environment installations
- NPM global installations

**LangGraph:**
- Python files containing `StateGraph` class usage
- Files with `from langgraph.graph import StateGraph` imports
- AST analysis of Python source files

### Running a Scan

1. Navigate to the **Workflow Detection** section
2. Click **Scan Workspace**
3. Wait for the progress bar to complete
4. View detected workflows in the results list

### Scan Results

Each detected workflow shows:

| Field | Description | Example |
|-------|-------------|---------|
| Type | Runtime type | `swarmgraph` or `langgraph` |
| Name | Human-readable name | `SwarmGraph CLI` |
| Path | Absolute path | `/usr/local/bin/swarmgraph` |

### No Workflows Detected

If scanning returns no results:

1. **For SwarmGraph:**
   ```bash
   # Check if installed
   which swarmgraph
   
   # Install from: https://github.com/Hansuqwer/SwarmGraph
   ```

2. **For LangGraph:**
   - Ensure Python files with `StateGraph` definitions exist in the workspace
   - Verify imports: `from langgraph.graph import StateGraph`

---

## Configuration

### Environment Variables

| Variable | Purpose | Default |
|----------|---------|---------|
| `NODE_ENV` | Build mode | `development` |
| `ARC_SWARMGRAPH_CLI` | Path to SwarmGraph CLI binary | Auto-detected |
| `ARC_CONTEXT7_API_KEY` | Context7 API key | Not set |
| `GITHUB_TOKEN` | GitHub API token | Not set |
| `THEIA_HOST` | Theia server hostname | `0.0.0.0` |
| `THEIA_PORT` | Theia server port | `3000` |

### Python Daemon Configuration

The optional ARC daemon provides additional features:

```bash
# Start the daemon
cd python
uv run arc serve

# Default: http://localhost:7777
# Use a different port:
uv run arc serve --port 7778
```

The daemon enables:
- Real-time workspace inspection
- Adapter management
- Context pack generation
- AG-UI-compatible SSE event streaming

### Trace Configuration

Traces are stored in `.arc/traces/` by default. This location is not currently configurable via UI.

### Backend Configuration

The execution backend can be configured via the `ExecutionOptions` protocol:

```typescript
{
  backend: 'gateway' | 'stub',  // Default: 'gateway'
  costAllowed: boolean,          // Default: true
  timeout: number,               // Default: 300000 (5 min)
  workspaceRoot: string          // Default: cwd
}
```

---

## Keyboard Shortcuts

### Complete Reference

| Action | Windows/Linux | Mac | When |
|--------|--------------|-----|------|
| Execute Workflow | `Ctrl+E` | `⌘+E` | Widget focused |
| Load Traces | `Ctrl+L` | `⌘+L` | Widget focused |
| Scan Workspace | `Ctrl+S` | `⌘+S` | Widget focused |
| Show Shortcuts | `Ctrl+H` | `⌘+H` | Widget focused |
| Show Shortcuts (alt) | `Ctrl+?` | `⌘+?` | Widget focused |
| Execute from Input | `Ctrl+Enter` | `⌘+Enter` | Input focused |
| Close Modal | `Esc` | `Esc` | Modal open |
| Retry Error | `Esc` | `Esc` | Error shown |

### Tips

- Shortcuts require the ARC widget to have focus (click inside the panel first)
- Press `Ctrl+H` to see the shortcuts help modal at any time
- `Ctrl+Enter` only works when the prompt input is focused
- `Esc` has contextual behavior based on current state

---

## Troubleshooting

### Quick Fixes

| Problem | Quick Fix |
|---------|-----------|
| Build fails | `pnpm clean && pnpm install && pnpm build` |
| App won't start | Check port 3000 is free: `lsof -i :3000` |
| Widget not visible | Rebuild extension: `cd packages/arc-extension && pnpm build` |
| Execution fails | Check SwarmGraph: `which swarmgraph` |
| Traces not loading | Execute a workflow first to generate traces |
| Shortcuts not working | Click inside the ARC widget first |
| High memory usage | Clean old traces: `find .arc/traces/ -mtime +7 -delete` |

### Common Error Messages

**"Please enter a prompt for workflow execution"**
- Type text in the prompt input field before executing

**"swarmgraph command not found"**
- Install SwarmGraph from https://github.com/Hansuqwer/SwarmGraph
- Ensure it's in your PATH

**"Failed to load traces"**
- Check `.arc/traces/` directory exists
- Execute a workflow to generate trace files

**"Failed to scan workspace"**
- Verify workspace is properly opened in Theia

### Detailed Troubleshooting

See the [Troubleshooting Guide](TROUBLESHOOTING.md) for comprehensive solutions.

---

## FAQ

### General

**Q: What is ARC Studio?**
A: ARC Studio (Agent Runtime Cockpit) is an IDE for agent workflow development built on Eclipse Theia. It supports SwarmGraph and LangGraph workflows with execution, tracing, and workspace detection features.

**Q: What's the difference between ARC Studio and SwarmGraph?**
A: SwarmGraph is a CLI tool for executing agent workflows. ARC Studio is an IDE that integrates SwarmGraph (and other runtimes) with a visual interface for execution, tracing, and workflow management.

**Q: Is ARC Studio free?**
A: Yes. ARC Studio is licensed under EPL-2.0 OR GPL-2.0 WITH Classpath-exception-2.0.

### Setup

**Q: Do I need Python to use ARC Studio?**
A: Python >= 3.11 is required for the optional daemon and LangGraph support. The core browser app works with just Node.js and pnpm.

**Q: Do I need SwarmGraph installed?**
A: Yes, to execute SwarmGraph workflows. Install from https://github.com/Hansuqwer/SwarmGraph. The stub backend works without SwarmGraph for testing.

**Q: Can I use ARC Studio without internet?**
A: Yes, the stub backend works offline. The gateway backend requires internet for LLM provider access.

### Usage

**Q: Where are traces stored?**
A: In `.arc/traces/` directory in your workspace root. Each trace is a `.jsonl` file.

**Q: How do I clean up old traces?**
A: Manually delete trace files:
```bash
find .arc/traces/ -name "*.jsonl" -mtime +7 -delete
```

**Q: Can I export traces?**
A: Trace files are plain JSONL. Copy them from `.arc/traces/` to share or archive.

**Q: How long can my prompt be?**
A: Maximum 10,000 characters. Empty prompts are rejected with a warning.

**Q: What happens if execution times out?**
A: The default timeout is 5 minutes. On timeout, the subprocess receives SIGTERM, then SIGKILL if it doesn't exit.

### Features

**Q: What workflow types are supported?**
A: Currently SwarmGraph (full support) and LangGraph (detection + dynamic workflow export). CrewAI, OpenAI Agents SDK, and AG2 are planned.

**Q: Can I run multiple workflows at once?**
A: There's no built-in concurrency limit, but running many workflows simultaneously may overwhelm your system.

**Q: Does ARC Studio support real-time trace streaming?**
A: The `streamTrace()` API method supports streaming trace events. The UI currently loads complete traces.

**Q: Can I cancel a running workflow?**
A: The `cancelWorkflow` API sends SIGTERM to the subprocess. A UI cancel button is not yet implemented.

### Troubleshooting

**Q: Why does the ARC panel show mock data?**
A: This is expected when the Python daemon is not running. Start it with `cd python && uv run arc serve`.

**Q: Why are keyboard shortcuts not working?**
A: Click inside the ARC widget first to give it focus, then try the shortcut.

**Q: Why is the build so large?**
A: Development builds include source maps (~521 MB). Production builds are ~38 MB.

### Development

**Q: How do I contribute?**
A: See the [Development Guide](DEVELOPMENT.md) and [Contributing](../README.md#contributing) section.

**Q: What's the current development phase?**
A: Phase 6 (Alpha Acceptance) is in progress. Phase 7 (Final Handover) is next.

**Q: Where do I report bugs?**
A: Create an issue at https://github.com/Hansuqwer/arc-theia-studio/issues

---

## See Also

| Document | Description |
|----------|-------------|
| [Quick Start](QUICKSTART.md) | 5-minute setup guide |
| [Feature Walkthrough](WALKTHROUGH.md) | Step-by-step feature guides |
| [Development Guide](DEVELOPMENT.md) | Setup and development |
| [API Reference](API.md) | REST API and JSON-RPC |
| [Architecture](ARCHITECTURE.md) | System architecture |
| [Troubleshooting](TROUBLESHOOTING.md) | Common issues and solutions |
| [Security](SECURITY.md) | Security implementation |
| [Deployment](DEPLOYMENT.md) | Production deployment |
| [Testing](TESTING.md) | Test setup |
| [Roadmap](ROADMAP.md) | Future plans |
