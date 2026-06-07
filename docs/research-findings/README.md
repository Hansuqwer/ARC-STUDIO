# ARC Studio Audit Findings — 2026-06-07

> Six deep-research sessions run with 12 parallel sub-agents each.  
> All findings are read-only analysis. No production code was changed.

---

## Files

| File | Domain | Top issues |
|---|---|---|
| [unified-implementation-backlog-2026-06-07.md](./unified-implementation-backlog-2026-06-07.md) | **SYNTHESIS** — feature coverage matrix, top 25 prioritized slices, next-3 ready-to-run prompts | Consolidates all 17 audits below into one prioritized backlog |
| [swarmgraph-audit-2026-06-07.md](./swarmgraph-audit-2026-06-07.md) | SwarmGraph runtime, CLI, IDE, events, consensus, DAG, evals | SDK events never reach IDE; two disconnected runners; IDE components orphaned |
| [memory-context-session-audit-2026-06-07.md](./memory-context-session-audit-2026-06-07.md) | AGENTS.md, SKILL.md, session, compaction, memory graph, context injection | AGENTS.md content invisible to agents; `.env` not excluded from context; IDE ChatTab is ephemeral stub |
| [workspace-intelligence-audit-2026-06-07.md](./workspace-intelligence-audit-2026-06-07.md) | Workspace inventory, code search, symbols, testbench, IDE search | `.env` in inventory; no result cap on search; ContextPackEntry has no line_number |
| [mcp-audit-2026-06-07.md](./mcp-audit-2026-06-07.md) | MCP workbench, risk scoring, proxy, policy, audit, IDE | Resources bypass risk gate; proxy env=None leaks secrets; `arc mcp serve` corrupts stdio |
| [provider-model-budget-audit-2026-06-07.md](./provider-model-budget-audit-2026-06-07.md) | Providers, model catalog, routing, paid-call gates, budget, wallet, cost events | TUI paid-call defaults to True; `_map_error()` unredacted; ProviderRouter is dead code |
| [cli-audit-2026-06-07.md](./cli-audit-2026-06-07.md) | CLI structure, help UX, JSON envelope compliance, safety gates, install story, parity | Run ID path traversal; a2a/flight/events non-compliant JSON; `arc policy rule-add` unprotected; `arc wallet` missing from CLI |
| [tui-audit-2026-06-07.md](./tui-audit-2026-06-07.md) | TUI widgets, slash commands, theming, keyboard nav, shell escape, transcript, diff, cards, parity | Streaming broken at widget layer; CommandPalette empty on first open; SettingsView missing 4 themes; HelpScreen missing 12 features |
| [theia-ide-audit-2026-06-07.md](./theia-ide-audit-2026-06-07.md) | Theia IDE architecture, widgets, protocol, services, commands, keybindings, layout, backend safety | Ctrl+E/H/Shift+S conflict with Theia defaults; ArcRunTimelineWidget dead code; NotificationBackendService no env allowlist; 72-method god interface |
| [ux-audit-2026-06-07.md](./ux-audit-2026-06-07.md) | UX audit (IDE + TUI), IA proposal, design system, component inventory, copy, accessibility, implementation prompt | 12-tab flat nav; streaming broken; critical=high same badge; accessibility tests are no-ops; ChatTab transcript ephemeral |
| [security-audit-2026-06-07.md](./security-audit-2026-06-07.md) | Security architecture, enforcement surfaces, claim review, IDE assurance gaps, test gaps, hardening prompt | MCP resources bypass D-02 gate; McpProxy env=None; run ID path traversal; TUI paid-call default True; _map_error() unredacted |
| [runs-events-streaming-audit-2026-06-07.md](./runs-events-streaming-audit-2026-06-07.md) | Runs, traces, events, streaming, SSE transport, receipts, active run, cancellation, failure autopsy | startRun() blocks Node 120s; liveEvents array unbounded; ChatTab has no run link; MESSAGE schema mismatch; ArcRunTimelineWidget dead code |
| [auditability-audit-2026-06-07.md](./auditability-audit-2026-06-07.md) | RunContract, RunReceipt, EvidenceRef, FailureAutopsy, audit chains, keyed audit, replay, fork, diff, undo/redo, review provenance | Receipts silently absent (.catch null); audit_path not rendered; no replay navigation; fork doesn't use transaction journal; undo/redo CLI-only |
| [ci-quality-gates-audit-2026-06-07.md](./ci-quality-gates-audit-2026-06-07.md) | CI guardrails, TestBench, evals, private mode, policy verification, audit verification, release quality gates | TestBenchTab has no Run button; CiGuardrailsTab doesn't show advisory label; all checks advisory not blocking; denied_commands not shown in IDE |
| [notifications-dag-planner-audit-2026-06-07.md](./notifications-dag-planner-audit-2026-06-07.md) | Notifications, managed service, push hooks, offline retry, DAG planner, orchestration UI | NotificationBackendService no env allowlist; protocol:"sse" hardcoded lie; EventBrokerNotificationHook broken; IR no cycle detection; DagPlannerViz orphaned stub |
| [config-settings-profiles-audit-2026-06-07.md](./config-settings-profiles-audit-2026-06-07.md) | Config architecture, profile schema, workspace trust, safe-save, runtime/isolation/provider settings, CLI/TUI/IDE parity | Profile schema v1 loaded without migration; TUI SettingsView theme/mode not persisted on Apply; saveConfig execFileSync blocks Node; 3 ConfigService methods have no try/catch |
| [release-packaging-audit-2026-06-07.md](./release-packaging-audit-2026-06-07.md) | Release architecture, install story, packaging, signing/electron, npm/pipx/PyPI/Homebrew, artifacts, licenses, release checklist | arch-studio-cli entrypoint typo; Apache-2.0 vs Proprietary license mismatch; no prod build in CI gate; bootstrap.sh defeats --frozen-lockfile; swarmgraph-sdk blocks pip install |
| [accessibility-performance-reliability-audit-2026-06-07.md](./accessibility-performance-reliability-audit-2026-06-07.md) | Accessibility (WCAG 2.1 AA), keyboard nav, reduced motion, high contrast, large trace perf, event buffers, async cancellation, degraded states, error boundaries | critical=high same color (WCAG 1.4.1); no React ErrorBoundary; liveEvents unbounded; TUI streaming broken; axe tests are no-ops |

---

## Cross-cutting P0 security items

These appear across multiple audits and should be prioritised first:

| Item | Files affected | Severity |
|---|---|---|
| `.env`/`*.key` files not excluded from context injection and workspace scan | `LocalRepoProvider`, `iter_workspace_files` | **HIGH** |
| TUI `allow_paid_calls` defaults to `True` (should be `False`) | `tui/screen.py` line 368 | **HIGH** |
| `_map_error()` has no redaction in Anthropic + OpenAI-compatible clients | `providers/anthropic.py`, `providers/openai_compatible.py` | **HIGH** |
| MCP resources bypass risk gate and audit entirely | `mcp/server.py` | **HIGH** |
| `McpProxy` with `env=None` inherits full `os.environ` including API keys | `mcp/proxy.py` | **HIGH** |
| `arc mcp serve` prints Rich markup to stdout, corrupting MCP stdio framing | `cli/mcp.py` | **HIGH** |
| SwarmGraph SDK events never reach the IDE (EventBrokerNotificationHook broken) | `mcp/proxy.py`, `swarmgraph/notifications.py` | **HIGH** |
| `workspace inventory` and `workspace search` have no trust gate | `cli/studio_workspace.py` | **HIGH** |
| Run IDs not sanitized before path construction — path traversal possible | `storage/jsonl.py`, all `arc runs *` commands | **HIGH** |
| `arc policy rule-add/remove` and `arc sandbox audit-compact` have no confirmation gate | `cli/capabilities_policy.py`, `cli/sandbox.py` | **HIGH** |
| TUI streaming broken at widget layer — `append_to_last()` mutates DataStore but `MarkdownBlock` not refreshed | `tui/widgets/transcript.py` | **HIGH** |
| TUI shell escape stdout not redacted — `cat ~/.aws/credentials` output shown in plain text | `tui/screen.py::_handle_shell_escape` | **HIGH** |
| Theia `NotificationBackendService` passes full `process.env` (with API keys) to child process — no env allowlist | `packages/arc-extension/src/node/services/notification-service.ts` | **HIGH** |
| Theia keybindings `Ctrl+E`, `Ctrl+Shift+S`, `Ctrl+H` conflict with Go to File / Save All / Find & Replace | `packages/arc-extension/src/browser/arc-keybinding-contribution.ts` | **HIGH** |
| Theia `ArcRunTimelineWidget` has no contribution file — dead code, unreachable by users | `packages/arc-extension/src/browser/arc-run-timeline-widget.tsx` | **HIGH** |

---

## Next recommended implementation slices (in priority order)

1. **Sensitive file exclusion** — add `_SENSITIVE_FILENAMES`/`_SENSITIVE_SUFFIXES` to `iter_workspace_files()` and `LocalRepoProvider`
2. **TUI paid-call gate fix** — `getattr(self.data, "allow_paid", False)` (not `True`)
3. **`_map_error()` redaction** — apply `Redactor` to `str(exc)` in both provider clients
4. **MCP resource risk gate** — route resource handlers through `_tool_result()`
5. **MCP proxy env fix** — always sanitise env, never pass `None` to subprocess
6. **`arc mcp serve` stdout fix** — redirect pre-start console output to stderr
7. **SwarmGraph event bridge** — `translate_swarmgraph_event()` wired into `_run_native_workflow()`
8. **`arc wallet` CLI command** — fix README documentation mismatch
9. **ContextPackEntry `line_number` field** — enable IDE navigation from context results
10. **Search result cap** — `MAX_SEARCH_RESULTS = 200` in `workspace_search()`
11. **TUI streaming fix** — `MarkdownBlock.update()` called from polling loop during streaming
12. **McpWorkbenchTab risk badge** — `critical` → danger (red), `high` → warning (amber); add `aria-label`
13. **IDE status rail** — persistent top rail showing mode/trust/model/daemon
14. **Theia keybinding fix** — replace Ctrl+E/H/Shift+S with non-conflicting bindings + `when` guards
15. **HelpScreen auto-generate** — derive from slash command registry at mount time
