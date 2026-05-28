# Enforcement Surfaces

This document catalogs all security-sensitive surfaces in ARC Studio and their enforcement status. It is the **single source of truth** for every execution surface that routes through the typed enforcement helpers introduced in Phase 23 (and the bypass-warning helper from ADR-0022.1).

**Last updated:** 2026-05-27  
**Phase:** 23.3 (Baseline Complete) + extended by Phases 25.5, 26, 32, 35, 50, 52, 55 + sandbox/MCP hardening  
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

### Phase 26 — ARC MCP Local Control Plane

#### S-26.MCP.1 · Local MCP server start
- **What:** Starting ARC's local MCP control plane over stdio only.
- **Where:** `mcp/server.py`, `cli/mcp.py`
- **Gate:** `ensure_trusted()` at server creation.
- **Transport:** stdio only; HTTP/listen sockets remain excluded until auth/trust policy is accepted.
- **Audit coverage:** `python/tests/mcp/test_mcp_server.py` (FastMCP internals) and `python/tests/mcp/test_mcp_client_session.py` (real MCP ClientSession with in-process memory-stream transport) verifies trusted/untrusted creation, tool/resource invocation, ARC envelope shape, denied error envelopes, and unsupported transport behavior.

#### S-26.MCP.2 · MCP tool/resource invocation
- **What:** Each MCP tool/resource call reads local ARC state (runs, traces, audit, HITL, tasks) or creates/cancels local task records.
- **Where:** `mcp/server.py`
- **Gate:** `ensure_trusted()` is re-checked per tool/resource call.
- **Data controls:** Safe ID validation, trace/audit path guard, trace pagination, output caps, stable ARC envelopes, and redaction before returning or auditing data.
- **Audit coverage:** Best-effort local JSONL at `.arc/audit/mcp.events.jsonl` records tool/resource name, workspace, redacted args, args hash, decision (`allowed`, `denied`, `error`), error code/reason, timing, transport (`stdio`), and truncation flag. Audit write failure does not fail the tool response.
- **Bypass-warning conditions:** None. No provider/network/paid calls are made by this local control plane.

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

#### S-32.5 · Event bus publish (Phase 32 / R25)
- **What:** In-memory typed event bus. Producers (HITL store, audit verifier, supervisor, budget) publish events. Fire-and-forget — never blocks producer.
- **Where:** `events/bus.py` (`EventBus.publish()`)
- **Gate:** None (internal instrumentation). Events are typed and do not carry user secrets by default.
- **Denial event:** N/A — no denial path. Producers log on failure.
- **Audit coverage:** 14 event bus tests, wiring tests in existing producer test files.

#### S-32.6 · Webhook delivery (Phase 32 / R25)
- **What:** Optional HMAC-SHA256 signed webhook POST delivery for ARC events. Bounded exponential backoff retry (max 5, 60s cap). Dead-letter log for permanent failures.
- **Where:** `events/webhooks.py` (`WebhookManager.deliver()`)
- **Gate:** `httpx.AsyncClient` POST with 5s timeout. No network gate required (webhooks are opt-in per-workspace config).
- **Denial event:** Dead-letter entry written on permanent failure.
- **Secrets:** `secret` stored in `.arc/events/webhooks.json` with `0o600` permissions. Warned on `arc events webhook-add`.
- **Audit coverage:** 17 webhook tests (config CRUD, HMAC sign/verify, dead-letter, retry bounds).

#### S-32.7 · CLI events watch (Phase 32 / R25)
- **What:** `arc events watch` subscribes to the in-process event bus and prints events to stdout.
- **Where:** `cli/events.py`
- **Gate:** None — diagnostic/watch command. Only observes already-published events.
- **Audit coverage:** 5 CLI events tests.

#### S-63.1 · Local event-log persistence and summary
- **What:** `EventBus.publish()` writes typed events to local `.arc/events/event-log.jsonl` before delivering to active SSE clients; `arc events summary --json` derives local/recent notification counts from that log.
- **Where:** `events/bus.py`, `events/persistence.py`, `cli/events.py`, `web/routes.py`
- **Gate:** Workspace trust at `GET /api/events/stream` connect time. CLI summary reads only the local workspace event log.
- **Summary semantics:** `arc events summary --json` is local/recent/derived. If compaction leaves a `hitl_decided` event without its matching `hitl_required`, the summary reports `degraded=true`, `unmatched_hitl_decisions`, and `summary_semantics=local_recent_derived_compaction_may_drop_pairs` instead of implying canonical HITL state.
- **Transport:** SSE only. No WebSocket, shared-server, remote sync, or complete audit coverage claim.
- **Audit coverage:** `python/tests/events/`, `python/tests/cli/test_events_cli.py` cover event persistence/query behavior and CLI contracts.

#### S-63.2 · IDE notification badge CLI bridge
- **What:** The Theia backend notification service invokes `arc events summary --json` using argv-only `spawn('arc', ['events', 'summary', '--json'], { shell: false })`.
- **Where:** `packages/arc-extension/src/node/services/notification-service.ts`
- **Gate:** No shell-string execution; output capped in-process and failures degrade counts to zero with `source: cli_fallback`.
- **Audit coverage:** `packages/arc-extension/src/node/services/__tests__/notification-service.test.ts` asserts argv-only spawn and summary parsing.

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
- read-only absolute and relative paths outside the workspace deny by default unless a future ADR documents a safe exception.
- shell, Git, package-manager, and Python write forms have regression coverage for known adversarial argv patterns.

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
- `arc sandbox doctor --json` reports subprocess, microVM preflight, and container preflight state.
- `arc sandbox audit-verify --json` verifies the sandbox audit chain.
- `arc sandbox audit-list --json` reads persisted sandbox events with filters.
- `arc sandbox audit-query --json` queries local persisted sandbox events with time/classification/provider filters.
- `arc sandbox audit-compact --json` compacts events-only sandbox logs; canonical hash-chain logs are refused to preserve verification semantics.
- `arc sandbox audit-show <audit_id> --json` reads one local sandbox audit event.
- `arc sandbox audit verify|list|query|compact|show` are nested aliases for the same local audit operations.
- `arc sandbox run --provider container -- <cmd...>` executes through Docker/Podman only when `ARC_ENABLE_CONTAINER_SANDBOX=1` and local runtime checks pass.
- `arc sandbox firecracker-artifacts --output <dir> --json` generates Firecracker proof init/manifest artifacts without booting a VM.
- `arc policy list/show/validate` discovers and validates configured sandbox policies.
- `arc policy validate-yaml --file <path>` validates a local YAML sandbox policy file.
- `arc policy apply --file <path>` installs a local YAML sandbox policy under the workspace boundary.

P0 policy defaults:

- read-only commands are auto-allowed.
- network, install, privileged, destructive, and unknown commands are denied unless an explicit future policy enables them.
- subprocess execution uses argv lists only, not shell strings.
- cwd must resolve inside the workspace.
- environment is allowlisted and secret-looking variables are stripped.
- timeout kills the POSIX process group.
- stdout/stderr are capped and redacted.
- every allowed/denied sandbox command returns an audit payload.
- sandbox audit events include an `audit_id` correlation key.
- sandbox audit events are persisted to a local sandbox hash-chain store by default.
- sandbox audit events best-effort mirror a typed `sandbox_command` event into `.arc/events/event-log.jsonl`; this mirror is local/recent/derived and not canonical global audit state.
- sandbox audit events best-effort mirror into the keyed audit store when an audit key exists; missing keys do not block CLI execution.
- Firecracker artifact generation validates static proof-init safety and manifest no-network metadata, but does not prove VM execution.
- sandbox audit chain appends continue across CLI invocations and verify against raw events.
- container execution requires `ARC_ENABLE_CONTAINER_SANDBOX=1`.

MicroVM status: doctor/preflight/proof-harness only. Linux checks Firecracker/Cloud Hypervisor and `/dev/kvm`; private Firecracker proof paths stay gated behind Linux, `/dev/kvm`, `firecracker`, `ARC_MICROVM_INTEGRATION=1`, `ARC_FC_REAL_EXEC=1`, and explicit kernel/rootfs paths. macOS checks Lima/VZ availability and remains a low-security developer harness. Windows is explicitly unsupported. Public `MicroVMIsolationProvider.execute()` and `arc sandbox run --provider microvm` remain blocked.

---

### Phase 50 — Trust Enforcement Surface Audit (R16 derivative)

**Last updated:** 2026-05-27  
**Status:** Baseline Complete  
**Audit scope:** All workspace-sensitive HTTP routes in `web/routes.py` + MCP tool/resource handlers.

#### Audit findings and gap closure

Pre-Phase 50 gap: eleven routes in `web/routes.py` read workspace-local data (traces, context, arena runs) without first calling `enforce_workspace_trust`. An untrusted workspace could oracle-probe run IDs and leak trace contents via 404 vs 500 distinction. All gaps are now closed.

#### Phase 50 Surface Table

| Surface | Route/Command | Trust checked | Order (before/after read) | Test | Gap status |
|---------|---------------|---------------|--------------------------|------|------------|
| `sessions_write` | `POST /api/sessions/write` | `enforce_workspace_trust` | before session save | `test_session_daemon_routes.py::test_sessions_write_untrusted_workspace` | closed pre-P50 |
| `sessions_delete` | `DELETE /api/sessions/{id}` | `enforce_workspace_trust` | before existence check | `test_session_daemon_routes.py::test_sessions_delete_untrusted_workspace_checks_trust_before_existence` | closed pre-P50 |
| `sessions_update` | `PATCH /api/sessions/{id}` | `enforce_workspace_trust` | before session load | `test_session_daemon_routes.py::test_sessions_update_untrusted_workspace_checks_trust_before_load` | closed pre-P50 |
| `start_run` | `POST/GET /api/runs/start` | `enforce_workspace_trust` | before runtime resolution | `test_phase50_trust_surface_audit.py::test_start_run_post_untrusted_returns_403` | **closed P50** |
| `list_runs` | `GET /api/runs` | `enforce_workspace_trust` | before trace store read | `test_phase50_trust_surface_audit.py::test_list_runs_untrusted_returns_403` | **closed P50** |
| `get_run` | `GET /api/runs/{run_id}` | `enforce_workspace_trust` | before trace load (oracle-leak guard) | `test_phase50_trust_surface_audit.py::test_get_run_untrusted_returns_403_not_404` | **closed P50** |
| `context_pack` | `GET /api/context/pack` | `enforce_workspace_trust` | before workspace file scan | `test_phase50_trust_surface_audit.py::test_context_pack_untrusted_returns_403` | **closed P50** |
| `run_links` | `GET /api/runs/{run_id}/links` | `enforce_workspace_trust` | before trace load (oracle-leak guard) | `test_phase50_trust_surface_audit.py::test_run_links_untrusted_returns_403_not_404` | **closed P50** |
| `export_trace` | `POST /api/telemetry/export/{run_id}` | `enforce_workspace_trust` | before trace load (oracle-leak guard) | `test_phase50_trust_surface_audit.py::test_export_trace_untrusted_returns_403_not_404` | **closed P50** |
| `runs_diff` | `GET /api/runs/diff` | `enforce_workspace_trust` | before both trace loads | `test_phase50_trust_surface_audit.py::test_runs_diff_untrusted_returns_403` | **closed P50** |
| `runs_eval` | `POST /api/evals/run` | `enforce_workspace_trust` | before trace load (oracle-leak guard) | `test_phase50_trust_surface_audit.py::test_runs_eval_untrusted_returns_403_not_404` | **closed P50** |
| `arena_chat` | `POST /api/arena/chat` | `enforce_workspace_trust` | before arena request processing | `test_phase50_trust_surface_audit.py::test_arena_chat_untrusted_returns_403` | **closed P50** |
| `arena_vote` | `POST /api/arena/vote` | `enforce_workspace_trust` | before run existence check (oracle-leak guard) | `test_phase50_trust_surface_audit.py::test_arena_vote_untrusted_returns_403_not_404` | **closed P50** |
| `arena_adopt` | `POST /api/arena/adopt` | `enforce_workspace_trust` | before workspace patch apply | `test_phase50_trust_surface_audit.py::test_arena_adopt_untrusted_returns_403` | **closed P50** |
| MCP tool/resource handlers | all `@mcp.tool()` / `@mcp.resource()` | `ensure_trusted()` per call via `_tool_result()` | before callback execution | `tests/mcp/test_mcp_server.py` | closed pre-P50 |

#### Consistency verification

- All 14 surfaces return HTTP 403 + `ArcErrorCode.PERMISSION_DENIED` on untrusted workspace.
- No surface leaks existence (oracle-leak pattern): trust check precedes the first data read in all cases.
- CLI and daemon paths use the same `_session_error(exc, 500)` handler which maps `TrustEnforcementError` → 403 PERMISSION_DENIED.
- MCP path uses `ensure_trusted()` → `WorkspaceUntrusted` → `_error_json(PERMISSION_DENIED, ...)`.
- Parity test: `test_trust_enforcement_error_code_consistent_across_surfaces` verifies all 11 newly-hardened routes return the same code.

---

### Phase 52 — SSE Push and Event Persistence

#### S-52.1 · SSE event stream connect
- **What:** Client connects to `GET /api/events/stream` for local push events.
- **Where:** `web/routes.py` `events_stream()`
- **Gate:** `enforce_workspace_trust` at connect time — returns 403 before streaming.
- **Transport:** SSE only. No WebSocket. No shared-server. No remote-sync. Local daemon only.
- **Event types pushed:** session_changed, hitl_required, audit_verified, run_completed, run_failed, quota_warning.
- **Last-Event-ID:** Resume replay from persisted event log after daemon restart.
- **Audit coverage:** `python/tests/events/test_phase52_sse_push.py::test_sse_stream_untrusted_returns_403_not_mid_stream`

#### S-52.2 · Dead-letter log redaction
- **What:** Failed webhook deliveries write to DLQ. Payload must be redacted before write.
- **Where:** `events/webhooks.py`, `events/models.py`
- **Gate:** Redactor applied before `DeadLetterEntry` construction. No plaintext secrets in DLQ.
- **Audit coverage:** `python/tests/events/test_phase52_sse_push.py::test_dead_letter_payload_is_redacted`

---

### Phase 55 — Provider Workspace Isolation

**Last updated:** 2026-05-27  
**Status:** Baseline Complete  
**Scope:** Provider routing and account mutation surfaces now enforce workspace trust.

#### Phase 55 Surface Table

| Surface | Route/Method | Trust checked | Order (before/after mutation) | Test | Gap status |
|---------|-------------|---------------|------------------------------|------|------------|
| `providers_routing` | `PUT /api/providers/routing` | `enforce_workspace_trust` | before routing policy write | `test_phase55_provider_trust.py::test_providers_routing_put_untrusted` | **closed P55** |
| `providers_accounts_create` | `POST /api/providers/accounts` | `enforce_workspace_trust` | before account creation | `test_phase55_provider_trust.py::test_providers_accounts_post_untrusted` | **closed P55** |
| `providers_account_update` | `PATCH /api/providers/accounts/{id}` | `enforce_workspace_trust` | before account mutation | `test_phase55_provider_trust.py::test_providers_account_patch_untrusted` | **closed P55** |
| `providers_account_delete` | `DELETE /api/providers/accounts/{id}` | `enforce_workspace_trust` | before account deletion | `test_phase55_provider_trust.py::test_providers_account_delete_untrusted` | **closed P55** |

All surfaces return HTTP 403 + `ArcErrorCode.PERMISSION_DENIED` on untrusted workspace.

#### Remaining known gaps (not in scope for P50/P55)

- `/health`, `/api/inspect`, `/api/runtimes`, `/api/runtimes/capabilities`, `/api/workflows`, `/api/schemas` — diagnostic/detection endpoints; no workspace-private data exposed. Annotated not-applicable.
- `GET /api/providers/*` — read-only provider metadata; no mutation. Read surfaces do not require trust.
- `/api/arena/models`, `/api/arena/tags`, `/api/arena/rankings` — read-only model metadata, not workspace-private data.
- `run_events_sse` (`GET /api/runs/{run_id}/events`) — per-run SSE endpoint; trust check deferred pending future ADR (no workspace-private data served that isn't already trust-checked on run creation).
- `events_stream` (`GET /api/events/stream`) — added in Phase 52; trust checked at connect time before any event data is sent. See Phase 52 SSE surface below.
