# ARC Studio Security Architecture Audit — 2026-06-07

> **Scope:** Deterministic security, policy, sandbox, isolation, trust, audit, keyed audit, capability cards, MCP risk gates, provider-call gates, secret redaction  
> **Source:** Synthesized from 8 prior research sessions + direct read of enforcement-surfaces.md, enforcement.py, profiles.py, policy_linter.py  
> **Last updated:** 2026-06-07 (Phase 131, HEAD aa788f3)

---

## 1. Security Architecture Map

```
┌─────────────────────────────────────────────────────────────────────┐
│                   ARC STUDIO SECURITY STACK                          │
│                                                                      │
│  LAYER 1 — ENFORCEMENT CONTEXT (immutable, thread-safe)             │
│  EnforcementContext(frozen=True, ContextVar)                        │
│  ├── dry_run      → DENIES ALL gates unconditionally (cannot bypass) │
│  ├── allow_paid   → bypasses enforce_paid_call_gate                 │
│  └── trust_workspace → bypasses enforce_workspace_trust             │
│                                                                      │
│  LAYER 2 — ENFORCEMENT HELPERS (4 typed gates + bypass warning)     │
│  enforce_workspace_trust()  → TrustDeniedEvent + TrustEnforcementError     │
│  enforce_paid_call_gate()   → PaidCallDeniedEvent + PaidCallEnforcementError│
│  enforce_shell_gate()       → ShellDeniedEvent + ShellEnforcementError      │
│  enforce_network_gate()     → NetworkDeniedEvent + NetworkEnforcementError  │
│  emit_policy_bypass_warning() → rate-limited, non-blocking, 1/run/surface  │
│                                                                      │
│  LAYER 3 — RUN PROFILES (4 built-in, frozen, versioned v2)          │
│  stub / local-safe → allow_paid=F, allow_network=F, allow_shell=F   │
│  local-paid        → allow_paid=T, allow_network=T, allow_shell=F   │
│  gateway           → allow_paid=T, allow_network=T, allow_shell=T   │
│  Custom profiles   → ~/.arc/profiles.json (schema v2, no migrate ⚠️) │
│                                                                      │
│  LAYER 4 — SANDBOX (deny-default, classification-based)             │
│  decide(argv, policy) → allow/deny/warn + SandboxReasonCode          │
│  ├── READ_ONLY → auto-allow                                          │
│  ├── WRITES_WORKSPACE → allow (path-confined)                       │
│  ├── NETWORK / INSTALL / UNKNOWN → deny (approvable with token)     │
│  ├── PRIVILEGED / DESTRUCTIVE → deny (never approvable)             │
│  ├── H1-H9 hardening (path resolve, env allowlist, secret/credential│
│  │   read deny, argv bounds, git global option strip, python -c AST) │
│  ├── PR-A exit code semantics, PR-B secret read deny, PR-C reason codes │
│  └── Audit: every decision appended to sandbox.audit.jsonl          │
│                                                                      │
│  LAYER 5 — ISOLATION BACKENDS (default: subprocess)                 │
│  subprocess → env-filtered (SAFE_ENV_KEYS), argv-list, path-confined│
│  docker     → gated (ARC_ENABLE_CONTAINER_SANDBOX=1)               │
│  microvm    → gated, macOS VZ 1 proof (pwd), NOT production-grade  │
│  none       → direct, workspace-resolved cwd (H4)                   │
│                                                                      │
│  LAYER 6 — HMAC AUDIT CHAIN (SHA-256 chain, tamper-evident)        │
│  ~/.arc/audit/{run_id}.audit.jsonl + .checkpoint.json sidecar       │
│  Scope: single-session local runs; no protection vs local attacker  │
│                                                                      │
│  LAYER 7 — MCP RISK GATE (D-02, deterministic, no LLM)             │
│  4 risk levels (critical/high/medium/low)                           │
│  7 injection patterns (BLOCKED/DEGRADED severity)                  │
│  2 policies (STRICT/PERMISSIVE)                                     │
│  Decisions → <workspace>/.arc/mcp/decisions.jsonl                  │
│                                                                      │
│  LAYER 8 — WORKSPACE TRUST (external DB, non-global)               │
│  ~/.arc/trusted-workspaces.json                                     │
│  resolve_trust() → TRUSTED/UNTRUSTED/PARTIAL                       │
│  TOCTOU re-check per gate call (enforced)                           │
│                                                                      │
│  LAYER 9 — SECRET REDACTION (multi-layer)                          │
│  security/redaction.py → canonical SECRET_PATTERNS                 │
│  ├── redact_output() in subprocess layer                            │
│  ├── redact_payload() in FlightRecorder                             │
│  └── Redactor().redact_dict() in MCP audit + memory extraction     │
│  ⚠️ _map_error() in providers NOT redacted                         │
│  ⚠️ LocalRepoProvider does NOT exclude .env/*.key                  │
│  ⚠️ Non-OpenAI/Anthropic key formats not in named patterns          │
└─────────────────────────────────────────────────────────────────────┘
```

### Key design principles (all confirmed in code)

| Principle | Status | Evidence |
|---|---|---|
| All decisions deterministic (no LLM) | ✅ | Policy linter, sandbox classify, MCP risk scoring — pure functions |
| `dry_run` cannot be bypassed | ✅ | `if ctx.dry_run: raise DryRunAbort` before every gate bypass check |
| `EnforcementContext` is immutable | ✅ | `@dataclass(frozen=True)` + `ContextVar`; mutations via `copy_with()` only |
| TOCTOU re-check per gate call | ✅ | S-35.5, S-126.1 enforce per-call trust re-check |
| Audit write failure non-fatal | ✅ | H9: `_persist_audit_safely` never fail-opens a denial |
| Bypass warning rate-limited | ✅ | `should_emit_warning()` per (run_id, surface_identifier) |
| shell=True prohibited | ✅ | S-60.3 confirmed complete; audit script enforces annotation |
| Approval tokens store hash only | ✅ | Plaintext token → hash stored |
| MCP server stdio-only | ✅ | No HTTP bind anywhere |

---

## 2. Enforcement Surface Map

### Summary (from enforcement-surfaces.md, phase 131)

| Phase range | Surfaces | Key gates |
|---|---|---|
| S-23.x | Baseline: JobSupervisor, MCP server, workspace prompt, tool/shell, HTTP, paid calls | trust, paid, shell, network |
| S-26.x | MCP local control plane, LangChain LCEL | trust (per-call), bypass-warning for unknown LLM |
| S-32.x | SmolAgents: LocalPythonExecutor → deny; Docker/E2B → shell+network; experimental → always deny | shell, network |
| S-35.x | MCP client: stdio→shell, HTTP→network, SSE→network+bypass-warning (deprecated) | shell, network |
| S-60-65 | Env filter, path confinement, shell=True removal | sandbox primitives |
| S-80.x | HMAC audit chain, checkpoint sidecar | audit |
| S-100.x | CapabilityCard conformance gate, adapter paid-call gate | paid |
| S-116.x | _call_with_retry: gate called once before loop; permanent errors short-circuit | paid |
| S-126.1 | ApprovalCard HITL gate hook in TurnManager | HITL |
| Phase 50 | 14 HTTP routes: trust check before any data read (oracle-leak prevention) | trust |
| Phase 55 | Provider routing/account mutation routes: trust check before mutation | trust |

### Critical surface gaps (not in enforcement-surfaces.md)

| Gap | Severity | Detail |
|---|---|---|
| `NotificationBackendService` env | **Fixed (S-63.2)** | Now annotated; spawn with shell=false and no secret env per enforcement-surfaces |
| MCP resources bypass risk gate | **HIGH** | `arc://runs/`, `arc://traces/`, `arc://audit/` call tool functions directly, skipping `_tool_result()` risk gate and audit |
| `McpProxy env=None` | **HIGH** | Default `McpProxy.start()` with no `env` arg passes full `os.environ` to subprocess |
| `arc mcp serve` stdout pollution | **HIGH** | Rich markup printed to stdout before `mcp.run(transport="stdio")` corrupts MCP framing |
| Registry `approved_tools`/`blocked_tools` | **HIGH** | Per-tool override mechanism in `McpServerRecord` never consulted by `decide_call()` |
| `workspace inventory` no trust gate | **HIGH** | `iter_workspace_files()` has no `enforce_workspace_trust()` call |
| Run ID path traversal | **HIGH** | `base_dir / f"{run_id}.jsonl"` — no character allowlist or `relative_to()` confinement |
| `_map_error()` no redaction | **MEDIUM** | Both `anthropic.py` and `openai_compatible.py` pass `str(exc)` unredacted |
| `LocalRepoProvider` secrets | **MEDIUM** | `.env`, `*.key`, credential files included in context injection |
| Non-standard key format redaction | **MEDIUM** | Groq `gsk-`, DashScope, GLM key formats not in `SECRET_PATTERNS` |

### Confirmed not-applicable surfaces

The enforcement-surfaces.md document correctly annotates these as not-applicable:
- GitHub code search, Vercel grep, Context7 API, web search — internal context providers
- Daemon health checks, provider connectivity check — diagnostic only
- CLI availability checks — diagnostic only

---

## 3. Claim Safety Review

### Claims verified true (with evidence)

| Claim | Evidence |
|---|---|
| "Deny by default — unknown, destructive, and privileged commands are blocked" | `decide()` classification table in `sandbox.py`; PRIVILEGED/DESTRUCTIVE not approvable |
| "Path confinement — writes confined to workspace; symlink escapes rejected" | H1 validation.py + S-60.2 + `is_path_within_root()` with `os.path.realpath()` |
| "Env allowlist — only safe env vars pass to child processes; secrets stripped" | H2 `SAFE_ENV_KEYS`, H3 redaction; confirmed by `test_sandbox_shell_escape.py` |
| "Audit chain — HMAC-signed streaming audit verifier" | S-80.1/S-80.2; `arc audit verify`; checkpoint sidecar |
| "Tamper-evident for single-session local runs; does not protect against a local attacker with write access to ~/.arc/audit/" | README caveat confirmed in enforcement-surfaces.md |
| "MCP stdio-only; no HTTP listener; no external server auto-start" | `mcp/server.py` — no HTTP bind; FastMCP(transport="stdio") only |
| "Landlock detection — Linux Landlock LSM ABI probed at startup" | `arc sandbox doctor` |
| "Remote MCP beyond loopback: deferred" | roadmap.md Non-Negotiable Boundary |
| "Deterministic risk scoring (no LLM judgment)" | `mcp/risk.py` pure if-else cascade; `swarmgraph/policy_linter.py` 8 pure rules |
| "microVM execution is gated and default-off. macOS proof passed once for guest-available pwd" | ADR-024; enforcement-surfaces.md microVM section |

### Claims with caveats (true but limited)

| Claim | Caveat |
|---|---|
| "HMAC-signed audit" | decisions.jsonl (`<workspace>/.arc/mcp/decisions.jsonl`) is NOT HMAC-signed — plain JSON, no sequence. Only run trace audit is HMAC-signed. |
| "Decisions logged to `~/.arc/audit/decisions.jsonl`" | **Wrong path in roadmap.** Actual path: `<workspace>/.arc/mcp/decisions.jsonl` |
| "11 tools, 3 resources" for MCP | Correct count. But resources bypass the risk gate (see gaps above). |
| "109 OpenAI-compatible providers" | Catalog count is accurate. Only Anthropic has registry test coverage; 107 providers untested. |
| "Provider-backed execution gated" | Correct for CLI. TUI has `getattr(self.data, "allow_paid", True)` default — paid calls are **ON** by default in TUI sessions. |

### Claims that need correction

| False/misleading claim | Correction |
|---|---|
| `arc providers quota reset` implies resetting provider quota | `scope: "local_quota_counters_only"` — local only, no remote |
| MCP decisions at `~/.arc/audit/decisions.jsonl` | Actual: `<workspace>/.arc/mcp/decisions.jsonl` |
| `arc providers test` performs a live connection test | It is env-var presence check only; "No network calls are made" |

---

## 4. UI / IDE Assurance Gaps

### AssuranceTab gaps

| Feature | Status | Detail |
|---|---|---|
| HITL inbox: approve/reject | ✅ wired to `respondHitlPrompt` | Token-expiry blocking enforced |
| HITL inbox: age display | ⚠️ broken for real records | `created_at` is ISO string; `_age()` returns `""` for non-epoch input |
| Audit verify | ✅ wired via `getAuditChainInfo` | Shows present/missing/degraded states |
| Audit chain path shown | ❌ absent | `~/.arc/audit/{run_id}.audit.jsonl` path not displayed to user |
| MCP decisions audit path | ❌ absent | `<workspace>/.arc/mcp/decisions.jsonl` not shown anywhere in IDE |
| Sandbox decisions | ❌ absent | No IDE surface for sandbox audit events |
| Replay stepper | ✅ has prev/next | |
| Audit HMAC vs SHA-256 distinction | ❌ absent | Users cannot tell which chain type is being verified |
| 10s auto-refresh | ⚠️ tab-switch destroys timer | AssuranceTab interval created/destroyed on every tab switch |
| Policy bypass warnings | ❌ not surfaced | `POLICY_BYPASS_WARNING` events exist but no IDE panel |

### CommandCentreTab security panels

| Panel | Status | Detail |
|---|---|---|
| HITL pending count | ✅ shows count | Not actionable — only count, no inbox |
| Sandbox Inspect input | ✅ present | Missing `aria-label` (WCAG 1.3.1 fail) |
| Provider Health | ✅ shows connected/warning | Env-var presence only, no ping |
| Workspace/Risk | ✅ shows trust level | No per-file risk score; no sensitive file warnings |

### McpWorkbenchTab security gaps

| Item | Status |
|---|---|
| Per-tool risk badges | ❌ only on past decisions, not live tool registry |
| `decisions.jsonl` audit path shown | ❌ absent |
| Trust.markerPath shown | ❌ typed but not rendered |
| `critical` and `high` risk indistinguishable | ❌ both map to 'info' CSS class |
| Policy-explain panel | ❌ absent (CLI: `arc mcp policy-explain`) |
| Registry `approved_tools`/`blocked_tools` status | ❌ absent (these fields are dead code in practice) |

### Status bar security context

| Item | TUI | IDE |
|---|---|---|
| Execution mode (fake/real) | ✅ status bar | ❌ not in status bar (bottom strip only) |
| Trust level | ❌ not in status bar | ❌ not in persistent status rail |
| Paid-call status | ✅ `[paid]` indicator | ❌ absent |
| Isolation backend | ❌ not shown | ❌ not shown |
| Profile name | ❌ not shown | ❌ not shown |
| Sandbox denial count | ❌ not shown | ❌ not shown |

---

## 5. Test Gaps

### Security surfaces with test coverage ✅

| Surface | Test file | Quality |
|---|---|---|
| TUI shell escape (all 11 paths) | `tests/tui/test_sandbox_shell_escape.py` | Strong — covers fail-closed, untrusted, destructive, timeout, oversized argv |
| MCP server trust gate | `tests/mcp/test_mcp_server.py` | Strong — per-call trust re-check, revocation, path traversal |
| MCP proxy env filtering | `tests/mcp/test_proxy_env.py` | Basic — 4 tests for `_sanitise_env()` |
| Sandbox security utils (TS) | `node/__tests__/security-utils.test.ts` | Strong — 7 functions, path traversal, injection vectors |
| Workspace escape | `tests/security/test_workspace_escape.py` | Strong — `is_path_within_root()`, chained symlinks, prefix collisions |
| Provider-backed gate | `tests/swarmgraph/test_provider_backed_and_resume.py` | Good — `gated_local`, budget, resume |
| Run ID validation (Python) | `tests/mcp/test_mcp_server.py` | Path traversal in run_id verified |
| Secret redaction (memory extraction) | `tests/memory_graph/test_phase59_memory_graph.py` | `sk-secret*` pattern; `redaction_applied=True` |
| Session export bundle redaction | `tests/test_session_export_import.py` | `sk-*` redaction in export |
| Sandbox H1-H9 hardening | `tests/security/test_hardening.py` | Comprehensive matrix |
| PR-A/B/C sandbox hardening | `tests/security/test_sandbox_pr_abc.py` | Exit code semantics, secret read deny, reason codes |
| Phase 50 trust surface audit (14 routes) | `tests/web/test_phase50_trust_surface_audit.py` | All 14 surfaces; oracle-leak prevention |
| Phase 55 provider trust (4 routes) | `tests/web/test_phase55_provider_trust.py` | 4 mutation surfaces |
| MCP drift detection | `tests/observability/test_mcp_drift.py` | Manifest hash comparison, blocked status |

### Critical test gaps

| Gap | Severity | Detail |
|---|---|---|
| MCP resources bypass risk gate | **HIGH** | No test verifying `arc://runs/{id}` resource reads go through `decide_call()` |
| `McpProxy env=None` leaks | **HIGH** | No test for `McpProxy.start()` without `env` arg not inheriting `os.environ` |
| `arc mcp serve` stdout pollution | **HIGH** | No test asserting Rich markup absent from stdout before `mcp.run()` |
| Run ID path traversal (Python storage) | **HIGH** | `base_dir / f"{run_id}.jsonl"` — no test for `../../etc/passwd` run_id |
| `_map_error()` no redaction | **MEDIUM** | No test for `str(exc)` containing API key being redacted |
| `LocalRepoProvider` secret exclusion | **MEDIUM** | No test verifying `.env` files absent from context entries |
| Groq `gsk-` key pattern redaction | **MEDIUM** | Not in `SECRET_PATTERNS`; no test |
| `load_custom_profiles()` schema version check | **MEDIUM** | No test for v1 profile loaded without migration |
| `is_valid_session_id()` path traversal | **MEDIUM** | `SESSION_ID_RE` validation exists but no dedicated tests |
| `arc policy rule-add/remove` no gate | **MEDIUM** | No test requiring confirmation before rule mutation |
| Budget exhaustion hard stop | **LOW** | `enable_budget=True` tested but cost never reaches cap limit |
| `McpCallDecisionEvent` (schema v2) not persisted | **LOW** | Protocol type exists but never written; no test for persistence path |

### IDE security tests

| Test | Status | Quality |
|---|---|---|
| `accessibility.test.tsx` | ❌ Tests fake components | 3 describe blocks are pure no-ops (`expect(true).toBe(true)`) |
| ConfigTab no `type="password"` | ✅ via contract test regex | Structural check only |
| ConfigTab no raw api_key | ✅ via contract test regex | Structural check only |
| `security-utils.test.ts` (TS side) | ✅ Real execution | Strong — path confinement, sanitization, error mapping |

---

## 6. Improved Hardening Prompt

**Target:** Fix the 5 highest-severity unresolved security gaps from prior sessions, all of which are focused on enforcement/gate correctness.

```
# Security Hardening Slice: MCP Gates + Path Traversal + Paid-call Default

## Context

ARC Studio v0.8-r-ux2. Five security gaps discovered across prior audits:

1. MCP resources (arc://runs/, arc://traces/, arc://audit/) call tool functions
   directly without going through _tool_result(), bypassing the D-02 risk gate
   and producing no audit event. This is the enforcement-surfaces.md violation:
   every tool/resource call must go through the gate.

2. McpProxy.start() with env=None (the default) passes full os.environ to the
   upstream subprocess, including all API keys. _sanitise_env() exists and works
   but is not called when env is None.

3. Run IDs are used directly in path construction without sanitization:
   `base_dir / f"{run_id}.jsonl"`. A run_id of "../../etc/passwd" would escape
   the base directory. The _SAFE_ID_RE regex exists in mcp/server.py but is
   not applied at the storage layer.

4. TUI sessions default allow_paid_calls=True via:
   `self._session.allow_paid_calls = bool(getattr(self.data, "allow_paid", True))`
   The fallback is True, silently enabling paid calls in all TUI sessions.

5. Both _map_error() implementations (anthropic.py and openai_compatible.py)
   do str(exc) with no redaction. If an SDK exception embeds a key fragment
   (e.g., in a 401 response body), it propagates unredacted into ProviderError
   messages, stream chunks, and potentially into traces.

## Scope

### 1. Route MCP resources through _tool_result (risk gate + audit)

File: python/src/agent_runtime_cockpit/mcp/server.py

Extract tool implementations into `_impl` functions and route resource
handlers through `_tool_result()`:

```python
# Pattern: extract implementation
async def _arc_run_status_impl(run_id: str) -> dict:
    """Core implementation shared by @mcp.tool and resource."""
    _validate_safe_id(run_id)
    # ... existing logic ...

@mcp.tool()
async def arc_run_status(run_id: str) -> dict:
    return await _tool_result("arc_run_status", {"run_id": run_id},
                               lambda: _arc_run_status_impl(run_id))

@mcp.resource("arc://runs/{run_id}")
async def resource_run(run_id: str) -> dict:
    # Now correctly gated:
    return await _tool_result("arc_run_status", {"run_id": run_id},
                               lambda: _arc_run_status_impl(run_id))
```

Apply same pattern to `arc://traces/{run_id}` and `arc://audit/{run_id}`.

Tests: tests/mcp/test_mcp_server.py (add):
- `test_resource_read_emits_audit_event`
- `test_resource_read_is_denied_when_untrusted`
- `test_resource_read_goes_through_risk_gate`

### 2. Fix McpProxy env=None bypass

File: python/src/agent_runtime_cockpit/mcp/proxy.py

```python
# In McpProxy.start() or __init__:
# BEFORE (dangerous — env=None → inherits full os.environ):
env = kwargs.get("env")

# AFTER:
raw_env = kwargs.get("env", os.environ.copy())
env = _sanitise_env(raw_env)  # always sanitise; never pass None to subprocess
```

This ensures that even if a caller omits the `env` argument, the subprocess
never receives API keys.

Tests: tests/mcp/test_proxy_env.py (add):
- `test_no_env_arg_does_not_leak_secrets` — call McpProxy.start() with no
  `env` kwarg while `os.environ` contains `TEST_API_KEY=secret-value`; assert
  the spawned subprocess env does NOT contain `TEST_API_KEY`.

### 3. Run ID sanitization at storage layer

File: python/src/agent_runtime_cockpit/storage/jsonl.py

Add validation function used before path construction:

```python
import re

_SAFE_RUN_ID_RE = re.compile(r'^[A-Za-z0-9][A-Za-z0-9_\-\.]{0,127}$')

def _validate_run_id(run_id: str) -> str:
    if not _SAFE_RUN_ID_RE.match(run_id):
        raise ValueError(f"Invalid run_id format: {run_id!r}")
    return run_id

def _run_path(self, run_id: str) -> Path:
    return self.base_dir / f"{_validate_run_id(run_id)}.jsonl"
```

Also add confinement check as defense-in-depth:
```python
path = self.base_dir / f"{run_id}.jsonl"
resolved = path.resolve()
if not resolved.is_relative_to(self.base_dir.resolve()):
    raise ValueError(f"Run ID {run_id!r} escapes base directory")
```

Apply to all methods: `load`, `save`, `trace_path`, `load_contract`, `load_autopsy`.

Add the same fix to `audit.py` which accepts `--chain <path>` as raw Path.

Tests: tests/cli/test_cli_runs.py (add):
- `test_run_id_path_traversal_rejected` — `arc runs get "../../etc/passwd"` exits 1
- `test_run_id_with_semicolons_rejected` — `arc runs get "run;rm -rf ."` exits 1

### 4. Fix TUI paid-call gate default

File: python/src/agent_runtime_cockpit/tui/screen.py

```python
# BEFORE (dangerous — defaults to True):
self._session.allow_paid_calls = bool(getattr(self.data, "allow_paid", True))

# AFTER:
self._session.allow_paid_calls = bool(getattr(self.data, "allow_paid", False))
```

Add this to enforcement-surfaces.md as a new surface entry:

> S-TUI-1 · TUI session paid-call default
> - What: New TUI sessions default allow_paid_calls to False.
> - Where: tui/screen.py (_get_session)
> - Gate: getattr(data, "allow_paid", False) — fail-closed default
> - Audit coverage: tests/tui/test_paid_call_default.py

Tests: tests/tui/ (add):
- `test_tui_session_allow_paid_defaults_false` — DataStore with no allow_paid
  attribute → session.allow_paid_calls is False

### 5. Add redaction to _map_error() in provider clients

File: python/src/agent_runtime_cockpit/providers/openai_compatible.py
File: python/src/agent_runtime_cockpit/providers/anthropic.py

Promote `redacted()` from `agentrouter_proxy.py` to `providers/redaction.py`:

```python
# providers/redaction.py (new, minimal):
from ..security.redaction import Redactor

def redact_provider_error(text: str, api_key: str | None = None) -> str:
    """Apply canonical redaction to a provider error string."""
    if api_key and api_key in text:
        text = text.replace(api_key, "[REDACTED]")
    return Redactor().redact(text)
```

Apply in both clients:
```python
# In _map_error():
from .redaction import redact_provider_error

def _map_error(self, exc: Exception) -> ProviderError:
    _, api_key = self._api_key()
    text = redact_provider_error(str(exc), api_key)
    # ... rest unchanged ...
```

Tests: tests/providers/ (add):
- `test_openai_compatible_map_error_redacts_api_key`
- `test_anthropic_map_error_redacts_api_key`

### 6. Add Groq/DashScope key patterns to SECRET_PATTERNS

File: python/src/agent_runtime_cockpit/security/redaction.py

```python
# Add to SECRET_PATTERNS list:
r"gsk-[A-Za-z0-9]{40,}",          # Groq API keys
r"(?i)DASHSCOPE_API_KEY\s*=\s*\S+", # DashScope env-style
```

Tests: tests/security/ (add):
- `test_redactor_covers_groq_gsk_key`
- `test_redactor_covers_dashscope_env_style`

### 7. Fix load_custom_profiles() schema version check

File: python/src/agent_runtime_cockpit/security/profiles.py

```python
def load_custom_profiles(path: Path | None = None) -> dict[str, RunProfile]:
    store_path = path or profile_store_path()
    if not store_path.exists():
        return {}
    raw = json.loads(store_path.read_text())
    
    # ADD: schema version guard
    stored_version = raw.get("version", 1)
    if stored_version > PROFILE_SCHEMA_VERSION:
        raise ValueError(
            f"Profile store version {stored_version} > supported {PROFILE_SCHEMA_VERSION}. "
            "Upgrade ARC Studio to read these profiles."
        )
    if stored_version < PROFILE_SCHEMA_VERSION:
        # v1 → v2 migration: add 'extra' field if missing
        for item in raw.get("profiles", []):
            item.setdefault("extra", {})
    
    # ... rest unchanged ...
```

Tests: tests/security/ (add):
- `test_load_custom_profiles_rejects_future_version`
- `test_load_custom_profiles_v1_migrates_silently`

## Do NOT do in this slice

- Protocol service split (separate protocol slice)
- AGENTS.md content injection (officially deferred)
- @file/@folder mention parsing
- McpWorkbenchTab decisions audit path UI (separate UI slice)
- HMAC signing decisions.jsonl (separate audit hardening slice)

## Enforcement-surfaces.md updates required

Add new surface entries:
```markdown
#### S-TUI-1 · TUI session paid-call default (2026-06-07)
- What: New TUI sessions default allow_paid_calls to False.
- Where: tui/screen.py (_get_session)
- Gate: getattr(data, "allow_paid", False) — fail-closed default

#### S-STORAGE-1 · Run ID path validation (2026-06-07)
- What: Run IDs validated against _SAFE_RUN_ID_RE before path construction.
- Where: storage/jsonl.py (_validate_run_id)
- Gate: ValueError on non-matching IDs; confinement check via is_relative_to()

#### S-MCP-RESOURCE-1 · MCP resource reads gated (2026-06-07)
- What: arc://runs/ arc://traces/ arc://audit/ resource reads go through _tool_result().
- Where: mcp/server.py resource handlers
- Gate: same D-02 risk gate as @mcp.tool() handlers
```

## Verification

After all changes:
```bash
cd python && uv run pytest tests/mcp/ tests/tui/ tests/storage/ tests/providers/ tests/security/ -q
./scripts/audit-enforcement-surfaces.sh
```

## Non-negotiable constraints (AGENTS.md)

- Run ID validation must be fail-closed (reject on non-match, never allow on error)
- env sanitisation must always call _sanitise_env(); never pass None to subprocess
- TUI paid-call gate default MUST be False
- _map_error() redaction MUST use the canonical Redactor from security/redaction.py
- enforcement-surfaces.md must be updated to reflect all new surfaces
- Document failures honestly; do not claim fixed unless tests pass and run
```

---

## Appendix: Verified Security Properties

### Properties confirmed correct throughout all sessions

| Property | Source evidence |
|---|---|
| `EnforcementContext.dry_run=True` denies all gates unconditionally | `enforcement.py` — dry_run branch raises `DryRunAbort` before bypass check |
| `shell=True` fully removed from TUI shell escape | `test_sandbox_shell_escape.py::test_allowed_command_executes_argv_without_shell` |
| 4 builtin profiles are frozen (`@dataclass(frozen=True)`) | `profiles.py` |
| MCP HMAC audit on output AND args | `mcp/server.py::_tool_result` → `Redactor.redact_dict()` on both |
| MCP `arc_trace_read` has `_resolve_workspace_child` path guard | `mcp/server.py` |
| Sandbox approval tokens stored as hash only | `cli/sandbox.py` (enforcement-surfaces.md notes legacy plain-text remains for existing tokens during alpha) |
| Rate-limited bypass warnings (1 per run/surface) | `_bypass_rate_limit.py::should_emit_warning()` |
| Provider-backed execution default: `fake/offline` | `cli/exec.py` default `--runtime-mode fake/offline` |
| Budget broker default-off | `ARC_BUDGET_BROKER_URL` required, `ARC_ALLOW_LIVE_PROVIDER_TESTS=true` |
| Remote MCP: explicitly deferred | `roadmap.md` Non-Negotiable Boundary |
| microVM: one gated proof for `pwd` only | ADR-024; enforcement-surfaces.md microVM section |
| `arc providers quota reset` local-only | `scope: "local_quota_counters_only"` in CLI output |
| policy_linter 8 rules are pure deterministic functions | `security/policy_linter.py` — no I/O, no state |

### Quick audit reference: confirmed-gap summary

| Gap | Filed | Fix priority |
|---|---|---|
| MCP resources bypass D-02 risk gate | security audit 2026-06-07 | P0 |
| McpProxy env=None inherits full os.environ | security audit 2026-06-07 | P0 |
| Run ID path traversal in storage layer | CLI audit 2026-06-07 | P0 |
| TUI session allow_paid defaults True | provider audit + security audit | P0 |
| _map_error() unredacted str(exc) | provider audit 2026-06-07 | P1 |
| .env/*.key in LocalRepoProvider context | memory/context audit 2026-06-07 | P1 |
| Groq/DashScope keys not in SECRET_PATTERNS | provider audit 2026-06-07 | P1 |
| load_custom_profiles() no schema version check | swarmgraph/security audit | P1 |
| McpCallDecisionEvent (schema v2) never persisted | MCP audit 2026-06-07 | P2 |
| Registry approved_tools/blocked_tools dead code | MCP audit 2026-06-07 | P2 |
| decisions.jsonl no HMAC/sequence | MCP audit 2026-06-07 | P2 |
| workspace inventory/search no trust gate | workspace audit 2026-06-07 | P2 |
| arc policy rule-add/remove no gate | CLI audit 2026-06-07 | P2 |
| arc sandbox audit-compact no gate | CLI audit 2026-06-07 | P2 |
| No arc memory wipe command | memory audit 2026-06-07 | P3 |
| Memory graph has no TTL/retention policy | memory audit 2026-06-07 | P3 |
