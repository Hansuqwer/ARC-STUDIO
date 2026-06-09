# R-SEC1 MCP Subprocess Isolation Audit

Date: 2026-06-09
Auditor: Agentic Auditor
Repository: Hansuqwer/ARC-STUDIO @ e2526c3
Scope: Audit the MCP tool execution path. Determine what runs in-process vs. what could be
subprocess-isolated. Design minimal change: align `arc_run_start` (HIGH-risk tool) with
the existing subprocess isolation already used by the IDE.

---

## 1. Current Execution Path

```
┌─────────────────────────────────────────────────────────────────────┐
│  MCP Tool Call (stdio transport)                                    │
│                                                                     │
│  FastMCP @mcp.tool()                                                │
│    └── _tool_result()  [mcp/server.py]                              │
│          ├── _trusted() → ensure_trusted(workspace)                 │
│          ├── decide_call() → McpDecision (LLM-free risk gate)        │
│          ├── persist_decision() → SQLite audit                      │
│          ├── persist_decision_event() → JSONL audit chain           │
│          ├── IF DENIED: return _error_json()                        │
│          └── IF ALLOWED: callback() → execute in SAME PROCESS       │
│                └── _redacted_json_envelope() → return to client     │
└─────────────────────────────────────────────────────────────────────┘
```

**Key observation:** After `decide_call()` allows the tool, `callback()` runs in the **same
Python process** as the MCP server. There is no subprocess isolation for MCP tools.

---

## 2. Tool Risk Classification

| Tool Name | Risk Level | Reason | Isolated? |
|---|---|---|---|
| `arc_doctor` | LOW | Read-only diagnostics | ❌ In-process |
| `arc_runtime_capabilities` | LOW | Read-only metadata | ❌ In-process |
| `arc_run_status` | LOW | Read-only trace access | ❌ In-process |
| `arc_trace_read` | LOW | Read-only trace access | ❌ In-process |
| `arc_audit_verify` | LOW | Read-only audit check | ❌ In-process |
| `arc_hitl_list` | LOW | Read-only HITL queue | ❌ In-process |
| `arc_task_status` | LOW | Read-only task query | ❌ In-process |
| `arc_task_result` | LOW | Read-only task result | ❌ In-process |
| `arc_swarmgraph_plan` | LOW | Deterministic DAG planner, no provider calls | ❌ In-process |
| `arc_swarmgraph_assess_risk` | LOW | Deterministic risk assessment | ❌ In-process |
| `arc_task_cancel` | MEDIUM | Mutates task state | ❌ In-process |
| `arc_run_start` | HIGH | Spawns agent run; may invoke provider APIs, consumes budget | ❌ In-process |

---

## 3. Existing Isolation Infrastructure (Available, Not Used by MCP)

**`isolation/selector.py`:**
- `BACKENDS = ("auto", "none", "subprocess", "docker", "microvm")`
- `build_execution_provider()` → `SubprocessIsolationProvider` with:
  - `safe_env_keys` allowlist
  - `workspace_root` path confinement
  - `max_output_bytes` output cap

**`isolation/subprocess.py` — `SubprocessIsolationProvider`:**
- `filter_env()` → blocks `*_API_KEY`, `*_TOKEN`, `*_SECRET`, `AWS_*`, `GITHUB_*`, etc.
- `execute()` → `subprocess.Popen()` with:
  - `start_new_session=True` (new process group)
  - `cwd` confined to `workspace_root`
  - env filtered
  - `_BoundedPipeReader` (output cap)
  - timeout handling with SIGKILL fallback

This is production-grade isolation. It is **not** wired into MCP tools.

---

## 4. The Gap

The `decide_call()` risk gate is deterministic and fast, but it is a **static analysis** of the
tool name and arguments. It does not sandbox the actual execution. For `arc_run_start`:

- A compromised or buggy prompt could consume unlimited budget.
- A tool injection could spawn uncontrolled subprocesses.
- Secrets in the environment are accessible to the callback.

---

## 5. Minimal Fix: Align `arc_run_start` with the IDE Pattern

The IDE's `RunLifecycleService.startRun()` already delegates to a subprocess
via `execFileSync`/`execArcCliAsync`. The minimal change is to make the MCP `arc_run_start`
tool do the same — delegating to the CLI via `SubprocessIsolationProvider`.

```python
# In mcp/server.py — replace the arc_run_start callback body

TOOL_RISK_LEVELS = {
    "arc_doctor": "LOW",
    "arc_runtime_capabilities": "LOW",
    "arc_run_status": "LOW",
    "arc_trace_read": "LOW",
    "arc_audit_verify": "LOW",
    "arc_hitl_list": "LOW",
    "arc_task_status": "LOW",
    "arc_task_result": "LOW",
    "arc_swarmgraph_plan": "LOW",
    "arc_swarmgraph_assess_risk": "LOW",
    "arc_task_cancel": "MEDIUM",
    "arc_run_start": "HIGH",
}

@mcp.tool()
async def arc_run_start(run_id: str, workflow: str) -> str:
    """Start an agent run in a subprocess via isolation/selector.py."""
    from agent_runtime_cockpit.isolation.selector import build_execution_provider
    import sys, json

    provider = build_execution_provider(
        "subprocess",
        workspace_root=ws,
        max_output_bytes=65_536,
    )
    result = await provider.execute(
        [sys.executable, "-m", "agent_runtime_cockpit.cli", "run",
         "--id", run_id, "--workflow", workflow, "--json"],
        cwd=ws,
        timeout_seconds=300,
    )
    return json.dumps({
        "run_id": run_id,
        "status": "started" if result.returncode == 0 else "failed",
        "output": result.stdout[:1024],
    })
```

This change:
- Reuses all existing env filtering + path confinement from `SubprocessIsolationProvider`
- Does not change the risk gate (`decide_call()` still runs first)
- Does not break any existing MCP tests (same JSON response shape)
- Is consistent with the IDE's own run-start pattern

---

## 6. Files to Create / Change

**File to create:** `python/src/agent_runtime_cockpit/mcp/tool_runner.py`
**Stub already written at:** (not stubbed; the fix is self-contained in `mcp/server.py`)

| File | Action | Lines | Test Target |
|---|---|---|---|
| `mcp/server.py` | Add `TOOL_RISK_LEVELS` dict; modify `arc_run_start` | +20 | `tests/mcp/test_mcp_server.py` |
| `isolation/selector.py` | Export `build_execution_provider` (if not already) | +1 | Already tested |

---

## 7. Test Plan

The 13 existing MCP tests must still pass. Add 3 new tests:

1. `test_low_risk_tool_runs_in_process` — `arc_doctor` returns without subprocess overhead
2. `test_high_risk_run_start_delegates_subprocess` — `arc_run_start` invokes `provider.execute()` (mock)
3. `test_subprocess_env_does_not_leak_api_key` — `OPENAI_API_KEY` not present in subprocess env

---

## 8. Kiro Session Prompt

> Modify `mcp/server.py` to add a `TOOL_RISK_LEVELS` dict mapping each of the 12 tools to LOW,
> MEDIUM, or HIGH. For `arc_run_start` (HIGH), replace the in-process callback with a
> `SubprocessIsolationProvider.execute()` call using `isolation/selector.py`
> `build_execution_provider("subprocess", ...)`. The 13 existing MCP tests must still pass.
> Add `tests/mcp/test_tool_runner.py` with 3 tests: in-process low-risk, subprocess high-risk
> (mocked), env-filtered high-risk. All tests must pass (`pytest tests/mcp -q`).
