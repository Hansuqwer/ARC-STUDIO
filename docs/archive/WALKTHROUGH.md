# ARC Studio Feature Walkthrough

**Step-by-step guides for all ARC Studio features.**

---

## Table of Contents

1. [Workflow Execution](#workflow-execution)
2. [Trace Viewing](#trace-viewing)
3. [Workspace Scanning](#workspace-scanning)
4. [Keyboard Shortcuts](#keyboard-shortcuts)
5. [Accessibility Features](#accessibility-features)
6. [Error Handling and Recovery](#error-handling-and-recovery)

---

## Workflow Execution

### Overview

The Workflow Execution section lets you run SwarmGraph and LangGraph workflows using natural language prompts. The system handles execution, tracing, and result display automatically.

### Step-by-Step: Execute a Workflow

#### Step 1: Open ARC Studio Panel

1. Launch the application: `pnpm start:browser`
2. Open http://localhost:3000 in your browser
3. Click the **ARC Studio** icon in the left activity bar (looks like a project diagram / network graph icon)
4. The ARC Studio side panel opens on the left

> **Screenshot description:** Theia IDE with the left sidebar showing the ARC Studio icon highlighted. The panel slides open showing the ARC Studio header with "Agent Runtime Cockpit" subtitle.

#### Step 2: Enter Your Prompt

1. Locate the **Workflow Execution** section (first collapsible section)
2. Find the text input field labeled "Prompt:"
3. Type your workflow prompt, for example:
   - `What is 2+2?`
   - `Summarize the latest news about AI`
   - `Write a poem about coding`
4. The input field has a placeholder: "Enter workflow prompt..."

> **Screenshot description:** Close-up of the Workflow Execution section showing the prompt input field with "What is 2+2?" typed in. Below it, the "Execute Workflow" button is visible with a help text showing "Press Ctrl+Enter to execute or Ctrl+E".

#### Step 3: Execute the Workflow

**Option A — Click the button:**
- Click the **Execute Workflow** button

**Option B — Keyboard shortcut from input:**
- Press `Ctrl+Enter` (`⌘+Enter` on Mac) while focused on the input field

**Option C — Global keyboard shortcut:**
- Press `Ctrl+E` (`⌘+E` on Mac) from anywhere in the widget

#### Step 4: Monitor Execution Progress

While the workflow runs, you'll see:

1. **Progress bar** — fills from 0% to 100%
2. **Execution steps** — five sequential steps with status indicators:

   | Step | Indicator (Running) | Indicator (Done) | Description |
   |------|-------------------|-----------------|-------------|
   | Parsing prompt | ⟳ | ✓ | Validates and processes the input |
   | Planning execution | ⟳ | ✓ | Prepares execution environment |
   | Executing workflow | ⟳ | ✓ | Runs the SwarmGraph CLI |
   | Recording trace | ⟳ | ✓ | Writes trace to JSONL file |
   | Finalizing results | ⟳ | ✓ | Formats and displays results |

3. **Button state** — changes to "Executing..." with a spinner
4. **Status indicator** — shows "Workflow is running..." with ⏳ icon

> **Screenshot description:** The execution section mid-run showing a progress bar at 60%, with the first three steps showing ✓ (completed), the fourth showing ⟳ (in-progress), and the fifth showing ○ (pending). The button shows a spinner and "Executing..." text.

#### Step 5: View Results

On successful completion:

1. The status changes to ✓ with execution time: "Completed in 3.45s"
2. A **Execution Result** box appears showing:
   - **Run ID:** e.g., `run-sg-a1b2c3d4`
   - **Trace:** e.g., `.arc/traces/run-sg-a1b2c3d4.jsonl`
   - **Status:** Completed (green badge)
3. A toast notification appears: "Workflow completed in 3.45s"
4. Theia's message service shows an info notification

> **Screenshot description:** Completed execution showing green status bar, execution result box with run ID and trace path in code formatting, and a green success toast notification in the top-right corner.

### Execution Options

ARC Studio supports two backends:

| Backend | Use Case | API Costs |
|---------|----------|-----------|
| `gateway` | Production execution with real LLM providers | Yes |
| `stub` | Testing and development without API calls | No |

The default backend is `gateway`. Configure via the execution options in the protocol.

---

## Trace Viewing

### Overview

The Trace Viewer lets you browse and inspect execution traces stored in `.arc/traces/`. Traces use JSONL format (one JSON event per line) for streaming-friendly storage.

### Step-by-Step: Load and View Traces

#### Step 1: Load Traces

1. Scroll to the **Trace Viewer** section
2. Click the **Load Traces** button
3. A progress bar appears: "Loading traces..."
4. The system scans `.arc/traces/` for `.jsonl` files
5. A toast notification confirms: "Loaded N trace(s)"

> **Screenshot description:** Trace Viewer section with the "Load Traces" button being clicked, a progress bar at 50%, and the section header showing a badge with the trace count.

#### Step 2: Browse the Trace List

Loaded traces appear in a list with columns:

| Column | Description |
|--------|-------------|
| Status | ✓ (completed) or ✗ (failed) |
| Run ID | Unique identifier like `run-sg-abc123` |
| Timestamp | Local date and time of execution |

Traces are sorted by timestamp (newest first).

> **Screenshot description:** Trace list showing 5 traces in a table-like layout. The header row shows "Status | Run ID | Timestamp". Each row has a status icon, monospace run ID, and formatted timestamp. The most recent trace is at the top.

#### Step 3: Filter Traces

1. Locate the **Filter traces** input field above the trace list
2. Type any text to filter by run ID
3. Filtering is debounced (300ms delay for performance)
4. A clear button (×) appears when the filter is active
5. If no traces match, "No traces match the filter" is shown

> **Screenshot description:** Filter input with "abc" typed in, showing a × clear button on the right side of the input. The trace list below shows only traces containing "abc" in their ID.

#### Step 4: Select a Trace

1. Click on any trace row to select it
2. The selected row is highlighted
3. Keyboard navigation: use `Tab` to focus, `Enter` or `Space` to select
4. The trace is marked with `aria-selected="true"` for accessibility

#### Step 5: Inspect Trace File

Trace files are stored in JSONL format at `.arc/traces/{runId}.jsonl`.

View a trace file manually:

```bash
cat .arc/traces/run-sg-abc123.jsonl | jq
```

Each line is a `TraceEvent`:

```jsonl
{"type":"RUN_STARTED","timestamp":"2026-05-12T20:30:00Z","runId":"run-sg-abc123","sequence":0,"data":{}}
{"type":"NODE_COMPLETED","timestamp":"2026-05-12T20:30:10Z","runId":"run-sg-abc123","sequence":1,"data":{"nodeId":"agent-1"}}
{"type":"RUN_COMPLETED","timestamp":"2026-05-12T20:30:15Z","runId":"run-sg-abc123","sequence":2,"data":{}}
```

### Trace Event Types

| Event Type | Description |
|------------|-------------|
| `RUN_STARTED` | Workflow execution began |
| `NODE_COMPLETED` | A graph node finished execution |
| `MESSAGE` | A message was sent or received |
| `RUN_COMPLETED` | Workflow execution succeeded |
| `RUN_FAILED` | Workflow execution failed |
| `ERROR` | An error occurred during execution |

---

## Workspace Scanning

### Overview

The Workspace Detection feature scans your current workspace for SwarmGraph and LangGraph workflow definitions. It detects CLI installations and StateGraph definitions in Python files.

### Step-by-Step: Scan Your Workspace

#### Step 1: Open the Detection Section

1. Scroll to the **Workflow Detection** section in the ARC Studio panel
2. The section description reads: "Detect workflows in workspace"

#### Step 2: Start the Scan

1. Click the **Scan Workspace** button
2. A progress bar appears: "Scanning workspace..."
3. The button changes to "Scanning..." with a spinner
4. The system searches for:
   - SwarmGraph CLI installations (local, venv, npm, PATH)
   - LangGraph `StateGraph` definitions in Python files

#### Step 3: View Results

On completion:

1. A toast notification shows: "Found N workflow(s)"
2. Detected workflows appear in a list with columns:

   | Column | Description |
   |--------|-------------|
   | Type | `swarmgraph` or `langgraph` |
   | Name | Human-readable workflow name |
   | Path | Absolute path to the workflow |

> **Screenshot description:** Workflow Detection section showing scan results with 2 detected workflows. The first row shows "swarmgraph | SwarmGraph CLI | /usr/local/bin/swarmgraph". The second shows "langgraph | MyAgent | /workspace/agent.py".

#### Step 4: No Workflows Found

If no workflows are detected:

1. The message reads: "No workflows detected. Click 'Scan Workspace' to detect workflows."
2. Possible causes:
   - SwarmGraph CLI not installed or not in PATH
   - No LangGraph StateGraph definitions in the workspace
   - Workspace is empty or doesn't contain agent code

**To install SwarmGraph:**

```bash
# SwarmGraph source now lives in this repo under runtimes/swarmgraph/.
# The archived Hansuqwer/SwarmGraph repository remains available for old SHA references.
which swarmgraph  # Verify installation
```

### What Gets Detected

**SwarmGraph:**
- CLI binary in PATH
- Local installations in `node_modules/.bin/`
- Virtual environment installations

**LangGraph:**
- Python files containing `StateGraph` class instantiation
- Files with `from langgraph.graph import StateGraph` imports

---

## Keyboard Shortcuts

### All Shortcuts

| Action | Windows/Linux | Mac | Scope |
|--------|--------------|-----|-------|
| Execute Workflow | `Ctrl+E` | `⌘+E` | ARC Widget focused |
| Load Traces | `Ctrl+L` | `⌘+L` | ARC Widget focused |
| Scan Workspace | `Ctrl+S` | `⌘+S` | ARC Widget focused |
| Show Shortcuts Help | `Ctrl+H` | `⌘+H` | ARC Widget focused |
| Show Shortcuts Help (alt) | `Ctrl+?` | `⌘+?` | ARC Widget focused |
| Execute from Input | `Ctrl+Enter` | `⌘+Enter` | Prompt input focused |
| Close Modal | `Esc` | `Esc` | Modal open |
| Retry on Error | `Esc` | `Esc` | Error displayed |

### Shortcuts Help Modal

Press `Ctrl+H` (`⌘+H`) to open the keyboard shortcuts help modal:

> **Screenshot description:** A centered modal overlay with a dark semi-transparent background. The modal has a title "Keyboard Shortcuts" and a table with columns: Action, Windows/Linux, Mac. Each shortcut is shown with `<kbd>` styled keys. A close button (×) is in the top-right corner.

The modal:
- Shows all available shortcuts in a table
- Can be closed with `Esc`, the × button, or clicking outside
- Is accessible with `role="dialog"` and `aria-modal="true"`

### Shortcut Behavior Notes

- Shortcuts only work when the ARC widget has focus
- `Ctrl+S` overrides the browser's save shortcut within the widget
- `Ctrl+Enter` only works when the prompt input is focused
- `Esc` has contextual behavior: closes modal first, then dismisses errors

---

## Accessibility Features

### ARIA Attributes

ARC Studio uses comprehensive ARIA attributes for screen reader support:

| Element | ARIA Attribute | Purpose |
|---------|---------------|---------|
| Main container | `role="main"` | Identifies primary content area |
| Sections | `aria-labelledby`, `aria-expanded` | Collapsible section state |
| Progress bars | `role="progressbar"`, `aria-valuenow` | Progress indication |
| Toast notifications | `role="alert"`, `aria-live="polite"` | Notification announcements |
| Error display | `role="alert"`, `aria-live="assertive"` | Error announcements |
| Trace list | `role="listbox"`, `aria-selected` | Selection state |
| Shortcuts modal | `role="dialog"`, `aria-modal="true"` | Modal dialog |
| Loading buttons | `aria-busy="true"` | Loading state indication |
| Status updates | `role="status"`, `aria-live="polite"` | Live status updates |

### Keyboard Navigation

- All interactive elements are reachable via `Tab`
- Trace items support `Enter` and `Space` for selection
- Modal can be dismissed with `Esc`
- Section headers are buttons for collapse/expand
- Focus is managed properly within modals

### Visual Accessibility

- Color is not the only indicator of state (icons + text used)
- Progress bars have text labels
- Status indicators use both icons and text
- Error messages are descriptive and actionable
- Contrast ratios follow WCAG guidelines

### Screen Reader Support

- Toast notifications announce via `aria-live="polite"`
- Errors announce immediately via `aria-live="assertive"`
- Progress updates include percentage labels
- Trace items announce selection state changes
- Collapsible sections announce expanded/collapsed state

---

## Error Handling and Recovery

### Error Display

When an error occurs, ARC Studio displays:

1. **Error banner** at the top of the widget:
   - Warning icon (⚠)
   - Error title (bold)
   - Error details (description)
   - "Try Again" button
   - Dismiss button (×)

2. **Toast notification** (top-right corner):
   - Red toast with ✗ icon
   - Error message
   - Auto-dismisses after 5 seconds
   - Manual dismiss with × button

3. **Theia message service** notification in the status bar

> **Screenshot description:** Error banner with red/warning styling showing "⚠ Workflow execution failed" with detail text "swarmgraph command not found". Below the banner, a "Try Again" button and × dismiss button are visible. A red toast notification is in the top-right corner.

### Common Errors and Recovery

#### Workflow Execution Failed

**Cause:** SwarmGraph CLI not found or execution error

**Recovery:**
1. Click **Try Again** or press `Esc`
2. Verify SwarmGraph is installed: `which swarmgraph`
3. Check the error details for specific failure reason
4. Re-enter prompt and try again

#### Failed to Load Traces

**Cause:** `.arc/traces/` directory doesn't exist or is unreadable

**Recovery:**
1. Click **Try Again**
2. Ensure at least one workflow has been executed
3. Check directory exists: `ls .arc/traces/`
4. Verify file permissions: `ls -la .arc/traces/`

#### Failed to Scan Workspace

**Cause:** Workspace directory inaccessible

**Recovery:**
1. Click **Try Again**
2. Verify workspace is properly opened in Theia
3. Check workspace path is accessible

### Input Validation Errors

These appear as warnings (not full errors):

- **Empty prompt:** "Please enter a prompt for workflow execution"
  - Fix: Type a prompt before executing
- **Prompt too long:** Max 10,000 characters
  - Fix: Shorten your prompt

### Error States in UI

| State | Visual Indicator | Recovery |
|-------|-----------------|----------|
| Execution failed | Red status ✗, error banner | Try Again button |
| Trace load failed | Error banner, toast | Try Again button |
| Scan failed | Error banner, toast | Try Again button |
| Empty prompt | Warning toast | Enter a prompt |
| No traces | Empty state message | Execute a workflow first |
| No workflows | Empty state message | Install SwarmGraph or add LangGraph |

### Automatic Recovery

- Toast notifications auto-dismiss after 5 seconds
- Filter input clears when × is clicked
- Error state resets when "Try Again" is clicked
- Loading states prevent duplicate operations (buttons disabled during loading)
