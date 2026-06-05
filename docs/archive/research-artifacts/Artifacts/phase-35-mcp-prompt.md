---
title: Phase 35 — MCP Python SDK Implementation Prompt
parent: docs/research/adapter-roadmap.md
date: 2026-05-22
status: DRAFT — ready for PR start when Phase 34 Baseline Complete
mandatory_review: true
pinned_upstream: mcp >=1.27,<2.0
---

# Phase 35 — MCP Python SDK Adapter

## Goal

Detection and live-streaming support for the Model Context Protocol Python SDK as an MCP client. ARC Studio consumes MCP servers as external capability providers; it does not build MCP servers in this phase.

**Critical posture:** Every MCP server connection is external code. The trust model is fundamentally different from in-process framework adapters. Mandatory architecture review sign-off required.

## Transport support matrix

| Transport | Upstream status | Gate | ARC support |
|-----------|----------------|------|-------------|
| stdio | Stable | `enforce_shell_gate` (spawns subprocess) | T1+T3 |
| Streamable HTTP | Stable, superseding SSE | `enforce_network_gate` + lifetime cap | T1+T3 |
| SSE | **Deprecated** | `enforce_network_gate` + `POLICY_BYPASS_WARNING` | T1 detection only; T3 emits bypass warning |

## Trust-model invariants

1. MCP servers are external code — treated as new trust boundary independent of workspace trust.
2. Per-server allow gesture required — `--allow-mcp <server-id>` or session-scoped consent.
3. No auto-discovery from workspace files — discovered but not auto-connected.
4. Server identity is locally-observed (SHA-256 of command/args/transport), not server-attested.

## Commit series

### Commit 35.1.1 — Optional dependency wiring

**Files:** `python/pyproject.toml` — `[project.optional-dependencies]` group `mcp = ["mcp>=1.27,<2.0"]`. `mcp[cli]` documented but not bundled.

**Tests:** 3 — core install doesn't import mcp, extra resolves, cli extra not pulled implicitly.

### Commit 35.1.2 — Detection module

**Files:** `adapters/mcp/{__init__.py,detect.py,capabilities.py,_server_id.py}`.

Probe mcp import. Enumerate configured servers from ARC config only (not workspace). Compute stable `server_id` per transport. Report each in `arc runtimes list --type mcp-server` with trust_status.

**Tests:** 10 — not installed, installed no servers, stdio server, HTTP server, SSE server with deprecation warning, workspace-discovered never trusted, different args → different IDs, env values excluded from ID, golden output, no network probes.

### Commit 35.3.1 — Stdio transport runner

**Files:** `adapters/mcp/{runner.py,_stdio_runner.py,_event_translator.py}`.

Wrap `mcp.client.stdio.stdio_client()` with `enforce_shell_gate`. Reuse existing TypedRunEvent variants — no union extension needed. Session lifecycle: RunStart → ToolDiscovery (initialize) → ToolDiscovery (list_tools) → ToolStart/ToolEnd (call_tool) → RunEnd.

**Tests:** 12 — untrusted server denied, trusted succeeds, TOCTOU revocation, dry-run, lifecycle ordering, call_tool ordering, tool error, HMAC replay, argument_hash determinism, payload storage by hash, server-claimed vs computed ID, untrusted workspace path in args.

### Commit 35.3.2 — Streamable HTTP transport

**Files:** `adapters/mcp/_streamable_http_runner.py`, `_connection_lifetime.py`.

Wrap `mcp.client.streamable_http.streamablehttp_client()` with `enforce_network_gate`. Connection-lifetime cap (default 3600s, configurable via `--mcp-streamable-http-max-lifetime`).

**Tests:** 10 — untrusted denied, trusted succeeds, lifetime cap reached, TOCTOU, dry-run, HMAC replay, cap=0 rejected, default cap enforced, per-session cap, cap recorded in trace.

### Commit 35.3.3 — SSE transport (deprecated)

**Files:** `adapters/mcp/_sse_runner.py`.

Wrap `mcp.client.sse.sse_client()` with `enforce_network_gate`. Always emits `POLICY_BYPASS_WARNING` per session with `suggested_remediation="Migrate to Streamable HTTP"`.

**Tests:** 6 — trusted succeeds + 1 bypass warning, untrusted denied, TOCTOU, HMAC replay, remediation string snapshot, lifetime cap inherits.

### Commit 35.3.4 — Per-server allow flag and dialog

**Files:** `cli/_mcp_flags.py`, extension `MCPConsentDialog.tsx`.

`--allow-mcp <server-id>` (comma-separated, no wildcards). Dialog options: Deny, Allow once, Allow for session. Headless denies by default.

**Tests:** 4 Python + 3 TypeScript — flag accepts server ID, wildcard rejected, headless denies, dialog renders correctly, Allow once per-op, Allow for session persists, Deny aborts.

### Commit 35.3.5 — E2E test

**Files:** `tests/adapters/mcp/test_e2e.py`, `tests/fixtures/adapters/mcp/fake_server.py`.

In-process fake server using `mcp.server.fastmcp.FastMCP` with in-memory transport. 3 tools, 2 resources, 1 prompt, 1 error-raising tool. One E2E test per transport.

## Verification

```bash
pytest python/tests/adapters/mcp/ -v
pytest python/tests/packaging/test_extras_mcp.py -v
bash scripts/audit-enforcement-surfaces.sh
bash scripts/check-banned-claims.sh
pytest python/tests/ -q
pnpm --filter @arc/arc-extension test
```

## Exit gate

Mandatory architecture review. No new TypedRunEvent variants added (reuse table holds; union extension would require ADR before merge). Per-server consent documented. SSE deprecation warning fires as specified.
