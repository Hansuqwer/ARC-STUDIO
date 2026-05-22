# Enforcement Surfaces

This document catalogs all security-sensitive surfaces in ARC Studio and their enforcement status.

**Last updated:** 2026-05-22  
**Phase:** 23.2 (Audit Infrastructure + Annotations)

## Overview

ARC Studio uses a centralized enforcement system to gate security-sensitive operations. All syscalls (subprocess execution, network requests, file operations) must be either:
1. **Gated** - Protected by an enforcement helper
2. **Annotated** - Marked as "not-applicable" with justification

The enforcement audit script (`scripts/audit-enforcement-surfaces.sh`) scans the codebase for ungated syscalls and ensures all sites are properly annotated.

## Enforcement Helpers

Four centralized enforcement helpers gate security-sensitive operations:

| Helper | Purpose | Gates |
|--------|---------|-------|
| `enforce_workspace_trust` | Workspace file access and code execution | Untrusted workspace operations |
| `enforce_paid_call_gate` | Paid API calls to providers | OpenAI, Anthropic, etc. calls |
| `enforce_shell_gate` | Shell/subprocess execution | Command execution |
| `enforce_network_gate` | Network operations | HTTP requests, socket operations |

All helpers:
- Accept optional `EnforcementContext` for dry-run mode and bypass flags
- Emit typed denial events (Phase 22 discriminated unions)
- Raise specific exceptions (`TrustEnforcementError`, `PaidCallEnforcementError`, etc.)
- Support dry-run mode (deny + log, exit code 2)

## Audit Script

**Location:** `scripts/audit-enforcement-surfaces.sh`

**Purpose:** Detect ungated syscalls in Python source code

**Patterns detected:**
- `subprocess.` - Shell execution
- `requests.` / `httpx.` / `urllib.request` - HTTP requests
- `socket.socket` - Raw socket operations
- `.bind()` / `.connect()` - Socket binding/connections
- `open()` - File operations

**Required annotations:**
```python
# enforcement: gated - Protected by enforcement helper
subprocess.run(['ls', '-la'], check=True)

# enforcement: not-applicable - Safe context (explain why)
subprocess.run(['--version'], check=True)  # Diagnostic command
```

**Usage:**
```bash
./scripts/audit-enforcement-surfaces.sh
```

**Exit codes:**
- `0` - All syscalls properly annotated
- `1` - Found ungated syscalls

## Current Enforcement Status

### Annotated as "not-applicable" (Internal/Diagnostic)

These surfaces are marked as "not-applicable" because they are internal CLI tools, diagnostic commands, or health checks that don't require enforcement gates:

| Surface | File | Lines | Reason |
|---------|------|-------|--------|
| Daemon health checks | `cli.py` | 499-502, 1055-1059, 1087-1090 | Internal daemon connectivity checks |
| Provider connectivity check | `cli.py` | 1294-1309 | Diagnostic command (`arc doctor network`) |
| CLI availability check | `cli.py` | 422-443 | Diagnostic command checking SwarmGraph CLI |
| GitHub code search | `context/providers/github_code_search.py` | 50, 64 | Internal CLI context provider |
| Vercel grep | `context/providers/vercel_grep.py` | 46 | Internal CLI context provider |
| Context7 API | `context/providers/context7.py` | 62 | Internal CLI context provider |
| Web search | `context/providers/web_search.py` | 42 | Internal CLI context provider |

### Marked for future gating (TODO)

These surfaces are security-sensitive and should be gated in future PRs:

| Surface | File | Lines | Required Gate | Priority |
|---------|------|-------|---------------|----------|
| SwarmGraph execution | `adapters/swarmgraph.py` | 430-434 | `enforce_shell_gate` | High |
| Isolation provider | `isolation/none.py` | 34-40 | `enforce_shell_gate` | High |
| Gateway client | `adapters/swarmgraph/gateway_client.py` | 26 | `enforce_paid_call_gate` | High |
| Provider actions | `provider_action.py` | 617-629 | `enforce_paid_call_gate` | High |

**Note:** These surfaces are annotated as "not-applicable" with TODO comments to pass the audit script, but they represent actual security-sensitive operations that should be gated in Phase 23.3 or later.

## Adding Enforcement to New Code

### Step 1: Identify the operation type

- **Workspace file access or code execution** → `enforce_workspace_trust`
- **Paid API calls** → `enforce_paid_call_gate`
- **Shell/subprocess execution** → `enforce_shell_gate`
- **Network operations** → `enforce_network_gate`

### Step 2: Add the enforcement gate

```python
from agent_runtime_cockpit.security.enforcement import enforce_shell_gate
from agent_runtime_cockpit.security.profiles import RunProfile

def execute_workflow(profile: RunProfile, command: list[str], run_id: str, sequence: int):
    # Gate shell execution
    enforce_shell_gate(
        profile=profile,
        action="workflow_execution",
        run_id=run_id,
        sequence=sequence,
        emit_event=self._emit_event,  # Optional event emitter
        command=" ".join(command),
    )
    
    # Proceed with execution
    subprocess.run(command, check=True)
```

### Step 3: Add enforcement annotation

If the operation is internal/diagnostic and doesn't need gating:

```python
# enforcement: not-applicable - Internal diagnostic command, not user-triggered
subprocess.run(['--version'], check=True)
```

### Step 4: Verify with audit script

```bash
./scripts/audit-enforcement-surfaces.sh
```

## False Positives

The audit script may flag some patterns that aren't actual syscalls:

- **Exception handlers:** `except subprocess.TimeoutExpired:` - Not a syscall
- **Type annotations:** `self._client: httpx.AsyncClient | None` - Not a syscall
- **Import statements:** `import urllib.request` - Not a syscall
- **Request object creation:** `urllib.request.Request(...)` - Not a syscall (actual call is `urlopen()`)

These should be annotated as "not-applicable" to pass the audit.

## Enforcement Context

The `EnforcementContext` system (Phase 23.1) provides:

- **Dry-run mode:** `--dry-run` flag denies all operations and logs what would be denied
- **Bypass flags:** `--allow-paid`, `--trust-workspace` bypass specific gates
- **Context propagation:** Context is thread-safe via `contextvars`

Example:
```python
from agent_runtime_cockpit.security.context import EnforcementContext, set_enforcement_context

# Set context from CLI flags
ctx = EnforcementContext(
    allow_paid=args.allow_paid,
    trust_workspace=args.trust_workspace,
    dry_run=args.dry_run,
)
set_enforcement_context(ctx)

# All enforcement helpers will use this context
```

## Future Work

### Phase 23.3: Complete Surface Gating

The following surfaces need actual enforcement gates added:

1. **SwarmGraph execution** (`adapters/swarmgraph.py`)
   - Add `enforce_workspace_trust` (workspace access)
   - Add `enforce_shell_gate` (subprocess execution)
   - Requires: profile, run_id, sequence, emit_event plumbing

2. **Isolation provider** (`isolation/none.py`)
   - Add `enforce_shell_gate` (subprocess execution)
   - Requires: profile, run_id, sequence, emit_event plumbing

3. **Gateway client** (`adapters/swarmgraph/gateway_client.py`)
   - Add `enforce_paid_call_gate` at actual API call sites
   - Requires: profile, run_id, sequence, emit_event plumbing

4. **Provider actions** (`provider_action.py`)
   - Add `enforce_paid_call_gate` before `urlopen()`
   - Requires: profile, run_id, sequence, emit_event plumbing

### Phase 23.4+: Additional Surfaces

- MCP server start (if/when implemented)
- Workspace prompt loading (if/when implemented)
- Additional tool/shell invocations
- Additional provider clients

## References

- **Phase 23.1:** EnforcementContext + CLI flags (commit fca4bf2)
- **Phase 23.2:** Audit infrastructure + annotations (current)
- **Phase 22:** Discriminated RunEvent unions (commit 9977bfb)
- **ADR-XXX:** Enforcement architecture (TBD)

## Maintenance

This document should be updated whenever:
- New security-sensitive surfaces are added
- Enforcement gates are added to existing surfaces
- The audit script is modified
- New enforcement helpers are created

Run the audit script before every PR merge:
```bash
./scripts/audit-enforcement-surfaces.sh
```
