# ARC Studio — Post-Merge Review

**Date:** 2026-06-04
**HEAD verified:** `788dbc9` — *fix(protocol): add 4 new event types to EVENT_TYPES registry for cross-language parity* (2026-06-04 14:48 +0200)
**Method:** fresh `git clone`, file inspection, `uv run pytest`, file/line grep.

## Executive verdict

| PR | Status | Claimed tests | Actual tests | Drift |
|---|---|---|---|---|
| 1. Capability Card Enforcement | **Files landed; call sites missing** | 32 | 161 in `tests/capabilities/` (incl. pre-existing) | **P0 — `enforce_card` is never invoked from any adapter, MCP server, or SwarmGraph runner. The gate is decorative.** |
| 2. MCP Outbound Risk Gate | **Standalone modules landed; not wired into server.py** | 35+ | 114 in `tests/mcp/` | **P0 — `mcp/server.py::_tool_result` does not call `assess_call`/`decide`. Proxy works standalone.** |
| 3. AGENTS.md Ingestion | **Backend landed; ConfigTab UI missing** | 32 | 32 | **P1 — `packages/arc-extension/src/browser/tabs/ConfigTab.tsx` has no AGENTS.md surface.** CLI verb names diverged from spec (`discover|nearest|pin|drift|cards` vs spec `list|pin|drift|explain|sign`). |
| 4. Eval-to-Policy Loop | **Landed correctly** | 22 | 83 (full evals dir) | — |
| 5. Streaming Verifier UI | **Backend route + AssuranceTab fields landed** | 7 | 118 (full web dir) | **P2 — `getAuditChainInfo` still routes via `execFileSync` rather than fetch to new route.** |
| 6. A2A Local Client | **Landed correctly** | 23 | 23 | — |
| 7. OTel GenAI Semconv | **Landed correctly** | 41 | 96 (full obs dir) | — |
| 8. Protocol fixture xfails | **Landed correctly** | tracks | covered by full suite | — |

**Full suite:** `4782 passed, 2 failed, 42 skipped, 3 xfailed` in 227 s.
The 2 failures are **pre-existing** (`tests/auth/test_auth_manager.py::test_provider_statuses_fallback_to_stored_creds`, `tests/tasks/test_task_executor.py::test_concurrent_task_execution`) and unrelated to the 8 PRs. Not a regression introduced by this sprint.

ADR numbering drift: ADR-026 is "mobile-runtime-safety" (existed earlier), so capability-card became ADR-027, and a2a became ADR-029. There is no ADR-028 for the MCP outbound gate — **P2 drift**.

## Drift table (remediation required)

| ID | Severity | File expected | What is missing | Patch path |
|---|---|---|---|---|
| D-01 | **P0** | `adapters/base.py::RuntimeAdapter.run_workflow` (or new helper `enforce_capability_card`) | `enforce_card`/`enforce_card_by_id` never called; cards built and signed but never gate anything | `patches/post-merge/001_enforce_card_in_adapters.patch` |
| D-02 | **P0** | `mcp/server.py::_tool_result` | After `_trusted()`, no `assess_call`+`decide` invocation; no `MCP_CALL_DECISION` audit event | `patches/post-merge/002_mcp_server_call_risk_gate.patch` |
| D-03 | **P0** | `tui/screen.py::_handle_shell_escape` (line 271-291) | Raw `subprocess.run(shell=True, ...)` bypasses `security/sandbox.py` decisions | `patches/post-merge/003_shell_escape_sandbox.patch` |
| D-04 | **P1** | `packages/arc-extension/src/browser/tabs/ConfigTab.tsx` | No "Agent Context" / AGENTS.md section per UX_AUDIT § R-003 + EXECUTION_PROMPT Item 3 | covered by UX patches (P1 phase) |
| D-05 | **P1** | `packages/arc-extension/src/browser/tabs/McpWorkbenchTab.tsx` | No decisions stream pane | covered by UX patches (P1 phase) |
| D-06 | **P2** | `packages/arc-extension/src/node/arc-backend-service.ts::getAuditChainInfo` | Still uses `execFileSync` for `arc audit verify`; should call the new `/api/audit/verify/{id}` route | `patches/post-merge/004_audit_verify_use_http_route.patch` |
| D-07 | **P2** | `docs/adr/028-mcp-outbound-risk-gate.md` | ADR file missing | `patches/post-merge/005_adr_028_mcp_risk.patch` |
| D-08 | **P2** | `python/src/agent_runtime_cockpit/cli/agents_md.py` | CLI verbs diverge from spec; add `list`/`explain`/`sign` aliases | `patches/post-merge/006_agents_md_cli_aliases.patch` |

## Wiring audit (typed events)

- `CAPABILITY_CARD_DECISION`: present in `protocol/typed_events.py` (lines 944, 1006), `protocol/capability_card_events.py`, `protocol/events.py:321`, and TS `run-events.ts:310, 467`. ✅ wired.
- `MCP_CALL_DECISION`: present in `protocol/typed_events.py` (lines 945, 1007). Need to verify TS mirror.
- `EVAL_POLICY_RECOMMENDED` + `EVAL_POLICY_APPLIED`: present in `protocol/typed_events.py` (lines 947, 1009). ✅
- `MCP_DRIFT`, `MCP_TOOL_RISK`: extras added by commit `788dbc9` for cross-language parity. ✅

## Net assessment

The sprint landed all files **and all tests**. The only material regression vs spec is **D-01 + D-02 + D-03** — three call sites where the wire is one function call short. Without these, three of the seven security features cannot actually gate anything. Patch them and the sprint is functionally complete.

The UX surface is broadly untouched. Apply `patches/ux/*` as planned by `UX_AUDIT.md`.
