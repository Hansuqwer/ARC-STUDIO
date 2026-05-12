# Adapter Development Guide

This guide documents the adapter pattern used in ARC Studio for integrating agent frameworks. All adapters follow a consistent structure that provides dual-gated execution, audit chain integration, and AG-UI event mapping.

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Adapter Structure](#adapter-structure)
3. [Core Components](#core-components)
4. [Step-by-Step Implementation](#step-by-step-implementation)
5. [Testing Strategy](#testing-strategy)
6. [Security Considerations](#security-considerations)
7. [Examples](#examples)

---

## Architecture Overview

### Event Flow

```
Native Runtime Events → Adapter Mapping → AG-UI Events → JSONL Trace + Audit Chain
```

### Key Principles

1. **Dual-Gate Security** - Prevents accidental costs via two-factor confirmation
2. **Audit Chain** - SHA-256 hash-chained tamper-evident logs
3. **Runtime-Agnostic Events** - 18 AG-UI event types work across all frameworks
4. **Consistent Structure** - All adapters follow the same pattern

---

## Adapter Structure

Every adapter follows this directory structure:

```
python/src/agent_runtime_cockpit/adapters/<runtime>/
├── __init__.py           # Package marker
├── runner.py             # Main execution logic with dual-gating
├── mapping.py            # Native → AG-UI event mapping
└── detect.py             # Workspace detection logic
```

### Optional Components

- `listener.py` - Event bus subscriber (e.g., CrewAI)
- `loader.py` - Configuration loading (e.g., LangGraph)
- `streaming.py` - Streaming bridge (e.g., OpenAI Agents)
- `gateway_client.py` - Remote execution client (e.g., SwarmGraph)
- `local_executor.py` - In-process execution (e.g., SwarmGraph)

---

## Core Components

### 1. Runner (`runner.py`)

The runner is the main entry point for adapter execution. It:
- Enforces dual-gate security
- Manages trace and audit file creation
- Orchestrates event flow from native runtime to AG-UI
- Handles errors and lifecycle events

**Template:**

```python
"""<Runtime> runner. Real execution gated; events mapped to AG-UI."""
from __future__ import annotations

import pathlib
import uuid
from typing import Any

from agent_runtime_cockpit.ag_ui import MappingContext, map_event
from agent_runtime_cockpit.audit.chain import AuditChainWriter
from agent_runtime_cockpit.gating import require_dual_gate
from agent_runtime_cockpit.tracing.jsonl_writer import JsonlTraceWriter

from . import mapping  # noqa: F401 - registers mapper


class <Runtime>Runner:
    def __init__(self, workspace: pathlib.Path) -> None:
        self.workspace = workspace

    async def run(self, entrypoint: str, inputs: dict[str, Any]) -> str:
        # 1. Enforce dual-gate
        require_dual_gate("<RUNTIME>")
        
        # 2. Generate run ID
        run_id = uuid.uuid4().hex[:12]
        ctx = MappingContext(
            thread_id=f"th-{run_id}",
            run_id=run_id,
            runtime="<runtime>"
        )

        # 3. Setup trace and audit files
        traces = self.workspace / ".arc" / "traces" / f"{run_id}.jsonl"
        audit = self.workspace / ".arc" / "audit" / f"{run_id}.chain.jsonl"
        traces.parent.mkdir(parents=True, exist_ok=True)
        audit.parent.mkdir(parents=True, exist_ok=True)

        # 4. Execute and map events
        with JsonlTraceWriter(traces) as t, AuditChainWriter(audit) as a:
            async for native_event in self._execute(entrypoint, inputs):
                for ag_event in map_event("<runtime>", native_event, ctx):
                    t.write(ag_event)
                    a.append(ag_event)
        
        return run_id

    async def _execute(self, entrypoint: str, inputs: dict[str, Any]):
        """Execute runtime and yield native events."""
        # Implementation specific to runtime
        pass
```

### 2. Mapping (`mapping.py`)

The mapping module converts native runtime events to AG-UI events.

**Template:**

```python
"""Native <Runtime> → AG-UI mapping."""
from __future__ import annotations

import time
from typing import Any

from agent_runtime_cockpit.ag_ui import AGUIEventType, MappingContext, register_mapper


def _map(native: dict[str, Any], ctx: MappingContext) -> list[dict[str, Any]]:
    """Map native event to AG-UI events.
    
    Args:
        native: Native runtime event
        ctx: Mapping context with thread_id, run_id, runtime
    
    Returns:
        List of AG-UI events (may be empty or multiple)
    """
    kind = native.get("kind")
    ts = native.get("ts", time.time())
    
    if kind == "run.start":
        return [{
            "type": AGUIEventType.RUN_STARTED.value,
            "timestamp": ts,
            "threadId": ctx.thread_id,
            "runId": ctx.run_id
        }]
    
    if kind == "run.finish":
        return [{
            "type": AGUIEventType.RUN_FINISHED.value,
            "timestamp": ts,
            "threadId": ctx.thread_id,
            "runId": ctx.run_id
        }]
    
    # Add more mappings...
    
    # Fallback: emit as RAW event
    return [{
        "type": AGUIEventType.RAW.value,
        "timestamp": ts,
        "event": native,
        "source": "<runtime>"
    }]


# Register mapper
register_mapper("<runtime>", _map)
```

### 3. Detection (`detect.py`)

Workspace detection identifies if a directory contains a project for this runtime.

**Template:**

```python
"""Detect <Runtime> workspace."""
from __future__ import annotations

import pathlib


def is_<runtime>_workspace(workspace: pathlib.Path) -> bool:
    """Check if workspace contains <Runtime> project.
    
    Args:
        workspace: Path to workspace directory
    
    Returns:
        True if workspace contains <Runtime> project markers
    """
    # Check for configuration files
    if (workspace / "<config-file>").exists():
        return True
    
    # Check for imports in Python files
    for py_file in workspace.glob("**/*.py"):
        try:
            content = py_file.read_text()
            if "from <runtime> import" in content or "import <runtime>" in content:
                return True
        except (OSError, UnicodeDecodeError):
            continue
    
    return False
```

---

## Step-by-Step Implementation

### Step 1: Create Directory Structure

```bash
mkdir -p python/src/agent_runtime_cockpit/adapters/<runtime>
touch python/src/agent_runtime_cockpit/adapters/<runtime>/__init__.py
touch python/src/agent_runtime_cockpit/adapters/<runtime>/runner.py
touch python/src/agent_runtime_cockpit/adapters/<runtime>/mapping.py
touch python/src/agent_runtime_cockpit/adapters/<runtime>/detect.py
```

### Step 2: Implement Detection

Start with `detect.py` to identify workspaces for your runtime.

### Step 3: Define Native Event Schema

Document the native events your runtime produces:

```python
# Example native events for your runtime
NATIVE_EVENTS = {
    "run.start": {"kind": "run.start", "ts": float},
    "agent.text": {"kind": "agent.text", "agent": str, "text": str, "ts": float},
    "tool.call": {"kind": "tool.call", "tool": {"id": str, "name": str, "args": dict}, "ts": float},
    # ...
}
```

### Step 4: Implement Mapping

Create `mapping.py` to convert native events to AG-UI events. Reference the AG-UI event types:

**AG-UI Event Types:**
- `RUN_STARTED`, `RUN_FINISHED`, `RUN_ERROR`, `RUN_CANCELLED`
- `STEP_STARTED`, `STEP_FINISHED`, `STEP_ERROR`
- `TEXT_MESSAGE_START`, `TEXT_MESSAGE_CONTENT`, `TEXT_MESSAGE_END`, `TEXT_MESSAGE_CHUNK`
- `TOOL_CALL_START`, `TOOL_CALL_ARGS`, `TOOL_CALL_END`, `TOOL_CALL_RESULT`, `TOOL_CALL_ERROR`
- `HANDOFF`, `CUSTOM`, `RAW`

### Step 5: Implement Runner

Create `runner.py` with dual-gate enforcement and event streaming.

### Step 6: Create Tests

```bash
mkdir -p python/tests/adapters/<runtime>
touch python/tests/adapters/<runtime>/__init__.py
touch python/tests/adapters/<runtime>/test_adapter.py
```

---

## Testing Strategy

### Test Structure

```python
"""Tests for <Runtime> adapter."""
import pathlib
import asyncio

from agent_runtime_cockpit.adapters.<runtime>.detect import is_<runtime>_workspace
from agent_runtime_cockpit.adapters.<runtime>.mapping import _map
from agent_runtime_cockpit.adapters.<runtime>.runner import <Runtime>Runner
from agent_runtime_cockpit.ag_ui import MappingContext


def test_detect_workspace(tmp_path: pathlib.Path):
    """Test workspace detection."""
    (tmp_path / "<config-file>").write_text("...")
    assert is_<runtime>_workspace(tmp_path)


def test_detect_negative(tmp_path: pathlib.Path):
    """Test negative workspace detection."""
    (tmp_path / "main.py").write_text("print('hi')")
    assert not is_<runtime>_workspace(tmp_path)


def test_mapping_lifecycle():
    """Test event mapping for full lifecycle."""
    ctx = MappingContext(thread_id="th", run_id="r1", runtime="<runtime>")
    
    # Test run start
    result = _map({"kind": "run.start"}, ctx)
    assert result[0]["type"] == "RUN_STARTED"
    
    # Test run finish
    result = _map({"kind": "run.finish"}, ctx)
    assert result[0]["type"] == "RUN_FINISHED"


def test_runner_with_fake_runtime(tmp_path, monkeypatch):
    """Test runner with fake runtime."""
    monkeypatch.setenv("ARC_<RUNTIME>_RUN_BACKEND", "local")
    monkeypatch.setenv("ARC_<RUNTIME>_ALLOW_COSTS", "true")
    
    # Create fake runtime
    (tmp_path / "runtime.py").write_text("""
        # Fake runtime implementation
    """)
    
    runner = <Runtime>Runner(tmp_path)
    run_id = asyncio.run(runner.run("runtime:obj", {}))
    
    # Verify trace file created
    trace_file = tmp_path / ".arc" / "traces" / f"{run_id}.jsonl"
    assert trace_file.exists()
    
    # Verify events
    text = trace_file.read_text()
    assert "RUN_STARTED" in text
    assert "RUN_FINISHED" in text
```

### Integration Tests

Add golden fixtures for cross-adapter conformance:

```bash
# Create golden fixture
cat > python/tests/integration/fixtures/<runtime>.golden.jsonl << 'EOF'
{"type":"RUN_STARTED","timestamp":1.0,"threadId":"th-test","runId":"test"}
{"type":"TEXT_MESSAGE_CHUNK","timestamp":2.0,"role":"assistant","delta":"Hello"}
{"type":"RUN_FINISHED","timestamp":3.0,"threadId":"th-test","runId":"test"}
EOF
```

---

## Security Considerations

### Dual-Gate Pattern

Always enforce dual-gate for non-stub backends:

```python
from agent_runtime_cockpit.gating import require_dual_gate, BackendMode

backend, allow_costs = require_dual_gate("<RUNTIME>")

if backend != BackendMode.STUB and allow_costs:
    # Emit cost warning
    warning = {
        "type": "CUSTOM",
        "name": "arc.cost_warning",
        "value": {
            "runtime": "<runtime>",
            "backend": backend.value,
            "gated_at": datetime.utcnow().isoformat() + "Z"
        }
    }
    trace.write(warning)
    audit.append(warning)
```

### Environment Variables

- `ARC_<RUNTIME>_RUN_BACKEND` - Backend mode: `stub` (default), `local`, `gateway`
- `ARC_<RUNTIME>_ALLOW_COSTS` - Must be `"true"` for non-stub backends

### Secret Redaction

Never log secrets in traces or audit chains. Test for this:

```python
def test_no_secrets_in_trace(tmp_path):
    """Verify no secrets leaked in trace."""
    import re
    
    runner = <Runtime>Runner(tmp_path)
    run_id = asyncio.run(runner.run("runtime:obj", {"api_key": "sk-secret"}))
    
    trace_file = tmp_path / ".arc" / "traces" / f"{run_id}.jsonl"
    text = trace_file.read_text()
    
    # Check for common secret patterns
    assert not re.search(r"sk-[A-Za-z0-9_-]{16,}", text)
    assert not re.search(r"ghp_[A-Za-z0-9]{20,}", text)
```

---

## Examples

### Example 1: SwarmGraph Adapter

**Key Features:**
- 3 backends: stub, local, gateway
- Real in-process execution
- Cost warnings

**Files:**
- `runner.py` - Main runner with backend selection
- `local_executor.py` - In-process execution
- `gateway_client.py` - Remote execution client
- `mapping.py` - Event mapping

### Example 2: LangGraph Adapter

**Key Features:**
- Canonical `langgraph.json` loading
- Streams via `astream_events(version="v2")`

**Files:**
- `runner.py` - Main runner
- `loader.py` - Graph loading from config
- `mapping.py` - Event mapping

### Example 3: CrewAI Adapter

**Key Features:**
- Event bus listener pattern
- 12 event types
- Async/sync execution

**Files:**
- `runner.py` - Main runner with queue
- `listener.py` - Event bus subscriber
- `mapping.py` - Event mapping

---

## Checklist

Before submitting your adapter:

- [ ] Directory structure follows pattern
- [ ] `detect.py` identifies workspaces correctly
- [ ] `mapping.py` handles all native event types
- [ ] `runner.py` enforces dual-gate
- [ ] Audit chain integration working
- [ ] Tests cover detection, mapping, and runner
- [ ] Golden fixture created
- [ ] No secrets in traces
- [ ] Documentation updated

---

## Resources

- **AG-UI Event Schema:** `python/src/agent_runtime_cockpit/ag_ui/__init__.py`
- **Gating Module:** `python/src/agent_runtime_cockpit/gating.py`
- **Audit Chain:** `python/src/agent_runtime_cockpit/audit/chain.py`
- **Existing Adapters:** `python/src/agent_runtime_cockpit/adapters/`
- **Integration Tests:** `python/tests/integration/test_multi_adapter.py`

---

## Support

For questions or issues:
1. Review existing adapters in `python/src/agent_runtime_cockpit/adapters/`
2. Check integration tests for patterns
3. Open an issue with the `adapter` label
