# ARC Studio Quick Start Guide

**Get up and running with ARC Studio in 5 minutes.**

---

## Prerequisites

Before you begin, ensure you have:

- **Node.js** >= 18.0.0 — `node --version`
- **pnpm** >= 8.0.0 — `pnpm --version`
- **Python** >= 3.11 — `python --version`
- **Git** — `git --version`
- **SwarmGraph CLI** (optional, for workflow execution) — `which swarmgraph`

---

## 5-Minute Setup

### Step 1: Clone the Repository

```bash
git clone https://github.com/Hansuqwer/arc-theia-studio.git
cd arc-theia-studio
git checkout build/no-mockups-handoff
```

### Step 2: Check Environment

```bash
bash scripts/check-env.sh
```

This verifies all prerequisites are met.

### Step 3: Install Dependencies

```bash
bash scripts/bootstrap-dev.sh
```

This runs `pnpm install` and `pnpm build` to set up the full development environment.

### Step 4: Start the Application

```bash
pnpm start:browser
```

### Step 5: Open in Browser

Navigate to **http://localhost:3000**

ARC Studio loads as an Eclipse Theia IDE in your browser.

---

## First Workflow Execution

### Open the ARC Studio Panel

1. Look for the **ARC Studio** icon in the left activity bar (project-diagram icon)
2. Click it to open the ARC Studio side panel

### Execute Your First Workflow

1. In the **Workflow Execution** section, find the prompt input field
2. Enter a prompt, e.g.: `What is 2+2?`
3. Click **Execute Workflow** or press `Ctrl+Enter` (`⌘+Enter` on Mac)
4. Watch the progress bar and execution steps:
   - Parsing prompt
   - Planning execution
   - Executing workflow
   - Recording trace
   - Finalizing results
5. When complete, you'll see:
   - Run ID (e.g., `run-sg-abc123`)
   - Trace file path
   - Execution time

### View the Trace

1. Scroll to the **Trace Viewer** section
2. Click **Load Traces**
3. Your executed workflow's trace appears in the list
4. Click on a trace to select it
5. Trace details show status, ID, and timestamp

---

## Key Features Overview

### Workflow Execution

- Execute SwarmGraph workflows with natural language prompts
- Real-time progress tracking with step-by-step visualization
- Execution results with run ID and trace path
- Support for gateway (real LLM) and stub (testing) backends

### Trace Visualization

- Browse all execution traces from `.arc/traces/`
- Filter traces by run ID
- View trace metadata: status, timestamp, event count
- JSONL format for streaming-friendly, human-readable traces

### Workspace Scanning

- Automatic detection of SwarmGraph and LangGraph workflows
- Scans for CLI installations and StateGraph definitions
- Displays workflow type, name, and path

### Security

- Input sanitization for all user prompts
- Path traversal prevention
- Workspace boundary enforcement
- Subprocess isolation with `shell: false`

---

## Keyboard Shortcuts Reference

| Action | Windows/Linux | Mac |
|--------|--------------|-----|
| Execute Workflow | `Ctrl+E` | `⌘+E` |
| Load Traces | `Ctrl+L` | `⌘+L` |
| Scan Workspace | `Ctrl+S` | `⌘+S` |
| Show Shortcuts Help | `Ctrl+H` | `⌘+H` |
| Execute from Input | `Ctrl+Enter` | `⌘+Enter` |
| Close Modal / Retry | `Esc` | `Esc` |

**Tip:** Press `Ctrl+H` (`⌘+H`) at any time to see the shortcuts help modal.

---

## Optional: Start the Python Daemon

For real data (instead of mock data), start the ARC daemon:

```bash
cd python
uv run arc serve
```

The daemon runs on `http://localhost:7777`. Theia auto-detects it on startup.

---

## Links to Full Documentation

| Document | Description |
|----------|-------------|
| [User Guide](USER_GUIDE.md) | Complete user documentation |
| [Feature Walkthrough](WALKTHROUGH.md) | Step-by-step feature guides |
| [Development Guide](DEVELOPMENT.md) | Setup and development workflow |
| [API Reference](API.md) | REST API and JSON-RPC protocol |
| [Architecture](ARCHITECTURE.md) | System architecture and components |
| [Troubleshooting](TROUBLESHOOTING.md) | Common issues and solutions |
| [Security](SECURITY.md) | Security implementation details |
| [Testing](TESTING.md) | Test setup and execution |
| [Deployment](DEPLOYMENT.md) | Production deployment guide |
| [Roadmap](ROADMAP.md) | Future development plans |

---

## Next Steps

1. Read the [Feature Walkthrough](WALKTHROUGH.md) for detailed feature usage
2. Explore the [User Guide](USER_GUIDE.md) for comprehensive documentation
3. Check [Troubleshooting](TROUBLESHOOTING.md) if you encounter issues
4. Visit [Development Guide](DEVELOPMENT.md) to contribute code
