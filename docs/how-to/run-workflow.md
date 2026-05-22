# How to Run a Workflow

**Goal:** Execute an agent workflow using ARC Studio.

**Time:** 2-5 minutes  
**Prerequisites:**
- ARC Studio installed
- Workspace with a workflow file
- Provider configured (optional, for real runs)

---

## Quick Start

Run the built-in test workflow:

```bash
cd python
uv run arc run wf-swarmgraph-fixture
```

This runs a fake/offline workflow (no provider calls, no cost).

---

## Step 1: Find Available Workflows

List workflows in your workspace:

```bash
uv run arc workflows
```

Output shows:
- Workflow ID
- Runtime (swarmgraph, langgraph, crewai)
- File path
- Status (can_run: true/false)

**Example output:**
```
Workflows:
  wf-swarmgraph-fixture (swarmgraph) — can_run: true
    /path/to/workflow.py
  
  my-crew (crewai) — can_run: false
    /path/to/crew.py
    Reason: CrewAI not installed
```

---

## Step 2: Run a Workflow (CLI)

### Basic Run

```bash
uv run arc run <workflow-id>
```

**Example:**
```bash
uv run arc run wf-swarmgraph-fixture
```

### Run with Options

```bash
uv run arc run <workflow-id> \
  --runtime swarmgraph \
  --profile local-safe \
  --runtime-mode fake
```

**Options:**
- `--runtime`: Runtime to use (swarmgraph, langgraph, crewai)
- `--profile`: Security profile (local-safe, local-paid)
- `--runtime-mode`: Execution mode (fake, gated_local, provider_backed)
- `--allow-paid-calls`: Allow paid provider calls (requires paid profile)
- `--isolation`: Isolation provider (subprocess, none, docker)

---

## Step 3: Run a Workflow (IDE)

### From the Chat Tab

1. Open ARC Studio in browser: `pnpm start:browser:arc`
2. Click the ARC icon in the left sidebar
3. Go to the **Chat** tab
4. Select runtime and profile
5. Type your prompt
6. Click **Run** or press Enter

### From the Workflows Tab

1. Go to the **Workflows** tab
2. Select a workflow from the list
3. Click **Run Workflow**
4. Configure options (runtime, profile, mode)
5. Click **Execute**

---

## Step 4: Monitor Execution

### CLI Output

The CLI shows:
- Run ID
- Runtime used
- Execution status
- Duration
- Trace file path

**Example:**
```
Running workflow wf-swarmgraph-fixture
Runtime: swarmgraph (fake/offline)
Run ID: abc123def456
Status: completed
Duration: 0.42s
Trace: /path/to/.arc/traces/abc123def456.jsonl
```

### IDE Output

The IDE shows:
- Real-time event stream
- Progress bar
- Execution steps
- Run timeline

---

## Step 5: Check Run Status

### List Recent Runs

```bash
uv run arc runs search
```

### Get Run Details

```bash
uv run arc runs status <run-id>
```

### View Run Receipt

```bash
uv run arc runs receipt <run-id>
```

---

## Runtime Modes

ARC Studio supports three runtime modes:

### fake (Offline, No Cost)

```bash
uv run arc run <workflow-id> --runtime-mode fake
```

- **No provider calls:** Uses fake/mocked responses
- **No cost:** Free to run
- **Fast:** No network latency
- **Use for:** Testing, development, CI/CD

### gated_local (Local, Gated)

```bash
uv run arc run <workflow-id> --runtime-mode gated_local
```

- **Local execution:** Runs on your machine
- **Gated:** Requires explicit opt-in via environment variables
- **Provider calls:** May call providers (check workflow)
- **Use for:** Local testing with real providers

**Required environment variables:**
```bash
export ARC_REAL_RUNTIME_SMOKE=1
export ARC_LANGGRAPH_SWARMGRAPH_REAL=1
```

### provider_backed (Cloud, Production)

```bash
uv run arc run <workflow-id> --runtime-mode provider_backed
```

- **Cloud execution:** Runs on provider infrastructure
- **Real provider calls:** Uses real LLM APIs
- **Cost:** Charges apply
- **Use for:** Production workloads

**Note:** Provider-backed mode is not yet fully implemented. Use `gated_local` for now.

---

## Profiles

Profiles control what a workflow can do:

### local-safe (Default)

```bash
uv run arc run <workflow-id> --profile local-safe
```

- **No paid calls:** Blocks provider API calls
- **No network:** Blocks network access
- **No shell:** Blocks shell commands
- **No secrets:** Blocks secret access
- **Use for:** Untrusted workflows, testing

### local-paid

```bash
uv run arc run <workflow-id> --profile local-paid --allow-paid-calls
```

- **Paid calls allowed:** Can call provider APIs
- **Network allowed:** Can make network requests
- **Shell blocked:** Still blocks shell commands
- **Secrets blocked:** Still blocks secret access
- **Use for:** Trusted workflows with provider access

**Important:** Must pass `--allow-paid-calls` flag explicitly.

---

## Troubleshooting

### "Workflow not found"

**Problem:** `arc run` fails with "Workflow not found: xyz"

**Solution:**
1. List available workflows: `uv run arc workflows`
2. Use the exact workflow ID from the list
3. Check the workflow file exists and is valid

---

### "Runtime not detected"

**Problem:** Workflow shows `can_run: false` with "Runtime not detected"

**Solution:**
1. Install the required runtime:
   ```bash
   # For SwarmGraph
   uv pip install swarmgraph
   
   # For LangGraph
   uv pip install langgraph
   
   # For CrewAI
   uv pip install crewai
   ```
2. Run `uv run arc doctor all` to verify installation
3. Check `uv run arc runtimes` to see detected runtimes

---

### "Profile blocked"

**Problem:** Run fails with "Profile blocked" or "Paid calls not allowed"

**Solution:**
1. Use a paid profile: `--profile local-paid`
2. Add the `--allow-paid-calls` flag
3. Or use fake mode: `--runtime-mode fake`

---

### "Gated local requires environment variables"

**Problem:** Run fails with "Set ARC_REAL_RUNTIME_SMOKE=1..."

**Solution:**
1. Set the required environment variables:
   ```bash
   export ARC_REAL_RUNTIME_SMOKE=1
   export ARC_LANGGRAPH_SWARMGRAPH_REAL=1
   ```
2. Or use fake mode: `--runtime-mode fake`

---

### "Provider not configured"

**Problem:** Run fails with "Provider not configured" or "API key missing"

**Solution:**
1. Configure a provider: [How to Configure a Provider](./configure-provider.md)
2. Or use fake mode: `--runtime-mode fake`

---

### Run hangs or times out

**Problem:** Run never completes, hangs indefinitely

**Solution:**
1. Cancel the run: Press Ctrl+C (CLI) or click Cancel (IDE)
2. Check the trace for errors: `uv run arc runs export <run-id>`
3. Check the workflow code for infinite loops
4. Increase timeout if needed (not yet configurable)

---

## Next Steps

After running a workflow:

- **[Inspect the trace](./inspect-trace.md)** to see what happened
- **[View the receipt](./inspect-trace.md#view-receipt)** for run summary
- **[Respond to HITL prompts](./respond-hitl.md)** if the workflow requests approval
- **[Compare runs](./compare-runs.md)** to see differences

---

## Related Documentation

- **[Getting Started](../tutorials/getting-started.md)** — First workflow tutorial
- **[Runtime Reference](../reference/runtimes.md)** — All supported runtimes
- **[Profile Reference](../reference/profiles.md)** — Security profiles
- **[Error Codes](../reference/error-codes.md)** — Run-related error codes
