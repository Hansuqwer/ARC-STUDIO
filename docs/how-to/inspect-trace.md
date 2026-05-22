# How to Inspect a Trace

**Goal:** View and analyze a workflow execution trace to understand what happened.

**Time:** 5-10 minutes  
**Prerequisites:**
- A completed workflow run
- Run ID from the execution

---

## Quick Start

View a trace in the terminal:

```bash
cd python
uv run arc runs export <run-id>
```

This shows all events from the run in JSON format.

---

## Step 1: Find Your Run

### List Recent Runs

```bash
uv run arc runs search
```

Output shows:
- Run ID
- Status (completed, failed, cancelled)
- Workflow ID
- Runtime
- Timestamp

### Search by Status

```bash
uv run arc runs search --status completed
uv run arc runs search --status failed
```

### Search by Runtime

```bash
uv run arc runs search --runtime swarmgraph
```

---

## Step 2: View Run Summary

Get a quick overview:

```bash
uv run arc runs status <run-id>
```

**Output includes:**
- Run ID and status
- Workflow ID and runtime
- Start and end time
- Duration
- Event count
- Trace file path

**Example:**
```
Run: abc123def456
Status: completed
Workflow: wf-swarmgraph-fixture
Runtime: swarmgraph
Started: 2026-05-22 05:00:00
Completed: 2026-05-22 05:00:42
Duration: 42.3s
Events: 127
Trace: /path/to/.arc/traces/abc123def456.jsonl
```

---

## Step 3: View Run Receipt

Get a detailed summary with verification:

```bash
uv run arc runs receipt <run-id>
```

**Receipt includes:**
- Run metadata (ID, workflow, runtime, status)
- Execution timeline (start, end, duration)
- Event summary (total events, event types)
- Cost summary (if provider calls were made)
- Audit chain reference (if audit is enabled)
- HMAC signature (for verification)

**Export receipt to file:**

```bash
uv run arc runs receipt <run-id> --output receipt.json
```

**Export as Markdown:**

```bash
uv run arc runs receipt <run-id> --format markdown --output receipt.md
```

---

## Step 4: View Trace Events

### Export All Events

```bash
uv run arc runs export <run-id>
```

This prints all events as JSON to stdout.

### Export to File

```bash
uv run arc runs export <run-id> > trace.json
```

### View Specific Event Types

The trace contains different event types:
- `RUN_STARTED` — Run began
- `RUN_FINISHED` — Run completed
- `AGENT_TEXT` — Agent generated text
- `TOOL_CALL_START` — Tool invocation started
- `TOOL_CALL_RESULT` — Tool returned result
- `LLM_REQUEST` — LLM API request
- `LLM_RESPONSE` — LLM API response
- `ERROR` — Error occurred

**Filter events with jq:**

```bash
# Show only tool calls
uv run arc runs export <run-id> | jq 'select(.type == "TOOL_CALL_START")'

# Show only errors
uv run arc runs export <run-id> | jq 'select(.type == "ERROR")'

# Count events by type
uv run arc runs export <run-id> | jq -r '.type' | sort | uniq -c
```

---

## Step 5: Inspect in the IDE

### View in Runs Tab

1. Open ARC Studio: `pnpm start:browser:arc`
2. Click the ARC icon in the left sidebar
3. Go to the **Runs** tab
4. Select your run from the list
5. View:
   - Run receipt card
   - Failure autopsy (if failed)
   - Run contract
   - Audit chain info

### View Timeline

1. Open the **Run Timeline** widget
2. Select your run
3. See:
   - Execution timeline
   - Event sequence
   - Agent interactions
   - Tool calls

### View Event Stream

1. Open the **Event Stream** widget
2. Select your run
3. See:
   - Real-time event feed
   - Event details
   - Timestamps
   - Event metadata

---

## Step 6: Analyze Failures

If a run failed, get the autopsy:

```bash
uv run arc runs autopsy <run-id>
```

**Autopsy includes:**
- Probable cause (why it failed)
- Error message
- Error code
- Stack trace (if available)
- Remediation steps
- Related events

**Example output:**
```
Failure Autopsy: abc123def456
Probable cause: TOOL_EXECUTION_FAILED
Error: Tool 'read_file' failed: File not found
Error code: TOOL_ERROR
Remediation:
  1. Check that the file path is correct
  2. Verify the file exists in the workspace
  3. Check file permissions
Related events: 3 events before failure
```

---

## Step 7: View Audit Chain

If audit is enabled, verify the audit chain:

```bash
uv run arc audit verify <run-id>
```

**Output:**
- Verification status (verified/failed)
- Event count
- Chain integrity
- HMAC signature status

**Export audit bundle:**

```bash
uv run arc audit export <run-id> --format json > audit-bundle.json
```

---

## Step 8: Compare Runs

Compare two runs to see differences:

```bash
uv run arc runs diff <run-id-a> <run-id-b>
```

**Diff shows:**
- Status differences
- Event count differences
- Duration differences
- Event type distribution
- Tool usage differences

**Example output:**
```
Run Diff:
  Run A: abc123 (completed, 42s, 127 events)
  Run B: def456 (completed, 38s, 115 events)

Differences:
  - Duration: 42s vs 38s (4s faster)
  - Events: 127 vs 115 (12 fewer events)
  - Tool calls: 15 vs 12 (3 fewer calls)
  - Status: both completed
```

---

## Understanding Trace Format

Traces are stored as JSONL (JSON Lines):
- One event per line
- Each event is a JSON object
- Events are ordered chronologically

**Example event:**

```json
{
  "type": "TOOL_CALL_START",
  "timestamp": "2026-05-22T05:00:15.123Z",
  "runId": "abc123def456",
  "threadId": "th-abc123",
  "toolCallId": "call_xyz",
  "toolName": "read_file",
  "args": {
    "path": "README.md"
  }
}
```

**Common fields:**
- `type` — Event type
- `timestamp` — When it happened (ISO 8601)
- `runId` — Run identifier
- `threadId` — Thread identifier
- Event-specific fields (vary by type)

---

## Troubleshooting

### "Run not found"

**Problem:** `arc runs export` fails with "Run not found: xyz"

**Solution:**
1. Check the run ID is correct
2. List available runs: `uv run arc runs search`
3. Verify the trace file exists: `ls ~/.arc/traces/`

---

### "Trace file corrupted"

**Problem:** Trace export fails with "Parse error" or "Invalid JSON"

**Solution:**
1. Check the trace file directly:
   ```bash
   cat ~/.arc/traces/<run-id>.jsonl
   ```
2. Look for malformed JSON lines
3. If corrupted, the run may have crashed mid-execution
4. Check system logs for errors

---

### "Empty trace"

**Problem:** Trace has 0 events

**Solution:**
1. Check if the run actually started
2. Check run status: `uv run arc runs status <run-id>`
3. If status is "pending" or "running", the run may still be in progress
4. If status is "failed", check the autopsy

---

### "Audit verification failed"

**Problem:** `arc audit verify` fails with "Chain integrity check failed"

**Solution:**
1. Check if the audit key is available:
   ```bash
   uv run arc audit key show
   ```
2. If key is missing, verification will fail
3. If key exists but verification fails, the trace may have been tampered with
4. Check audit chain details for specific failure reason

---

### "Receipt not found"

**Problem:** `arc runs receipt` fails with "Receipt not found"

**Solution:**
1. Receipts are generated after run completion
2. If run is still in progress, wait for completion
3. If run completed but no receipt, it may be an old run (receipts added in v0.2)
4. Re-run the workflow to generate a receipt

---

## Advanced: Raw Trace Analysis

### Count Events by Type

```bash
uv run arc runs export <run-id> | \
  jq -r '.type' | \
  sort | \
  uniq -c | \
  sort -rn
```

### Extract Tool Calls

```bash
uv run arc runs export <run-id> | \
  jq 'select(.type == "TOOL_CALL_START") | {tool: .toolName, args: .args}'
```

### Calculate Duration

```bash
uv run arc runs export <run-id> | \
  jq -r 'select(.type == "RUN_STARTED" or .type == "RUN_FINISHED") | .timestamp'
```

### Find Errors

```bash
uv run arc runs export <run-id> | \
  jq 'select(.type == "ERROR" or .type == "TOOL_CALL_ERROR")'
```

### Extract LLM Costs

```bash
uv run arc runs export <run-id> | \
  jq 'select(.type == "LLM_RESPONSE") | .cost'
```

---

## Next Steps

After inspecting a trace:

- **[Compare with another run](./compare-runs.md)** to see differences
- **[Respond to HITL prompts](./respond-hitl.md)** if the run requested approval
- **[Export to OTel](./export-otel.md)** for observability platforms
- **[Replay the run](./replay-run.md)** to reproduce behavior

---

## Related Documentation

- **[Trace Format Reference](../reference/trace-format.md)** — Event schema and types
- **[Audit Chain Architecture](../adr/021-audit-chain-architecture.md)** — How audit chains work
- **[Error Codes](../reference/error-codes.md)** — Error codes in traces
- **[Run Receipts](../reference/run-receipts.md)** — Receipt format and verification
