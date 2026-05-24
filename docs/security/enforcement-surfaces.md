# Enforcement Surfaces

This document catalogs all security-sensitive surfaces in ARC Studio and their enforcement status. It is the **single source of truth** for every execution surface that routes through the typed enforcement helpers introduced in Phase 23 (and the bypass-warning helper from ADR-0022.1).

**Last updated:** 2026-05-22  
**Phase:** 23.3 (Baseline Complete) + extended by Phases 25.5, 26, 32, 35 + sandbox hardening  
**Audit script:** `scripts/audit-enforcement-surfaces.sh`

If a code path performs a subprocess call, a file read in a user-controlled location, a socket bind, or an HTTP call and is **not** listed here, that is a bug. Either the path needs a row in this document, or it needs a `# enforcement: not-applicable` annotation that the audit script can verify.

## How to read this document

Each surface has:
- **What:** plain-language description of what the code is doing.
- **Where:** file paths and the helper(s) it routes through.
- **Why:** the threat the gate addresses.
- **Denial event:** the typed event variant that fires when the gate denies, with payload fields.
- **Recovery flag:** the CLI flag that allows the operation (per Phase 23 dialog options).
- **Audit coverage:** the test files that confirm the surface stays gated.
- **Bypass-warning conditions:** when (if ever) this surface emits `POLICY_BYPASS_WARNING` per ADR-0022.1.

## Enforcement Helpers

Five typed enforcement helpers (four denial + one bypass warning) gate security-sensitive operations:

| Helper | Purpose | Gates |
|--------|---------|-------|
| `enforce_workspace_trust` | Workspace file access and code execution | Untrusted workspace operations |
| `enforce_paid_call_gate` | Paid API calls to providers | OpenAI, Anthropic, etc. calls |
| `enforce_shell_gate` | Shell/subprocess execution | Command execution |
| `enforce_network_gate` | Network operations | HTTP requests, socket operations |
| `emit_policy_bypass_warning` | Records gap in gate coverage (ADR-0022.1) | Does not abort — signals cannot-prove coverage |

All helpers:
- Accept `EnforcementContext` as first positional argument (Phase 23.1)
- Emit typed denial events (Phase 22 discriminated unions)
- Raise specific exceptions on denial
- Support dry-run mode (deny + log, exit code 2)

## Bypass warnings vs. denial events

```
                      Can ARC prove the gate
                      applies to this call?
                             │
               ┌─────────────┴─────────────┐
              yes                          no
               │                           │
      Did the gate ALLOW?            Emit POLICY_BYPASS_WARNING
               │                     (ADR-0022.1), run proceeds,
      ┌────────┴────────┐            audit trail records gap.
     yes               no
      │                 │
Proceed normally   Emit typed denial
(audit trail        event. Run aborts
records gate).      unless user consents
                    via Phase 23 dialog.
```

## Audit script

**Location:** `scripts/audit-enforcement-surfaces.sh`

**Patterns detected:** subprocess.*, os.system/exec/spawn, asyncio.create_subprocess.*, socket.socket/bind/connect, httpx.*, requests.*, urllib.request.*, aiohttp.ClientSession, open(), pathlib .read_text/bytes.

**Annotation grammar:** `# enforcement: gated` | `# enforcement: helper=<name>` | `# enforcement: not-applicable — <reason>`. Must appear on the same line as the matched expression. `not-applicable` without a reason fails audit.

**Exit codes:** 0 = all annotated, 1 = unannotated hits found (build fails), 2 = script error.

---

## Per-Phase Surface Inventory

### Phase 23 — Baseline

#### S-23.1 · JobSupervisor job submission
- **What:** Every job submitted to JobSupervisor is gated by its declared resource needs.
- **Where:** `orchestration/job_supervisor.py`
- **Gates:** `enforce_workspace_trust` (startup), `enforce_paid_call_gate`/`enforce_shell_gate`/`enforce_network_gate` per job
- **Denial event:** Any Phase 23 typed denial with `{"surface": "orchestration.job_supervisor"}`

#### S-23.2 · Daemon MCP server start
- **What:** ARC daemon's own MCP-exposing socket requires workspace trust + network gate.
- **Where:** `extensions/<mcp-server-module>.py`
- **Gates:** `enforce_workspace_trust`, `enforce_network_gate`
- **Denial event:** `TRUST_DENIED` or `NETWORK_DENIED` with `{"surface": "daemon.mcp_server_start"}`

#### S-23.3 · Workspace prompt loading
- **What:** Loading prompts/agents from workspace passes trust + symlink-escape check.
- **Where:** `workspace.py`
- **Gate:** `enforce_workspace_trust`
- **Denial event:** `TRUST_DENIED` with `{"reason": "untrusted" | "symlink_escape"}`

#### S-23.4 · Tool/shell invocation
- **What:** Every subprocess.*, os.system, os.exec* invocation in adapter code.
- **Where:** Every adapter runner.py, `tools/`
- **Gate:** `enforce_shell_gate`
- **Denial event:** `SHELL_DENIED` with `{"surface": "<adapter>.tool"}`

#### S-23.5 · HTTP/network calls
- **What:** Every outbound HTTP call via provider SDKs, workspace fetchers, etc.
- **Where:** `providers/`, context providers, workspace fetchers
- **Gate:** `enforce_network_gate`
- **Denial event:** `NETWORK_DENIED` with `{"surface": "...", "host": ..., "port": ...}`

#### S-23.6 · Paid provider calls
- **What:** Every billable call to a provider SDK.
- **Where:** All `ProviderClient` implementations
- **Gate:** `enforce_paid_call_gate`
- **Denial event:** `PAID_CALL_DENIED` with `{"surface": "provider.<name>"}`

---

### Phase 25.5 — Prep surfaces

#### S-25.5.1 · ProviderClient contract
- **What:** The single boundary every provider-SDK adapter implements. All methods route through `enforce_paid_call_gate` and `enforce_network_gate`.
- **Where:** `providers/client.py`, `providers/registry.py`
- **Gates:** Inherits from S-23.5, S-23.6
- **Audit coverage:** `python/tests/providers/test_provider_client_contract.py` with two-strategy network monitor

---

### Phase 26 — LangChain

#### S-26.1 · LangChain Runnable execution
- **What:** Executing a LangChain LCEL pipeline. Recognized LLMs route through `ProviderClient`; unrecognized -> bypass warning.
- **Where:** `adapters/langchain/runner.py`
- **Gates:** Inherits S-23.4, S-23.5, S-23.6
- **Bypass-warning conditions:** Unrecognized `BaseLanguageModel` subclass -> `POLICY_BYPASS_WARNING` with `bypass_reason=UNKNOWN_PROVIDER_PLUGIN`

---

### Phase 32 — Smolagents

#### S-32.1 · LocalPythonExecutor (default reject)
- **What:** Detecting that a `CodeAgent` uses `LocalPythonExecutor`. Upstream declares it "not a security sandbox."
- **Where:** `adapters/smolagents/runner.py`, `_sandbox_policy.py`
- **Gate:** `enforce_shell_gate`
- **Denial event:** `SHELL_DENIED` with `{"executor_backend": "LocalPythonExecutor", "sandbox_classification": "not_a_sandbox"}`
- **Recovery flag:** `--allow-unsandboxed-shell` (distinct from `--allow-shell`). Dialog displays upstream warning verbatim.
- **Bypass-warning conditions:** When `--allow-unsandboxed-shell` is set, exactly one `POLICY_BYPASS_WARNING` fires per run with `bypass_reason=UPSTREAM_BYPASSED_BOUNDARY`.

#### S-32.2 · Sandboxed backends (Docker, E2B, Modal)
- **What:** CodeAgent with explicit sandbox backend.
- **Gate:** `enforce_shell_gate` + `enforce_network_gate` for cloud-managed (E2B, Modal)
- **Denial event:** `SHELL_DENIED` with `{"sandbox_classification": "sandbox"}`; `NETWORK_DENIED` for cloud backends

#### S-32.3 · Experimental backends (Blaxel, Pyodide)
- **What:** CodeAgent with backend classified as experimental. T1+T2 only; T3 deferred.
- **Gate:** `enforce_shell_gate`
- **Denial event:** `SHELL_DENIED` with `{"sandbox_classification": "experimental"}` regardless of flags
- **Recovery flag:** None at this phase. Users must use supported backend.

#### S-32.4 · Unrecognized Model subclass
- **Bypass-warning conditions:** `POLICY_BYPASS_WARNING` with `bypass_reason=UNKNOWN_PROVIDER_PLUGIN`, `surface="smolagents.model"`, `surface_identifier=<class-name>`.

---

### Phase 35 — MCP Client

#### S-35.1 · Server-identity derivation
- **What:** Computing stable `server_id` from locally-observable data (command+args hash for stdio, base_url for HTTP). Excludes secrets.
- **Where:** `adapters/mcp/_server_id.py`
- **Gate:** N/A — identity is input to subsequent gates
- **Audit coverage:** `python/tests/adapters/mcp/test_detect.py`

#### S-35.2 · Stdio transport
- **What:** MCP server over stdio (spawns subprocess).
- **Where:** `adapters/mcp/_stdio_runner.py`
- **Gate:** `enforce_shell_gate`
- **Denial event:** `SHELL_DENIED` with `{"transport": "stdio", "server_id": ..., "command": <sanitized>}`
- **Recovery flags:** `--allow-shell` + `--allow-mcp <server-id>`

#### S-35.3 · Streamable HTTP transport
- **What:** MCP server over Streamable HTTP (upstream-recommended).
- **Where:** `adapters/mcp/_streamable_http_runner.py`, `_connection_lifetime.py`
- **Gate:** `enforce_network_gate` + connection-lifetime cap (default 3600s)
- **Denial event:** `NETWORK_DENIED` with `{"transport": "streamable_http", "connection_lifetime_cap_seconds": ...}`
- **Recovery flags:** `--allow-network` + `--allow-mcp <server-id>`

#### S-35.4 · SSE transport (deprecated)
- **What:** MCP server over SSE. Deprecated upstream.
- **Where:** `adapters/mcp/_sse_runner.py`
- **Gate:** `enforce_network_gate`
- **Denial event:** Same as S-35.3 with `"deprecation_warning": true`
- **Bypass-warning conditions:** **Always** emits `POLICY_BYPASS_WARNING` per session with `suggested_remediation="Migrate to Streamable HTTP"`.

#### S-35.5 · call_tool invocation
- **What:** Each `ClientSession.call_tool(name, args)` against a connected MCP server.
- **Gate:** Re-evaluates EnforcementContext (TOCTOU defense).
- **Denial event:** `TRUST_DENIED` if trust revoked mid-session.

---

## Annotated as "not-applicable" (Internal/Diagnostic)

These surfaces are annotated as not-applicable because they are internal CLI tools, diagnostic commands, or health checks:

| Surface | File | Lines | Reason |
|---------|------|-------|--------|
| Daemon health checks | `cli.py` | 499-502, 1055-1059, 1087-1090 | Internal daemon connectivity checks |
| Provider connectivity check | `cli.py` | 1294-1309 | Diagnostic (`arc doctor network`) |
| CLI availability check | `cli.py` | 422-443 | Diagnostic checking SwarmGraph CLI |
| GitHub code search | `context/providers/github_code_search.py` | 50, 64 | Internal CLI context provider |
| Vercel grep | `context/providers/vercel_grep.py` | 46 | Internal CLI context provider |
| Context7 API | `context/providers/context7.py` | 62 | Internal CLI context provider |
| Web search | `context/providers/web_search.py` | 42 | Internal CLI context provider |

## Cross-phase invariants

1. **Helper invocation is the only way to make a gated call.** Direct subprocess/HTTP/file calls are detected by audit script and fail build unless annotated.
2. **TOCTOU re-checks.** Gates re-evaluate on every call. Long-lived sessions re-check trust at each step boundary.
3. **Audit trail completeness.** Every gate call records its decision to the trace before returning. Phase 21 verifier replays this trail.
4. **Dry-run semantics.** `--dry-run` emits same denial events as real run but never performs side effect. Ends in `DryRunAbort`.
5. **Non-interactive mode.** Headless/CI runs deny by default. No dialog is silently auto-accepted.
6. **Bypass-warning rate limit.** Per ADR-0022.1, at most one `POLICY_BYPASS_WARNING` per `(run_id, surface_identifier)` per run. Dedup state in same `contextvar` as EnforcementContext.

## Sandbox Approval Tokens

`arc policy approve --token <token> -- <cmd...>` stores scoped non-interactive approvals in `~/.arc/approvals.json` (override: `ARC_SANDBOX_APPROVAL_STORE`). `arc sandbox run --approval-token <token> -- <cmd...>` only applies a stored approval when policy, workspace root, classification, and command hash all match. Destructive and privileged classifications remain unapprovable. `arc policy revoke --token <token>` deletes all entries for that token.

New approvals store only a token hash, include `expires_at`, and write the approval file with private user permissions where the platform supports chmod. Legacy plaintext-token approvals remain readable so existing persisted approvals do not fail closed unexpectedly during this alpha phase.

Research note: Context7 Typer docs confirm `CliRunner` command tests and subcommands; Pydantic docs confirm `model_validate`, `model_dump`, and JSON serialization for stable file envelopes. Vercel/Google code search was unavailable in this session due provider 403, so implementation used existing ARC policy patterns only.

## Sandbox Classification And Path Intent

`arc sandbox run` remains real subprocess execution only. It now denies additional adversarial forms before execution:

- interpreter one-liners with unknown side effects default to `unknown`; Python package install/network/write hints classify as `install`, `network`, or `writes_workspace`.
- destructive VCS/file commands (`git clean`, `git reset --hard`, `git checkout --`, `git rm`, `find -delete`, `find -exec rm`, `tar --overwrite`, `dd`, `truncate`) deny by default.
- privileged ownership/mode changes (`chmod`, `chown`, `sudo`, etc.) deny and are not approvable.
- write-class commands with known path args must stay inside the workspace; symlink/outside/absolute escapes deny before subprocess execution.
- path extraction covers known output/input flags, Python literal `open`/`write_text`/`write_bytes`, `dd of=`, simple `cp`/`mv` destinations, and archive output suffixes.
- read-only absolute paths outside the workspace deny by default unless a future ADR documents a safe exception.

Limits: this is policy/classifier hardening, not syscall or kernel sandboxing. MicroVM remains preflight/doctor-only; container fallback remains gated by `ARC_ENABLE_CONTAINER_SANDBOX=1`.

## HMAC Audit Append Durability

`HmacAuditChainWriter` now creates parent directories, uses advisory file locking where available, writes stable canonical JSON, flushes, and calls `os.fsync` per append. Verification rejects partial trailing lines clearly. The JSONL record shape is unchanged.

## Adding Enforcement to New Code

### Step 1: Identify operation type
- **Workspace file access or code execution** → `enforce_workspace_trust`
- **Paid API calls** → `enforce_paid_call_gate`
- **Shell/subprocess execution** → `enforce_shell_gate`
- **Network operations** → `enforce_network_gate`
- **Cannot determine gate applicability** → `emit_policy_bypass_warning`

### Step 2: Add gate
```python
from agent_runtime_cockpit.security.enforcement import enforce_shell_gate

enforce_shell_gate(profile=profile, action="workflow_execution", run_id=run_id, sequence=sequence, command=" ".join(command))
subprocess.run(command, check=True)
```

### Step 3: Add annotation (if gate is not on the same line)
```python
# enforcement: gated
subprocess.run(command, check=True)

# enforcement: not-applicable — Internal diagnostic command, not user-triggered
subprocess.run(['--version'], check=True)
```

### Step 4: Verify
```bash
./scripts/audit-enforcement-surfaces.sh
```

## Change Procedure

To add a new surface: add row under the appropriate phase, update audit script patterns if needed, add tests, update `docs/phases.md`. To modify an existing surface: ADR required, update this document and affected tests, CHANGELOG entry.

## References

- **Phase 23.1:** EnforcementContext + CLI flags (commit fca4bf2)
- **Phase 23.3:** Baseline Complete (commits 09bfbb8, b65f57e)
- **Phase 22:** Discriminated RunEvent unions (commit 9977bfb)
- **ADR-0022.1:** `POLICY_BYPASS_WARNING` (docs/adr/ADR-0022.1.md)
- **docs/research/adapter-roadmap.md:** Phases 26-35 surface scheduling
# CLI Sandbox Surface

ARC now has a first-class sandbox CLI foundation:

- `arc policy explain -- <cmd...>` classifies argv and reports policy decision without execution.
- `arc sandbox run --policy local-safe -- <cmd...>` enforces local-safe policy before subprocess execution.
- `arc sandbox run --ask -- <cmd...>` can approve only `network`, `install`, and `unknown`; non-interactive default remains deny.
- `arc sandbox doctor --json` reports subprocess and microVM preflight state.
- `arc sandbox audit-verify --json` verifies the sandbox audit chain.
- `arc sandbox audit-list --json` reads persisted sandbox events with filters.
- `arc policy list/show/validate` discovers and validates configured sandbox policies.

P0 policy defaults:

- read-only commands are auto-allowed.
- network, install, privileged, destructive, and unknown commands are denied unless an explicit future policy enables them.
- subprocess execution uses argv lists only, not shell strings.
- cwd must resolve inside the workspace.
- environment is allowlisted and secret-looking variables are stripped.
- timeout kills the POSIX process group.
- stdout/stderr are capped and redacted.
- every allowed/denied sandbox command returns an audit payload.
- sandbox audit events are persisted to an external hash-chain store by default.
- sandbox audit events best-effort mirror into the keyed audit store when an audit key exists; missing keys do not block CLI execution.
- sandbox audit chain appends continue across CLI invocations and verify against raw events.
- container execution requires `ARC_ENABLE_CONTAINER_SANDBOX=1`.

MicroVM status: doctor/preflight only. Linux checks Firecracker/Cloud Hypervisor and `/dev/kvm`. macOS checks Lima/VZ availability. Windows is explicitly unsupported for this phase.
