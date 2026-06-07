# ARC Studio Unified Implementation Backlog — 2026-06-07

> **Synthesis of 17 category audits** in `docs/research-findings/`.  
> **Prioritization rule:** Prefer slices that improve user-visible product coherence, safety, CLI/TUI/IDE parity, evidence visibility, and release confidence — without overclaiming production readiness.  
> All findings are read-only analysis. No production code changed by the audits.

---

## 1. Unified Feature Coverage Matrix

Legend: ✅ solid · ⚠️ partial/gap · ❌ broken/missing · 🔒 security gap

| Domain | CLI | TUI | IDE | Backend | Tests | Top gap |
|---|---|---|---|---|---|---|
| **SwarmGraph runtime** | ✅ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | SDK events never reach IDE; 2 disconnected runners |
| **Consensus/DAG** | ✅ | ❌ | ⚠️ | ✅ | ✅ | IR has no cycle detection; DagPlannerViz orphaned |
| **Memory/Context** | ✅ | ⚠️ | ❌ | ✅ | ✅ | AGENTS.md content invisible; 🔒 `.env` in context |
| **Workspace/Search** | ✅ | ⚠️ | ❌ | ✅ | ⚠️ | 🔒 `.env` in inventory; no result cap; no trust gate |
| **MCP/Tools** | ✅ | ❌ | ⚠️ | ⚠️ | ⚠️ | 🔒 resources bypass risk gate; 🔒 proxy env=None |
| **Providers/Budget** | ✅ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | 🔒 TUI paid-call=True; 🔒 _map_error unredacted; router dead |
| **CLI structure** | ✅ | n/a | n/a | n/a | ⚠️ | 🔒 run ID path traversal; non-compliant JSON; rule-add ungated |
| **TUI** | n/a | ⚠️ | n/a | n/a | ⚠️ | streaming broken; CommandPalette empty; Ctrl+O/R stubs |
| **Theia IDE arch** | n/a | n/a | ⚠️ | ⚠️ | ⚠️ | keybinding conflicts; 🔒 notif env; dead widget; 72-method protocol |
| **UI/UX** | n/a | ⚠️ | ⚠️ | n/a | ❌ | 12-tab flat nav; critical=high color; a11y tests no-op |
| **Security/Policy** | ✅ | ⚠️ | ⚠️ | ✅ | ✅ | 🔒 MCP resources; 🔒 proxy env; profile schema no migration |
| **Runs/Events** | ✅ | ✅ | ⚠️ | ⚠️ | ⚠️ | startRun blocks 120s; liveEvents unbounded; no active-run UI |
| **Audit/Evidence** | ✅ | ⚠️ | ⚠️ | ✅ | ⚠️ | receipts silently absent; audit_path not shown; fork no journal |
| **CI/TestBench** | ✅ | ❌ | ⚠️ | ✅ | ✅ | TestBenchTab no Run button; advisory not labeled |
| **Notifications** | ✅ | ✅ | ⚠️ | ⚠️ | ✅ | 🔒 notif no env allowlist; protocol:"sse" lie; hook broken |
| **Config/Profiles** | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | profile v1 no migration; SettingsView theme/mode not saved |
| **Release/Packaging** | ⚠️ | n/a | ⚠️ | n/a | ⚠️ | typo entrypoint; license mismatch; no prod build gate |
| **A11y/Perf/Reliability** | n/a | ⚠️ | ⚠️ | ⚠️ | ❌ | no ErrorBoundary; liveEvents OOM; axe tests fake |

### Cross-cutting themes
1. **Secret exposure** (5 audits): `.env` in context/inventory, `_map_error` unredacted, proxy env=None, notif service env, TUI shell stdout
2. **Fail-open defaults** (3 audits): TUI paid-call=True, profile schema no version check, RunsTab silent `.catch(()=>null)`
3. **Blocking sync calls** (3 audits): startRun 120s, saveConfig 10s, getConfigStatus 20s — all freeze Node backend
4. **Dead/orphaned code** (4 audits): ArcRunTimelineWidget, arena-frontend-module, ArcContextDrawer, NotificationOutbox, DagPlannerViz/ConsensusEvidenceCard/HitlApprovalPanel
5. **CLI/IDE/TUI parity holes** (every audit): SwarmGraph events, TestBench run, evals, AGENTS.md, @mention, active-run panel

---

## 2. Top 25 Implementation Slices

> Ordered by priority. P0 = safety/correctness; P1 = product coherence/parity; P2 = polish/coverage.

---

### SLICE 1 — Sensitive file exclusion in context & workspace scan `[P0 · Security]`
- **Objective:** Stop `.env`, `*.key`, `credentials.*`, `id_rsa` from entering LLM context and workspace inventory output.
- **Files:** `python/src/agent_runtime_cockpit/workspace.py`, `context/providers/local_repo.py`
- **Dependencies:** None
- **Safety concerns:** This IS a safety fix — secrets leaking into prompts. Must be additive (never changes non-sensitive traversal).
- **Tests:** `test_env_file_not_in_inventory`, `test_key_file_not_in_inventory`, `test_env_not_in_context_pack`, `test_normal_py_still_included`
- **Docs:** Update `docs/security/enforcement-surfaces.md` with new exclusion surface
- **Acceptance:** `.env`, `id_rsa`, `*.key`, `credentials.yaml` never appear in `arc workspace inventory --json` or context pack entries; normal `.py`/`.ts` files still included
- **Verify:** `cd python && uv run pytest tests/cli/test_workspace_inventory.py tests/context/ -q`
- **Now:** Highest-severity secret exposure, appears in 2 audits, trivial scope, no breaking change.

---

### SLICE 2 — TUI paid-call gate fail-closed default `[P0 · Security]`
- **Objective:** Change TUI session `allow_paid_calls` default from `True` to `False`.
- **Files:** `python/src/agent_runtime_cockpit/tui/screen.py` (`_get_session`)
- **Dependencies:** None
- **Safety concerns:** Currently any TUI session can make paid calls without opt-in. One-line fix.
- **Tests:** `test_tui_session_allow_paid_defaults_false`
- **Docs:** Add `S-TUI-1` surface to enforcement-surfaces.md
- **Acceptance:** `getattr(self.data, "allow_paid", False)`; new sessions default to no paid calls
- **Verify:** `cd python && uv run pytest tests/tui/ -q`
- **Now:** One-character fix; closes a real money-spending fail-open.

---

### SLICE 3 — Provider `_map_error()` redaction `[P0 · Security]`
- **Objective:** Apply canonical `Redactor` to `str(exc)` in both provider clients before wrapping in `ProviderError`.
- **Files:** `providers/anthropic.py`, `providers/openai_compatible.py`, new `providers/redaction.py`
- **Dependencies:** None
- **Safety concerns:** SDK exception bodies may embed key fragments; currently propagate raw into traces/stream chunks.
- **Tests:** `test_anthropic_map_error_redacts_api_key`, `test_openai_compatible_map_error_redacts_api_key`
- **Docs:** None
- **Acceptance:** A simulated exception containing `sk-secret...` produces a `ProviderError` with `[REDACTED]`
- **Verify:** `cd python && uv run pytest tests/providers/ -q`
- **Now:** Secret exposure in error paths; small, isolated.

---

### SLICE 4 — MCP resources through risk gate `[P0 · Security]`
- **Objective:** Route `arc://runs/`, `arc://traces/`, `arc://audit/` resource handlers through `_tool_result()` so they hit the D-02 risk gate and write audit events.
- **Files:** `mcp/server.py`
- **Dependencies:** None
- **Safety concerns:** Resources currently bypass the entire risk gate and audit trail — a documented enforcement-surfaces.md violation.
- **Tests:** `test_resource_read_emits_audit_event`, `test_resource_read_denied_when_untrusted`, `test_resource_goes_through_risk_gate`
- **Docs:** Update enforcement-surfaces.md S-26.MCP.2
- **Acceptance:** Resource reads produce `mcp.events.jsonl` entries; untrusted workspace denies resource reads
- **Verify:** `cd python && uv run pytest tests/mcp/ -q`
- **Now:** Closes a confirmed enforcement bypass.

---

### SLICE 5 — MCP proxy env=None fix `[P0 · Security]`
- **Objective:** `McpProxy.start()` must always sanitise env; never pass `None` (which inherits full `os.environ` with API keys).
- **Files:** `mcp/proxy.py`
- **Dependencies:** None
- **Safety concerns:** Default proxy invocation leaks all secrets to upstream subprocess.
- **Tests:** `test_no_env_arg_does_not_leak_secrets`, `test_empty_env_dict_is_safe`
- **Docs:** None
- **Acceptance:** `McpProxy.start()` with no `env` arg → subprocess does NOT receive `TEST_API_KEY`
- **Verify:** `cd python && uv run pytest tests/mcp/test_proxy_env.py -q`
- **Now:** Secret leak; tiny change.

---

### SLICE 6 — Run ID path-traversal sanitization `[P0 · Security]`
- **Objective:** Validate run IDs against a safe regex + confinement check before path construction in the storage layer.
- **Files:** `storage/jsonl.py`, `cli/audit.py` (`--chain` path)
- **Dependencies:** None
- **Safety concerns:** `base_dir / f"{run_id}.jsonl"` with `run_id="../../etc/passwd"` escapes the directory.
- **Tests:** `test_run_id_path_traversal_rejected`, `test_run_id_special_chars_rejected`, `test_valid_run_id_accepted`
- **Docs:** Add `S-STORAGE-1` to enforcement-surfaces.md
- **Acceptance:** `arc runs get "../etc/passwd"` exits 1 with validation error
- **Verify:** `cd python && uv run pytest tests/cli/test_cli_runs.py -q`
- **Now:** Path traversal in security-sensitive code.

---

### SLICE 7 — Theia NotificationBackendService env allowlist `[P0 · Security]`
- **Objective:** `spawn('arc', args)` must use `buildArcCliEnv()` instead of inheriting full `process.env`.
- **Files:** `packages/arc-extension/src/node/services/notification-service.ts`
- **Dependencies:** None
- **Safety concerns:** Currently passes all API keys to the child process.
- **Tests:** `test_spawn_uses_env_allowlist`
- **Docs:** Update enforcement-surfaces.md S-63.2
- **Acceptance:** Spawned process env excludes `OPENAI_API_KEY`, includes `PATH`
- **Verify:** `pnpm --filter arc-extension test`
- **Now:** Only CLI-bridge service missing env allowlist.

---

### SLICE 8 — `arc mcp serve` stdout framing fix `[P0 · Correctness]`
- **Objective:** Redirect Rich console output to stderr before `mcp.run(transport="stdio")` so MCP framing isn't corrupted.
- **Files:** `cli/mcp.py`
- **Dependencies:** None
- **Safety concerns:** Pre-amble Rich markup breaks every MCP client connecting to ARC.
- **Tests:** `test_serve_stdout_clean_for_mcp_framing`
- **Docs:** None
- **Acceptance:** stdout contains no non-JSON lines before server init
- **Verify:** `cd python && uv run pytest tests/mcp/test_mcp_server.py -q`
- **Now:** Silently breaks the advertised MCP server feature.

---

### SLICE 9 — TUI streaming widget refresh `[P0 · Product coherence]`
- **Objective:** Refresh the last `MarkdownBlock` during `is_streaming` so streamed tokens are visible in the transcript.
- **Files:** `tui/widgets/transcript.py`, `tui/widgets/markdown_block.py`
- **Dependencies:** None
- **Safety concerns:** None — must wrap in try/except to never crash poll loop.
- **Tests:** `test_streaming_tokens_appear_in_markdown_block`
- **Docs:** None
- **Acceptance:** `append_to_last()` during streaming → MarkdownBlock shows updated content within one poll tick
- **Verify:** `cd python && uv run pytest tests/tui/ -q`
- **Now:** The single most visible TUI failure — streamed responses appear blank until the next message.

---

### SLICE 10 — McpWorkbenchTab risk badge color + aria-label `[P0 · A11y]`
- **Objective:** Map `critical`→danger (red), `high`→warning (amber); add `aria-label="Risk level: X"`.
- **Files:** `packages/arc-extension/src/browser/tabs/McpWorkbenchTab.tsx`, `arc-studio-widget.css`
- **Dependencies:** None
- **Safety concerns:** WCAG 1.4.1 — critical risk currently indistinguishable from high (both blue).
- **Tests:** Contract test asserting `RISK_VARIANT['critical'] !== RISK_VARIANT['high']`
- **Docs:** None
- **Acceptance:** Critical badge is red, high is amber, both have aria-labels
- **Verify:** `pnpm --filter arc-extension test`
- **Now:** WCAG violation; misleads users about risk severity.

---

### SLICE 11 — RunsTab honest receipt/autopsy/contract states `[P1 · Evidence]`
- **Objective:** Replace `.catch(() => null)` with explicit error/missing/loading states for the 3 run artifact cards.
- **Files:** `packages/arc-extension/src/browser/tabs/RunsTab.tsx`
- **Dependencies:** None
- **Safety concerns:** None
- **Tests:** Contract test: "shows receipt unavailable state"
- **Docs:** None
- **Acceptance:** Missing receipt shows "Receipt unavailable" banner with CLI hint, not silent absence
- **Verify:** `pnpm --filter arc-extension test`
- **Now:** Evidence visibility — users can't tell missing from broken.

---

### SLICE 12 — startRun async (non-blocking Node backend) `[P1 · Reliability]`
- **Objective:** Convert `startRun()`, `getConfigStatus()`, `saveConfig()`, `listRuntimeCapabilities()` from `execFileSync` to `execFileAsync`.
- **Files:** `node/services/run-lifecycle-service.ts`, `node/services/config-service.ts`
- **Dependencies:** None
- **Safety concerns:** None — behavior-preserving.
- **Tests:** `test_startRun_does_not_block_other_rpc`
- **Docs:** None
- **Acceptance:** A second RPC call completes while a 120s run executes
- **Verify:** `pnpm --filter arc-extension test`
- **Now:** Backend freezes for up to 120s during a run; degrades all IDE interactivity.

---

### SLICE 13 — IDE status rail (mode/trust/model/daemon) `[P1 · UX coherence]`
- **Objective:** Persistent top rail in ArcStudioWidget showing execution mode, trust level, provider/model, daemon status with semantic colors.
- **Files:** `arc-studio-widget.tsx`, `tokens.css`, `arc-studio-widget.css`
- **Dependencies:** Uses existing `getConfigStatus()`
- **Safety concerns:** None
- **Tests:** Contract test for rail elements + aria-label
- **Docs:** None
- **Acceptance:** Rail shows `[fake] [untrusted ⚠] [model] [● daemon]`; mode colored by risk
- **Verify:** `pnpm --filter arc-extension test`
- **Now:** Mode/trust currently buried in 11px bottom strip; users can't tell what mode they're in.

---

### SLICE 14 — Theia keybinding conflict fix `[P1 · UX]`
- **Objective:** Replace `Ctrl+E`/`Ctrl+Shift+S`/`Ctrl+H` (conflict with Go to File/Save All/Find&Replace) with ARC-safe bindings + `when` guards; redirect to ArcStudioWidget not legacy.
- **Files:** `arc-keybinding-contribution.ts`
- **Dependencies:** None
- **Safety concerns:** None — but coordinate with release notes for muscle-memory change.
- **Tests:** Contract test asserting no conflict with core bindings
- **Docs:** Release note
- **Acceptance:** Core Theia keybindings work; ARC bindings have `when: focusedView == arc-studio-widget`
- **Verify:** `pnpm --filter arc-extension test`
- **Now:** Breaks three of the most-used editor keybindings.

---

### SLICE 15 — Remove dead code (3 widgets/modules) `[P1 · Maintainability]`
- **Objective:** Delete `ArcRunTimelineWidget` (no contribution), `arena-frontend-module.ts` (never loaded), and `notifications/outbox.py` (no consumer).
- **Files:** `arc-run-timeline-widget.tsx`, `arc-extension-frontend-module.ts`, `arena-frontend-module.ts`, `notifications/outbox.py`, `notifications/__init__.py`
- **Dependencies:** None
- **Safety concerns:** Confirm no imports reference these (audits confirm none).
- **Tests:** Existing suite must stay green
- **Docs:** None
- **Acceptance:** Files removed; build green; no broken imports
- **Verify:** `pnpm typecheck && pnpm build && cd python && uv run pytest -q`
- **Now:** Reduces confusion; removes ~1000 lines of unreachable code.

---

### SLICE 16 — MCP proxy timeout + 1MB cap structured error `[P1 · Reliability]`
- **Objective:** Catch `asyncio.TimeoutError` in `send_raw()` → return JSONRPC error (not crash loop); return structured error on 1MB truncation (not corrupt JSON).
- **Files:** `mcp/proxy.py`
- **Dependencies:** None
- **Safety concerns:** Currently a hung upstream crashes the whole proxy session.
- **Tests:** `test_proxy_timeout_returns_jsonrpc_error`, `test_proxy_1mb_cap_structured_error`
- **Docs:** None
- **Acceptance:** Upstream hang → JSONRPC error returned, proxy survives; oversized response → structured truncation error
- **Verify:** `cd python && uv run pytest tests/mcp/test_proxy.py -q`
- **Now:** Reliability of the MCP proxy under failure.

---

### SLICE 17 — Profile schema version guard + migration `[P1 · Correctness]`
- **Objective:** `load_custom_profiles()` rejects future versions, migrates v1→v2.
- **Files:** `security/profiles.py`
- **Dependencies:** None
- **Safety concerns:** None
- **Tests:** `test_rejects_future_version`, `test_v1_migrates_silently`, `test_v2_loads_correctly`
- **Docs:** None
- **Acceptance:** v999 profile raises ValueError; v1 profile gets `extra={}` added
- **Verify:** `cd python && uv run pytest tests/security/test_profiles.py -q`
- **Now:** AGENTS.md P0 item (profile schema reconciliation); small.

---

### SLICE 18 — SwarmGraph SDK → IDE event bridge `[P1 · Product coherence]`
- **Objective:** `translate_swarmgraph_event()` maps SDK `SwarmGraphEventKind` events to typed `RunEvent`s wired into `_run_native_workflow()` so they reach the IDE via SSE.
- **Files:** new `adapters/swarmgraph/event_bridge.py`, `adapters/swarmgraph.py`
- **Dependencies:** None (offline, no provider)
- **Safety concerns:** None — additive event translation.
- **Tests:** `test_topology_event_translated`, `test_consensus_event_translated`
- **Docs:** None
- **Acceptance:** Native SwarmGraph run emits SWARMGRAPH_TOPOLOGY/CONSENSUS events visible in the IDE event stream
- **Verify:** `cd python && uv run pytest tests/swarmgraph/ tests/protocol/ -q`
- **Now:** Unblocks all SwarmGraph IDE panels (the biggest structural gap in SwarmGraph audit).

---

### SLICE 19 — TestBenchTab Run button (safe policy) `[P1 · Parity]`
- **Objective:** Add a Run button to each detected test command, routed through `arc testbench run --policy local-safe`.
- **Files:** `packages/arc-extension/src/browser/tabs/TestBenchTab.tsx`, `arc-protocol.ts`, `arc-backend-service.ts`
- **Dependencies:** None
- **Safety concerns:** Must use `local-safe` policy; show exit code/denial clearly.
- **Tests:** Contract test: "has Run button per command"
- **Docs:** None
- **Acceptance:** Run button executes detected test via sandbox; shows pass/fail/denied
- **Verify:** `pnpm --filter arc-extension test`
- **Now:** TestBenchTab is detect-only — false affordance; closes a CLI/IDE parity gap.

---

### SLICE 20 — Search result cap + sensitive exclusion `[P1 · Reliability+Security]`
- **Objective:** `MAX_SEARCH_RESULTS = 200` in `workspace_search()`, pathlib fallback timeout, realpath confinement.
- **Files:** `cli/studio_workspace.py`
- **Dependencies:** SLICE 1 (sensitive exclusion patterns)
- **Safety concerns:** No cap → OOM/flood on large repos; weak `relative_to()` confinement.
- **Tests:** `test_search_result_cap`, `test_search_pathlib_timeout`, `test_search_confinement_realpath`
- **Docs:** README `arc workspace search`
- **Acceptance:** 300-match repo returns ≤200 with `truncated: true`; symlink `--path` rejected
- **Verify:** `cd python && uv run pytest tests/cli/test_workspace_search.py -q`
- **Now:** Memory safety + path confinement; pairs with SLICE 1.

---

### SLICE 21 — Per-tab React ErrorBoundary `[P1 · Reliability]`
- **Objective:** Wrap each ArcStudioWidget tab panel in an ErrorBoundary so a tab crash doesn't white-screen the whole widget.
- **Files:** `arc-studio-widget.tsx`
- **Dependencies:** None
- **Safety concerns:** None
- **Tests:** `test_tab_error_isolated`
- **Docs:** None
- **Acceptance:** A throwing tab shows an error banner with Retry; other tabs still work
- **Verify:** `pnpm --filter arc-extension test`
- **Now:** No error boundaries exist anywhere; one bad tab crashes everything.

---

### SLICE 22 — Real jest-axe accessibility coverage `[P2 · A11y]`
- **Objective:** Replace fake-component accessibility tests with real renders + axe; remove 3 no-op describe blocks.
- **Files:** `packages/arc-extension/src/browser/__tests__/accessibility.test.tsx`
- **Dependencies:** SLICE 10 (risk badge fix), SLICE 13 (status rail)
- **Safety concerns:** None
- **Tests:** This IS the test slice
- **Docs:** None
- **Acceptance:** Real `McpWorkbenchTab`/`ConfigTab`/`RunsTab` pass `axe()`; no `expect(true).toBe(true)`
- **Verify:** `pnpm --filter arc-extension test`
- **Now:** Current a11y tests provide zero protection.

---

### SLICE 23 — liveEvents bounded buffer `[P2 · Performance]`
- **Objective:** Cap `liveEvents` at 2000 in ArcEventStreamWidget; show eviction banner.
- **Files:** `arc-event-stream-widget.tsx`
- **Dependencies:** None
- **Safety concerns:** None
- **Tests:** `test_liveEvents_capped_at_2000`
- **Docs:** None
- **Acceptance:** 2500 events → array length 2000, eviction banner visible
- **Verify:** `pnpm --filter arc-extension test`
- **Now:** OOM risk on long-running streams.

---

### SLICE 24 — Release hygiene (entrypoint typo + license + prod build) `[P2 · Release]`
- **Objective:** Fix `arch-studio-cli`→`arc-studio-cli`; reconcile license (Apache-2.0 vs Proprietary); add `pnpm build:prod` to release gate.
- **Files:** `python/pyproject.toml`, `scripts/release_check.sh`, `scripts/bootstrap.sh`
- **Dependencies:** None
- **Safety concerns:** None
- **Tests:** Release gate check
- **Docs:** README install section honesty pass
- **Acceptance:** No typo; license consistent; prod build verified in CI
- **Verify:** `bash scripts/release_check.sh`
- **Now:** Release confidence; small fixes.

---

### SLICE 25 — IR cycle detection + DAG validation `[P2 · Correctness]`
- **Objective:** Add DFS cycle detection to `validate_graph()`.
- **Files:** `swarmgraph_ir/validation.py`
- **Dependencies:** None
- **Safety concerns:** None
- **Tests:** `test_rejects_direct_cycle`, `test_rejects_self_loop`, `test_accepts_diamond_dag`
- **Docs:** None
- **Acceptance:** Cyclic IR graph returns `ok=False` with cycle path
- **Verify:** `cd python && uv run pytest tests/swarmgraph_ir/test_validation.py -q`
- **Now:** Correctness gap; cyclic graphs currently pass validation.

---

## 3. Priority Tiers Summary

| Tier | Slices | Theme |
|---|---|---|
| **P0 (do first)** | 1–10 | Secret exposure, fail-open defaults, enforcement bypass, broken core features (MCP serve, TUI streaming, WCAG) |
| **P1 (next)** | 11–21 | Evidence visibility, backend reliability, UX coherence, dead code, parity |
| **P2 (then)** | 22–25 | Test coverage, performance, release hygiene, correctness |

---

## 4. Next 3 Best Slices (chosen)

Selection rationale per the prioritization rule (product coherence + safety + parity + evidence + release confidence, no overclaiming):

**Why these 3:**
- **SLICE 1 (Sensitive file exclusion)** — highest-severity safety gap, appears in 2 audits, zero breaking-change risk, blocks SLICE 20. Pure safety win.
- **SLICE 9 (TUI streaming fix)** — the single most user-visible product-coherence failure (streamed responses appear blank). High visibility, low risk, no provider dependency.
- **SLICE 11 (RunsTab honest evidence states)** — directly improves evidence visibility (a named prioritization criterion); turns silent failures into honest UI; pairs naturally with the auditability findings.

These three are independent, span Python+TUI+IDE (broad coverage), each is small and verifiable, and none overclaim production readiness.

---

## 5. Ready-to-Run Implementation Prompts

### Prompt A — Sensitive File Exclusion (SLICE 1)

```
# Slice: Sensitive File Exclusion in Context & Workspace Scan

## Context
ARC Studio v0.8-r-ux2. `iter_workspace_files()` in workspace.py and
LocalRepoProvider in context/providers/local_repo.py scan all workspace
files including .env, *.key, credentials.*, id_rsa. These can enter the
LLM context window and appear in `arc workspace inventory` output. The
sandbox _SECRET_READ_DENY list exists but is never consulted during scanning.

## Scope

### 1. Add exclusion constants (python/src/agent_runtime_cockpit/workspace.py)
```python
_SENSITIVE_FILENAMES = frozenset({
    ".env", ".env.local", ".env.production", ".env.staging", ".env.test",
    "id_rsa", "id_ed25519", "id_dsa", "id_ecdsa",
    ".netrc", ".npmrc", ".pypirc", ".git-credentials", ".pgpass",
})
_SENSITIVE_SUFFIXES = frozenset({".key", ".pem", ".p12", ".pfx", ".cer", ".crt"})
_SENSITIVE_SUBSTRINGS = frozenset({"credentials", "secrets"})

def _is_sensitive_file(path: Path) -> bool:
    name = path.name.lower()
    if name in _SENSITIVE_FILENAMES:
        return True
    if path.suffix.lower() in _SENSITIVE_SUFFIXES:
        return True
    if any(s in name for s in _SENSITIVE_SUBSTRINGS):
        return True
    # also skip files under a secrets/ or .secrets/ directory component
    parts = [p.lower() for p in path.parts]
    return ".secrets" in parts or "secrets" in parts
```

In iter_workspace_files(), skip files where _is_sensitive_file(path) is True.
Log a single INFO with the count (never the names).

### 2. Apply in LocalRepoProvider (context/providers/local_repo.py)
Before any read_text(), skip files matching _is_sensitive_file().
Import the helper from workspace.py (or duplicate the frozensets if circular).

### 3. Tests (python/tests/cli/test_workspace_inventory.py + tests/context/)
- test_env_file_not_in_inventory: create .env, assert absent from files.entries
- test_key_file_not_in_inventory: create id_rsa, assert absent
- test_credentials_yaml_not_in_inventory: create credentials.yaml, assert absent
- test_normal_py_file_still_in_inventory: create main.py, assert present
- test_env_file_not_in_context_pack (tests/context/): assert .env not in entries

### 4. Docs
Add a row to docs/security/enforcement-surfaces.md under a new
"Workspace Scan Sensitive-File Exclusion" surface.

## Do NOT do
- gitignore integration (separate slice)
- @file/@folder mentions
- Search result cap (SLICE 20, separate)

## Constraints (AGENTS.md)
- Exclusion must be additive only — never changes traversal of non-sensitive files
- No new dependencies
- Run: cd python && uv run pytest tests/cli/test_workspace_inventory.py tests/context/ -q
- Document failures honestly
```

---

### Prompt B — TUI Streaming Widget Refresh (SLICE 9)

```
# Slice: TUI Streaming Widget Refresh

## Context
ARC Studio v0.8-r-ux2. The TUI transcript polls DataStore.entries every
100ms and mounts new entries. But append_to_last() mutates the last
assistant entry's content in place WITHOUT refreshing the already-mounted
MarkdownBlock. Streamed tokens are invisible until the next entry is added.
DataStore.is_streaming is set correctly; the status bar shows "streaming"
but the transcript body lags.

## Scope

### 1. Add update() to MarkdownBlock (tui/widgets/markdown_block.py)
```python
def update_content(self, content: str) -> None:
    """Re-render this block with new content (used during streaming)."""
    self._content = content
    try:
        from rich.markdown import Markdown
        self.update(Markdown(content, code_theme="monokai") if content else "")
    except Exception:
        self.update(content)  # plain text fallback
```
(If MarkdownBlock already has a render path, reuse it; the key is calling
self.refresh() / self.update() with the new content.)

### 2. Refresh last block during streaming (tui/widgets/transcript.py)
In the 100ms polling method, after mounting new entries:
```python
if self.data.is_streaming and self.data.entries:
    last = self.data.entries[-1]
    if last.role == "assistant":
        try:
            blocks = list(self.query(MarkdownBlock))
            if blocks:
                blocks[-1].update_content(last.content)
        except Exception:
            pass  # never crash the poll loop
```

### 3. Tests (python/tests/tui/test_transcript_streaming.py — new)
- test_streaming_tokens_appear_in_markdown_block:
  - Create DataStore with one assistant entry, is_streaming=True
  - Call data.append_to_last(" more text")
  - Trigger the poll method
  - Assert the mounted MarkdownBlock's content includes "more text"
- test_poll_loop_never_crashes_on_streaming_error:
  - Force query() to raise; assert poll method does not propagate

## Do NOT do
- Transcript virtualization (separate slice)
- Streaming for IDE ChatTab (separate)

## Constraints (AGENTS.md)
- The refresh must be wrapped in try/except — never crash the poll loop
- No new dependencies
- Run: cd python && uv run pytest tests/tui/ -q
- Document failures honestly
```

---

### Prompt C — RunsTab Honest Evidence States (SLICE 11)

```
# Slice: RunsTab Honest Receipt/Autopsy/Contract States

## Context
ARC Studio v0.8-r-ux2. RunsTab fetches RunReceipt, FailureAutopsy, and
RunContract with `.catch(() => null)`. When the CLI fails or an artifact
is missing, the cards are silently absent — the user sees an identical
placeholder for "loading", "missing artifact", and "CLI error". This hides
evidence and undermines trust in the audit surface.

## Scope

### 1. Replace silent catch with explicit state (tabs/RunsTab.tsx)
For each of the three artifacts, track loading/error/data explicitly:
```typescript
interface ArtifactState<T> {
    loading: boolean;
    data: T | null;
    error: string | null;
}

// In the detail-load effect:
const loadReceipt = async (runId: string) => {
    setReceiptState({ loading: true, data: null, error: null });
    try {
        const receipt = await arcService.getRunReceipt(runId);
        setReceiptState({ loading: false, data: receipt, error: null });
    } catch (error) {
        setReceiptState({
            loading: false, data: null,
            error: error instanceof Error ? error.message : 'Failed to load receipt',
        });
    }
};
```

### 2. Render explicit states
```tsx
{receiptState.loading ? (
    <div className="arc-studio-assurance__loading">Loading receipt…</div>
) : receiptState.error ? (
    <div className="arc-studio-assurance__state-banner arc-studio-assurance__state-banner--warning" role="alert">
        <span className="arc-studio-assurance__state-icon">⚠</span>
        <div className="arc-studio-assurance__state-body">
            <div className="arc-studio-assurance__state-title">Receipt unavailable</div>
            <div className="arc-studio-assurance__state-detail">{receiptState.error}</div>
            <div className="arc-studio-assurance__state-detail">
                CLI: <code>arc runs budget {selectedRunId}</code>
            </div>
        </div>
    </div>
) : receiptState.data ? (
    <RunReceiptCard receipt={receiptState.data} onVerify={...} onExport={...} />
) : null}
```

Apply the same pattern to FailureAutopsy (CLI: `arc runs autopsy <id>`)
and RunContract (CLI: `arc runs contract <id>`).

### 3. Tests (studio-tabs.contract.test.ts, RunsTab section)
- "shows receipt unavailable state": assert source contains "Receipt unavailable"
  and references an error state (not bare .catch(() => null))
- "shows CLI hint in missing-artifact state": assert "arc runs budget" hint present
- "renders RunReceiptCard when data present": assert <RunReceiptCard rendered

## Do NOT do
- audit_path / signature_status rendering (separate auditability slice)
- Replay navigation (separate slice)
- EvidenceRef line-range navigation

## Constraints (AGENTS.md)
- Error banners must use role="alert"
- Must distinguish loading / error / missing / present — four states
- Run: pnpm typecheck && pnpm --filter arc-extension test
- Document failures honestly
```

---

## Appendix: Dependency Graph for Top Slices

```
SLICE 1 (sensitive exclusion) ──┬──> SLICE 20 (search cap)
                                 └──> (independent)
SLICE 2 (paid-call default) ─────────> (independent, standalone)
SLICE 3 (map_error redaction) ───────> (independent)
SLICE 4 (MCP resource gate) ─────────> (independent)
SLICE 5 (proxy env) ──────────────────> SLICE 16 (proxy timeout)
SLICE 6 (run ID traversal) ──────────> (independent)
SLICE 7 (notif env) ─────────────────> (independent)
SLICE 8 (mcp serve stdout) ──────────> (independent)
SLICE 9 (TUI streaming) ─────────────> (independent, standalone)
SLICE 10 (risk badge) ───────────────> SLICE 22 (axe tests)
SLICE 13 (status rail) ──────────────> SLICE 22 (axe tests)
SLICE 18 (event bridge) ─────────────> (unblocks SwarmGraph IDE panels)
```

Slices 1–10 are almost entirely independent and can be done in parallel.
Slices 22 depends on 10+13. Slice 20 depends on 1. Slice 16 pairs with 5.
